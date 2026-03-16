from fastapi import Depends, Path
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.session import get_session

from .models import Company
from .service import get_company_or_404


async def company_by_id(
    company_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_session),
) -> Company:
    return await get_company_or_404(session, company_id)