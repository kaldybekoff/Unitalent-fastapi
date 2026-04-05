from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from src.jobs.models import Job
    from src.applications.models import Application


class InterviewSession(SQLModel, table=True):
    __tablename__ = "interview_sessions"

    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id", index=True)

    scheduled_at: datetime
    mode: str = Field(default="online", max_length=20)
    location: str | None = Field(default=None, max_length=200)
    meeting_link: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)
    result: str | None = Field(default=None, max_length=50)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    job: "Job" = Relationship(
        back_populates="interview_sessions",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    interviews: list["Interview"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"lazy": "selectin"},
    )


class Interview(SQLModel, table=True):
    __tablename__ = "interviews"
    __table_args__ = (
        UniqueConstraint("session_id", "application_id", name="uq_interview_session_application"),
    )

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="interview_sessions.id", index=True)
    application_id: int = Field(foreign_key="applications.id", index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    session: "InterviewSession" = Relationship(
        back_populates="interviews",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    application: "Application" = Relationship(
        back_populates="interviews",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
