from fastapi import APIRouter, Depends, Query, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.dependencies import get_current_user
from src.db.session import get_session
from src.middleware.rate_limit import write_rate_limit
from src.users.models import User
from src.jobs.models import Job
from src.jobs.schemas import JobRead

from .dependencies import company_by_id
from .models import Company
from .schemas import CompanyCreate, CompanyRead, CompanyUpdate
from .service import create_company, delete_company, list_companies, update_company

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get("", response_model=list[CompanyRead])
async def api_list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(default=None),
    sort_by: str = Query(default="id", pattern="^(id|name|created_at)$"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    session: AsyncSession = Depends(get_session),
):
    return await list_companies(session, skip, limit, search, sort_by, sort_order)


@router.get("/{company_id}", response_model=CompanyRead)
async def api_get_company(company: Company = Depends(company_by_id)):
    return company


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(write_rate_limit())])
async def api_create_company(
    payload: CompanyCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await create_company(session, payload, current_user)


@router.patch("/{company_id}", response_model=CompanyRead,
              dependencies=[Depends(write_rate_limit())])
async def api_patch_company(
    payload: CompanyUpdate,
    company: Company = Depends(company_by_id),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await update_company(session, company.id, payload, current_user)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(write_rate_limit())])
async def api_delete_company(
    company: Company = Depends(company_by_id),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await delete_company(session, company.id, current_user)
    return None


@router.get("/{company_id}/jobs", response_model=list[JobRead])
async def api_company_jobs(
    company: Company = Depends(company_by_id),
    session: AsyncSession = Depends(get_session),
):
    res = await session.exec(select(Job).where(Job.company_id == company.id).order_by(Job.id))
    return list(res.all())