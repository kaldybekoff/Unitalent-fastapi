from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from src.db.session import get_session
from src.applications.models import Application
from src.applications.schemas import ApplicationRead

from .dependencies import candidate_by_id
from .models import Candidate
from .schemas import CandidateCreate, CandidateUpdate, CandidateRead
from .service import (
    list_candidates,
    create_candidate,
    put_candidate,
    patch_candidate,
    delete_candidate,
)

router = APIRouter(
    prefix="/candidates",
    tags=["Candidates"],
)


@router.get("", response_model=list[CandidateRead])
async def api_list_candidates(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return await list_candidates(session, skip, limit)


@router.get("/{candidate_id}", response_model=CandidateRead)
async def api_get_candidate(
    candidate: Candidate = Depends(candidate_by_id),
):
    return candidate


@router.post("", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
async def api_create_candidate(
    payload: CandidateCreate,
    session: AsyncSession = Depends(get_session),
):
    return await create_candidate(session, payload)


@router.put("/{candidate_id}", response_model=CandidateRead)
async def api_put_candidate(
    payload: CandidateCreate,
    candidate: Candidate = Depends(candidate_by_id),
    session: AsyncSession = Depends(get_session),
):
    return await put_candidate(session, candidate.id, payload)


@router.patch("/{candidate_id}", response_model=CandidateRead)
async def api_patch_candidate(
    payload: CandidateUpdate,
    candidate: Candidate = Depends(candidate_by_id),
    session: AsyncSession = Depends(get_session),
):
    return await patch_candidate(session, candidate.id, payload)


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_candidate(
    candidate: Candidate = Depends(candidate_by_id),
    session: AsyncSession = Depends(get_session),
):
    await delete_candidate(session, candidate.id)
    return None


@router.get("/{candidate_id}/applications", response_model=list[ApplicationRead])
async def api_candidate_applications(
    candidate: Candidate = Depends(candidate_by_id),
    session: AsyncSession = Depends(get_session),
):
    res = await session.exec(
        select(Application).where(Application.candidate_id == candidate.id).order_by(Application.id)
    )
    return list(res.all())