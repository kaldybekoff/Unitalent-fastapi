from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import get_current_user, require_roles
from src.db.session import get_session
from src.exceptions.custom_exceptions import BadRequestException, ForbiddenException
from src.middleware.rate_limit import write_rate_limit
from src.users.models import User
from src.applications.models import Application
from src.applications.schemas import ApplicationRead

from .dependencies import candidate_by_id
from .models import Candidate
from .schemas import CandidateCreate, CandidateRead, CandidateUpdate
from .service import create_candidate, delete_candidate, list_candidates, update_candidate

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.get("", response_model=list[CandidateRead])
async def api_list_candidates(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_roles("admin", "recruiter")),
):
    return await list_candidates(session, skip, limit)


@router.get("/{candidate_id}", response_model=CandidateRead)
async def api_get_candidate(candidate: Candidate = Depends(candidate_by_id)):
    return candidate


@router.post("", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
async def api_create_candidate(
    payload: CandidateCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await create_candidate(session, payload, current_user)


@router.patch("/{candidate_id}", response_model=CandidateRead)
async def api_patch_candidate(
    payload: CandidateUpdate,
    candidate: Candidate = Depends(candidate_by_id),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await update_candidate(session, candidate.id, payload, current_user)


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_candidate(
    candidate: Candidate = Depends(candidate_by_id),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await delete_candidate(session, candidate.id, current_user)
    return None


@router.get("/{candidate_id}/applications", response_model=list[ApplicationRead])
async def api_candidate_applications(
    candidate: Candidate = Depends(candidate_by_id),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"admin", "recruiter"} and candidate.user_id != current_user.id:
        from src.exceptions.custom_exceptions import ForbiddenException
        raise ForbiddenException("You can view only your own applications")

    res = await session.exec(
        select(Application).where(Application.candidate_id == candidate.id).order_by(Application.id)
    )
    return list(res.all())


@router.post(
    "/{candidate_id}/photo",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(write_rate_limit())],
)
async def api_upload_photo(
    candidate: Candidate = Depends(candidate_by_id),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload a profile photo. Compression and storage are handled asynchronously by Celery."""
    if current_user.role not in {"admin"} and candidate.user_id != current_user.id:
        raise ForbiddenException("You can upload photos only to your own profile")

    allowed = {"image/jpeg", "image/png", "image/jpg"}
    if file.content_type not in allowed:
        raise BadRequestException("Only JPEG and PNG images are allowed")

    raw = await file.read()
    max_size = 5 * 1024 * 1024  # 5 MB
    if len(raw) > max_size:
        raise BadRequestException("File size exceeds 5 MB limit")

    from src.tasks.image_tasks import compress_and_store_photo
    compress_and_store_photo.delay(candidate.id, raw)

    return {"message": "Photo upload accepted — compression and storage are processing in background"}