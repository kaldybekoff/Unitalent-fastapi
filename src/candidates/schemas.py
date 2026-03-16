from datetime import datetime

from sqlmodel import SQLModel, Field


class CandidateCreate(SQLModel):
    full_name: str = Field(min_length=1, max_length=120)
    major: str | None = Field(default=None, max_length=120)
    year: int | None = Field(default=None, ge=1, le=8)


class CandidateUpdate(SQLModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    major: str | None = Field(default=None, max_length=120)
    year: int | None = Field(default=None, ge=1, le=8)


class CandidateRead(SQLModel):
    id: int
    user_id: int
    full_name: str
    major: str | None
    year: int | None
    created_at: datetime
    updated_at: datetime