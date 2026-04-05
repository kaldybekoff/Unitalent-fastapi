from datetime import datetime

from pydantic import model_validator
from sqlmodel import SQLModel, Field


class CandidateCreate(SQLModel):
    full_name: str = Field(min_length=1, max_length=120)
    major: str | None = Field(default=None, max_length=120)
    year: int | None = Field(default=None, ge=1, le=8)


class CandidateUpdate(SQLModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    major: str | None = Field(default=None, max_length=120)
    year: int | None = Field(default=None, ge=1, le=8)


class CandidateRead(SQLModel):
    id: int
    user_id: int
    full_name: str
    major: str | None
    year: int | None
    has_photo: bool = False
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def compute_has_photo(cls, data):
        if hasattr(data, "photo"):
            data.__dict__["has_photo"] = data.photo is not None
        return data
