from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .models import Candidate
from .schemas import CandidateCreate, CandidateUpdate


async def list_candidates(session: AsyncSession, skip: int, limit: int) -> list[Candidate]:
    res = await session.exec(select(Candidate).offset(skip).limit(limit).order_by(Candidate.id))
    return list(res.all())


async def get_candidate_or_404(session: AsyncSession, candidate_id: int) -> Candidate:
    candidate = await session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate with id {candidate_id} not found")
    return candidate


async def create_candidate(session: AsyncSession, payload: CandidateCreate) -> Candidate:
    now = datetime.utcnow()
    candidate = Candidate(**payload.model_dump(), created_at=now, updated_at=now)
    session.add(candidate)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Candidate with this email already exists")

    await session.refresh(candidate)
    return candidate


async def put_candidate(session: AsyncSession, candidate_id: int, payload: CandidateCreate) -> Candidate:
    existing = await get_candidate_or_404(session, candidate_id)
    now = datetime.utcnow()

    existing.full_name = payload.full_name
    existing.email = payload.email
    existing.major = payload.major
    existing.year = payload.year
    existing.updated_at = now

    session.add(existing)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Candidate with this email already exists")

    await session.refresh(existing)
    return existing


async def patch_candidate(session: AsyncSession, candidate_id: int, payload: CandidateUpdate) -> Candidate:
    existing = await get_candidate_or_404(session, candidate_id)
    data = payload.model_dump(exclude_unset=True)

    if not data:
        raise HTTPException(status_code=400, detail="At least one field must be provided for update")

    for k, v in data.items():
        setattr(existing, k, v)

    existing.updated_at = datetime.utcnow()
    session.add(existing)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Candidate with this email already exists")

    await session.refresh(existing)
    return existing


async def delete_candidate(session: AsyncSession, candidate_id: int) -> None:
    existing = await get_candidate_or_404(session, candidate_id)
    await session.delete(existing)
    await session.commit()