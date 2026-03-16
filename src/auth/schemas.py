from datetime import datetime

from pydantic import EmailStr
from sqlmodel import SQLModel, Field


class RegisterRequest(SQLModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: str = Field(default="candidate", max_length=30)


class LoginRequest(SQLModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class TokenPair(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(SQLModel):
    refresh_token: str


class UserRead(SQLModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime