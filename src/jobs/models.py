from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from src.companies.models import Company
    from src.applications.models import Application


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: int | None = Field(default=None, primary_key=True)

    title: str = Field(min_length=1, max_length=200, index=True)
    location: str | None = Field(default=None, max_length=200, index=True)
    description: str = Field(min_length=1, max_length=5000)
    is_open: bool = Field(default=True, index=True)

    company_id: int = Field(foreign_key="companies.id", index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    company: "Company" = Relationship(
        back_populates="jobs",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    applications: list["Application"] = Relationship(
        back_populates="job",
        sa_relationship_kwargs={"lazy": "selectin"},
    )