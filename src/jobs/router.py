from fastapi import APIRouter, Depends, Query, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import get_current_user
from src.db.session import get_session
from src.users.models import User
from src.applications.models import Application
from src.applications.schemas import ApplicationRead

from .dependencies import job_by_id
from .models import Job
from .schemas import JobCreate, JobRead, JobUpdate
from .service import create_job, delete_job, list_jobs, update_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=list[JobRead])
async def api_list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(default=None),
    is_open: bool | None = Query(default=None),
    company_id: int | None = Query(default=None, gt=0),
    sort_by: str = Query(default="id", pattern="^(id|title|created_at)$"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    session: AsyncSession = Depends(get_session),
):
    return await list_jobs(session, skip, limit, search, is_open, company_id, sort_by, sort_order)


@router.get("/{job_id}", response_model=JobRead)
async def api_get_job(job: Job = Depends(job_by_id)):
    return job


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def api_create_job(
    payload: JobCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await create_job(session, payload, current_user)


@router.patch("/{job_id}", response_model=JobRead)
async def api_patch_job(
    payload: JobUpdate,
    job: Job = Depends(job_by_id),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await update_job(session, job.id, payload, current_user)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_job(
    job: Job = Depends(job_by_id),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await delete_job(session, job.id, current_user)
    return None


@router.get("/{job_id}/applications", response_model=list[ApplicationRead])
async def api_job_applications(
    job: Job = Depends(job_by_id),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"recruiter", "admin"}:
        from src.exceptions.custom_exceptions import ForbiddenException
        raise ForbiddenException("Only recruiter or admin can view job applications")

    if current_user.role != "admin" and job.company.owner_id != current_user.id:
        from src.exceptions.custom_exceptions import ForbiddenException
        raise ForbiddenException("You can view applications only for your own jobs")

    res = await session.exec(select(Application).where(Application.job_id == job.id).order_by(Application.id))
    return list(res.all())