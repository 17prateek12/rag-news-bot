import re

_MAX_TRENDING_QUERY_LEN = 120
_MAX_TRENDING_WORDS = 15
_MIN_TRENDING_QUERY_LEN = 4

_BLOCKLIST_PATTERNS = (
    re.compile(r"^test\b"),
    re.compile(r"\btest chat\b"),
    re.compile(r"\btest query\b"),
    re.compile(r"^nonsense\b"),
    re.compile(r"xyzabc"),
    re.compile(r"^foo\b"),
    re.compile(r"^bar\b"),
    re.compile(r"^asdf\b"),
    re.compile(r"^hello\b"),
    re.compile(r"^hi\b"),
    re.compile(r"zorbax"),
    re.compile(r"\bdevices getting\b"),
    re.compile(r"\bmade by google\b"),
    re.compile(r"\bpixel feature\b"),
)

# Standalone hex tokens (common in smoke-test query suffixes).
_HEX_TOKEN = re.compile(r"\b[a-f0-9]{6,}\b")

# Multiple sentences or transcript-like speech patterns.
_SENTENCE_MARKERS = re.compile(r"[.!?]")
_TRANSCRIPT_MARKERS = (
    re.compile(r"\bwelcome to the\b"),
    re.compile(r"\bhere's your host\b"),
    re.compile(r"\btoday, we're talking\b"),
    re.compile(r"\bmade by google podcast\b"),
)


def _normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


def is_trending_worthy_query(query: str) -> bool:
    normalized = _normalize_query(query)
    if len(normalized) < _MIN_TRENDING_QUERY_LEN:
        return False
    if len(normalized) > _MAX_TRENDING_QUERY_LEN:
        return False

    words = normalized.split()
    if len(words) > _MAX_TRENDING_WORDS:
        return False

    if any(pattern.search(normalized) for pattern in _BLOCKLIST_PATTERNS):
        return False
    if _HEX_TOKEN.search(normalized):
        return False
    if len(_SENTENCE_MARKERS.findall(normalized)) >= 2:
        return False
    if any(pattern.search(normalized) for pattern in _TRANSCRIPT_MARKERS):
        return False

    alnum = sum(ch.isalnum() or ch.isspace() for ch in normalized)
    if alnum / len(normalized) < 0.85:
        return False
    return True
