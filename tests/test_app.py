import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_outreach.db"

from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db, engine
from app.models import Target, TargetStatus
from sqlmodel import Session, select


client = TestClient(app)


def setup_module(module):
    db_path = Path("./test_outreach.db")
    if db_path.exists():
        db_path.unlink()
    init_db()


def teardown_module(module):
    db_path = Path("./test_outreach.db")
    if db_path.exists():
        db_path.unlink()


def test_create_target_and_list():
    response = client.post(
        "/targets",
        data={
            "name": "City of Utrecht",
            "type": "municipality",
            "sector": "Public",
            "website": "https://utrecht.nl",
            "notes": "Focus on mobility partnerships",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    list_response = client.get("/targets")
    assert list_response.status_code == 200
    assert "City of Utrecht" in list_response.text


def test_outreach_event_updates_status():
    with Session(engine) as session:
        target = session.exec(select(Target).where(Target.name == "City of Utrecht")).one()
        assert target.status == TargetStatus.new

    response = client.post(
        "/outreach",
        data={
            "target_id": target.id,
            "template_name": "first-touch",
            "channel": "email",
            "subject": "Intro",
            "value_prop": "Helping streamline outreach",
            "case_study_url": "https://example.com/case",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    with Session(engine) as session:
        refreshed = session.get(Target, target.id)
        assert refreshed.status == TargetStatus.contacted


def test_export_targets_contains_last_contacted():
    response = client.get("/export/targets")
    assert response.status_code == 200
    assert "last_contacted" in response.text
    assert "City of Utrecht" in response.text
