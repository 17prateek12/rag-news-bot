from dataclasses import dataclass


@dataclass(frozen=True)
class FeedContext:
    source: str
    feed_url: str
    default_category: str
