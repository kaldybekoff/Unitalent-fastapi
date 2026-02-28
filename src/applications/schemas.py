from datetime import datetime
from typing import Literal

from sqlmodel import SQLModel, Field

ApplicationStatus = Literal["submitted", "reviewing", "accepted", "rejected"]


class ApplicationCreate(SQLModel):
    candidate_id: int = Field(gt=0)
    job_id: int = Field(gt=0)
    cover_letter: str | None = Field(default=None, max_length=5000)


class ApplicationPut(SQLModel):
    candidate_id: int = Field(gt=0)
    job_id: int = Field(gt=0)
    status: ApplicationStatus
    cover_letter: str | None = Field(default=None, max_length=5000)


class ApplicationPatch(SQLModel):
    status: ApplicationStatus | None = None
    cover_letter: str | None = Field(default=None, max_length=5000)


class ApplicationRead(SQLModel):
    id: int
    candidate_id: int
    job_id: int
    status: ApplicationStatus
    cover_letter: str | None
    created_at: datetime
    updated_at: datetime