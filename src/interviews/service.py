from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.users.models import User
from src.applications.models import Application
from src.exceptions.custom_exceptions import BadRequestException, ForbiddenException, NotFoundException

from .models import Interview
from .schemas import InterviewCreate, InterviewPatch


async def list_interviews(
    session: AsyncSession,
    skip: int,
    limit: int,
    application_id: int | None,
) -> list[Interview]:
    stmt = select(Interview)
    if application_id is not None:
        stmt = stmt.where(Interview.application_id == application_id)

    stmt = stmt.order_by(Interview.id).offset(skip).limit(limit)
    res = await session.exec(stmt)
    return list(res.all())


async def get_interview_or_404(session: AsyncSession, interview_id: int) -> Interview:
    obj = await session.get(Interview, interview_id)
    if not obj:
        raise NotFoundException(f"Interview with id {interview_id} not found")
    return obj


async def get_application_or_404(session: AsyncSession, app_id: int) -> Application:
    application = await session.get(Application, app_id)
    if not application:
        raise NotFoundException(f"Application with id {app_id} not found")
    return application


def validate_interview_mode(mode: str, location: str | None, meeting_link: str | None) -> None:
    if mode not in {"online", "offline"}:
        raise BadRequestException("Mode must be either 'online' or 'offline'")

    if mode == "online" and not meeting_link:
        raise BadRequestException("Online interview requires meeting_link")

    if mode == "offline" and not location:
        raise BadRequestException("Offline interview requires location")


async def create_interview(session: AsyncSession, payload: InterviewCreate, current_user: User) -> Interview:
    if current_user.role not in {"recruiter", "admin"}:
        raise ForbiddenException("Only recruiter or admin can create interviews")

    application = await get_application_or_404(session, payload.application_id)

    if application.status == "rejected":
        raise BadRequestException("Cannot create interview for rejected application")

    if current_user.role != "admin" and application.job.company.owner_id != current_user.id:
        raise ForbiddenException("You can create interview only for your own job application")

    validate_interview_mode(payload.mode, payload.location, payload.meeting_link)

    now = datetime.utcnow()
    interview = Interview(**payload.model_dump(), created_at=now, updated_at=now)
    session.add(interview)
    await session.commit()
    await session.refresh(interview)
    return interview


async def patch_interview(
    session: AsyncSession,
    interview_id: int,
    payload: InterviewPatch,
    current_user: User,
) -> Interview:
    if current_user.role not in {"recruiter", "admin"}:
        raise ForbiddenException("Only recruiter or admin can update interviews")

    interview = await get_interview_or_404(session, interview_id)

    if current_user.role != "admin" and interview.application.job.company.owner_id != current_user.id:
        raise ForbiddenException("You can update only your own interview")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestException("At least one field must be provided for update")

    new_mode = data.get("mode", interview.mode)
    new_location = data.get("location", interview.location)
    new_meeting_link = data.get("meeting_link", interview.meeting_link)

    validate_interview_mode(new_mode, new_location, new_meeting_link)

    for k, v in data.items():
        setattr(interview, k, v)

    interview.updated_at = datetime.utcnow()
    session.add(interview)
    await session.commit()
    await session.refresh(interview)
    return interview


async def delete_interview(session: AsyncSession, interview_id: int, current_user: User) -> None:
    if current_user.role not in {"recruiter", "admin"}:
        raise ForbiddenException("Only recruiter or admin can delete interviews")

    interview = await get_interview_or_404(session, interview_id)

    if current_user.role != "admin" and interview.application.job.company.owner_id != current_user.id:
        raise ForbiddenException("You can delete only your own interview")

    await session.delete(interview)
    await session.commit()