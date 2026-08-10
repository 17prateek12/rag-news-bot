from abc import ABC, abstractmethod
from typing import Any

from app.ingestion.date_parser import parse_published_at
from app.ingestion.feed_context import FeedContext
from app.ingestion.html_cleaner import strip_html
from app.ingestion.url_normalizer import normalize_url
from app.schemas.article import NormalizedArticleDTO


class BaseFeedParser(ABC):
    """Template Method: shared normalization, subclasses override extractors."""

    def parse_entry(self, entry: Any, context: FeedContext) -> NormalizedArticleDTO | None:
        url = self.extract_url(entry)
        if not url:
            return None

        title = strip_html(self.extract_title(entry))
        if not title:
            return None

        summary = strip_html(self.extract_summary(entry))
        body = strip_html(self.extract_body(entry))

        return NormalizedArticleDTO(
            title=title,
            summary=summary,
            body=body,
            url=normalize_url(url),
            image_url=self.extract_image_url(entry),
            source=context.source,
            author=self.extract_author(entry),
            published_at=parse_published_at(self.extract_published_at(entry)),
            categories=[context.default_category],
        )

    def extract_title(self, entry: Any) -> str | None:
        return getattr(entry, "title", None)

    def extract_url(self, entry: Any) -> str | None:
        return getattr(entry, "link", None)

    def extract_summary(self, entry: Any) -> str | None:
        return getattr(entry, "summary", None) or getattr(entry, "description", None)

    def extract_body(self, entry: Any) -> str | None:
        content = getattr(entry, "content", None)
        if content and isinstance(content, list) and content:
            value = content[0].get("value")
            if value:
                return value
        return None

    def extract_published_at(self, entry: Any) -> str | None:
        return getattr(entry, "published", None) or getattr(entry, "updated", None)

    def extract_author(self, entry: Any) -> str | None:
        return getattr(entry, "author", None)

    @abstractmethod
    def extract_image_url(self, entry: Any) -> str | None:
        raise NotImplementedError
