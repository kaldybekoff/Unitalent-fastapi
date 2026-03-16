from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import get_current_user
from src.db.session import get_session
from src.users.models import User

from .dependencies import resume_by_id
from .models import Resume
from .schemas import ResumeCreate, ResumeRead, ResumeUpdate
from .service import create_resume, delete_resume, list_resumes, update_resume

router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.get("", response_model=list[ResumeRead])
async def api_list_resumes(
    candidate_id: int | None = Query(default=None, gt=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return await list_resumes(session, candidate_id, skip, limit)


@router.get("/{resume_id}", response_model=ResumeRead)
async def api_get_resume(resume: Resume = Depends(resume_by_id)):
    return resume


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def api_create_resume(
    payload: ResumeCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await create_resume(session, payload, current_user)


@router.patch("/{resume_id}", response_model=ResumeRead)
async def api_patch_resume(
    payload: ResumeUpdate,
    resume: Resume = Depends(resume_by_id),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await update_resume(session, resume.id, payload, current_user)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_resume(
    resume: Resume = Depends(resume_by_id),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await delete_resume(session, resume.id, current_user)
    return None