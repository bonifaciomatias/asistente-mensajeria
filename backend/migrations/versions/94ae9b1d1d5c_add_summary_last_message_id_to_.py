"""add summary_last_message_id to conversations

Revision ID: 94ae9b1d1d5c
Revises: 06061732738c
Create Date: 2026-11-16 22:58:43.567527

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94ae9b1d1d5c'
down_revision: Union[str, Sequence[str], None] = '06061732738c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
