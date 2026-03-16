from fastapi import Depends, Path
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.session import get_session

from .models import Candidate
from .service import get_candidate_or_404


async def candidate_by_id(
    candidate_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_session),
) -> Candidate:
    return await get_candidate_or_404(session, candidate_id)