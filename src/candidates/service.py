from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.users.models import User
from src.exceptions.custom_exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)

from .models import Candidate
from .schemas import CandidateCreate, CandidateUpdate


async def list_candidates(session: AsyncSession, skip: int, limit: int) -> list[Candidate]:
    res = await session.exec(select(Candidate).order_by(Candidate.id).offset(skip).limit(limit))
    return list(res.all())


async def get_candidate_or_404(session: AsyncSession, candidate_id: int) -> Candidate:
    candidate = await session.get(Candidate, candidate_id)
    if not candidate:
        raise NotFoundException(f"Candidate with id {candidate_id} not found")
    return candidate


async def get_candidate_by_user_id(session: AsyncSession, user_id: int) -> Candidate | None:
    res = await session.exec(select(Candidate).where(Candidate.user_id == user_id))
    return res.first()


async def create_candidate(session: AsyncSession, payload: CandidateCreate, current_user: User) -> Candidate:
    if current_user.role != "candidate":
        raise ForbiddenException("Only candidate users can create candidate profile")

    existing = await get_candidate_by_user_id(session, current_user.id)
    if existing:
        raise ConflictException("Candidate profile already exists for this user")

    now = datetime.utcnow()
    candidate = Candidate(
        user_id=current_user.id,
        full_name=payload.full_name,
        major=payload.major,
        year=payload.year,
        created_at=now,
        updated_at=now,
    )
    session.add(candidate)
    await session.commit()
    await session.refresh(candidate)
    return candidate


async def update_candidate(
    session: AsyncSession,
    candidate_id: int,
    payload: CandidateUpdate,
    current_user: User,
) -> Candidate:
    candidate = await get_candidate_or_404(session, candidate_id)

    if current_user.role != "admin" and candidate.user_id != current_user.id:
        raise ForbiddenException("You can update only your own candidate profile")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestException("At least one field must be provided for update")

    for k, v in data.items():
        setattr(candidate, k, v)

    candidate.updated_at = datetime.utcnow()
    session.add(candidate)
    await session.commit()
    await session.refresh(candidate)
    return candidate


async def delete_candidate(session: AsyncSession, candidate_id: int, current_user: User) -> None:
    candidate = await get_candidate_or_404(session, candidate_id)

    if current_user.role != "admin" and candidate.user_id != current_user.id:
        raise ForbiddenException("You can delete only your own candidate profile")

    if candidate.applications:
        raise BadRequestException("Cannot delete candidate with existing applications")

    if candidate.resumes:
        raise BadRequestException("Cannot delete candidate with existing resumes")

    await session.delete(candidate)
    await session.commit()