import asyncio
import logging
from typing import Any

from app.config import settings
from app.core.tracing import traceable
from app.schemas.intent import ChatTurn
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

REWRITE_PROMPT_TEMPLATE = """You are an expert search query rewriter for a news Q&A agent.
Your task is to rewrite the user's latest query into a standalone, fully-qualified search query that resolves any pronouns, typos, or context from the recent conversation history.

Rules:
- Extract the active topic (entities, subject, location, event) from the conversation history.
- If the user's latest query is a follow-up, elliptical, brief, or has minor typos (like "jantar manter"), expand and correct it to include the specific entity names, locations, and topic of discussion so it can be searched independently.
- If the user's latest query is already complete, standalone, or shifts the topic entirely, output it as-is (with minor spelling corrections if needed).
- Do NOT answer the query. Just output the rewritten search query and nothing else.

Recent conversation:
{history_text}

User's latest query: {query}
Rewritten Query:"""


class LCELQueryRewriter:
    """Query rewriter expressed as a LangChain Expression Language (LCEL) chain."""

    def __init__(self) -> None:
        self._chain = None

    def _get_chain(self):
        if self._chain is None:
            from langchain_core.output_parsers import StrOutputParser
            from langchain_core.prompts import PromptTemplate
            from langchain_core.runnables import RunnableLambda

            prompt = PromptTemplate.from_template(REWRITE_PROMPT_TEMPLATE)
            # Wrap LLMService.generate as a runnable lambda
            llm_runnable = RunnableLambda(lambda prompt_val: llm_service.generate(prompt_val.to_string()))
            output_parser = StrOutputParser()
            self._chain = prompt | llm_runnable | output_parser
        return self._chain

    @traceable(name="lcel_rewrite_query", run_type="chain")
    async def rewrite(self, query: str, history: list[ChatTurn]) -> str:
        if not history:
            return query

        history_text = "\n".join(f"{turn.role}: {turn.text}" for turn in history[-6:])
        try:
            chain = self._get_chain()
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: chain.invoke({"query": query, "history_text": history_text}),
            )
            rewritten = result.strip().strip('"').strip("'")
            if rewritten:
                return rewritten
        except Exception as exc:
            logger.warning("LCEL query rewriting failed (%s), returning original query", exc)

        return query


lcel_query_rewriter = LCELQueryRewriter()
