"""Add subscription period fields to users

Revision ID: c3e8a15f7b21
Revises: b7f2d9c41a58
Create Date: 2026-10-06 12:00:00.000000

Stores what the billing page needs to show without a Stripe round-trip: which
price the subscription is on, when the paid period ends, and whether it is set to
lapse then. Existing subscribers get these filled in by their next Stripe event.

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3e8a15f7b21"
down_revision: Union[str, None] = "b7f2d9c41a58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("subscription_interval", sa.String(20), nullable=True))
    op.add_column(
        "users",
        sa.Column("subscription_current_period_end", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "subscription_cancel_at_period_end",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    # The billing webhook looks users up by these on every event.
    op.create_index("ix_users_stripe_customer_id", "users", ["stripe_customer_id"])
    op.create_index("ix_users_subscription_id", "users", ["subscription_id"])


def downgrade() -> None:
    op.drop_index("ix_users_subscription_id", table_name="users")
    op.drop_index("ix_users_stripe_customer_id", table_name="users")
    op.drop_column("users", "subscription_cancel_at_period_end")
    op.drop_column("users", "subscription_current_period_end")
    op.drop_column("users", "subscription_interval")
