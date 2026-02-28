from datetime import datetime, timezone

from pydantic import field_validator
from sqlmodel import SQLModel, Field


def to_naive_utc(dt: datetime) -> datetime:
    # Если datetime с таймзоной (например "Z") -> переводим в UTC и делаем naive
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


class InterviewCreate(SQLModel):
    application_id: int = Field(gt=0)
    scheduled_at: datetime
    mode: str = Field(default="online", max_length=20)
    location: str | None = Field(default=None, max_length=200)
    meeting_link: str | None = Field(default=None, max_length=500)
    result: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("scheduled_at")
    @classmethod
    def normalize_scheduled_at(cls, v: datetime) -> datetime:
        return to_naive_utc(v)


class InterviewPut(SQLModel):
    # PUT = replace (полная замена)
    application_id: int = Field(gt=0)
    scheduled_at: datetime
    mode: str = Field(max_length=20)
    location: str | None = Field(default=None, max_length=200)
    meeting_link: str | None = Field(default=None, max_length=500)
    result: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("scheduled_at")
    @classmethod
    def normalize_scheduled_at(cls, v: datetime) -> datetime:
        return to_naive_utc(v)


class InterviewPatch(SQLModel):
    application_id: int | None = Field(default=None, gt=0)
    scheduled_at: datetime | None = None
    mode: str | None = None
    location: str | None = None
    meeting_link: str | None = None
    result: str | None = None
    notes: str | None = None

    @field_validator("scheduled_at")
    @classmethod
    def normalize_scheduled_at(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return None
        return to_naive_utc(v)


class InterviewRead(SQLModel):
    id: int
    application_id: int
    scheduled_at: datetime
    mode: str
    location: str | None
    meeting_link: str | None
    result: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime