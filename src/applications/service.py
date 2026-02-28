from datetime import datetime

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.candidates.models import Candidate
from src.jobs.models import Job
from .models import Application
from .schemas import ApplicationCreate, ApplicationPut, ApplicationPatch


async def list_applications(
    session: AsyncSession,
    skip: int,
    limit: int,
    candidate_id: int | None,
    job_id: int | None,
    status_filter: str | None,
) -> list[Application]:
    stmt = select(Application)

    if candidate_id is not None:
        stmt = stmt.where(Application.candidate_id == candidate_id)
    if job_id is not None:
        stmt = stmt.where(Application.job_id == job_id)
    if status_filter is not None:
        stmt = stmt.where(Application.status == status_filter)

    stmt = stmt.order_by(Application.id).offset(skip).limit(limit)
    res = await session.exec(stmt)
    return list(res.all())


async def get_application_or_404(session: AsyncSession, app_id: int) -> Application:
    app_obj = await session.get(Application, app_id)
    if not app_obj:
        raise HTTPException(status_code=404, detail=f"Application with id {app_id} not found")
    return app_obj


async def ensure_candidate_exists(session: AsyncSession, candidate_id: int) -> None:
    if not await session.get(Candidate, candidate_id):
        raise HTTPException(status_code=404, detail=f"Candidate with id {candidate_id} not found")


async def ensure_job_exists_and_open(session: AsyncSession, job_id: int) -> Job:
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with id {job_id} not found")
    if not job.is_open:
        raise HTTPException(status_code=400, detail="Cannot apply: job is closed")
    return job


async def ensure_no_duplicate(session: AsyncSession, candidate_id: int, job_id: int) -> None:
    stmt = select(Application).where(
        Application.candidate_id == candidate_id,
        Application.job_id == job_id,
    )
    res = await session.exec(stmt)
    if res.first():
        raise HTTPException(status_code=400, detail="Duplicate application is not allowed")


async def ensure_no_duplicate_except_self(
    session: AsyncSession, candidate_id: int, job_id: int, self_app_id: int
) -> None:
    stmt = select(Application).where(
        Application.candidate_id == candidate_id,
        Application.job_id == job_id,
        Application.id != self_app_id,
    )
    res = await session.exec(stmt)
    if res.first():
        raise HTTPException(status_code=400, detail="Duplicate application is not allowed")


async def create_application(session: AsyncSession, payload: ApplicationCreate) -> Application:
    await ensure_candidate_exists(session, payload.candidate_id)
    await ensure_job_exists_and_open(session, payload.job_id)
    await ensure_no_duplicate(session, payload.candidate_id, payload.job_id)

    now = datetime.utcnow()
    app_obj = Application(
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        status="submitted",
        cover_letter=payload.cover_letter,
        created_at=now,
        updated_at=now,
    )
    session.add(app_obj)
    await session.commit()
    await session.refresh(app_obj)
    return app_obj


async def put_application(session: AsyncSession, app_id: int, payload: ApplicationPut) -> Application:
    existing = await get_application_or_404(session, app_id)

    # Business rules
    await ensure_candidate_exists(session, payload.candidate_id)
    await ensure_job_exists_and_open(session, payload.job_id)
    await ensure_no_duplicate_except_self(session, payload.candidate_id, payload.job_id, existing.id)

    existing.candidate_id = payload.candidate_id
    existing.job_id = payload.job_id
    existing.status = payload.status
    existing.cover_letter = payload.cover_letter
    existing.updated_at = datetime.utcnow()

    session.add(existing)
    await session.commit()
    await session.refresh(existing)
    return existing


async def patch_application(session: AsyncSession, app_id: int, payload: ApplicationPatch) -> Application:
    existing = await get_application_or_404(session, app_id)
    data = payload.model_dump(exclude_unset=True)

    if not data:
        raise HTTPException(status_code=400, detail="At least one field must be provided for update")

    for k, v in data.items():
        setattr(existing, k, v)

    existing.updated_at = datetime.utcnow()

    session.add(existing)
    await session.commit()
    await session.refresh(existing)
    return existing


async def delete_application(session: AsyncSession, app_id: int) -> None:
    existing = await get_application_or_404(session, app_id)
    await session.delete(existing)
    await session.commit()