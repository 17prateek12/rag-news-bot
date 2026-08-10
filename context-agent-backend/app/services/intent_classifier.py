import json
import logging
import re

from app.schemas.intent import ChatTurn, IntentClassification, QueryIntent
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

CLASSIFY_PROMPT = """You are an intent classifier for a news Q&A agent.

Classify the user query into exactly ONE intent:

- single_fact: A narrow factual lookup (who, what, when, where, how many). Expect a short direct answer.
- context: Wants background, explanation, significance, or an overview (why it matters, what's going on, summarize).
- follow_up: Depends on earlier conversation (e.g. "what about the economy?", "tell me more", "and then?", "how does that affect India?").

{history_section}
User query: {query}

Respond with JSON only, no markdown:
{{"intent": "single_fact" or "context" or "follow_up", "confidence": 0.0 to 1.0, "reason": "brief explanation"}}"""


class IntentClassifier:
    def classify(self, query: str, history: list[ChatTurn] | None = None) -> IntentClassification:
        history = history or []
        if history:
            lines = [f"- {turn.role}: {turn.text}" for turn in history[-6:]]
            history_section = "Recent conversation:\n" + "\n".join(lines)
        else:
            history_section = "Recent conversation: none"

        prompt = CLASSIFY_PROMPT.format(query=query.strip(), history_section=history_section)
        logger.info("Classifying intent query=%r history_turns=%s", query, len(history))

        raw = llm_service.generate(prompt)
        parsed = self._parse_response(raw, query=query, history=history)
        logger.info(
            "Intent classified intent=%s confidence=%s reason=%r",
            parsed.intent,
            parsed.confidence,
            parsed.reason,
        )
        return parsed

    def _parse_response(
        self,
        raw: str,
        *,
        query: str,
        history: list[ChatTurn],
    ) -> IntentClassification:
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise ValueError("No JSON object in classifier response")
            data = json.loads(match.group())
            intent = QueryIntent(data["intent"])
            return IntentClassification(
                intent=intent,
                confidence=float(data.get("confidence", 0.7)),
                reason=str(data.get("reason", "")),
            )
        except Exception as exc:
            logger.warning("Intent parse failed, using heuristic fallback: %s", exc)
            return self._heuristic_fallback(query, history)

    def _heuristic_fallback(self, query: str, history: list[ChatTurn]) -> IntentClassification:
        lowered = query.lower().strip()
        follow_up_markers = (
            "what about",
            "tell me more",
            "and then",
            "how about",
            "what else",
            "that",
            "those",
            "it ",
            "they ",
        )
        if history and any(lowered.startswith(marker) or f" {marker}" in f" {lowered}" for marker in follow_up_markers):
            return IntentClassification(
                intent=QueryIntent.FOLLOW_UP,
                confidence=0.55,
                reason="Heuristic: follow-up phrasing with conversation history",
            )
        if lowered.startswith(("why ", "explain ", "what is happening", "give me context", "overview")):
            return IntentClassification(
                intent=QueryIntent.CONTEXT,
                confidence=0.55,
                reason="Heuristic: context-style phrasing",
            )
        if lowered.startswith(("who ", "when ", "where ", "how many ", "how much ")) or len(query) < 60:
            return IntentClassification(
                intent=QueryIntent.SINGLE_FACT,
                confidence=0.5,
                reason="Heuristic: short or fact-style question",
            )
        return IntentClassification(
            intent=QueryIntent.CONTEXT,
            confidence=0.5,
            reason="Heuristic: default to context",
        )


intent_classifier = IntentClassifier()
