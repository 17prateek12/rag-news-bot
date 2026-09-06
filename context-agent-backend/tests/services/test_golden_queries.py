import json
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from app.schemas.intent import ChatTurn, IntentClassification, QueryIntent
from app.services.intent_classifier import IntentClassifier


@pytest.fixture
def golden_queries():
    dataset_path = Path(__file__).parent.parent / "data" / "golden_queries.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_golden_queries_dataset_structure(golden_queries):
    assert len(golden_queries) >= 40
    for item in golden_queries:
        assert "id" in item
        assert "query" in item
        assert "expected_intent" in item
        assert item["expected_intent"] in ("single_fact", "follow_up", "context")


def test_intent_classifier_regex_and_heuristic_on_golden_samples():
    classifier = IntentClassifier()

    # Test heuristic fallback for follow-up with history
    history = [ChatTurn(role="user", text="Tell me about the budget.")]
    res = classifier._heuristic_fallback("what about the deficit?", history)
    assert res.intent == QueryIntent.FOLLOW_UP

    # Test heuristic fallback for single fact
    res = classifier._heuristic_fallback("who is the president of france?", [])
    assert res.intent == QueryIntent.SINGLE_FACT

    # Test heuristic fallback for context
    res = classifier._heuristic_fallback("what is happening in parliament today?", [])
    assert res.intent == QueryIntent.CONTEXT


def test_intent_classifier_langchain_parser():
    classifier = IntentClassifier()
    raw_llm_json = '{"intent": "single_fact", "confidence": 0.95, "reason": "Lookup of a specific individual"}'
    
    parsed = classifier._parse_with_langchain(raw_llm_json, query="who is x", history=[])
    assert parsed.intent == QueryIntent.SINGLE_FACT
    assert parsed.confidence == 0.95
    assert parsed.reason == "Lookup of a specific individual"


def test_intent_classifier_langchain_parser_fallback_on_malformed():
    classifier = IntentClassifier()
    malformed_raw = 'Some leading chatter {"intent": "context", "confidence": 0.8, "reason": "General overview"} and trailing text'
    
    parsed = classifier._parse_with_langchain(malformed_raw, query="overview", history=[])
    assert parsed.intent == QueryIntent.CONTEXT
    assert parsed.confidence == 0.8
