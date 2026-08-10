import asyncio
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes

from app.models.chat import ChatMessage, ChatSession
from app.services.cache_service import cache_service


def _message_to_cache(message: ChatMessage) -> dict:
    return {
        "id": str(message.id),
        "session_id": str(message.session_id),
        "role": message.role,
        "text": message.text,
        "sources": message.sources or [],
        "created_at": message.created_at.isoformat(),
    }


def _message_from_cache(data: dict) -> ChatMessage:
    return ChatMessage(
        id=UUID(data["id"]),
        session_id=UUID(data["session_id"]),
        role=data["role"],
        text=data["text"],
        sources=data.get("sources") or [],
        created_at=datetime.fromisoformat(data["created_at"]),
    )


def _session_to_cache(session: ChatSession) -> dict:
    return {
        "id": str(session.id),
        "title": session.title,
        "created_at": session.created_at.isoformat(),
    }


def _session_from_cache(data: dict, user_id: UUID) -> ChatSession:
    return ChatSession(
        id=UUID(data["id"]),
        user_id=user_id,
        title=data["title"],
        created_at=datetime.fromisoformat(data["created_at"]),
    )


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(self, user_id: UUID, title: str) -> ChatSession:
        session = ChatSession(user_id=user_id, title=title[:255])
        self._session.add(session)
        await self._session.commit()
        await self._session.refresh(session)
        await asyncio.to_thread(
            cache_service.invalidate_session,
            str(session.id),
            str(user_id),
        )
        return session

    async def list_sessions(self, user_id: UUID, *, limit: int = 50) -> list[ChatSession]:
        cached = await asyncio.to_thread(cache_service.get_user_sessions, str(user_id))
        if cached is not None:
            return [_session_from_cache(item, user_id) for item in cached[:limit]]

        result = await self._session.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.created_at.desc())
            .limit(limit)
        )
        sessions = list(result.scalars().all())
        await asyncio.to_thread(
            cache_service.set_user_sessions,
            str(user_id),
            [_session_to_cache(session) for session in sessions],
        )
        return sessions

    async def get_session_for_user(self, session_id: UUID, user_id: UUID) -> ChatSession | None:
        return await self._session.scalar(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
        )

    async def list_messages(self, session_id: UUID, *, limit: int = 100) -> list[ChatMessage]:
        cached = await asyncio.to_thread(cache_service.get_session_messages, str(session_id))
        if cached is not None:
            messages = [_message_from_cache(item) for item in cached]
            return messages[-limit:]

        result = await self._session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        messages = list(result.scalars().all())
        if messages:
            await asyncio.to_thread(
                cache_service.set_session_messages,
                str(session_id),
                [_message_to_cache(message) for message in messages],
            )
        return messages

    async def get_session_with_messages(
        self,
        session_id: UUID,
        user_id: UUID,
        *,
        message_limit: int = 20,
    ) -> ChatSession | None:
        session = await self.get_session_for_user(session_id, user_id)
        if not session:
            return None

        cached = await asyncio.to_thread(cache_service.get_session_messages, str(session_id))
        if cached is not None:
            messages = [_message_from_cache(item) for item in cached]
        else:
            result = await self._session.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.asc())
            )
            messages = list(result.scalars().all())
            if messages:
                await asyncio.to_thread(
                    cache_service.set_session_messages,
                    str(session_id),
                    [_message_to_cache(message) for message in messages],
                )

        if len(messages) > message_limit:
            messages = messages[-message_limit:]
        attributes.set_committed_value(session, "messages", messages)
        return session

    async def add_message(
        self,
        session_id: UUID,
        *,
        role: str,
        text: str,
        sources: list[dict] | None = None,
        user_id: UUID | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            session_id=session_id,
            role=role,
            text=text,
            sources=sources or [],
        )
        self._session.add(message)
        await self._session.commit()
        await self._session.refresh(message)
        await asyncio.to_thread(
            cache_service.invalidate_session,
            str(session_id),
            str(user_id) if user_id else None,
        )
        return message

    async def delete_session(self, session_id: UUID, user_id: UUID) -> bool:
        session = await self.get_session_for_user(session_id, user_id)
        if not session:
            return False
        await self._session.delete(session)
        await self._session.commit()
        await asyncio.to_thread(cache_service.invalidate_session, str(session_id), str(user_id))
        return True
