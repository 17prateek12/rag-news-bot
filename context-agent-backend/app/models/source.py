from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    rss_feeds: Mapped[list["RssSource"]] = relationship(back_populates="source_relation")
    articles: Mapped[list["Article"]] = relationship(back_populates="source_relation")
