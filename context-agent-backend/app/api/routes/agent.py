import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.user_auth import get_current_user
from app.models.user import User
from app.schemas.agent import ClassifyQueryResponse, RAGQueryRequest, RAGResponse
from app.schemas.intent import ChatTurn
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/query", response_model=RAGResponse)
async def agent_query(
    payload: RAGQueryRequest,
    current_user: User = Depends(get_current_user),  # H-4: require auth
    db: AsyncSession = Depends(get_db),
):
    logger.info("Agent query query=%r intent_history=%s user=%s", payload.query, len(payload.history), current_user.id)
    service = RAGService(db)
    return await service.query(
        payload.query,
        limit=payload.limit,
        history=payload.history,
    )


@router.post("/query/stream")
async def agent_query_stream(
    payload: RAGQueryRequest,
    current_user: User = Depends(get_current_user),  # H-4: require auth
    db: AsyncSession = Depends(get_db),
):
    logger.info("Agent query stream query=%r intent_history=%s user=%s", payload.query, len(payload.history), current_user.id)
    service = RAGService(db)
    return StreamingResponse(
        service.query_stream(
            payload.query,
            limit=payload.limit,
            history=payload.history,
        ),
        media_type="text/event-stream",
    )


@router.get("/classify", response_model=ClassifyQueryResponse)
async def classify_query(
    q: str = Query(min_length=1),
    current_user: User = Depends(get_current_user),  # H-4: require auth (was a public debug endpoint)
    db: AsyncSession = Depends(get_db),
):
    """Classify query intent (requires authentication)."""
    service = RAGService(db)
    classification = await service.classify_only(q)
    return ClassifyQueryResponse(query=q, classification=classification)
