"""add summary_last_message_id to conversations

Revision ID: 7a88ff01cb68
Revises: 94ae9b1d1d5c
Create Date: 2026-11-16 23:09:47.935152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a88ff01cb68'
down_revision: Union[str, Sequence[str], None] = '94ae9b1d1d5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
