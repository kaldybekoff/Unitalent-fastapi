from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from src.db.session import get_session
from src.jobs.models import Job
from src.jobs.schemas import JobRead

from .dependencies import company_by_id
from .models import Company
from .schemas import CompanyCreate, CompanyUpdate, CompanyRead
from .service import (
    list_companies,
    create_company,
    put_company,
    patch_company,
    delete_company,
)

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get("", response_model=list[CompanyRead])
async def api_list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return await list_companies(session, skip, limit)


@router.get("/{company_id}", response_model=CompanyRead)
async def api_get_company(
    company: Company = Depends(company_by_id),
):
    return company


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def api_create_company(
    payload: CompanyCreate,
    session: AsyncSession = Depends(get_session),
):
    return await create_company(session, payload)


@router.put("/{company_id}", response_model=CompanyRead)
async def api_put_company(
    payload: CompanyCreate,
    company: Company = Depends(company_by_id),
    session: AsyncSession = Depends(get_session),
):
    return await put_company(session, company.id, payload)


@router.patch("/{company_id}", response_model=CompanyRead)
async def api_patch_company(
    payload: CompanyUpdate,
    company: Company = Depends(company_by_id),
    session: AsyncSession = Depends(get_session),
):
    return await patch_company(session, company.id, payload)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_company(
    company: Company = Depends(company_by_id),
    session: AsyncSession = Depends(get_session),
):
    await delete_company(session, company.id)
    return None


@router.get("/{company_id}/jobs", response_model=list[JobRead])
async def api_company_jobs(
    company: Company = Depends(company_by_id),
    session: AsyncSession = Depends(get_session),
):
    res = await session.exec(select(Job).where(Job.company_id == company.id).order_by(Job.id))
    return list(res.all())