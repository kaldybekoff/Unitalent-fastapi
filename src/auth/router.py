from fastapi import APIRouter, Depends, Header, Path, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.session import get_session
from src.users.models import User

from .dependencies import get_current_user
from .schemas import (
    LoginRequest,
    PasswordResetInitRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserRead,
)
from .service import (
    login_user,
    logout_user,
    refresh_user_tokens,
    register_user,
    request_email_verification,
    request_password_reset,
    reset_password,
    verify_email,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def api_register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    return await register_user(session, payload)


@router.post("/login", response_model=TokenPair)
async def api_login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    _, access_token, refresh_token = await login_user(session, payload)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
async def api_refresh(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    _, access_token, new_refresh_token = await refresh_user_tokens(session, payload.refresh_token)
    return TokenPair(access_token=access_token, refresh_token=new_refresh_token)


@router.get("/me", response_model=UserRead)
async def api_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def api_logout(
    authorization: str = Header(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    token = authorization.replace("Bearer ", "").strip()
    await logout_user(session, current_user, token)
    return None


# ── Email verification ────────────────────────────────────────────────────────

@router.post("/request-verification", status_code=status.HTTP_204_NO_CONTENT)
async def api_request_verification(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Resend email verification link to the current user."""
    await request_email_verification(session, current_user.id)
    return None


@router.post("/verify-email/{token}", response_model=UserRead)
async def api_verify_email(
    token: str = Path(...),
    session: AsyncSession = Depends(get_session),
):
    """Verify email using the token from the confirmation email."""
    return await verify_email(session, token)


# ── Password reset ────────────────────────────────────────────────────────────

@router.post("/request-password-reset", status_code=status.HTTP_204_NO_CONTENT)
async def api_request_password_reset(
    payload: PasswordResetInitRequest,
    session: AsyncSession = Depends(get_session),
):
    """Send password reset email. Always returns 204 to prevent email enumeration."""
    await request_password_reset(session, str(payload.email))
    return None


@router.post("/reset-password/{token}", response_model=UserRead)
async def api_reset_password(
    payload: PasswordResetRequest,
    token: str = Path(...),
    session: AsyncSession = Depends(get_session),
):
    """Set a new password using the token from the reset email."""
    return await reset_password(session, token, payload.new_password)
