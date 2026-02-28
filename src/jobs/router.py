from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from src.db.session import get_session
from src.applications.models import Application
from src.applications.schemas import ApplicationRead

from .dependencies import job_by_id
from .models import Job
from .schemas import JobCreate, JobUpdate, JobRead
from .service import (
    list_jobs,
    create_job,
    put_job,
    patch_job,
    delete_job,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=list[JobRead])
async def api_list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(default=None, description="Search by job title"),
    is_open: bool | None = Query(default=None),
    company_id: int | None = Query(default=None, gt=0),
    session: AsyncSession = Depends(get_session),
):
    return await list_jobs(session, skip, limit, search, is_open, company_id)


@router.get("/{job_id}", response_model=JobRead)
async def api_get_job(
    job: Job = Depends(job_by_id),
):
    return job


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def api_create_job(
    payload: JobCreate,
    session: AsyncSession = Depends(get_session),
):
    return await create_job(session, payload)


@router.put("/{job_id}", response_model=JobRead)
async def api_put_job(
    payload: JobCreate,
    job: Job = Depends(job_by_id),
    session: AsyncSession = Depends(get_session),
):
    return await put_job(session, job.id, payload)


@router.patch("/{job_id}", response_model=JobRead)
async def api_patch_job(
    payload: JobUpdate,
    job: Job = Depends(job_by_id),
    session: AsyncSession = Depends(get_session),
):
    return await patch_job(session, job.id, payload)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_job(
    job: Job = Depends(job_by_id),
    session: AsyncSession = Depends(get_session),
):
    await delete_job(session, job.id)
    return None


@router.get("/{job_id}/applications", response_model=list[ApplicationRead])
async def api_job_applications(
    job: Job = Depends(job_by_id),
    session: AsyncSession = Depends(get_session),
):
    res = await session.exec(select(Application).where(Application.job_id == job.id).order_by(Application.id))
    return list(res.all())