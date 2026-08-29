"""Add error_message to indices

Revision ID: a1c4e77b9d02
Revises: 98f26ea4f190
Create Date: 2026-08-29 12:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c4e77b9d02"
down_revision: Union[str, None] = "98f26ea4f190"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("indices", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("indices", "error_message")
