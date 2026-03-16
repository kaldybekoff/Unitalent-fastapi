from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.users.models import User
from src.exceptions.custom_exceptions import BadRequestException, ForbiddenException, NotFoundException
from src.candidates.service import get_candidate_by_user_id

from .models import Resume
from .schemas import ResumeCreate, ResumeUpdate


async def list_resumes(session: AsyncSession, candidate_id: int | None, skip: int, limit: int) -> list[Resume]:
    stmt = select(Resume)
    if candidate_id is not None:
        stmt = stmt.where(Resume.candidate_id == candidate_id)

    stmt = stmt.order_by(Resume.id).offset(skip).limit(limit)
    res = await session.exec(stmt)
    return list(res.all())


async def get_resume_or_404(session: AsyncSession, resume_id: int) -> Resume:
    resume = await session.get(Resume, resume_id)
    if not resume:
        raise NotFoundException(f"Resume with id {resume_id} not found")
    return resume


async def create_resume(session: AsyncSession, payload: ResumeCreate, current_user: User) -> Resume:
    if current_user.role != "candidate":
        raise ForbiddenException("Only candidate users can create resumes")

    candidate = await get_candidate_by_user_id(session, current_user.id)
    if not candidate:
        raise BadRequestException("Candidate profile does not exist")

    now = datetime.utcnow()
    resume = Resume(
        candidate_id=candidate.id,
        title=payload.title,
        summary=payload.summary,
        skills=payload.skills,
        education=payload.education,
        experience=payload.experience,
        is_active=payload.is_active,
        created_at=now,
        updated_at=now,
    )
    session.add(resume)
    await session.commit()
    await session.refresh(resume)
    return resume


async def update_resume(
    session: AsyncSession,
    resume_id: int,
    payload: ResumeUpdate,
    current_user: User,
) -> Resume:
    resume = await get_resume_or_404(session, resume_id)

    if current_user.role != "admin":
        candidate = await get_candidate_by_user_id(session, current_user.id)
        if not candidate or resume.candidate_id != candidate.id:
            raise ForbiddenException("You can update only your own resume")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestException("At least one field must be provided for update")

    for k, v in data.items():
        setattr(resume, k, v)

    resume.updated_at = datetime.utcnow()
    session.add(resume)
    await session.commit()
    await session.refresh(resume)
    return resume


async def delete_resume(session: AsyncSession, resume_id: int, current_user: User) -> None:
    resume = await get_resume_or_404(session, resume_id)

    if current_user.role != "admin":
        candidate = await get_candidate_by_user_id(session, current_user.id)
        if not candidate or resume.candidate_id != candidate.id:
            raise ForbiddenException("You can delete only your own resume")

    if resume.applications:
        raise BadRequestException("Cannot delete resume that is used in applications")

    await session.delete(resume)
    await session.commit()