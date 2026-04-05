from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import settings
from src.db.session import get_session
from src.exceptions.custom_exceptions import UnauthorizedException, ForbiddenException
from redis.exceptions import RedisError

from src.cache.client import redis_client
from src.users.models import User

from .service import get_user_or_none

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        is_blocked = await redis_client.get(f"blocklist:{token}")
    except RedisError:
        is_blocked = None
    if is_blocked:
        raise UnauthorizedException("Token has been revoked")

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise UnauthorizedException("Invalid token") from exc

    if payload.get("type") != "access":
        raise UnauthorizedException("Invalid token type")

    user_id = int(payload["sub"])
    user = await get_user_or_none(session, user_id)
    if not user:
        raise UnauthorizedException("User not found")

    if not user.is_active:
        raise UnauthorizedException("User is inactive")

    return user


def require_roles(*roles: str):
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise ForbiddenException("You do not have permission for this action")
        return current_user

    return checker