from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.core.security import decode_admin_token
from app.models.admin import Admin
from app.repositories.admin_repository import AdminRepository

oauth2_admin_scheme = OAuth2PasswordBearer(tokenUrl="/admin/login", auto_error=False)
admin_api_key_header = APIKeyHeader(name="X-Admin-Api-Key", auto_error=False)


async def get_current_admin(
    token: str | None = Depends(oauth2_admin_scheme),
    api_key: str | None = Depends(admin_api_key_header),
    db: AsyncSession = Depends(get_db),
) -> Admin:
    """Validate admin session token or cron API key. Never accepts public user tokens."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid admin credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    repo = AdminRepository(db)

    if api_key and settings.admin_api_key and api_key == settings.admin_api_key:
        admin = await repo.get_singleton()
        if admin:
            return admin
        raise credentials_exception

    if not token:
        raise credentials_exception

    try:
        payload = decode_admin_token(token)
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    admin = await repo.get_by_email(email)
    if admin is None:
        raise credentials_exception
    return admin
