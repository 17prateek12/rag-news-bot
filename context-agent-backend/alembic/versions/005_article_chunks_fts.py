"""article_chunks table with full-text search

Revision ID: 005
Revises: 004
Create Date: 2026-08-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "article_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("article_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("categories", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("qdrant_point_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(chunk_text, ''))",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.UniqueConstraint("article_id", "chunk_index", name="uq_article_chunks_article_index"),
    )
    op.create_index("ix_article_chunks_article_id", "article_chunks", ["article_id"])
    op.create_index(
        "ix_article_chunks_search_vector",
        "article_chunks",
        ["search_vector"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_article_chunks_search_vector", table_name="article_chunks")
    op.drop_index("ix_article_chunks_article_id", table_name="article_chunks")
    op.drop_table("article_chunks")
