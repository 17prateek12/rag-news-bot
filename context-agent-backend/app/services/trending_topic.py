import re

_MAX_TOPIC_WORDS = 3

_QUESTION_PREFIXES = (
    re.compile(r"^what(?:'s| is) (?:happening |going on )?(?:in |with |at )?"),
    re.compile(r"^what about "),
    re.compile(r"^how (?:is|are|does|do|did|can|could|will|would) "),
    re.compile(r"^why (?:is|are|does|do|did|can|could|will|would) "),
    re.compile(r"^when (?:is|are|does|did|will|was) "),
    re.compile(r"^where (?:is|are|does|did|can) "),
    re.compile(r"^who (?:is|are|was|were) "),
    re.compile(r"^tell me (?:about )?"),
    re.compile(r"^give me (?:the )?(?:latest )?(?:news )?(?:on|about|for) "),
    re.compile(r"^(?:latest|recent) (?:news )?(?:on|about|in|from) "),
    re.compile(r"^news (?:on|about|in|from) "),
    re.compile(r"^update(?:s)? (?:on|about|for) "),
)

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "from",
        "by",
        "as",
        "and",
        "or",
        "what",
        "how",
        "why",
        "when",
        "where",
        "who",
        "which",
        "that",
        "this",
        "happening",
        "happen",
        "happened",
        "going",
        "latest",
        "update",
        "updates",
        "news",
        "today",
        "yesterday",
        "now",
        "current",
        "currently",
        "recent",
        "recently",
        "tell",
        "about",
        "please",
        "any",
        "some",
        "more",
        "most",
        "has",
        "have",
        "had",
        "get",
        "got",
        "me",
        "you",
        "my",
        "your",
        "our",
        "their",
        "it",
        "its",
        "list",
        "player",
        "players",
    }
)

_MONTHS = frozenset(
    {
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
        "jan",
        "feb",
        "mar",
        "apr",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
    }
)

_YEAR = re.compile(r"^(19|20)\d{2}$")

_TOPIC_LABEL_OVERRIDES = {
    "spacex": "SpaceX",
    "ipl": "IPL",
    "ai": "AI",
    "uk": "UK",
    "us": "US",
    "usa": "USA",
    "nasa": "NASA",
    "ukraine": "Ukraine",
    "nepal": "Nepal",
}


def _normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


def extract_trending_topic(query: str) -> str:
    """Reduce a natural-language question to a short topical label key."""
    text = _normalize_query(query).rstrip("?").strip()

    for pattern in _QUESTION_PREFIXES:
        text = pattern.sub("", text).strip()

    words: list[str] = []
    for word in text.split():
        if word in _STOPWORDS or word in _MONTHS or _YEAR.match(word):
            continue
        words.append(word)

    if not words:
        words = text.split()[:_MAX_TOPIC_WORDS]

    return " ".join(words[:_MAX_TOPIC_WORDS])


def format_topic_label(topic_key: str) -> str:
    parts = []
    for word in topic_key.split():
        parts.append(_TOPIC_LABEL_OVERRIDES.get(word, word.capitalize()))
    return " ".join(parts)
