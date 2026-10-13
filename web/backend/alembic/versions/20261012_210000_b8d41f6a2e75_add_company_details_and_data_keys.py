"""add stored company details and users' market data API keys

Revision ID: b8d41f6a2e75
Revises: a7c39e5f1d64
Create Date: 2026-10-12 21:00:00

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b8d41f6a2e75"
down_revision = "a7c39e5f1d64"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_details",
        sa.Column("source", sa.String(length=60), nullable=False),
        sa.Column("ticker", sa.String(length=40), nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("wanted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("source", "ticker"),
    )
    op.create_index("ix_company_details_source_wanted", "company_details", ["source", "wanted_at"])
    op.create_index(
        "ix_company_details_source_fetched", "company_details", ["source", "fetched_at"]
    )
    op.add_column("users", sa.Column("market_data_keys", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "market_data_keys")
    op.drop_index("ix_company_details_source_fetched", table_name="company_details")
    op.drop_index("ix_company_details_source_wanted", table_name="company_details")
    op.drop_table("company_details")
