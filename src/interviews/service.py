from datetime import datetime

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.applications.models import Application
from .models import Interview
from .schemas import InterviewCreate, InterviewPut, InterviewPatch


async def list_interviews(
    session: AsyncSession,
    skip: int,
    limit: int,
    application_id: int | None,
) -> list[Interview]:
    stmt = select(Interview)
    if application_id is not None:
        stmt = stmt.where(Interview.application_id == application_id)

    stmt = stmt.order_by(Interview.id).offset(skip).limit(limit)
    res = await session.exec(stmt)
    return list(res.all())


async def get_interview_or_404(session: AsyncSession, interview_id: int) -> Interview:
    obj = await session.get(Interview, interview_id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"Interview with id {interview_id} not found")
    return obj


async def ensure_application_exists(session: AsyncSession, app_id: int) -> None:
    if not await session.get(Application, app_id):
        raise HTTPException(status_code=404, detail=f"Application with id {app_id} not found")


async def create_interview(session: AsyncSession, payload: InterviewCreate) -> Interview:
    await ensure_application_exists(session, payload.application_id)

    now = datetime.utcnow()
    obj = Interview(**payload.model_dump(), created_at=now, updated_at=now)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def put_interview(session: AsyncSession, interview_id: int, payload: InterviewPut) -> Interview:
    existing = await get_interview_or_404(session, interview_id)

    await ensure_application_exists(session, payload.application_id)

    existing.application_id = payload.application_id
    existing.scheduled_at = payload.scheduled_at
    existing.mode = payload.mode
    existing.location = payload.location
    existing.meeting_link = payload.meeting_link
    existing.result = payload.result
    existing.notes = payload.notes
    existing.updated_at = datetime.utcnow()

    session.add(existing)
    await session.commit()
    await session.refresh(existing)
    return existing


async def patch_interview(session: AsyncSession, interview_id: int, payload: InterviewPatch) -> Interview:
    existing = await get_interview_or_404(session, interview_id)
    data = payload.model_dump(exclude_unset=True)

    if not data:
        raise HTTPException(status_code=400, detail="At least one field must be provided for update")

    if "application_id" in data and data["application_id"] is not None:
        await ensure_application_exists(session, data["application_id"])

    for k, v in data.items():
        setattr(existing, k, v)

    existing.updated_at = datetime.utcnow()

    session.add(existing)
    await session.commit()
    await session.refresh(existing)
    return existing


async def delete_interview(session: AsyncSession, interview_id: int) -> None:
    existing = await get_interview_or_404(session, interview_id)
    await session.delete(existing)
    await session.commit()