"""add index followers

Revision ID: f6b28d4e0c53
Revises: e5a17c3d9b42
Create Date: 2026-10-11 12:00:00.000000

People who follow a publicly shared index and are emailed when it is rebalanced.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6b28d4e0c53"
down_revision: Union[str, None] = "e5a17c3d9b42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "index_followers",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("share_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmation_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["share_id"], ["public_shares.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("share_id", "email", name="uq_index_followers_share_email"),
    )
    op.create_index("ix_index_followers_share_id", "index_followers", ["share_id"])
    op.create_index("ix_index_followers_token", "index_followers", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_index_followers_token", table_name="index_followers")
    op.drop_index("ix_index_followers_share_id", table_name="index_followers")
    op.drop_table("index_followers")
