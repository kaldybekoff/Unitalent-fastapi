from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from src.applications.models import Application


class Interview(SQLModel, table=True):
    __tablename__ = "interviews"

    id: int | None = Field(default=None, primary_key=True)

    application_id: int = Field(foreign_key="applications.id", index=True)

    scheduled_at: datetime
    mode: str = Field(default="online", max_length=20)  # online/offline
    location: str | None = Field(default=None, max_length=200)
    meeting_link: str | None = Field(default=None, max_length=500)
    result: str | None = Field(default=None, max_length=50)  # passed/failed/pending (например)
    notes: str | None = Field(default=None, max_length=2000)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    application: "Application" = Relationship(
        back_populates="interviews",
        sa_relationship_kwargs={"lazy": "selectin"},
    )