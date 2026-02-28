from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import EmailStr
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from src.applications.models import Application


class Candidate(SQLModel, table=True):
    __tablename__ = "candidates"

    id: int | None = Field(default=None, primary_key=True)
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr = Field(index=True, unique=True)

    major: str | None = Field(default=None, max_length=120)
    year: int | None = Field(default=None, ge=1, le=8)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    applications: list["Application"] = Relationship(
        back_populates="candidate",
        sa_relationship_kwargs={"lazy": "selectin"},
    )