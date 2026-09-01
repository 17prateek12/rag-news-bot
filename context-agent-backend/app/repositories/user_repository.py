from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        return await self._session.scalar(select(User).where(User.email == email))

    async def get_by_id(self, user_id) -> User | None:
        return await self._session.get(User, user_id)

    async def create(self, email: str, hashed_password: str) -> User:
        user = User(email=email.lower().strip(), hashed_password=hashed_password)
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def count(self) -> int:
        result = await self._session.scalar(select(func.count()).select_from(User))
        return int(result or 0)

    async def update_password(self, user: User, new_hashed_password: str) -> None:
        user.hashed_password = new_hashed_password
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
