from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.session import get_session

from .dependencies import interview_by_id
from .models import Interview
from .schemas import InterviewCreate, InterviewPut, InterviewPatch, InterviewRead
from .service import (
    list_interviews,
    create_interview,
    put_interview,
    patch_interview,
    delete_interview,
)

router = APIRouter(prefix="/interviews", tags=["Interviews"])


@router.get("", response_model=list[InterviewRead])
async def api_list_interviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    application_id: int | None = Query(default=None, gt=0),
    session: AsyncSession = Depends(get_session),
):
    return await list_interviews(session, skip, limit, application_id)


@router.get("/{interview_id}", response_model=InterviewRead)
async def api_get_interview(
    interview: Interview = Depends(interview_by_id),
):
    return interview


@router.post("", response_model=InterviewRead, status_code=status.HTTP_201_CREATED)
async def api_create_interview(
    payload: InterviewCreate,
    session: AsyncSession = Depends(get_session),
):
    return await create_interview(session, payload)


@router.put("/{interview_id}", response_model=InterviewRead)
async def api_put_interview(
    payload: InterviewPut,
    interview: Interview = Depends(interview_by_id),
    session: AsyncSession = Depends(get_session),
):
    return await put_interview(session, interview.id, payload)


@router.patch("/{interview_id}", response_model=InterviewRead)
async def api_patch_interview(
    payload: InterviewPatch,
    interview: Interview = Depends(interview_by_id),
    session: AsyncSession = Depends(get_session),
):
    return await patch_interview(session, interview.id, payload)


@router.delete("/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_interview(
    interview: Interview = Depends(interview_by_id),
    session: AsyncSession = Depends(get_session),
):
    await delete_interview(session, interview.id)
    return None