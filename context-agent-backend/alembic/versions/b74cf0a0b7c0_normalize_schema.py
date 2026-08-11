"""normalize schema

Revision ID: b74cf0a0b7c0
Revises: 006
Create Date: 2026-08-11 14:12:08.926529

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b74cf0a0b7c0'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create sources table
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # 2. Create rss_feed table
    op.create_table(
        "rss_feed",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("feed_url", sa.Text(), nullable=False),
        sa.Column("parse_key", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feed_url"),
    )

    # 3. Create article_categories table
    op.create_table(
        "article_categories",
        sa.Column("article_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("article_id", "category_id"),
    )

    # 4. Backfill unique source names
    op.execute(
        "INSERT INTO sources (name) "
        "SELECT DISTINCT source FROM articles "
        "UNION "
        "SELECT DISTINCT source FROM rss_sources "
        "ON CONFLICT (name) DO NOTHING;"
    )

    # 5. Backfill rss_feed from rss_sources
    op.execute(
        "INSERT INTO rss_feed (id, source_id, category_id, feed_url, parse_key, is_active) "
        "SELECT rs.id, s.id, rs.category_id, rs.feed_url, rs.parser_key, rs.is_active "
        "FROM rss_sources rs "
        "JOIN sources s ON s.name = rs.source;"
    )
    # Set sequence
    op.execute("SELECT setval('rss_feed_id_seq', COALESCE((SELECT MAX(id)+1 FROM rss_feed), 1), false);")

    # 6. Alter articles: add source_id and embedded_at
    op.add_column("articles", sa.Column("source_id", sa.Integer(), nullable=True))
    op.add_column("articles", sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True))

    # 7. Backfill articles.source_id
    op.execute(
        "UPDATE articles a "
        "SET source_id = s.id "
        "FROM sources s "
        "WHERE s.name = a.source;"
    )

    # Make source_id NOT NULL
    op.alter_column("articles", "source_id", nullable=False)

    # 8. Backfill embedded_at
    op.execute(
        "UPDATE articles "
        "SET embedded_at = now() "
        "WHERE qdrant_point_ids IS NOT NULL AND cardinality(qdrant_point_ids) > 0;"
    )

    # 9. Drop old unique constraint on articles and add new one
    op.drop_constraint("uq_articles_source_url", "articles", type_="unique")
    op.create_unique_constraint("uq_articles_source_id_url", "articles", ["source_id", "url"])

    # 10. Backfill article_categories junction
    op.execute(
        "INSERT INTO article_categories (article_id, category_id) "
        "SELECT a.id, c.id "
        "FROM articles a "
        "CROSS JOIN LATERAL unnest(a.categories) AS cat_name "
        "JOIN categories c ON c.name = cat_name "
        "ON CONFLICT DO NOTHING;"
    )

    # 11. Drop old columns from articles
    op.drop_column("articles", "source")
    op.drop_column("articles", "categories")

    # 12. Drop old rss_sources table
    op.drop_table("rss_sources")

    # 13. Create indexes for foreign keys
    op.create_index("idx_article_categories_category_id", "article_categories", ["category_id"])
    op.create_index("idx_article_categories_article_id", "article_categories", ["article_id"])


def downgrade() -> None:
    # 1. Re-create rss_sources table
    op.create_table(
        "rss_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("feed_url", sa.Text(), nullable=False),
        sa.Column("parser_key", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feed_url"),
    )

    # 2. Add source and categories back to articles
    op.add_column("articles", sa.Column("source", sa.String(length=100), nullable=True))
    op.add_column("articles", sa.Column("categories", postgresql.ARRAY(sa.String()), server_default="{}", nullable=True))

    # 3. Backfill data
    op.execute(
        "INSERT INTO rss_sources (id, source, category_id, feed_url, parser_key, is_active) "
        "SELECT rf.id, s.name, rf.category_id, rf.feed_url, rf.parse_key, rf.is_active "
        "FROM rss_feed rf "
        "JOIN sources s ON s.id = rf.source_id;"
    )
    op.execute("SELECT setval('rss_sources_id_seq', COALESCE((SELECT MAX(id)+1 FROM rss_sources), 1), false);")

    op.execute(
        "UPDATE articles a "
        "SET source = s.name "
        "FROM sources s "
        "WHERE s.id = a.source_id;"
    )

    op.execute(
        "UPDATE articles a "
        "SET categories = COALESCE("
        "  (SELECT array_agg(c.name) "
        "   FROM article_categories ac "
        "   JOIN categories c ON c.id = ac.category_id "
        "   WHERE ac.article_id = a.id), "
        "  '{}'::text[]"
        ");"
    )

    # Make them NOT NULL
    op.alter_column("articles", "source", nullable=False)
    op.alter_column("articles", "categories", nullable=False)

    # 4. Drop new unique constraint and re-create old one
    op.drop_constraint("uq_articles_source_id_url", "articles", type_="unique")
    op.create_unique_constraint("uq_articles_source_url", "articles", ["source", "url"])

    # 5. Drop source_id and embedded_at columns
    op.drop_column("articles", "source_id")
    op.drop_column("articles", "embedded_at")

    # 6. Drop indexes
    op.drop_index("idx_article_categories_category_id")
    op.drop_index("idx_article_categories_article_id")

    # 7. Drop new tables
    op.drop_table("article_categories")
    op.drop_table("rss_feed")
    op.drop_table("sources")
