from __future__ import annotations

from datetime import date, datetime, timedelta
import csv
import io
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Iterable

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlalchemy import or_, func

from app.database import get_session, init_db
from app.importers import import_contacts_csv, import_municipalities_csv
from app.models import (
    ConfidenceScore,
    Contact,
    DncEntry,
    FollowUp,
    ImportLog,
    LeadSuggestion,
    LeadSuggestionStatus,
    OutreachChannel,
    OutreachDraft,
    OutreachDraftStatus,
    OutreachEvent,
    OutreachOutcome,
    Target,
    TargetStatus,
    TargetType,
)

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "templates"
OUTREACH_TEMPLATE_DIR = TEMPLATE_DIR / "outreach"

app = FastAPI(title="Outreach CRM")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


@app.on_event("startup")
def on_startup() -> None:
    init_db()


class SafeDict(dict):
    def __missing__(self, key: str) -> str:  # pragma: no cover - defensive
        return ""


def load_outreach_templates() -> list[dict[str, str]]:
    template_files = sorted(OUTREACH_TEMPLATE_DIR.glob("*.txt"))
    templates_data = []
    for path in template_files:
        templates_data.append({"name": path.stem, "filename": path.name})
    return templates_data


def render_template_text(filename: str, context: dict[str, Any]) -> tuple[str, str]:
    path = OUTREACH_TEMPLATE_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    content = path.read_text(encoding="utf-8")
    rendered = content.format_map(SafeDict(context))
    lines = rendered.splitlines()
    subject = ""
    body_lines = lines
    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        body_lines = lines[1:]
    body = "\n".join(body_lines).strip()
    return subject, body


def template_context(target: Target, contact: Contact | None, extras: dict[str, str]) -> dict[str, Any]:
    return {
        "target_name": target.name,
        "contact_name": contact.full_name if contact else "",
        "role": contact.role if contact else "",
        "province": target.province or "",
        "value_prop": extras.get("value_prop", ""),
        "case_study_url": extras.get("case_study_url", ""),
        "cta": extras.get("cta", ""),
        "municipality_case_study_url": os.getenv("CASE_STUDY_URL", ""),
    }


def get_keywords() -> list[str]:
    keywords = os.getenv(
        "LEAD_KEYWORDS",
        "digital twin,GIS,smart city,data,sensors,asset management,innovation",
    )
    return [item.strip() for item in keywords.split(",") if item.strip()]


def score_lead(target: Target, contacts: list[Contact]) -> tuple[int, dict[str, Any], list[str]]:
    tags: list[str] = []
    breakdown: dict[str, Any] = {}
    score = 0
    text_blob = " ".join(
        [
            target.name,
            target.sector or "",
            target.province or "",
            target.notes or "",
        ]
    ).lower()
    keyword_hits = [kw for kw in get_keywords() if kw.lower() in text_blob]
    if keyword_hits:
        score += 10 * len(keyword_hits)
        tags.extend(keyword_hits)
        breakdown["keyword_hits"] = keyword_hits

    role_keywords = ["digital", "data", "innovation", "smart", "technology", "gis"]
    role_hits = [
        contact.role
        for contact in contacts
        if contact.role and any(k in contact.role.lower() for k in role_keywords)
    ]
    if role_hits:
        score += 15
        breakdown["role_hits"] = role_hits

    if contacts:
        score += 5
        breakdown["contacts_present"] = len(contacts)
    else:
        score -= 5
        breakdown["missing_contacts"] = True

    email_contacts = [c for c in contacts if c.email]
    if email_contacts:
        score += 10
        breakdown["email_contacts"] = len(email_contacts)
    else:
        score -= 10
        breakdown["missing_email"] = True

    generic_only = target.general_email and not email_contacts
    if generic_only:
        score -= 5
        breakdown["generic_only"] = True

    return max(score, 0), breakdown, tags


