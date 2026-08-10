from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> Admin | None:
        return await self._session.scalar(select(Admin).where(Admin.email == email))

    async def get_singleton(self) -> Admin | None:
        return await self._session.scalar(select(Admin).limit(1))

    async def count(self) -> int:
        result = await self._session.scalar(select(func.count()).select_from(Admin))
        return int(result or 0)

    async def create(self, email: str, hashed_password: str) -> Admin:
        admin = Admin(email=email, hashed_password=hashed_password)
        self._session.add(admin)
        await self._session.commit()
        await self._session.refresh(admin)
        return admin
