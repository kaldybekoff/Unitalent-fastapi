from fastapi import Depends, Path
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.session import get_session

from .models import Interview, InterviewSession
from .service import get_interview_or_404, get_session_or_404


async def interview_by_id(
    interview_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_session),
) -> Interview:
    return await get_interview_or_404(session, interview_id)


async def session_by_id(
    session_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_session),
) -> InterviewSession:
    return await get_session_or_404(db, session_id)
