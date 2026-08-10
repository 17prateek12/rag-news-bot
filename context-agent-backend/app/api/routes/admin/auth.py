from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_auth import get_current_admin
from app.core.database import get_db
from app.core.security import create_admin_token, verify_password
from app.models.admin import Admin
from app.repositories.admin_repository import AdminRepository
from app.schemas.admin import AdminLoginRequest, AdminRead, AdminTokenResponse

router = APIRouter(prefix="/admin", tags=["admin-auth"])


@router.post("/login", response_model=AdminTokenResponse)
async def admin_login(payload: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    repo = AdminRepository(db)
    admin = await repo.get_by_email(payload.email)
    if not admin or not verify_password(payload.password, admin.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_admin_token(email=admin.email)
    return AdminTokenResponse(access_token=token)


@router.get("/me", response_model=AdminRead)
async def admin_me(current_admin: Admin = Depends(get_current_admin)):
    return AdminRead(id=str(current_admin.id), email=current_admin.email)
