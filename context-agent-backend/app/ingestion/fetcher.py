import logging

import feedparser
import httpx

from app.core.exceptions import FetchError

logger = logging.getLogger(__name__)


class FeedFetcher:
    def __init__(self, timeout: float = 20.0) -> None:
        self._timeout = timeout

    async def fetch(self, feed_url: str) -> feedparser.FeedParserDict:
        logger.info("Fetching RSS feed: %s", feed_url)
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                response = await client.get(feed_url)
                response.raise_for_status()
                feed = feedparser.parse(response.text)
                logger.info(
                    "Fetched RSS feed: %s status=%s entries=%s",
                    feed_url,
                    response.status_code,
                    len(getattr(feed, "entries", []) or []),
                )
                return feed
        except httpx.HTTPStatusError as exc:
            logger.error(
                "RSS feed HTTP error url=%s status=%s",
                feed_url,
                exc.response.status_code,
            )
            raise FetchError(
                f"Feed returned HTTP {exc.response.status_code}",
                details={"feed_url": feed_url, "status_code": exc.response.status_code},
                cause=exc,
            ) from exc
        except httpx.RequestError as exc:
            logger.error("RSS feed network error url=%s error=%s", feed_url, exc)
            raise FetchError(
                "Failed to reach feed URL",
                details={"feed_url": feed_url},
                cause=exc,
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected RSS fetch failure url=%s", feed_url)
            raise FetchError(
                "Unexpected feed fetch failure",
                details={"feed_url": feed_url},
                cause=exc,
            ) from exc