def lead_candidate_data(target: Target, contacts: list[Contact]) -> dict[str, Any]:
    return {
        "target_id": target.id,
        "name": target.name,
        "type": target.type.value,
        "province": target.province,
        "website": target.website,
        "general_email": target.general_email,
        "phone": target.phone,
        "contacts": [
            {
                "full_name": contact.full_name,
                "role": contact.role,
                "email": contact.email,
                "phone": contact.phone,
                "linkedin_url": contact.linkedin_url,
            }
            for contact in contacts
        ],
    }


def check_dnc(target: Target, contact: Contact | None) -> list[str]:
    warnings: list[str] = []
    if target.do_not_contact:
        warnings.append("Target is marked do-not-contact.")
    if contact and contact.do_not_contact:
        warnings.append("Contact is marked do-not-contact.")
    values = {target.general_email, contact.email if contact else None}
    values = {value for value in values if value}
    if values:
        with get_session() as session:
            blocked = session.exec(select(DncEntry.value)).all()
        blocked_values = {item for (item,) in blocked}
        if any(value in blocked_values for value in values):
            warnings.append("Email matches global do-not-contact list.")
    return warnings


def draft_warnings(target: Target, contact: Contact | None, extras: dict[str, str]) -> list[str]:
    warnings = []
    if not extras.get("case_study_url"):
        warnings.append("Missing case study URL.")
    if not extras.get("value_prop"):
        warnings.append("Missing value proposition.")
    if contact and not contact.email and target.general_email:
        warnings.append("Only a generic inbox is available.")
    daily_limit = int(os.getenv("DAILY_SEND_LIMIT", "20"))
    with get_session() as session:
        queued_count = session.exec(
            select(func.count(OutreachDraft.id)).where(
                OutreachDraft.status.in_([OutreachDraftStatus.queued, OutreachDraftStatus.approved])
            )
        ).one()
    if queued_count >= daily_limit:
        warnings.append("Too many emails queued for today.")
    warnings.extend(check_dnc(target, contact))
    return warnings


