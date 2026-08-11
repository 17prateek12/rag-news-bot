from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RssSource(Base):
    __tablename__ = "rss_feed"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    feed_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    parse_key: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    source_relation: Mapped["Source"] = relationship(back_populates="rss_feeds")
    category: Mapped["Category"] = relationship(back_populates="rss_sources")

    @property
    def source(self) -> str:
        return self.source_relation.name if self.source_relation else ""

    @property
    def parser_key(self) -> str:
        return self.parse_key
