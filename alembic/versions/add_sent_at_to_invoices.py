"""add sent_at to invoices

Revision ID: add_sent_at_001
Revises: 
Create Date: 2024-12-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_sent_at_001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sent_at column to invoices table
    op.add_column(
        'invoices',
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    # Remove sent_at column from invoices table
    op.drop_column('invoices', 'sent_at')

