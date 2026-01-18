import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_importers.db"

from sqlmodel import Session, delete, select

from app.database import engine, init_db
from app.importers import import_contacts_csv, import_municipalities_csv
from app.models import (
    Contact,
    DncEntry,
    FollowUp,
    ImportLog,
    LeadSuggestion,
    OutreachDraft,
    OutreachEvent,
    Target,
    TargetType,
)


def setup_module(module):
    db_path = Path("./test_importers.db")
    if db_path.exists():
        db_path.unlink()
    init_db()


def teardown_module(module):
    db_path = Path("./test_importers.db")
    if db_path.exists():
        db_path.unlink()


def reset_db() -> None:
    init_db()
    with Session(engine) as session:
        session.exec(delete(OutreachEvent))
        session.exec(delete(OutreachDraft))
        session.exec(delete(LeadSuggestion))
        session.exec(delete(ImportLog))
        session.exec(delete(DncEntry))
        session.exec(delete(Contact))
        session.exec(delete(FollowUp))
        session.exec(delete(Target))
        session.commit()


def test_import_municipalities_upsert() -> None:
    reset_db()
    rows = [
        {"name": "City One", "province": "Utrecht", "website": "https://one.nl"},
        {"name": "City One", "province": "Utrecht", "website": "https://one.nl", "phone": "123"},
        {"name": "City Two", "province": "Noord-Holland"},
    ]
    summary = import_municipalities_csv(rows)
    assert summary.inserted == 2
    assert summary.updated == 1

    with Session(engine) as session:
        targets = session.exec(select(Target).order_by(Target.name)).all()
    assert [target.name for target in targets] == ["City One", "City Two"]
    assert all(target.type == TargetType.municipality for target in targets)


def test_import_contacts_upsert() -> None:
    reset_db()
    with Session(engine) as session:
        target = Target(name="City Three", type=TargetType.municipality)
        session.add(target)
        session.commit()
        session.refresh(target)

    rows = [
        {"target_id": str(target.id), "full_name": "Jane Doe", "email": "jane@example.com"},
        {"target_id": str(target.id), "full_name": "Jane Doe", "email": "jane@example.com", "role": "Data Lead"},
    ]
    summary = import_contacts_csv(rows)
    assert summary.inserted == 1
    assert summary.updated == 1
