from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from sqlmodel import select

from app.database import get_session, init_db
from app.models import Contact, ConfidenceScore, ImportLog, Target, TargetStatus, TargetType


@dataclass(frozen=True)
class ImportSummary:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0


def _store_import_log(import_type: str, summary: ImportSummary) -> None:
    with get_session() as session:
        session.add(
            ImportLog(
                import_type=import_type,
                inserted=summary.inserted,
                updated=summary.updated,
                skipped=summary.skipped,
                failed=summary.failed,
            )
        )
        session.commit()


def import_municipalities_csv(rows: Iterable[dict[str, str]]) -> ImportSummary:
    init_db()
    inserted = updated = skipped = failed = 0
    now = datetime.utcnow()
    with get_session() as session:
        for row in rows:
            name = (row.get("name") or "").strip()
            if not name:
                failed += 1
                continue

            website = (row.get("website") or "").strip() or None
            province = (row.get("province") or "").strip() or None
            general_email = (row.get("general_email") or "").strip() or None
            phone = (row.get("phone") or "").strip() or None
            source = (row.get("source") or "").strip() or None

            existing = session.exec(select(Target).where(Target.name == name)).first()
            if not existing and website:
                existing = session.exec(select(Target).where(Target.website == website)).first()

            if existing:
                existing.website = website or existing.website
                existing.province = province or existing.province
                existing.general_email = general_email or existing.general_email
                existing.phone = phone or existing.phone
                existing.source = source or existing.source
                existing.status = existing.status or TargetStatus.new
                existing.imported_at = now
                existing.updated_at = now
                session.add(existing)
                updated += 1
                continue

            target = Target(
                name=name,
                type=TargetType.municipality,
                province=province,
                website=website,
                general_email=general_email,
                phone=phone,
                source=source,
                status=TargetStatus.new,
                imported_at=now,
                updated_at=now,
            )
            session.add(target)
            inserted += 1
        session.commit()

    summary = ImportSummary(inserted=inserted, updated=updated, skipped=skipped, failed=failed)
    _store_import_log("municipalities", summary)
    return summary


def import_municipalities_csv_path(csv_path: Path) -> ImportSummary:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return import_municipalities_csv(reader)


def _contact_confidence(email: str | None, role: str | None) -> ConfidenceScore:
    if email and role:
        return ConfidenceScore.high
    if email:
        return ConfidenceScore.medium
    return ConfidenceScore.low


def import_contacts_csv(rows: Iterable[dict[str, str]]) -> ImportSummary:
    init_db()
    inserted = updated = skipped = failed = 0
    now = datetime.utcnow()
    with get_session() as session:
        for row in rows:
            target_name = (row.get("target_name") or "").strip()
            target_id_raw = (row.get("target_id") or "").strip()
            full_name = (row.get("full_name") or "").strip()
            role = (row.get("role") or "").strip() or None
            email = (row.get("email") or "").strip() or None
            phone = (row.get("phone") or "").strip() or None
            linkedin_url = (row.get("linkedin_url") or "").strip() or None

            if not target_name and not target_id_raw:
                failed += 1
                continue

            target = None
            if target_id_raw:
                target = session.get(Target, int(target_id_raw))
            if not target and target_name:
                target = session.exec(select(Target).where(Target.name == target_name)).first()

            if not target:
                failed += 1
                continue

            if not full_name and not email:
                failed += 1
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
                existing.full_name = full_name or existing.full_name
                existing.role = role or existing.role
                existing.phone = phone or existing.phone
                existing.linkedin_url = linkedin_url or existing.linkedin_url
                existing.confidence_score = _contact_confidence(email or existing.email, role or existing.role)
                existing.updated_at = now
                session.add(existing)
                updated += 1
                continue

            contact = Contact(
                target_id=target.id,
                full_name=full_name or email or "Unknown",
                role=role,
                email=email,
                phone=phone,
                linkedin_url=linkedin_url,
                confidence_score=_contact_confidence(email, role),
                updated_at=now,
            )
            session.add(contact)
            inserted += 1
        session.commit()

    summary = ImportSummary(inserted=inserted, updated=updated, skipped=skipped, failed=failed)
    _store_import_log("contacts", summary)
    return summary


def import_contacts_csv_path(csv_path: Path) -> ImportSummary:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return import_contacts_csv(reader)