def send_email(subject: str, body: str, recipient: str) -> str:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_SENDER", user or "")
    if not host or not sender or not recipient:
        raise ValueError("SMTP configuration incomplete.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)

    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        if user and password:
            smtp.login(user, password)
        smtp.send_message(message)
    return "sent"


@app.get("/", response_class=HTMLResponse)
def root() -> RedirectResponse:
    return RedirectResponse(url="/targets")


@app.get("/targets", response_class=HTMLResponse)
def list_targets(
    request: Request,
    target_type: str | None = None,
    status: str | None = None,
    search: str | None = None,
    message: str | None = None,
) -> HTMLResponse:
    with get_session() as session:
        statement = select(Target)
        if target_type:
            try:
                statement = statement.where(Target.type == TargetType(target_type))
            except ValueError:
                target_type = None
        if status:
            try:
                statement = statement.where(Target.status == TargetStatus(status))
            except ValueError:
                status = None
        if search:
            like_term = f"%{search}%"
            statement = statement.where(
                or_(
                    Target.name.ilike(like_term),
                    Target.sector.ilike(like_term),
                    Target.province.ilike(like_term),
                )
            )
        targets = session.exec(statement.order_by(Target.created_at.desc())).all()

        pipeline = (
            session.exec(
                select(Target.status, func.count(Target.id)).group_by(Target.status)
            ).all()
        )
        pipeline_counts = {status: count for status, count in pipeline}

    return templates.TemplateResponse(
        "targets_list.html",
        {
            "request": request,
            "targets": targets,
            "pipeline_counts": pipeline_counts,
            "message": message,
            "filters": {"type": target_type, "status": status, "search": search},
            "target_types": list(TargetType),
            "target_statuses": list(TargetStatus),
        },
    )


@app.post("/targets")
def create_target(
    name: str = Form(...),
    type: TargetType = Form(...),
    sector: str | None = Form(None),
    province: str | None = Form(None),
    website: str | None = Form(None),
    general_email: str | None = Form(None),
    phone: str | None = Form(None),
    notes: str | None = Form(None),
    source: str | None = Form(None),
    do_not_contact: bool = Form(False),
) -> RedirectResponse:
    with get_session() as session:
        target = Target(
            name=name,
            type=type,
            sector=sector,
            province=province,
            website=website,
            general_email=general_email,
            phone=phone,
            notes=notes,
            source=source,
            do_not_contact=do_not_contact,
            updated_at=datetime.utcnow(),
        )
        session.add(target)
        session.commit()
    return RedirectResponse(url="/targets?message=Target%20created", status_code=303)


@app.get("/targets/{target_id}", response_class=HTMLResponse)
def target_detail(request: Request, target_id: int) -> HTMLResponse:
    with get_session() as session:
        target = session.get(Target, target_id)
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")
        contacts = session.exec(
            select(Contact).where(Contact.target_id == target_id)
        ).all()
        events = session.exec(
            select(OutreachEvent)
            .where(OutreachEvent.target_id == target_id)
            .options(selectinload(OutreachEvent.contact))
            .order_by(OutreachEvent.occurred_at.desc())
        ).all()
        followups = session.exec(
            select(FollowUp)
            .where(FollowUp.target_id == target_id)
            .order_by(FollowUp.due_date)
        ).all()
        last_event = events[0] if events else None
        followup_days = int(os.getenv("FOLLOW_UP_DAYS", "7"))
        suggested_followup = None
        if last_event and last_event.outcome == OutreachOutcome.no_reply:
            suggested_followup = last_event.occurred_at.date() + timedelta(days=followup_days)
    return templates.TemplateResponse(
        "target_detail.html",
        {
            "request": request,
            "target": target,
            "contacts": contacts,
            "events": events,
            "followups": followups,
            "suggested_followup": suggested_followup,
            "target_statuses": list(TargetStatus),
        },
    )


@app.post("/targets/{target_id}/status")
def update_target_status(
    target_id: int,
    status: TargetStatus = Form(...),
) -> RedirectResponse:
    with get_session() as session:
        target = session.get(Target, target_id)
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")
        target.status = status
        target.updated_at = datetime.utcnow()
        session.add(target)
        session.commit()
    return RedirectResponse(url=f"/targets/{target_id}", status_code=303)


@app.post("/targets/{target_id}/contacts")
def add_contact(
    target_id: int,
    full_name: str = Form(...),
    role: str | None = Form(None),
    email: str | None = Form(None),
    phone: str | None = Form(None),
    linkedin_url: str | None = Form(None),
    confidence_score: ConfidenceScore = Form(ConfidenceScore.low),
    do_not_contact: bool = Form(False),
) -> RedirectResponse:
    with get_session() as session:
        if not session.get(Target, target_id):
            raise HTTPException(status_code=404, detail="Target not found")
        contact = Contact(
            target_id=target_id,
            full_name=full_name,
            role=role,
            email=email,
            phone=phone,
            linkedin_url=linkedin_url,
            confidence_score=confidence_score,
            do_not_contact=do_not_contact,
            updated_at=datetime.utcnow(),
        )
        session.add(contact)
        session.commit()
    return RedirectResponse(url=f"/targets/{target_id}", status_code=303)


@app.post("/targets/{target_id}/followups")
def add_followup(
    target_id: int,
    due_date: date = Form(...),
    reason: str | None = Form(None),
) -> RedirectResponse:
    with get_session() as session:
        if not session.get(Target, target_id):
            raise HTTPException(status_code=404, detail="Target not found")
        followup = FollowUp(target_id=target_id, due_date=due_date, reason=reason)
        session.add(followup)
        session.commit()
    return RedirectResponse(url=f"/targets/{target_id}", status_code=303)


@app.post("/followups/{followup_id}/done")
def mark_followup_done(followup_id: int) -> RedirectResponse:
    with get_session() as session:
        followup = session.get(FollowUp, followup_id)
        if not followup:
            raise HTTPException(status_code=404, detail="Follow-up not found")
        followup.done = True
        session.add(followup)
        session.commit()
    return RedirectResponse(url=f"/targets/{followup.target_id}", status_code=303)


@app.post("/events/{event_id}/outcome")
def update_outcome(event_id: int, outcome: OutreachOutcome = Form(...)) -> RedirectResponse:
    with get_session() as session:
        event = session.get(OutreachEvent, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        event.outcome = outcome
        if outcome != OutreachOutcome.no_reply:
            event.responded_at = datetime.utcnow()
        session.add(event)
        session.commit()
    return RedirectResponse(url=f"/targets/{event.target_id}", status_code=303)


@app.get("/outreach/new", response_class=HTMLResponse)
def outreach_form(
    request: Request, target_id: int, contact_id: int | None = None
) -> HTMLResponse:
    return draft_form(request=request, target_id=target_id, contact_id=contact_id)


@app.get("/drafts", response_class=HTMLResponse)
def list_drafts(request: Request) -> HTMLResponse:
    with get_session() as session:
        drafts = session.exec(
            select(OutreachDraft)
            .options(selectinload(OutreachDraft.target), selectinload(OutreachDraft.contact))
            .order_by(OutreachDraft.created_at.desc())
        ).all()
    return templates.TemplateResponse(
        "drafts_list.html",
        {"request": request, "drafts": drafts, "statuses": list(OutreachDraftStatus)},
    )


@app.get("/drafts/new", response_class=HTMLResponse)
def draft_form(
    request: Request, target_id: int, contact_id: int | None = None
) -> HTMLResponse:
    with get_session() as session:
        target = session.get(Target, target_id)
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")
        contacts = session.exec(select(Contact).where(Contact.target_id == target_id)).all()

    return templates.TemplateResponse(
        "draft_form.html",
        {
            "request": request,
            "target": target,
            "contacts": contacts,
            "selected_contact_id": contact_id,
            "templates": load_outreach_templates(),
            "channels": list(OutreachChannel),
            "preview_mode": os.getenv("PREVIEW_MODE", "true").lower() == "true",
        },
    )


@app.post("/drafts")
def create_draft(
    target_id: int = Form(...),
    contact_id: int | None = Form(None),
    template_name: str = Form(...),
    channel: OutreachChannel = Form(...),
    subject: str | None = Form(None),
    value_prop: str | None = Form(None),
    case_study_url: str | None = Form(None),
    cta: str | None = Form(None),
    custom_body: str | None = Form(None),
) -> RedirectResponse:
    with get_session() as session:
        target = session.get(Target, target_id)
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")
        contact = session.get(Contact, contact_id) if contact_id else None
        template_filename = f"{template_name}.txt"
        extras = {
            "value_prop": value_prop or "",
            "case_study_url": case_study_url or "",
            "cta": cta or "",
        }
        context = template_context(target, contact, extras)
        rendered_subject, rendered_body = render_template_text(template_filename, context)
        edited_body = custom_body.strip() if custom_body else None
        edited_subject = subject.strip() if subject else None
        final_subject = edited_subject or rendered_subject
        final_body = edited_body or rendered_body
        missing_fields = draft_warnings(target, contact, extras)
        draft = OutreachDraft(
            target_id=target_id,
            contact_id=contact_id,
            template_id=template_name,
            channel=channel,
            rendered_subject=rendered_subject,
            rendered_body=rendered_body,
            edited_subject=edited_subject,
            edited_body=edited_body,
            final_subject=final_subject,
            final_body=final_body,
            status=OutreachDraftStatus.draft,
            missing_fields=missing_fields,
            updated_at=datetime.utcnow(),
        )
        session.add(draft)
        session.commit()
        session.refresh(draft)
    return RedirectResponse(url=f"/drafts/{draft.id}", status_code=303)


@app.post("/outreach")
def legacy_create_outreach() -> RedirectResponse:
    raise HTTPException(status_code=410, detail="Use /drafts to create outreach drafts.")


@app.get("/drafts/{draft_id}", response_class=HTMLResponse)
def draft_detail(request: Request, draft_id: int) -> HTMLResponse:
    with get_session() as session:
        draft = session.exec(
            select(OutreachDraft)
            .where(OutreachDraft.id == draft_id)
            .options(selectinload(OutreachDraft.target), selectinload(OutreachDraft.contact))
        ).first()
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
    return templates.TemplateResponse(
        "draft_detail.html",
        {
            "request": request,
            "draft": draft,
            "preview_mode": os.getenv("PREVIEW_MODE", "true").lower() == "true",
        },
    )


@app.post("/drafts/{draft_id}/approve")
def approve_draft(draft_id: int, approved_by: str = Form(...)) -> RedirectResponse:
    with get_session() as session:
        draft = session.get(OutreachDraft, draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        draft.status = OutreachDraftStatus.approved
        draft.approved_by = approved_by
        draft.approved_at = datetime.utcnow()
        draft.updated_at = datetime.utcnow()
        session.add(draft)
        session.commit()
    return RedirectResponse(url=f"/drafts/{draft_id}", status_code=303)


@app.post("/drafts/{draft_id}/queue")
def queue_draft(draft_id: int) -> RedirectResponse:
    with get_session() as session:
        draft = session.get(OutreachDraft, draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        if draft.status != OutreachDraftStatus.draft:
            raise HTTPException(status_code=400, detail="Only drafts can be queued")
        draft.status = OutreachDraftStatus.queued
        draft.updated_at = datetime.utcnow()
        session.add(draft)
        session.commit()
    return RedirectResponse(url=f"/drafts/{draft_id}", status_code=303)


@app.post("/drafts/{draft_id}/send")
def send_draft(draft_id: int) -> RedirectResponse:
    preview_mode = os.getenv("PREVIEW_MODE", "true").lower() == "true"
    daily_limit = int(os.getenv("DAILY_SEND_LIMIT", "20"))
    with get_session() as session:
        draft = session.get(OutreachDraft, draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        if draft.status != OutreachDraftStatus.approved:
            raise HTTPException(status_code=400, detail="Draft must be approved before sending")
        target = session.get(Target, draft.target_id)
        contact = session.get(Contact, draft.contact_id) if draft.contact_id else None
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")

        warnings = check_dnc(target, contact)
        if warnings:
            draft.status = OutreachDraftStatus.failed
            draft.send_error = " ".join(warnings)
            draft.updated_at = datetime.utcnow()
            session.add(draft)
            session.commit()
            raise HTTPException(status_code=400, detail=draft.send_error)

        today = datetime.utcnow().date()
        sent_count = session.exec(
            select(func.count(OutreachEvent.id)).where(
                OutreachEvent.occurred_at >= datetime.combine(today, datetime.min.time())
            )
        ).one()
        if sent_count >= daily_limit:
            raise HTTPException(status_code=400, detail="Daily send limit reached")

        recipient = (contact.email if contact and contact.email else target.general_email) or ""
        message_id = "preview"
        send_error = None
        if draft.channel == OutreachChannel.email:
            if not recipient:
                raise HTTPException(status_code=400, detail="No recipient email available")
            if not preview_mode:
                try:
                    message_id = send_email(
                        draft.final_subject or "", draft.final_body or "", recipient
                    )
                except Exception as exc:  # pragma: no cover - SMTP errors
                    send_error = str(exc)

        outcome = OutreachOutcome.no_reply
        event = OutreachEvent(
            target_id=target.id,
            contact_id=contact.id if contact else None,
            channel=draft.channel,
            template_id=draft.template_id,
            subject=draft.final_subject,
            body=draft.final_body or "",
            outcome=outcome,
            occurred_at=datetime.utcnow(),
        )
        session.add(event)

        if send_error:
            draft.status = OutreachDraftStatus.failed
            draft.send_error = send_error
        else:
            draft.status = OutreachDraftStatus.sent
            draft.sent_at = datetime.utcnow()
            draft.message_id = message_id
            if target.status == TargetStatus.new:
                target.status = TargetStatus.contacted
                target.updated_at = datetime.utcnow()
                session.add(target)
        draft.updated_at = datetime.utcnow()
        session.add(draft)
        session.commit()
    return RedirectResponse(url=f"/drafts/{draft_id}", status_code=303)


@app.get("/imports", response_class=HTMLResponse)
def imports_page(request: Request, message: str | None = None) -> HTMLResponse:
    with get_session() as session:
        logs = session.exec(select(ImportLog).order_by(ImportLog.created_at.desc())).all()
    return templates.TemplateResponse(
        "imports.html",
        {"request": request, "logs": logs, "message": message},
    )


@app.post("/import/municipalities")
def import_municipalities(file: UploadFile = File(...)) -> RedirectResponse:
    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    summary = import_municipalities_csv(reader)
    return RedirectResponse(
        url=(
            f"/imports?message=Imported%20{summary.inserted}%20municipalities"
            f"%20(updated%20{summary.updated})"
        ),
        status_code=303,
    )


@app.post("/import/contacts")
def import_contacts(file: UploadFile = File(...)) -> RedirectResponse:
    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    summary = import_contacts_csv(reader)
    return RedirectResponse(
        url=(
            f"/imports?message=Imported%20{summary.inserted}%20contacts"
            f"%20(updated%20{summary.updated})"
        ),
        status_code=303,
    )


@app.get("/leads", response_class=HTMLResponse)
def list_leads(
    request: Request, status: LeadSuggestionStatus | None = None
) -> HTMLResponse:
    with get_session() as session:
        statement = select(LeadSuggestion).order_by(LeadSuggestion.created_at.desc())
        if status:
            statement = statement.where(LeadSuggestion.status == status)
        leads = session.exec(statement).all()
    return templates.TemplateResponse(
        "leads.html",
        {
            "request": request,
            "leads": leads,
            "statuses": list(LeadSuggestionStatus),
            "selected_status": status.value if status else "",
        },
    )


@app.post("/leads/generate")
def generate_leads() -> RedirectResponse:
    with get_session() as session:
        existing = session.exec(select(LeadSuggestion)).all()
        existing_target_ids = {
            lead.candidate_target_data.get("target_id") for lead in existing
        }
        targets = session.exec(select(Target)).all()
        for target in targets:
            if target.do_not_contact:
                continue
            if target.id in existing_target_ids:
                continue
            contacts = session.exec(select(Contact).where(Contact.target_id == target.id)).all()
            score, breakdown, tags = score_lead(target, contacts)
            suggestion = LeadSuggestion(
                candidate_target_data=lead_candidate_data(target, contacts),
                relevance_tags=tags,
                score=score,
                score_breakdown=breakdown,
                evidence_links=[link for link in [target.website] if link],
            )
            session.add(suggestion)
        session.commit()
    return RedirectResponse(url="/leads", status_code=303)


@app.post("/leads/{lead_id}/accept")
def accept_lead(lead_id: int) -> RedirectResponse:
    with get_session() as session:
        lead = session.get(LeadSuggestion, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        lead.status = LeadSuggestionStatus.accepted
        candidate = lead.candidate_target_data
        target_id = candidate.get("target_id")
        if target_id:
            target = session.get(Target, target_id)
            if target and target.status == TargetStatus.new:
                target.status = TargetStatus.contacted
                target.updated_at = datetime.utcnow()
                session.add(target)
            if target:
                for contact_data in candidate.get("contacts", []):
                    full_name = contact_data.get("full_name")
                    email = contact_data.get("email")
                    if not full_name and not email:
                        continue
                    existing = None
                    if email:
                        existing = session.exec(
                            select(Contact).where(
                                Contact.target_id == target.id,
                                Contact.email == email,
                            )
                        ).first()
                    if not existing and full_name:
                        existing = session.exec(
                            select(Contact).where(
                                Contact.target_id == target.id,
                                Contact.full_name == full_name,
                            )
                        ).first()
                    if existing:
                        continue
                    contact = Contact(
                        target_id=target.id,
                        full_name=full_name or email or "Unknown",
                        role=contact_data.get("role"),
                        email=email,
                        phone=contact_data.get("phone"),
                        linkedin_url=contact_data.get("linkedin_url"),
                        confidence_score=ConfidenceScore.medium if email else ConfidenceScore.low,
                        updated_at=datetime.utcnow(),
                    )
                    session.add(contact)
        session.add(lead)
        session.commit()
    return RedirectResponse(url="/leads", status_code=303)


@app.post("/leads/{lead_id}/reject")
def reject_lead(lead_id: int, reason: str = Form(...)) -> RedirectResponse:
    with get_session() as session:
        lead = session.get(LeadSuggestion, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        lead.status = LeadSuggestionStatus.rejected
        lead.rejection_reason = reason
        session.add(lead)
        session.commit()
    return RedirectResponse(url="/leads", status_code=303)


@app.get("/dnc", response_class=HTMLResponse)
def dnc_page(request: Request) -> HTMLResponse:
    with get_session() as session:
        entries = session.exec(select(DncEntry).order_by(DncEntry.created_at.desc())).all()
    return templates.TemplateResponse(
        "dnc.html",
        {"request": request, "entries": entries},
    )


@app.post("/dnc")
def add_dnc_entry(value: str = Form(...), reason: str | None = Form(None)) -> RedirectResponse:
    with get_session() as session:
        session.add(DncEntry(value=value, reason=reason))
        session.commit()
    return RedirectResponse(url="/dnc", status_code=303)


@app.get("/metrics", response_class=HTMLResponse)
def metrics_page(request: Request) -> HTMLResponse:
    with get_session() as session:
        events = session.exec(
            select(OutreachEvent).options(selectinload(OutreachEvent.contact))
        ).all()
        drafts = session.exec(select(OutreachDraft)).all()

    totals_by_template: dict[str, dict[str, int]] = {}
    totals_by_confidence: dict[str, dict[str, int]] = {}
    reply_outcomes = {OutreachOutcome.reply, OutreachOutcome.meeting_set, OutreachOutcome.redirected}
    meeting_count = 0
    responded_deltas = []

    for event in events:
        template = event.template_id or "unknown"
        totals_by_template.setdefault(template, {"total": 0, "replies": 0})
        totals_by_template[template]["total"] += 1
        if event.outcome in reply_outcomes:
            totals_by_template[template]["replies"] += 1

        if event.contact and event.contact.confidence_score:
            key = event.contact.confidence_score.value
            totals_by_confidence.setdefault(key, {"total": 0, "replies": 0})
            totals_by_confidence[key]["total"] += 1
            if event.outcome in reply_outcomes:
                totals_by_confidence[key]["replies"] += 1

        if event.outcome == OutreachOutcome.meeting_set:
            meeting_count += 1

        if event.responded_at:
            responded_deltas.append((event.responded_at - event.occurred_at).days)

    avg_time_to_reply = (
        round(sum(responded_deltas) / len(responded_deltas), 2) if responded_deltas else None
    )
    conversion_rate = round((meeting_count / len(events)) * 100, 2) if events else 0

    return templates.TemplateResponse(
        "metrics.html",
        {
            "request": request,
            "totals_by_template": totals_by_template,
            "totals_by_confidence": totals_by_confidence,
            "avg_time_to_reply": avg_time_to_reply,
            "conversion_rate": conversion_rate,
            "draft_count": len(drafts),
        },
    )


@app.get("/export/targets")
def export_targets() -> StreamingResponse:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "name",
            "type",
            "sector",
            "province",
            "website",
            "general_email",
            "phone",
            "status",
            "last_contacted",
        ]
    )
    with get_session() as session:
        targets = session.exec(select(Target)).all()
        for target in targets:
            last_contacted = session.exec(
                select(func.max(OutreachEvent.occurred_at)).where(
                    OutreachEvent.target_id == target.id
                )
            ).one()
            writer.writerow(
                [
                    target.id,
                    target.name,
                    target.type.value,
                    target.sector or "",
                    target.province or "",
                    target.website or "",
                    target.general_email or "",
                    target.phone or "",
                    target.status.value,
                    last_contacted.isoformat() if last_contacted else "",
                ]
            )
    output.seek(0)
    headers = {"Content-Disposition": "attachment; filename=targets_export.csv"}
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
