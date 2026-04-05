from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.users.models import User
from src.candidates.service import get_candidate_by_user_id
from src.jobs.models import Job
from src.resumes.models import Resume
from src.exceptions.custom_exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)

from .models import Application
from .schemas import ApplicationCreate, ApplicationPatch


FINAL_STATUSES = {"accepted", "rejected"}


async def list_applications(
    session: AsyncSession,
    skip: int,
    limit: int,
    candidate_id: int | None,
    job_id: int | None,
    status_filter: str | None,
) -> list[Application]:
    stmt = select(Application)

    if candidate_id is not None:
        stmt = stmt.where(Application.candidate_id == candidate_id)
    if job_id is not None:
        stmt = stmt.where(Application.job_id == job_id)
    if status_filter is not None:
        stmt = stmt.where(Application.status == status_filter)

    stmt = stmt.order_by(Application.id).offset(skip).limit(limit)
    res = await session.exec(stmt)
    return list(res.all())


async def get_application_or_404(session: AsyncSession, app_id: int) -> Application:
    app_obj = await session.get(Application, app_id)
    if not app_obj:
        raise NotFoundException(f"Application with id {app_id} not found")
    return app_obj


async def get_job_or_404(session: AsyncSession, job_id: int) -> Job:
    job = await session.get(Job, job_id)
    if not job:
        raise NotFoundException(f"Job with id {job_id} not found")
    return job


async def get_resume_or_404(session: AsyncSession, resume_id: int) -> Resume:
    resume = await session.get(Resume, resume_id)
    if not resume:
        raise NotFoundException(f"Resume with id {resume_id} not found")
    return resume


async def ensure_no_duplicate(session: AsyncSession, candidate_id: int, job_id: int) -> None:
    stmt = select(Application).where(
        Application.candidate_id == candidate_id,
        Application.job_id == job_id,
    )
    res = await session.exec(stmt)
    if res.first():
        raise BadRequestException("Duplicate application is not allowed")


def validate_status_transition(old_status: str, new_status: str) -> None:
    allowed = {
        "submitted": {"reviewing", "rejected"},
        "reviewing": {"accepted", "rejected"},
        "accepted": set(),
        "rejected": set(),
    }

    if new_status == old_status:
        return

    if new_status not in allowed.get(old_status, set()):
        raise BadRequestException(f"Invalid status transition: {old_status} -> {new_status}")


async def create_application(session: AsyncSession, payload: ApplicationCreate, current_user: User) -> Application:
    if current_user.role != "candidate":
        raise ForbiddenException("Only candidate can apply for jobs")

    candidate = await get_candidate_by_user_id(session, current_user.id)
    if not candidate:
        raise BadRequestException("Candidate profile does not exist")

    job = await get_job_or_404(session, payload.job_id)
    if not job.is_open:
        raise BadRequestException("Cannot apply: job is closed")

    resume = await get_resume_or_404(session, payload.resume_id)
    if resume.candidate_id != candidate.id:
        raise ForbiddenException("You can use only your own resume")

    await ensure_no_duplicate(session, candidate.id, payload.job_id)

    now = datetime.utcnow()
    app_obj = Application(
        candidate_id=candidate.id,
        job_id=payload.job_id,
        resume_id=payload.resume_id,
        status="submitted",
        cover_letter=payload.cover_letter,
        created_at=now,
        updated_at=now,
    )
    session.add(app_obj)
    await session.commit()
    await session.refresh(app_obj)
    return app_obj


async def patch_application(
    session: AsyncSession,
    app_id: int,
    payload: ApplicationPatch,
    current_user: User,
) -> Application:
    application = await get_application_or_404(session, app_id)
    data = payload.model_dump(exclude_unset=True)

    if not data:
        raise BadRequestException("At least one field must be provided for update")

    if current_user.role == "candidate":
        candidate = await get_candidate_by_user_id(session, current_user.id)
        if not candidate or application.candidate_id != candidate.id:
            raise ForbiddenException("You can update only your own application")

        if "status" in data:
            raise ForbiddenException("Candidate cannot change application status")

        application.cover_letter = data.get("cover_letter", application.cover_letter)

    elif current_user.role in {"recruiter", "admin"}:
        if current_user.role != "admin" and application.job.company.owner_id != current_user.id:
            raise ForbiddenException("You can manage only applications for your own jobs")

        if "status" in data and data["status"] is not None:
            validate_status_transition(application.status, data["status"])
            application.status = data["status"]

        if "cover_letter" in data:
            application.cover_letter = data["cover_letter"]

    else:
        raise ForbiddenException("You do not have permission for this action")

    application.updated_at = datetime.utcnow()
    session.add(application)
    await session.commit()
    await session.refresh(application)

    # Notify candidate when status changes (background task)
    if "status" in data and data.get("status") and data["status"] != application.status:
        try:
            from src.tasks.email_tasks import send_application_status_email
            send_application_status_email.delay(
                application.candidate.user.email,
                application.candidate.full_name,
                application.job.title,
                application.job.company.name,
                application.status,
            )
        except Exception:
            pass  # Do not fail if Celery is unavailable

    return application


async def delete_application(session: AsyncSession, app_id: int, current_user: User) -> None:
    application = await get_application_or_404(session, app_id)

    if current_user.role == "candidate":
        candidate = await get_candidate_by_user_id(session, current_user.id)
        if not candidate or application.candidate_id != candidate.id:
            raise ForbiddenException("You can delete only your own application")
    elif current_user.role != "admin":
        raise ForbiddenException("You do not have permission to delete this application")

    if application.interviews:
        raise BadRequestException("Cannot delete application with existing interviews")

    await session.delete(application)
    await session.commit()