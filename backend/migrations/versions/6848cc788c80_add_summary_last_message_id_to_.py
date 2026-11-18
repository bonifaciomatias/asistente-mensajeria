"""add summary_last_message_id to conversations

Revision ID: 6848cc788c80
Revises: 7a88ff01cb68
Create Date: 2026-11-16 23:10:46.908506

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6848cc788c80'
down_revision: Union[str, Sequence[str], None] = '7a88ff01cb68'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.add_column(sa.Column("summary_last_message_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.drop_column("summary_last_message_id")
