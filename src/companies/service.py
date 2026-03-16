from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.users.models import User
from src.exceptions.custom_exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)

from .models import Company
from .schemas import CompanyCreate, CompanyUpdate


async def list_companies(
    session: AsyncSession,
    skip: int,
    limit: int,
    search: str | None,
    sort_by: str,
    sort_order: str,
) -> list[Company]:
    stmt = select(Company)

    if search:
        stmt = stmt.where(Company.name.ilike(f"%{search.strip()}%"))

    order_column = Company.id
    if sort_by == "name":
        order_column = Company.name
    elif sort_by == "created_at":
        order_column = Company.created_at

    stmt = stmt.order_by(order_column.desc() if sort_order == "desc" else order_column.asc())
    stmt = stmt.offset(skip).limit(limit)

    res = await session.exec(stmt)
    return list(res.all())


async def get_company_or_404(session: AsyncSession, company_id: int) -> Company:
    company = await session.get(Company, company_id)
    if not company:
        raise NotFoundException(f"Company with id {company_id} not found")
    return company


async def create_company(session: AsyncSession, payload: CompanyCreate, current_user: User) -> Company:
    if current_user.role not in {"recruiter", "admin"}:
        raise ForbiddenException("Only recruiter or admin can create company")

    now = datetime.utcnow()
    company = Company(
        owner_id=current_user.id,
        name=payload.name,
        industry=payload.industry,
        website=payload.website,
        created_at=now,
        updated_at=now,
    )
    session.add(company)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictException("Company with this name already exists") from exc

    await session.refresh(company)
    return company


async def update_company(
    session: AsyncSession,
    company_id: int,
    payload: CompanyUpdate,
    current_user: User,
) -> Company:
    company = await get_company_or_404(session, company_id)

    if current_user.role != "admin" and company.owner_id != current_user.id:
        raise ForbiddenException("You can update only your own company")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestException("At least one field must be provided for update")

    for k, v in data.items():
        setattr(company, k, v)

    company.updated_at = datetime.utcnow()
    session.add(company)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictException("Company with this name already exists") from exc

    await session.refresh(company)
    return company


async def delete_company(session: AsyncSession, company_id: int, current_user: User) -> None:
    company = await get_company_or_404(session, company_id)

    if current_user.role != "admin" and company.owner_id != current_user.id:
        raise ForbiddenException("You can delete only your own company")

    if company.jobs:
        raise BadRequestException("Cannot delete company with existing jobs")

    await session.delete(company)
    await session.commit()