from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.users.models import User
from src.exceptions.custom_exceptions import BadRequestException, ForbiddenException, NotFoundException
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
    sort_by: str,
    sort_order: str,
) -> list[Job]:
    stmt = select(Job)

    if search:
        s = search.strip()
        stmt = stmt.where((Job.title.ilike(f"%{s}%")) | (Job.location.ilike(f"%{s}%")))

    if is_open is not None:
        stmt = stmt.where(Job.is_open == is_open)

    if company_id is not None:
        stmt = stmt.where(Job.company_id == company_id)

    order_column = Job.id
    if sort_by == "title":
        order_column = Job.title
    elif sort_by == "created_at":
        order_column = Job.created_at

    stmt = stmt.order_by(order_column.desc() if sort_order == "desc" else order_column.asc())
    stmt = stmt.offset(skip).limit(limit)

    res = await session.exec(stmt)
    return list(res.all())


async def get_job_or_404(session: AsyncSession, job_id: int) -> Job:
    job = await session.get(Job, job_id)
    if not job:
        raise NotFoundException(f"Job with id {job_id} not found")
    return job


async def get_company_or_404(session: AsyncSession, company_id: int) -> Company:
    company = await session.get(Company, company_id)
    if not company:
        raise NotFoundException(f"Company with id {company_id} not found")
    return company


async def create_job(session: AsyncSession, payload: JobCreate, current_user: User) -> Job:
    if current_user.role not in {"recruiter", "admin"}:
        raise ForbiddenException("Only recruiter or admin can create jobs")

    company = await get_company_or_404(session, payload.company_id)

    if current_user.role != "admin" and company.owner_id != current_user.id:
        raise ForbiddenException("You can create job only for your own company")

    now = datetime.utcnow()
    job = Job(**payload.model_dump(), created_at=now, updated_at=now)
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def update_job(session: AsyncSession, job_id: int, payload: JobUpdate, current_user: User) -> Job:
    job = await get_job_or_404(session, job_id)
    company = await get_company_or_404(session, job.company_id)

    if current_user.role != "admin" and company.owner_id != current_user.id:
        raise ForbiddenException("You can update only your own job")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestException("At least one field must be provided for update")

    if "company_id" in data and data["company_id"] is not None:
        new_company = await get_company_or_404(session, data["company_id"])
        if current_user.role != "admin" and new_company.owner_id != current_user.id:
            raise ForbiddenException("You can move job only to your own company")

    for k, v in data.items():
        setattr(job, k, v)

    job.updated_at = datetime.utcnow()
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def delete_job(session: AsyncSession, job_id: int, current_user: User) -> None:
    job = await get_job_or_404(session, job_id)
    company = await get_company_or_404(session, job.company_id)

    if current_user.role != "admin" and company.owner_id != current_user.id:
        raise ForbiddenException("You can delete only your own job")

    if job.applications:
        raise BadRequestException("Cannot delete job with existing applications")

    await session.delete(job)
    await session.commit()