"""Widen sftp_destinations.password for ciphertext

Revision ID: e5a17c3d9b42
Revises: d4f9b26a8c13
Create Date: 2026-10-07 10:00:00.000000

SFTP credentials are now stored encrypted, and ciphertext is longer than the
secret it protects: a 255-character limit would reject long passwords. Existing
plaintext rows are left as they are and remain readable; each is encrypted the
next time it is saved.

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5a17c3d9b42"
down_revision: Union[str, None] = "d4f9b26a8c13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("sftp_destinations", "password", type_=sa.Text(), existing_type=sa.String(255))


def downgrade() -> None:
    op.alter_column("sftp_destinations", "password", type_=sa.String(255), existing_type=sa.Text())
