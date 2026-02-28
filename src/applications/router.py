from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from src.db.session import get_session
from src.interviews.models import Interview
from src.interviews.schemas import InterviewRead

from .dependencies import application_by_id
from .models import Application
from .schemas import ApplicationCreate, ApplicationPut, ApplicationPatch, ApplicationRead, ApplicationStatus
from .service import (
    list_applications,
    create_application,
    put_application,
    patch_application,
    delete_application,
)

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get("", response_model=list[ApplicationRead])
async def api_list_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    candidate_id: int | None = Query(default=None, gt=0),
    job_id: int | None = Query(default=None, gt=0),
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
):
    return await list_applications(session, skip, limit, candidate_id, job_id, status_filter)


@router.get("/{app_id}", response_model=ApplicationRead)
async def api_get_application(
    application: Application = Depends(application_by_id),
):
    return application


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def api_create_application(
    payload: ApplicationCreate,
    session: AsyncSession = Depends(get_session),
):
    return await create_application(session, payload)


@router.put("/{app_id}", response_model=ApplicationRead)
async def api_put_application(
    payload: ApplicationPut,
    application: Application = Depends(application_by_id),
    session: AsyncSession = Depends(get_session),
):
    return await put_application(session, application.id, payload)


@router.patch("/{app_id}", response_model=ApplicationRead)
async def api_patch_application(
    payload: ApplicationPatch,
    application: Application = Depends(application_by_id),
    session: AsyncSession = Depends(get_session),
):
    return await patch_application(session, application.id, payload)


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_application(
    application: Application = Depends(application_by_id),
    session: AsyncSession = Depends(get_session),
):
    await delete_application(session, application.id)
    return None


@router.get("/{app_id}/interviews", response_model=list[InterviewRead])
async def api_application_interviews(
    application: Application = Depends(application_by_id),
    session: AsyncSession = Depends(get_session),
):
    res = await session.exec(select(Interview).where(Interview.application_id == application.id).order_by(Interview.id))
    return list(res.all())