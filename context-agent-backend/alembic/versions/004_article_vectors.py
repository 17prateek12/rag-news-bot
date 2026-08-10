"""article vector fields

Revision ID: 004
Revises: 003
Create Date: 2026-08-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("cleaned_text", sa.Text(), nullable=True))
    op.add_column("articles", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "articles",
        sa.Column(
            "qdrant_point_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("articles", "qdrant_point_ids")
    op.drop_column("articles", "content_hash")
    op.drop_column("articles", "cleaned_text")
