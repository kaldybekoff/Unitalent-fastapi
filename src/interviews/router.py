from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import get_current_user
from src.db.session import get_session
from src.exceptions.custom_exceptions import ForbiddenException
from src.users.models import User

from .dependencies import interview_by_id, session_by_id
from .models import Interview, InterviewSession
from .schemas import (
    InterviewCreate,
    InterviewRead,
    InterviewSessionCreate,
    InterviewSessionPatch,
    InterviewSessionRead,
)
from .service import (
    add_candidate_to_session,
    create_session,
    delete_session,
    list_interviews,
    list_sessions,
    patch_session,
    remove_candidate_from_session,
)

router = APIRouter(tags=["Interviews"])


# ── Interview Sessions ────────────────────────────────────────────────────────

@router.get("/interview-sessions", response_model=list[InterviewSessionRead])
async def api_list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    job_id: int | None = Query(default=None, gt=0),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"recruiter", "admin"}:
        raise ForbiddenException("Only recruiter or admin can view interview sessions")
    return await list_sessions(db, skip, limit, job_id)


@router.get("/interview-sessions/{session_id}", response_model=InterviewSessionRead)
async def api_get_session(
    interview_session: InterviewSession = Depends(session_by_id),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "admin":
        return interview_session

    if current_user.role == "recruiter":
        if interview_session.job.company.owner_id != current_user.id:
            raise ForbiddenException("You can view only your own interview sessions")
        return interview_session

    if current_user.role == "candidate":
        for iv in interview_session.interviews:
            if iv.application.candidate.user_id == current_user.id:
                return interview_session
        raise ForbiddenException("You are not part of this interview session")

    raise ForbiddenException("You do not have permission for this action")


@router.post("/interview-sessions", response_model=InterviewSessionRead, status_code=status.HTTP_201_CREATED)
async def api_create_session(
    payload: InterviewSessionCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await create_session(db, payload, current_user)


@router.patch("/interview-sessions/{session_id}", response_model=InterviewSessionRead)
async def api_patch_session(
    payload: InterviewSessionPatch,
    interview_session: InterviewSession = Depends(session_by_id),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await patch_session(db, interview_session.id, payload, current_user)


@router.delete("/interview-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_session(
    interview_session: InterviewSession = Depends(session_by_id),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await delete_session(db, interview_session.id, current_user)
    return None


# ── Interviews (candidate slots) ──────────────────────────────────────────────

@router.get("/interviews", response_model=list[InterviewRead])
async def api_list_interviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session_id: int | None = Query(default=None, gt=0),
    application_id: int | None = Query(default=None, gt=0),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"recruiter", "admin"}:
        raise ForbiddenException("Only recruiter or admin can view interview list")
    return await list_interviews(db, skip, limit, session_id, application_id)


@router.get("/interviews/{interview_id}", response_model=InterviewRead)
async def api_get_interview(
    interview: Interview = Depends(interview_by_id),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "admin":
        return interview

    if current_user.role == "recruiter":
        if interview.session.job.company.owner_id != current_user.id:
            raise ForbiddenException("You can view only your own interview")
        return interview

    if current_user.role == "candidate":
        if interview.application.candidate.user_id != current_user.id:
            raise ForbiddenException("You can view only your own interview")
        return interview

    raise ForbiddenException("You do not have permission for this action")


@router.post("/interviews", response_model=InterviewRead, status_code=status.HTTP_201_CREATED)
async def api_add_candidate_to_session(
    payload: InterviewCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await add_candidate_to_session(db, payload, current_user)


@router.delete("/interviews/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_remove_candidate_from_session(
    interview: Interview = Depends(interview_by_id),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await remove_candidate_from_session(db, interview.id, current_user)
    return None
