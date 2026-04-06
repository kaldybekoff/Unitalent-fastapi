from datetime import datetime, timezone

from redis.exceptions import RedisError
from jose import JWTError, jwt
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import settings
from src.users.models import User
from src.exceptions.custom_exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from src.cache.client import redis_client

from .schemas import LoginRequest, RegisterRequest
from .tokens import create_email_verification_token, create_password_reset_token, decode_token
from .utils import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.exec(select(User).where(User.email == email))
    return result.first()


async def get_user_or_none(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def register_user(session: AsyncSession, payload: RegisterRequest) -> User:
    existing = await get_user_by_email(session, payload.email)
    if existing:
        raise ConflictException("User with this email already exists")

    if payload.role not in {"candidate", "recruiter", "admin"}:
        raise BadRequestException("Invalid role")

    now = datetime.utcnow()
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
        is_verified=False,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Fire-and-forget email verification via Celery (candidates only)
    if user.role == "candidate":
        try:
            from src.tasks.email_tasks import send_confirmation_email
            token = create_email_verification_token(user.id)
            send_confirmation_email.delay(user.id, user.email, token)
        except Exception:
            pass  # Do not block registration if Celery/email is unavailable

    return user


async def login_user(session: AsyncSession, payload: LoginRequest) -> tuple[User, str, str]:
    user = await get_user_by_email(session, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise UnauthorizedException("Invalid email or password")

    if not user.is_active:
        raise UnauthorizedException("User is inactive")

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id, user.role)

    user.refresh_token = refresh_token
    user.updated_at = datetime.utcnow()

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user, access_token, refresh_token


async def refresh_user_tokens(session: AsyncSession, refresh_token: str) -> tuple[User, str, str]:
    try:
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise UnauthorizedException("Invalid refresh token") from exc

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid token type")

    user_id = int(payload["sub"])
    user = await get_user_or_none(session, user_id)

    if not user:
        raise UnauthorizedException("User not found")

    if not user.is_active:
        raise UnauthorizedException("User is inactive")

    if user.refresh_token != refresh_token:
        raise UnauthorizedException("Refresh token is invalid or expired")

    new_access = create_access_token(user.id, user.role)
    new_refresh = create_refresh_token(user.id, user.role)

    user.refresh_token = new_refresh
    user.updated_at = datetime.utcnow()

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user, new_access, new_refresh


async def logout_user(session: AsyncSession, user: User, access_token: str) -> None:
    try:
        payload = jwt.decode(access_token, settings.secret_key, algorithms=[settings.algorithm])
        exp = payload.get("exp")
        if exp:
            ttl = int(exp - datetime.now(timezone.utc).timestamp())
            if ttl > 0:
                try:
                    await redis_client.setex(f"blocklist:{access_token}", ttl, "1")
                except RedisError:
                    pass
    except JWTError:
        pass

    user.refresh_token = None
    user.updated_at = datetime.utcnow()
    session.add(user)
    await session.commit()


# ── Email verification ────────────────────────────────────────────────────────

async def request_email_verification(session: AsyncSession, user_id: int) -> None:
    user = await session.get(User, user_id)
    if not user:
        raise NotFoundException("User not found")
    if user.is_verified:
        raise BadRequestException("Email is already verified")
    token = create_email_verification_token(user.id)
    from src.tasks.email_tasks import send_confirmation_email
    send_confirmation_email.delay(user.id, user.email, token)


async def verify_email(session: AsyncSession, token: str) -> User:
    user_id = decode_token(token, expected_type="email_verify")
    user = await session.get(User, user_id)
    if not user:
        raise NotFoundException("User not found")
    if user.is_verified:
        raise BadRequestException("Email is already verified")
    user.is_verified = True
    user.updated_at = datetime.utcnow()
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# ── Password reset ────────────────────────────────────────────────────────────

async def request_password_reset(session: AsyncSession, email: str) -> None:
    user = await get_user_by_email(session, email)
    if not user:
        return  # Silent — prevent email enumeration
    token = create_password_reset_token(user.id)
    from src.tasks.email_tasks import send_password_reset_email
    send_password_reset_email.delay(user.id, user.email, token)


async def reset_password(session: AsyncSession, token: str, new_password: str) -> User:
    user_id = decode_token(token, expected_type="password_reset")
    user = await session.get(User, user_id)
    if not user:
        raise NotFoundException("User not found")
    user.hashed_password = hash_password(new_password)
    user.refresh_token = None  # Invalidate all sessions
    user.updated_at = datetime.utcnow()
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
