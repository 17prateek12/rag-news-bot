from typing import Any

from app.ingestion.parsers.base import BaseFeedParser


class BBCParser(BaseFeedParser):
    def extract_image_url(self, entry: Any) -> str | None:
        media = getattr(entry, "media_thumbnail", None)
        if media and isinstance(media, list) and media:
            return media[0].get("url")
        media_content = getattr(entry, "media_content", None)
        if media_content and isinstance(media_content, list) and media_content:
            return media_content[0].get("url")
        return None

    def extract_author(self, entry: Any) -> str | None:
        return getattr(entry, "author", None)
