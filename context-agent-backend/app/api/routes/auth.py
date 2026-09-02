from jose import JWTError
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit_login
from app.core.security import (
    create_password_reset_token,
    create_user_token,
    decode_password_reset_token,
    hash_password,
    verify_password,
)
from app.core.user_auth import get_current_user
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    PasswordActionResponse,
    ResetPasswordRequest,
    UserLoginRequest,
    UserRead,
    UserRegisterRequest,
)
from app.services.email_service import EmailService

router = APIRouter(prefix="/auth", tags=["auth"])

# Cookie settings — driven by environment (requires SameSite=none and Secure=True across origins in production)
_COOKIE_MAX_AGE = settings.jwt_expire_minutes * 60
_COOKIE_SECURE = settings.environment.lower() == "production"
_COOKIE_SAMESITE = "none" if _COOKIE_SECURE else "lax"


def _set_auth_cookie(response: Response, token: str) -> None:
    """Write the JWT as an httpOnly cookie (H-2)."""
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=_COOKIE_MAX_AGE,
        samesite=_COOKIE_SAMESITE,
        secure=_COOKIE_SECURE,
        path="/",
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(rate_limit_login)])  # H-3: rate-limit register
async def register(payload: UserRegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    existing = await repo.get_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = await repo.create(payload.email, hash_password(payload.password))
    token = create_user_token(email=user.email)
    _set_auth_cookie(response, token)  # H-2: set httpOnly cookie instead of returning token
    return UserRead(id=str(user.id), email=user.email)


@router.post("/login", response_model=UserRead, dependencies=[Depends(rate_limit_login)])
async def login(payload: UserLoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    user = await repo.get_by_email(payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_user_token(email=user.email)
    _set_auth_cookie(response, token)  # H-2: set httpOnly cookie instead of returning token
    return UserRead(id=str(user.id), email=user.email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    """Clear the auth cookie (H-2)."""
    response.delete_cookie(
        key="access_token",
        path="/",
        samesite=_COOKIE_SAMESITE,
        secure=_COOKIE_SECURE,
    )


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return UserRead(id=str(current_user.id), email=current_user.email)


@router.post("/change-password", response_model=PasswordActionResponse)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password.",
        )

    repo = UserRepository(db)
    new_hashed = hash_password(payload.new_password)
    await repo.update_password(current_user, new_hashed)
    return PasswordActionResponse(message="Password changed successfully.")


@router.post(
    "/forgot-password",
    response_model=PasswordActionResponse,
    dependencies=[Depends(rate_limit_login)],
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    user = await repo.get_by_email(payload.email)
    if not user:
        # Generic response to prevent user enumeration
        return PasswordActionResponse(
            message="If this email is registered, a password reset link has been sent to your inbox."
        )

    reset_token = create_password_reset_token(user.email)
    reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={reset_token}"

    # Send email via SMTP in background
    await EmailService.send_password_reset_email(user.email, reset_url)

    return PasswordActionResponse(
        message="If this email is registered, a password reset link has been sent to your inbox."
    )


@router.post("/reset-password", response_model=PasswordActionResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    # M-7: Always return a generic 400 — never distinguish between "bad token" vs "user not found"
    # so an attacker cannot use this endpoint to confirm whether an email address is registered.
    invalid_exc = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired password reset token.",
    )
    try:
        token_payload = decode_password_reset_token(payload.token)
        email = token_payload.get("sub")
        if not email:
            raise invalid_exc
    except JWTError:
        raise invalid_exc

    repo = UserRepository(db)
    user = await repo.get_by_email(email)
    if not user:
        # M-7: Return the same generic error instead of 404 (prevents user enumeration)
        raise invalid_exc

    new_hashed = hash_password(payload.new_password)
    await repo.update_password(user, new_hashed)
    return PasswordActionResponse(
        message="Password reset successfully. You can now log in with your new password."
    )
