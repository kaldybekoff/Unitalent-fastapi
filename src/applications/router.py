from fastapi import APIRouter, Depends, Query, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import get_current_user
from src.db.session import get_session
from src.middleware.rate_limit import write_rate_limit
from src.users.models import User
from src.interviews.models import Interview
from src.interviews.schemas import InterviewRead
from src.candidates.service import get_candidate_by_user_id

from .dependencies import application_by_id
from .models import Application
from .schemas import ApplicationCreate, ApplicationPatch, ApplicationRead, ApplicationStatus
from .service import create_application, delete_application, list_applications, patch_application

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get("", response_model=list[ApplicationRead])
async def api_list_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    candidate_id: int | None = Query(default=None, gt=0),
    job_id: int | None = Query(default=None, gt=0),
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "candidate":
        candidate = await get_candidate_by_user_id(session, current_user.id)
        candidate_id = candidate.id if candidate else -1

    return await list_applications(session, skip, limit, candidate_id, job_id, status_filter)


@router.get("/{app_id}", response_model=ApplicationRead)
async def api_get_application(
    application: Application = Depends(application_by_id),
    current_user: User = Depends(get_current_user),
):
    from src.exceptions.custom_exceptions import ForbiddenException

    if current_user.role == "admin":
        return application

    if current_user.role == "candidate":
        if application.candidate.user_id != current_user.id:
            raise ForbiddenException("You can view only your own application")
        return application

    if current_user.role == "recruiter":
        if application.job.company.owner_id != current_user.id:
            raise ForbiddenException("You can view only applications for your own jobs")
        return application

    raise ForbiddenException("You do not have permission for this action")


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(write_rate_limit())])
async def api_create_application(
    payload: ApplicationCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await create_application(session, payload, current_user)


@router.patch("/{app_id}", response_model=ApplicationRead,
              dependencies=[Depends(write_rate_limit())])
async def api_patch_application(
    payload: ApplicationPatch,
    application: Application = Depends(application_by_id),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await patch_application(session, application.id, payload, current_user)


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(write_rate_limit())])
async def api_delete_application(
    application: Application = Depends(application_by_id),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await delete_application(session, application.id, current_user)
    return None


@router.get("/{app_id}/interviews", response_model=list[InterviewRead])
async def api_application_interviews(
    application: Application = Depends(application_by_id),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from src.exceptions.custom_exceptions import ForbiddenException

    if current_user.role == "candidate" and application.candidate.user_id != current_user.id:
        raise ForbiddenException("You can view only your own interview list")

    if current_user.role == "recruiter" and application.job.company.owner_id != current_user.id:
        raise ForbiddenException("You can view only interviews for your own jobs")

    res = await session.exec(select(Interview).where(Interview.application_id == application.id).order_by(Interview.id))
    return list(res.all())