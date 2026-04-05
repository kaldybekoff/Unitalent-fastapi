from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from src.config import settings
from src.exceptions.custom_exceptions import UnauthorizedException


def create_email_verification_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    return jwt.encode(
        {"sub": str(user_id), "type": "email_verify", "exp": expire},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def create_password_reset_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    return jwt.encode(
        {"sub": str(user_id), "type": "password_reset", "exp": expire},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def decode_token(token: str, expected_type: str) -> int:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise UnauthorizedException("Invalid or expired token") from exc

    if payload.get("type") != expected_type:
        raise UnauthorizedException("Invalid token type")

    return int(payload["sub"])
