from datetime import datetime
from sqlmodel import SQLModel, Field


class JobCreate(SQLModel):
    title: str = Field(min_length=1, max_length=200)
    company_id: int = Field(gt=0)
    location: str | None = Field(default=None, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    is_open: bool = True


class JobUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    company_id: int | None = Field(default=None, gt=0)
    location: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    is_open: bool | None = None


class JobRead(SQLModel):
    id: int
    title: str
    company_id: int
    location: str | None
    description: str
    is_open: bool
    created_at: datetime
    updated_at: datetime