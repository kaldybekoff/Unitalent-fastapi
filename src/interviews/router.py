from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import get_current_user
from src.db.session import get_session
from src.users.models import User

from .dependencies import interview_by_id
from .models import Interview
from .schemas import InterviewCreate, InterviewPatch, InterviewRead
from .service import create_interview, delete_interview, list_interviews, patch_interview

router = APIRouter(prefix="/interviews", tags=["Interviews"])


@router.get("", response_model=list[InterviewRead])
async def api_list_interviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    application_id: int | None = Query(default=None, gt=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"recruiter", "admin"}:
        from src.exceptions.custom_exceptions import ForbiddenException
        raise ForbiddenException("Only recruiter or admin can view interview list")

    return await list_interviews(session, skip, limit, application_id)


@router.get("/{interview_id}", response_model=InterviewRead)
async def api_get_interview(
    interview: Interview = Depends(interview_by_id),
    current_user: User = Depends(get_current_user),
):
    from src.exceptions.custom_exceptions import ForbiddenException

    if current_user.role == "admin":
        return interview

    if current_user.role == "recruiter":
        if interview.application.job.company.owner_id != current_user.id:
            raise ForbiddenException("You can view only your own interview")
        return interview

    if current_user.role == "candidate":
        if interview.application.candidate.user_id != current_user.id:
            raise ForbiddenException("You can view only your own interview")
        return interview

    raise ForbiddenException("You do not have permission for this action")


@router.post("", response_model=InterviewRead, status_code=status.HTTP_201_CREATED)
async def api_create_interview(
    payload: InterviewCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await create_interview(session, payload, current_user)


@router.patch("/{interview_id}", response_model=InterviewRead)
async def api_patch_interview(
    payload: InterviewPatch,
    interview: Interview = Depends(interview_by_id),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await patch_interview(session, interview.id, payload, current_user)


@router.delete("/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_interview(
    interview: Interview = Depends(interview_by_id),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await delete_interview(session, interview.id, current_user)
    return None