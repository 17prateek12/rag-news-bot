from typing import Any

from app.ingestion.parsers.base import BaseFeedParser


class NDTVParser(BaseFeedParser):
    def extract_summary(self, entry: Any) -> str | None:
        content = getattr(entry, "content", None)
        if content and isinstance(content, list) and content:
            value = content[0].get("value")
            if value:
                return value
        return super().extract_summary(entry)

    def extract_image_url(self, entry: Any) -> str | None:
        media = getattr(entry, "media_content", None)
        if media and isinstance(media, list) and media:
            return media[0].get("url")
        return None
