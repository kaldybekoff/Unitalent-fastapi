from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .models import Company
from .schemas import CompanyCreate, CompanyUpdate


async def list_companies(session: AsyncSession, skip: int, limit: int) -> list[Company]:
    res = await session.exec(select(Company).offset(skip).limit(limit).order_by(Company.id))
    return list(res.all())


async def get_company_or_404(session: AsyncSession, company_id: int) -> Company:
    company = await session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company with id {company_id} not found")
    return company


async def create_company(session: AsyncSession, payload: CompanyCreate) -> Company:
    now = datetime.utcnow()
    company = Company(**payload.model_dump(), created_at=now, updated_at=now)
    session.add(company)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Company with this name already exists")

    await session.refresh(company)
    return company


async def put_company(session: AsyncSession, company_id: int, payload: CompanyCreate) -> Company:
    existing = await get_company_or_404(session, company_id)
    now = datetime.utcnow()

    existing.name = payload.name
    existing.industry = payload.industry
    existing.website = payload.website
    existing.updated_at = now

    session.add(existing)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Company with this name already exists")

    await session.refresh(existing)
    return existing


async def patch_company(session: AsyncSession, company_id: int, payload: CompanyUpdate) -> Company:
    existing = await get_company_or_404(session, company_id)
    data = payload.model_dump(exclude_unset=True)

    if not data:
        raise HTTPException(status_code=400, detail="At least one field must be provided for update")

    for k, v in data.items():
        setattr(existing, k, v)

    existing.updated_at = datetime.utcnow()

    session.add(existing)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Company with this name already exists")

    await session.refresh(existing)
    return existing


async def delete_company(session: AsyncSession, company_id: int) -> None:
    existing = await get_company_or_404(session, company_id)
    await session.delete(existing)
    await session.commit()