from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.user_auth import get_current_user
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import (
    ChatMessageRead,
    ChatSendRequest,
    ChatSendResponse,
    ChatSessionCreate,
    ChatSessionRead,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ChatService(db)
    session_id = await service.create_session(current_user, title=payload.title)
    repo = ChatRepository(db)
    session = await repo.get_session_for_user(session_id, current_user.id)
    return ChatSessionRead(id=session.id, title=session.title, created_at=session.created_at)


@router.get("/sessions", response_model=list[ChatSessionRead])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ChatRepository(db)
    sessions = await repo.list_sessions(current_user.id)
    return [
        ChatSessionRead(id=session.id, title=session.title, created_at=session.created_at)
        for session in sessions
    ]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageRead])
async def list_messages(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ChatRepository(db)
    session = await repo.get_session_for_user(session_id, current_user.id)
    if not session:
        raise NotFoundError("Chat session not found", details={"session_id": str(session_id)})
    messages = await repo.list_messages(session_id)
    return [
        ChatMessageRead(
            id=message.id,
            role=message.role,
            text=message.text,
            sources=message.sources or [],
            created_at=message.created_at,
        )
        for message in messages
    ]


@router.post("/sessions/{session_id}/messages", response_model=ChatSendResponse)
async def send_message(
    session_id: UUID,
    payload: ChatSendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ChatService(db)
    return await service.send_message(
        current_user,
        session_id,
        payload.query,
        limit=payload.limit,
    )


@router.post("/sessions/{session_id}/messages/stream")
async def send_message_stream(
    session_id: UUID,
    payload: ChatSendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ChatService(db)
    return StreamingResponse(
        service.send_message_stream(
            current_user,
            session_id,
            payload.query,
            limit=payload.limit,
        ),
        media_type="text/event-stream",
    )


@router.post("/sessions/{session_id}/messages/audio", response_model=ChatSendResponse)
async def send_voice_message(
    session_id: UUID,
    audio: UploadFile = File(...),
    limit: int = Form(default=6, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    audio_bytes = await audio.read()
    service = ChatService(db)
    return await service.send_voice_message(
        current_user,
        session_id,
        audio_bytes,
        mime_type=audio.content_type,
        filename=audio.filename,
        limit=limit,
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ChatRepository(db)
    deleted = await repo.delete_session(session_id, current_user.id)
    if not deleted:
        raise NotFoundError("Chat session not found", details={"session_id": str(session_id)})
