from datetime import datetime, timezone

from dateutil import parser as date_parser


def parse_published_at(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    dt = date_parser.parse(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
