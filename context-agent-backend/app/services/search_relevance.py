import re
from typing import Any

_GENERIC_TOPIC_TERMS = frozenset(
    {
        "protest",
        "news",
        "update",
        "updates",
        "launch",
        "summit",
        "climbing",
        "policy",
        "tourism",
        "breakthrough",
        "auction",
        "devices",
        "getting",
        "better",
        "entanglement",
        "quantum",
        "starship",
        "cricket",
    }
)

_TOPIC_ALIASES: dict[str, list[str]] = {
    "ukraine": ["ukraine", "ukrainian", "kyiv", "kiev", "zelensky"],
    "spacex": ["spacex", "starship"],
    "nepal": ["nepal", "nepali", "everest"],
    "everest": ["everest", "nepal", "himalaya"],
    "ipl": ["ipl", "indian premier league"],
}


def _topic_term_groups(query: str) -> list[list[str]]:
    terms = [term for term in query.lower().split() if len(term) >= 3]
    specific = [term for term in terms if term not in _GENERIC_TOPIC_TERMS]
    if not specific:
        specific = terms

    groups: list[list[str]] = []
    for term in specific:
        groups.append(_TOPIC_ALIASES.get(term, [term]))
    return groups


def _hit_text(hit: dict[str, Any]) -> str:
    return f"{hit.get('title', '')} {hit.get('chunk', '')}".lower()


def hit_matches_topic(query: str, hit: dict[str, Any]) -> bool:
    groups = _topic_term_groups(query)
    if not groups:
        return True

    text = _hit_text(hit)
    for aliases in groups:
        if not any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in aliases):
            return False
    return True


def filter_hits_by_topic(query: str, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [hit for hit in hits if hit_matches_topic(query, hit)]
