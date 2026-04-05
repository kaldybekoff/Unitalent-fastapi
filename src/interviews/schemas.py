from datetime import datetime, timezone

from pydantic import field_validator
from sqlmodel import SQLModel, Field


def to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


# ── InterviewSession schemas ──────────────────────────────────────────────────

class InterviewSessionCreate(SQLModel):
    job_id: int = Field(gt=0)
    scheduled_at: datetime
    mode: str = Field(default="online", max_length=20)
    location: str | None = Field(default=None, max_length=200)
    meeting_link: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)
    result: str | None = Field(default=None, max_length=50)

    @field_validator("scheduled_at")
    @classmethod
    def normalize_scheduled_at(cls, v: datetime) -> datetime:
        return to_naive_utc(v)


class InterviewSessionPatch(SQLModel):
    scheduled_at: datetime | None = None
    mode: str | None = None
    location: str | None = None
    meeting_link: str | None = None
    notes: str | None = None
    result: str | None = None

    @field_validator("scheduled_at")
    @classmethod
    def normalize_scheduled_at(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return None
        return to_naive_utc(v)


class InterviewRead(SQLModel):
    id: int
    session_id: int
    application_id: int
    created_at: datetime
    updated_at: datetime


class InterviewSessionRead(SQLModel):
    id: int
    job_id: int
    scheduled_at: datetime
    mode: str
    location: str | None
    meeting_link: str | None
    notes: str | None
    result: str | None
    created_at: datetime
    updated_at: datetime
    interviews: list[InterviewRead] = []


# ── Interview (candidate slot) schemas ───────────────────────────────────────

class InterviewCreate(SQLModel):
    session_id: int = Field(gt=0)
    application_id: int = Field(gt=0)
