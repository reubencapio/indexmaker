"""Add divisor and generation_prompt to indices

Revision ID: b7f2d9c41a58
Revises: a1c4e77b9d02
Create Date: 2026-08-29 15:00:00.000000

`divisor` backs the index level (level = sum(price * shares) / divisor). It is left
null for existing rows: the next calculation re-establishes holdings and derives a
divisor from the base value, which is the correct starting point given the previous
values were not index levels at all.

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7f2d9c41a58"
down_revision: Union[str, None] = "a1c4e77b9d02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("indices", sa.Column("divisor", sa.Float(), nullable=True))
    op.add_column("indices", sa.Column("generation_prompt", sa.Text(), nullable=True))

    # Previously stored "index values" were a weighted average share price, not an
    # index level. Clearing them prevents a misleading number being charted against
    # correctly calculated points once recalculation begins.
    op.execute("UPDATE indices SET current_value = NULL")


def downgrade() -> None:
    op.drop_column("indices", "generation_prompt")
    op.drop_column("indices", "divisor")
