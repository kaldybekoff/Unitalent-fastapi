from datetime import datetime
from sqlmodel import SQLModel, Field


class CompanyCreate(SQLModel):
    name: str = Field(min_length=1, max_length=200)
    industry: str | None = Field(default=None, max_length=200)
    website: str | None = Field(default=None, max_length=300)


class CompanyUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    industry: str | None = Field(default=None, max_length=200)
    website: str | None = Field(default=None, max_length=300)


class CompanyRead(SQLModel):
    id: int
    name: str
    industry: str | None
    website: str | None
    created_at: datetime
    updated_at: datetime