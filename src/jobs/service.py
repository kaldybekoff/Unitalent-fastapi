from datetime import datetime

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.companies.models import Company
from .models import Job
from .schemas import JobCreate, JobUpdate


async def list_jobs(
    session: AsyncSession,
    skip: int,
    limit: int,
    search: str | None,
    is_open: bool | None,
    company_id: int | None,
) -> list[Job]:
    stmt = select(Job)

    if search:
        s = search.strip().lower()
        stmt = stmt.where((Job.title.ilike(f"%{s}%")))

    if is_open is not None:
        stmt = stmt.where(Job.is_open == is_open)

    if company_id is not None:
        stmt = stmt.where(Job.company_id == company_id)

    stmt = stmt.order_by(Job.id).offset(skip).limit(limit)

    res = await session.exec(stmt)
    return list(res.all())


async def get_job_or_404(session: AsyncSession, job_id: int) -> Job:
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with id {job_id} not found")
    return job


async def ensure_company_exists(session: AsyncSession, company_id: int) -> None:
    company = await session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company with id {company_id} not found")


async def create_job(session: AsyncSession, payload: JobCreate) -> Job:
    await ensure_company_exists(session, payload.company_id)

    now = datetime.utcnow()
    job = Job(**payload.model_dump(), created_at=now, updated_at=now)

    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job  


async def put_job(session: AsyncSession, job_id: int, payload: JobCreate) -> Job:
    existing = await get_job_or_404(session, job_id)
    await ensure_company_exists(session, payload.company_id)

    existing.title = payload.title
    existing.company_id = payload.company_id
    existing.location = payload.location
    existing.description = payload.description
    existing.is_open = payload.is_open
    existing.updated_at = datetime.utcnow()

    session.add(existing)
    await session.commit()
    await session.refresh(existing)
    return existing


async def patch_job(session: AsyncSession, job_id: int, payload: JobUpdate) -> Job:
    existing = await get_job_or_404(session, job_id)
    data = payload.model_dump(exclude_unset=True)

    if not data:
        raise HTTPException(status_code=400, detail="At least one field must be provided for update")

    if "company_id" in data and data["company_id"] is not None:
        await ensure_company_exists(session, data["company_id"])

    for k, v in data.items():
        setattr(existing, k, v)

    existing.updated_at = datetime.utcnow()

    session.add(existing)
    await session.commit()
    await session.refresh(existing)
    return existing


async def delete_job(session: AsyncSession, job_id: int) -> None:
    existing = await get_job_or_404(session, job_id)
    await session.delete(existing)
    await session.commit()