import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.agent import RAGResponse, SourceCitation
from app.schemas.intent import ChatTurn, IntentClassification, QueryIntent
from app.services.rag_graph import (
    RAGGraphState,
    build_rag_graph,
    classify_node,
    execute_rag_graph,
    generate_node,
    rewrite_node,
    should_retry_retrieval,
)
from app.services.shadow_harness import ShadowHarness


def test_should_retry_retrieval_logic():
    # 1. Empty hits on single_fact with retry_count = 0 -> should retry
    state_retry: RAGGraphState = {
        "hits": [],
        "classification": IntentClassification(
            intent=QueryIntent.SINGLE_FACT, confidence=0.9, reason="Fact lookup"
        ),
        "retry_count": 0,
    }
    assert should_retry_retrieval(state_retry) == "retry_retrieve"

    # 2. Empty hits on single_fact with retry_count = 1 -> should proceed to generate
    state_after_retry: RAGGraphState = {
        "hits": [],
        "classification": IntentClassification(
            intent=QueryIntent.SINGLE_FACT, confidence=0.9, reason="Fact lookup"
        ),
        "retry_count": 1,
    }
    assert should_retry_retrieval(state_after_retry) == "generate"

    # 3. Non-empty hits on single_fact -> should proceed to generate
    state_with_hits: RAGGraphState = {
        "hits": [{"title": "Article 1", "chunk": "Some text"}],
        "classification": IntentClassification(
            intent=QueryIntent.SINGLE_FACT, confidence=0.9, reason="Fact lookup"
        ),
        "retry_count": 0,
    }
    assert should_retry_retrieval(state_with_hits) == "generate"

    # 4. Context intent -> should proceed to generate
    state_context: RAGGraphState = {
        "hits": [],
        "classification": IntentClassification(
            intent=QueryIntent.CONTEXT, confidence=0.9, reason="Overview"
        ),
        "retry_count": 0,
    }
    assert should_retry_retrieval(state_context) == "generate"


def test_langgraph_workflow_compiles():
    graph = build_rag_graph()
    assert graph is not None


@pytest.mark.asyncio
async def test_shadow_harness_execution():
    async def baseline():
        return "baseline_value"

    async def shadow():
        return "shadow_value"

    diff_recorded = {}

    def custom_diff(b, s, b_lat, s_lat):
        diff_recorded["baseline"] = b
        diff_recorded["shadow"] = s
        return diff_recorded

    result = await ShadowHarness.execute_with_shadow(
        name="test_shadow",
        baseline_fn=baseline,
        shadow_fn=shadow,
        diff_fn=custom_diff,
        enabled=True,
    )

    # Baseline value must be returned unconditionally
    assert result == "baseline_value"
