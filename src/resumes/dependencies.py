from fastapi import Depends, Path
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.session import get_session

from .models import Resume
from .service import get_resume_or_404


async def resume_by_id(
    resume_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_session),
) -> Resume:
    return await get_resume_or_404(session, resume_id)