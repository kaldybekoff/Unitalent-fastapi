from fastapi import Depends, Path
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.session import get_session

from .models import Interview
from .service import get_interview_or_404


async def interview_by_id(
    interview_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_session),
) -> Interview:
    return await get_interview_or_404(session, interview_id)