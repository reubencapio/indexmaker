"""add index spec, build evidence and the user's data source

Revision ID: a7c39e5f1d64
Revises: f6b28d4e0c53
Create Date: 2026-10-12 09:00:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a7c39e5f1d64"
down_revision = "f6b28d4e0c53"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("indices", sa.Column("spec", sa.JSON(), nullable=True))
    op.add_column("indices", sa.Column("build_info", sa.JSON(), nullable=True))
    op.add_column("indices", sa.Column("build_snapshot", sa.JSON(), nullable=True))
    op.add_column("users", sa.Column("market_data_source", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "market_data_source")
    op.drop_column("indices", "build_snapshot")
    op.drop_column("indices", "build_info")
    op.drop_column("indices", "spec")
