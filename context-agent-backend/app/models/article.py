import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


article_categories = Table(
    "article_categories",
    Base.metadata,
    Column("article_id", ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint("source_id", "url", name="uq_articles_source_id_url"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    author: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    embedded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cleaned_text: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    qdrant_point_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source_relation: Mapped["Source"] = relationship(back_populates="articles", lazy="selectin")
    categories_relation: Mapped[list["Category"]] = relationship(
        secondary="article_categories",
        back_populates="articles",
        lazy="selectin",
    )

    @property
    def source(self) -> str:
        return self.source_relation.name if self.source_relation else ""

    @property
    def categories(self) -> list[str]:
        return [c.name for c in self.categories_relation] if self.categories_relation else []

    @property
    def chunk_count(self) -> int:
        return len(self.qdrant_point_ids or [])
