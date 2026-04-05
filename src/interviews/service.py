from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.users.models import User
from src.applications.models import Application
from src.jobs.models import Job
from src.exceptions.custom_exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)

from .models import Interview, InterviewSession
from .schemas import InterviewCreate, InterviewSessionCreate, InterviewSessionPatch


def validate_interview_mode(mode: str, location: str | None, meeting_link: str | None) -> None:
    if mode not in {"online", "offline"}:
        raise BadRequestException("Mode must be either 'online' or 'offline'")
    if mode == "online" and not meeting_link:
        raise BadRequestException("Online interview requires meeting_link")
    if mode == "offline" and not location:
        raise BadRequestException("Offline interview requires location")


# ── InterviewSession CRUD ─────────────────────────────────────────────────────

async def list_sessions(
    db: AsyncSession,
    skip: int,
    limit: int,
    job_id: int | None,
) -> list[InterviewSession]:
    stmt = select(InterviewSession)
    if job_id is not None:
        stmt = stmt.where(InterviewSession.job_id == job_id)
    stmt = stmt.order_by(InterviewSession.id).offset(skip).limit(limit)
    res = await db.exec(stmt)
    return list(res.all())


async def get_session_or_404(db: AsyncSession, session_id: int) -> InterviewSession:
    obj = await db.get(InterviewSession, session_id)
    if not obj:
        raise NotFoundException(f"InterviewSession with id {session_id} not found")
    return obj


async def create_session(
    db: AsyncSession,
    payload: InterviewSessionCreate,
    current_user: User,
) -> InterviewSession:
    if current_user.role not in {"recruiter", "admin"}:
        raise ForbiddenException("Only recruiter or admin can create interview sessions")

    job = await db.get(Job, payload.job_id)
    if not job:
        raise NotFoundException(f"Job with id {payload.job_id} not found")

    if current_user.role != "admin" and job.company.owner_id != current_user.id:
        raise ForbiddenException("You can create sessions only for your own jobs")

    validate_interview_mode(payload.mode, payload.location, payload.meeting_link)

    now = datetime.utcnow()
    obj = InterviewSession(**payload.model_dump(), created_at=now, updated_at=now)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def patch_session(
    db: AsyncSession,
    session_id: int,
    payload: InterviewSessionPatch,
    current_user: User,
) -> InterviewSession:
    if current_user.role not in {"recruiter", "admin"}:
        raise ForbiddenException("Only recruiter or admin can update interview sessions")

    obj = await get_session_or_404(db, session_id)

    if current_user.role != "admin" and obj.job.company.owner_id != current_user.id:
        raise ForbiddenException("You can update only your own interview sessions")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestException("At least one field must be provided for update")

    new_mode = data.get("mode", obj.mode)
    new_location = data.get("location", obj.location)
    new_meeting_link = data.get("meeting_link", obj.meeting_link)
    validate_interview_mode(new_mode, new_location, new_meeting_link)

    for k, v in data.items():
        setattr(obj, k, v)

    obj.updated_at = datetime.utcnow()
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def delete_session(db: AsyncSession, session_id: int, current_user: User) -> None:
    if current_user.role not in {"recruiter", "admin"}:
        raise ForbiddenException("Only recruiter or admin can delete interview sessions")

    obj = await get_session_or_404(db, session_id)

    if current_user.role != "admin" and obj.job.company.owner_id != current_user.id:
        raise ForbiddenException("You can delete only your own interview sessions")

    if obj.interviews:
        raise BadRequestException(
            "Cannot delete session with assigned candidates. Remove all candidates first."
        )

    await db.delete(obj)
    await db.commit()


# ── Interview (candidate slots) CRUD ─────────────────────────────────────────

async def list_interviews(
    db: AsyncSession,
    skip: int,
    limit: int,
    session_id: int | None,
    application_id: int | None,
) -> list[Interview]:
    stmt = select(Interview)
    if session_id is not None:
        stmt = stmt.where(Interview.session_id == session_id)
    if application_id is not None:
        stmt = stmt.where(Interview.application_id == application_id)
    stmt = stmt.order_by(Interview.id).offset(skip).limit(limit)
    res = await db.exec(stmt)
    return list(res.all())


async def get_interview_or_404(db: AsyncSession, interview_id: int) -> Interview:
    obj = await db.get(Interview, interview_id)
    if not obj:
        raise NotFoundException(f"Interview with id {interview_id} not found")
    return obj


async def add_candidate_to_session(
    db: AsyncSession,
    payload: InterviewCreate,
    current_user: User,
) -> Interview:
    if current_user.role not in {"recruiter", "admin"}:
        raise ForbiddenException("Only recruiter or admin can add candidates to sessions")

    interview_session = await get_session_or_404(db, payload.session_id)

    if current_user.role != "admin" and interview_session.job.company.owner_id != current_user.id:
        raise ForbiddenException("You can manage only your own interview sessions")

    application = await db.get(Application, payload.application_id)
    if not application:
        raise NotFoundException(f"Application with id {payload.application_id} not found")

    if application.job_id != interview_session.job_id:
        raise BadRequestException("Application does not belong to the job of this session")

    if application.status == "rejected":
        raise BadRequestException("Cannot add a rejected application to an interview session")

    now = datetime.utcnow()
    interview = Interview(
        session_id=payload.session_id,
        application_id=payload.application_id,
        created_at=now,
        updated_at=now,
    )
    db.add(interview)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictException("This application is already added to this session")
    await db.refresh(interview)
    return interview


async def remove_candidate_from_session(
    db: AsyncSession,
    interview_id: int,
    current_user: User,
) -> None:
    if current_user.role not in {"recruiter", "admin"}:
        raise ForbiddenException("Only recruiter or admin can remove candidates from sessions")

    interview = await get_interview_or_404(db, interview_id)

    if current_user.role != "admin" and interview.session.job.company.owner_id != current_user.id:
        raise ForbiddenException("You can manage only your own interview sessions")

    await db.delete(interview)
    await db.commit()
