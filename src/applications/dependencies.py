from fastapi import Depends, Path
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.session import get_session

from .models import Application
from .service import get_application_or_404


async def application_by_id(
    app_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_session),
) -> Application:
    return await get_application_or_404(session, app_id)