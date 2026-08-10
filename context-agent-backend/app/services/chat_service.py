import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import ChatMessageRead, ChatSendResponse
from app.schemas.intent import ChatTurn
from app.services.rag_service import RAGService
from app.services.stt_service import stt_service

logger = logging.getLogger(__name__)

DEFAULT_SESSION_TITLE = "New chat"
MAX_HISTORY_TURNS = 12


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._chat_repo = ChatRepository(session)
        self._rag = RAGService(session)

    def _to_message_read(self, message) -> ChatMessageRead:
        return ChatMessageRead(
            id=message.id,
            role=message.role,
            text=message.text,
            sources=message.sources or [],
            created_at=message.created_at,
        )

    def _history_from_messages(self, messages: list) -> list[ChatTurn]:
        history: list[ChatTurn] = []
        for message in messages[-MAX_HISTORY_TURNS:]:
            if message.role not in ("user", "assistant"):
                continue
            history.append(ChatTurn(role=message.role, text=message.text))
        return history

    def _sources_snapshot(self, sources: list) -> list[dict]:
        return [
            {
                "index": source.index,
                "title": source.title,
                "source": source.source,
                "url": source.url,
                "publish_date": source.publish_date,
                "excerpt": source.excerpt,
            }
            for source in sources
        ]

    async def send_message(
        self,
        user: User,
        session_id: UUID,
        query: str,
        *,
        limit: int = 6,
        track_trending: bool = True,
    ) -> ChatSendResponse:
        chat_session = await self._chat_repo.get_session_with_messages(
            session_id,
            user.id,
            message_limit=MAX_HISTORY_TURNS,
        )
        if not chat_session:
            raise NotFoundError("Chat session not found", details={"session_id": str(session_id)})

        is_first_message = len(chat_session.messages) == 0
        history = self._history_from_messages(chat_session.messages)
        logger.info(
            "Chat send session_id=%s user_id=%s history_turns=%s",
            session_id,
            user.id,
            len(history),
        )

        rag = await self._rag.query(query, limit=limit, history=history, track_trending=track_trending)

        user_message = await self._chat_repo.add_message(
            session_id,
            role="user",
            text=query,
            user_id=user.id,
        )
        assistant_message = await self._chat_repo.add_message(
            session_id,
            role="assistant",
            text=rag.answer,
            sources=self._sources_snapshot(rag.sources),
            user_id=user.id,
        )

        if is_first_message and chat_session.title == DEFAULT_SESSION_TITLE:
            chat_session.title = query.strip()[:80] or DEFAULT_SESSION_TITLE
            await self._session.commit()

        return ChatSendResponse.from_rag(
            session_id=session_id,
            user_message=self._to_message_read(user_message),
            assistant_message=self._to_message_read(assistant_message),
            rag=rag,
            input_mode="text",
        )

    async def send_voice_message(
        self,
        user: User,
        session_id: UUID,
        audio_bytes: bytes,
        *,
        mime_type: str | None = None,
        filename: str | None = None,
        limit: int = 6,
    ) -> ChatSendResponse:
        transcript, _ = await asyncio.to_thread(
            stt_service.transcribe,
            audio_bytes,
            mime_type=mime_type,
            filename=filename,
        )
        response = await self.send_message(
            user,
            session_id,
            transcript,
            limit=limit,
            track_trending=False,
        )
        return response.model_copy(update={"input_mode": "audio", "transcript": transcript})

    async def create_session(self, user: User, title: str | None = None) -> UUID:
        session = await self._chat_repo.create_session(
            user.id,
            title=title or DEFAULT_SESSION_TITLE,
        )
        return session.id
