import html
import re

_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = html.unescape(_TAG_RE.sub("", text))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or None
