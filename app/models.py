from datetime import datetime, date
from enum import Enum
from typing import Optional, Any

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column
from sqlalchemy.dialects.sqlite import JSON


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
    redirected = "redirected"
    rejected = "rejected"


class Target(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    type: TargetType
    sector: Optional[str] = None
    province: Optional[str] = None
    website: Optional[str] = None
    general_email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    status: TargetStatus = Field(default=TargetStatus.new)
    do_not_contact: bool = Field(default=False)
    source: Optional[str] = None
    imported_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    contacts: list["Contact"] = Relationship(back_populates="target")
    outreach_events: list["OutreachEvent"] = Relationship(back_populates="target")
    followups: list["FollowUp"] = Relationship(back_populates="target")
    outreach_drafts: list["OutreachDraft"] = Relationship(back_populates="target")


class ConfidenceScore(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Contact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    target_id: int = Field(foreign_key="target.id")
    full_name: str
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    confidence_score: ConfidenceScore = Field(default=ConfidenceScore.low)
    do_not_contact: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    target: Optional[Target] = Relationship(back_populates="contacts")
    outreach_events: list["OutreachEvent"] = Relationship(back_populates="contact")
    outreach_drafts: list["OutreachDraft"] = Relationship(back_populates="contact")


class OutreachEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    target_id: int = Field(foreign_key="target.id")
    contact_id: Optional[int] = Field(default=None, foreign_key="contact.id")
    channel: OutreachChannel
    template_id: Optional[str] = None
    subject: Optional[str] = None
    body: str
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    outcome: OutreachOutcome = Field(default=OutreachOutcome.no_reply)
    responded_at: Optional[datetime] = None

    target: Optional[Target] = Relationship(back_populates="outreach_events")
    contact: Optional[Contact] = Relationship(back_populates="outreach_events")


class FollowUp(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    target_id: int = Field(foreign_key="target.id")
    due_date: date
    reason: Optional[str] = None
    done: bool = Field(default=False)

    target: Optional[Target] = Relationship(back_populates="followups")


class LeadSuggestionStatus(str, Enum):
    new = "new"
    accepted = "accepted"
    rejected = "rejected"


class LeadSuggestion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_target_data: dict[str, Any] = Field(
        sa_column=Column(JSON, nullable=False)
    )
    relevance_tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    score: int = Field(default=0)
    score_breakdown: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    evidence_links: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    status: LeadSuggestionStatus = Field(default=LeadSuggestionStatus.new)
    rejection_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OutreachDraftStatus(str, Enum):
    draft = "draft"
    queued = "queued"
    approved = "approved"
    sent = "sent"
    failed = "failed"


class OutreachDraft(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    target_id: int = Field(foreign_key="target.id")
    contact_id: Optional[int] = Field(default=None, foreign_key="contact.id")
    template_id: str
    channel: OutreachChannel = Field(default=OutreachChannel.email)
    rendered_subject: Optional[str] = None
    rendered_body: Optional[str] = None
    edited_subject: Optional[str] = None
    edited_body: Optional[str] = None
    final_subject: Optional[str] = None
    final_body: Optional[str] = None
    status: OutreachDraftStatus = Field(default=OutreachDraftStatus.draft)
    missing_fields: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    message_id: Optional[str] = None
    send_error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    target: Optional[Target] = Relationship(back_populates="outreach_drafts")
    contact: Optional[Contact] = Relationship(back_populates="outreach_drafts")


class ImportLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    import_type: str
    inserted: int = Field(default=0)
    updated: int = Field(default=0)
    skipped: int = Field(default=0)
    failed: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DncEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    value: str
    reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
