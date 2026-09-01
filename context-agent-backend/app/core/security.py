from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings

ADMIN_TOKEN_TYPE = "admin_session"
USER_TOKEN_TYPE = "user_session"
PASSWORD_RESET_TOKEN_TYPE = "password_reset"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_admin_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": email,
        "token_type": ADMIN_TOKEN_TYPE,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_admin_token(token: str) -> dict:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("token_type") != ADMIN_TOKEN_TYPE:
        raise JWTError("Invalid token type")
    return payload


def create_user_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": email,
        "token_type": USER_TOKEN_TYPE,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_user_token(token: str) -> dict:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("token_type") != USER_TOKEN_TYPE:
        raise JWTError("Invalid token type")
    return payload


def _password_reset_secret() -> str:
    """Return the dedicated password-reset secret, falling back to jwt_secret if unset."""
    return settings.password_reset_secret if settings.password_reset_secret else settings.jwt_secret


def create_password_reset_token(email: str, expire_minutes: int = 15) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {
        "sub": email.lower().strip(),
        "token_type": PASSWORD_RESET_TOKEN_TYPE,
        "exp": expire,
    }
    return jwt.encode(payload, _password_reset_secret(), algorithm=settings.jwt_algorithm)


def decode_password_reset_token(token: str) -> dict:
    payload = jwt.decode(token, _password_reset_secret(), algorithms=[settings.jwt_algorithm])
    if payload.get("token_type") != PASSWORD_RESET_TOKEN_TYPE:
        raise JWTError("Invalid token type")
    return payload
