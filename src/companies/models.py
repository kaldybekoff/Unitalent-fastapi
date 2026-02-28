from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from src.jobs.models import Job


class Company(SQLModel, table=True):
    __tablename__ = "companies"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(min_length=1, max_length=200, index=True, unique=True)
    industry: str | None = Field(default=None, max_length=200)
    website: str | None = Field(default=None, max_length=300)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    jobs: list["Job"] = Relationship(
        back_populates="company",
        sa_relationship_kwargs={"lazy": "selectin"},
    )