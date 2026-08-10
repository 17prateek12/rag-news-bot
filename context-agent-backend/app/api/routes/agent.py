import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.agent import ClassifyQueryResponse, RAGQueryRequest, RAGResponse
from app.schemas.intent import ChatTurn
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/query", response_model=RAGResponse)
async def agent_query(
    payload: RAGQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    logger.info("Agent query query=%r intent_history=%s", payload.query, len(payload.history))
    service = RAGService(db)
    return await service.query(
        payload.query,
        limit=payload.limit,
        history=payload.history,
    )


@router.get("/classify", response_model=ClassifyQueryResponse)
async def classify_query(
    q: str = Query(min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """Debug endpoint: classify intent without retrieval or generation."""
    service = RAGService(db)
    classification = service.classify_only(q)
    return ClassifyQueryResponse(query=q, classification=classification)
