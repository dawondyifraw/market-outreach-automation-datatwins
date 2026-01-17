from datetime import datetime, date
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class TargetType(str, Enum):
    employer = "employer"
    municipality = "municipality"


class TargetStatus(str, Enum):
    new = "new"
    contacted = "contacted"
    replied = "replied"
    meeting = "meeting"
    won = "won"
    lost = "lost"


class OutreachChannel(str, Enum):
    email = "email"
    linkedin = "linkedin"
    phone = "phone"


class OutreachOutcome(str, Enum):
    no_reply = "no_reply"
    reply = "reply"
    meeting_set = "meeting_set"
    rejected = "rejected"


class Target(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    type: TargetType
    sector: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    status: TargetStatus = Field(default=TargetStatus.new)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    contacts: list["Contact"] = Relationship(back_populates="target")
    outreach_events: list["OutreachEvent"] = Relationship(back_populates="target")
    followups: list["FollowUp"] = Relationship(back_populates="target")


class Contact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    target_id: int = Field(foreign_key="target.id")
    full_name: str
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None

    target: Optional[Target] = Relationship(back_populates="contacts")
    outreach_events: list["OutreachEvent"] = Relationship(back_populates="contact")


class OutreachEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    target_id: int = Field(foreign_key="target.id")
    contact_id: Optional[int] = Field(default=None, foreign_key="contact.id")
    channel: OutreachChannel
    subject: Optional[str] = None
    body: str
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    outcome: OutreachOutcome = Field(default=OutreachOutcome.no_reply)

    target: Optional[Target] = Relationship(back_populates="outreach_events")
    contact: Optional[Contact] = Relationship(back_populates="outreach_events")


class FollowUp(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    target_id: int = Field(foreign_key="target.id")
    due_date: date
    reason: Optional[str] = None
    done: bool = Field(default=False)

    target: Optional[Target] = Relationship(back_populates="followups")
