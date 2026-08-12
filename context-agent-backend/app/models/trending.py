import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

article_entities = Table(
    "article_entities",
    Base.metadata,
    Column("article_id", ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
    Column("entity_id", ForeignKey("trending_entities.id", ondelete="CASCADE"), primary_key=True),
)


class TrendingEntity(Base):
    __tablename__ = "trending_entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    articles: Mapped[list["Article"]] = relationship(
        secondary="article_entities",
        back_populates="entities_relation",
        lazy="selectin",
    )


class TrendingNewsCount(Base):
    __tablename__ = "trending_news_counts"

    entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trending_entities.id", ondelete="CASCADE"), primary_key=True
    )
    hour_bucket: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    entity: Mapped[TrendingEntity] = relationship()


class TrendingQueryCount(Base):
    __tablename__ = "trending_query_counts"

    entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trending_entities.id", ondelete="CASCADE"), primary_key=True
    )
    hour_bucket: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    entity: Mapped[TrendingEntity] = relationship()
