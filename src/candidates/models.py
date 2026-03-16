from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from src.users.models import User
    from src.applications.models import Application
    from src.resumes.models import Resume


class Candidate(SQLModel, table=True):
    __tablename__ = "candidates"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True, index=True)

    full_name: str = Field(min_length=1, max_length=120)
    major: str | None = Field(default=None, max_length=120)
    year: int | None = Field(default=None, ge=1, le=8)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    user: "User" = Relationship(
        back_populates="candidate_profile",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    applications: list["Application"] = Relationship(
        back_populates="candidate",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    resumes: list["Resume"] = Relationship(
        back_populates="candidate",
        sa_relationship_kwargs={"lazy": "selectin"},
    )