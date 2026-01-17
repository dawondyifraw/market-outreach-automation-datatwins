from __future__ import annotations

from datetime import date, datetime
import csv
import io
from pathlib import Path
from typing import Any, Iterable

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from sqlalchemy import or_, func

from app.database import get_session, init_db
from app.models import (
    Contact,
    FollowUp,
    OutreachChannel,
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


def render_template_text(filename: str, context: dict[str, Any]) -> str:
    path = OUTREACH_TEMPLATE_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    content = path.read_text(encoding="utf-8")
    return content.format_map(SafeDict(context))


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
                or_(Target.name.ilike(like_term), Target.sector.ilike(like_term))
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
    website: str | None = Form(None),
    notes: str | None = Form(None),
) -> RedirectResponse:
    with get_session() as session:
        target = Target(
            name=name,
            type=type,
            sector=sector,
            website=website,
            notes=notes,
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
            .order_by(OutreachEvent.sent_at.desc())
        ).all()
        followups = session.exec(
            select(FollowUp)
            .where(FollowUp.target_id == target_id)
            .order_by(FollowUp.due_date)
        ).all()
    return templates.TemplateResponse(
        "target_detail.html",
        {
            "request": request,
            "target": target,
            "contacts": contacts,
            "events": events,
            "followups": followups,
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


@app.get("/outreach/new", response_class=HTMLResponse)
def outreach_form(
    request: Request, target_id: int, contact_id: int | None = None
) -> HTMLResponse:
    with get_session() as session:
        target = session.get(Target, target_id)
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")
        contacts = session.exec(
            select(Contact).where(Contact.target_id == target_id)
        ).all()

    return templates.TemplateResponse(
        "outreach_form.html",
        {
            "request": request,
            "target": target,
            "contacts": contacts,
            "selected_contact_id": contact_id,
            "templates": load_outreach_templates(),
            "channels": list(OutreachChannel),
        },
    )


@app.post("/outreach")
def create_outreach_event(
    target_id: int = Form(...),
    contact_id: int | None = Form(None),
    template_name: str = Form(...),
    channel: OutreachChannel = Form(...),
    subject: str | None = Form(None),
    value_prop: str | None = Form(None),
    case_study_url: str | None = Form(None),
    custom_body: str | None = Form(None),
) -> RedirectResponse:
    with get_session() as session:
        target = session.get(Target, target_id)
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")
        contact = session.get(Contact, contact_id) if contact_id else None
        template_filename = f"{template_name}.txt"
        context = {
            "target_name": target.name,
            "contact_name": contact.full_name if contact else "",
            "value_prop": value_prop or "",
            "case_study_url": case_study_url or "",
        }
        body = custom_body.strip() if custom_body else ""
        if not body:
            body = render_template_text(template_filename, context)
        event = OutreachEvent(
            target_id=target_id,
            contact_id=contact_id,
            channel=channel,
            subject=subject,
            body=body,
            outcome=OutreachOutcome.no_reply,
            sent_at=datetime.utcnow(),
        )
        session.add(event)
        if target.status == TargetStatus.new:
            target.status = TargetStatus.contacted
            session.add(target)
        session.commit()
    return RedirectResponse(url=f"/targets/{target_id}", status_code=303)


@app.post("/import/targets")
def import_targets(file: UploadFile = File(...)) -> RedirectResponse:
    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    imported = 0
    with get_session() as session:
        for row in reader:
            if not row.get("name"):
                continue
            try:
                target_type = TargetType(row.get("type", "employer"))
            except ValueError:
                target_type = TargetType.employer
            try:
                status = TargetStatus(row.get("status", TargetStatus.new.value))
            except ValueError:
                status = TargetStatus.new
            target = Target(
                name=row["name"],
                type=target_type,
                sector=row.get("sector"),
                website=row.get("website"),
                notes=row.get("notes"),
                status=status,
            )
            session.add(target)
            imported += 1
        session.commit()
    return RedirectResponse(
        url=f"/targets?message=Imported%20{imported}%20targets", status_code=303
    )


@app.post("/import/contacts")
def import_contacts(file: UploadFile = File(...)) -> RedirectResponse:
    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    imported = 0
    with get_session() as session:
        for row in reader:
            target_id = row.get("target_id")
            if not target_id or not row.get("full_name"):
                continue
            if not session.get(Target, int(target_id)):
                continue
            contact = Contact(
                target_id=int(target_id),
                full_name=row["full_name"],
                role=row.get("role"),
                email=row.get("email"),
                phone=row.get("phone"),
                linkedin_url=row.get("linkedin_url"),
            )
            session.add(contact)
            imported += 1
        session.commit()
    return RedirectResponse(
        url=f"/targets?message=Imported%20{imported}%20contacts", status_code=303
    )


@app.get("/export/targets")
def export_targets() -> StreamingResponse:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["id", "name", "type", "sector", "website", "status", "last_contacted"]
    )
    with get_session() as session:
        targets = session.exec(select(Target)).all()
        for target in targets:
            last_contacted = session.exec(
                select(func.max(OutreachEvent.sent_at)).where(
                    OutreachEvent.target_id == target.id
                )
            ).one()
            writer.writerow(
                [
                    target.id,
                    target.name,
                    target.type.value,
                    target.sector or "",
                    target.website or "",
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
