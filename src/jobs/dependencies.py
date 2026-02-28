from fastapi import Depends, Path
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.session import get_session
from .models import Job
from .service import get_job_or_404


async def job_by_id(
    job_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_session),
) -> Job:
    return await get_job_or_404(session, job_id)
