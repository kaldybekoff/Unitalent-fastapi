from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from src.candidates.models import Candidate
    from src.applications.models import Application


class Resume(SQLModel, table=True):
    __tablename__ = "resumes"

    id: int | None = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="candidates.id", index=True)

    title: str = Field(min_length=1, max_length=200)
    summary: str | None = Field(default=None, max_length=3000)
    skills: str | None = Field(default=None, max_length=3000)
    education: str | None = Field(default=None, max_length=3000)
    experience: str | None = Field(default=None, max_length=3000)
    is_active: bool = Field(default=True, index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    candidate: "Candidate" = Relationship(
        back_populates="resumes",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    applications: list["Application"] = Relationship(
        back_populates="resume",
        sa_relationship_kwargs={"lazy": "selectin"},
    )