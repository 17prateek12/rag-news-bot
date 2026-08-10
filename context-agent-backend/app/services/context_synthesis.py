import re
from typing import Any

from app.schemas.agent import ContextSection

SECTION_DEFINITIONS: list[tuple[str, str]] = [
    ("what_happened", "What happened"),
    ("why_it_matters", "Why it matters"),
    ("background", "Background"),
    ("whats_next", "What's next"),
]

SECTION_ALIASES: dict[str, str] = {
    "what happened": "what_happened",
    "why it matters": "why_it_matters",
    "background": "background",
    "what's next": "whats_next",
    "whats next": "whats_next",
    "what next": "whats_next",
}


def merge_hits(
    primary: list[dict[str, Any]],
    extra: list[dict[str, Any]],
    *,
    max_total: int,
) -> list[dict[str, Any]]:
    seen: set[tuple[str, int]] = set()
    merged: list[dict[str, Any]] = []

    for hit in primary + extra:
        key = (
            str(hit.get("article_id") or hit.get("url", "")),
            int(hit.get("chunk_index") or 0),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(hit)
        if len(merged) >= max_total:
            break
    return merged


def parse_context_sections(answer: str) -> list[ContextSection]:
    """Parse markdown ## sections from a structured context response."""
    if not answer.strip():
        return []

    header_pattern = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
    matches = list(header_pattern.finditer(answer))
    if not matches:
        return []

    sections: list[ContextSection] = []
    for idx, match in enumerate(matches):
        raw_title = match.group(1).strip()
        key = SECTION_ALIASES.get(raw_title.lower())
        if not key:
            continue
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(answer)
        content = answer[start:end].strip()
        if not content:
            continue
        sections.append(
            ContextSection(
                key=key,
                title=raw_title,
                content=content,
            )
        )
    return sections
