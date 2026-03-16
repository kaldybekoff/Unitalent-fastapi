from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from src.candidates.models import Candidate
    from src.jobs.models import Job
    from src.interviews.models import Interview
    from src.resumes.models import Resume


class Application(SQLModel, table=True):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", name="uq_application_candidate_job"),
    )

    id: int | None = Field(default=None, primary_key=True)

    candidate_id: int = Field(foreign_key="candidates.id", index=True)
    job_id: int = Field(foreign_key="jobs.id", index=True)
    resume_id: int = Field(foreign_key="resumes.id", index=True)

    status: str = Field(default="submitted", index=True, max_length=20)
    cover_letter: str | None = Field(default=None, max_length=5000)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    candidate: "Candidate" = Relationship(
        back_populates="applications",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    job: "Job" = Relationship(
        back_populates="applications",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    resume: "Resume" = Relationship(
        back_populates="applications",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    interviews: list["Interview"] = Relationship(
        back_populates="application",
        sa_relationship_kwargs={"lazy": "selectin"},
    )