from typing import Any

from app.ingestion.parsers.base import BaseFeedParser


class HinduParser(BaseFeedParser):
    """Ignore item-level sub-categories; feed default category is used."""

    def extract_image_url(self, entry: Any) -> str | None:
        media = getattr(entry, "media_content", None)
        if media and isinstance(media, list) and media:
            return media[0].get("url")
        thumbnail = getattr(entry, "media_thumbnail", None)
        if thumbnail and isinstance(thumbnail, list) and thumbnail:
            return thumbnail[0].get("url")
        return None
