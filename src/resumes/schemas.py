from datetime import datetime

from sqlmodel import SQLModel, Field


class ResumeCreate(SQLModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str | None = Field(default=None, max_length=3000)
    skills: str | None = Field(default=None, max_length=3000)
    education: str | None = Field(default=None, max_length=3000)
    experience: str | None = Field(default=None, max_length=3000)
    is_active: bool = True


class ResumeUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    summary: str | None = Field(default=None, max_length=3000)
    skills: str | None = Field(default=None, max_length=3000)
    education: str | None = Field(default=None, max_length=3000)
    experience: str | None = Field(default=None, max_length=3000)
    is_active: bool | None = None


class ResumeRead(SQLModel):
    id: int
    candidate_id: int
    title: str
    summary: str | None
    skills: str | None
    education: str | None
    experience: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime