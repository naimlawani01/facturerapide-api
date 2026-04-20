"""remove_vat_columns

Revision ID: 175573690489
Revises: 2ef0b6dcd406
Create Date: 2026-01-29 17:01:48.848342+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '175573690489'
down_revision: Union[str, None] = '2ef0b6dcd406'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove tax_rate from products table
    op.drop_column('products', 'tax_rate')
    
    # Remove tax_rate from invoice_items table
    op.drop_column('invoice_items', 'tax_rate')
    
    # Remove subtotal and tax_total from invoices table
    op.drop_column('invoices', 'subtotal')
    op.drop_column('invoices', 'tax_total')
    
    # Remove tax_rate from quote_items table
    op.drop_column('quote_items', 'tax_rate')
    
    # Remove subtotal and tax_total from quotes table
    op.drop_column('quotes', 'subtotal')
    op.drop_column('quotes', 'tax_total')


def downgrade() -> None:
    # Add back tax_rate to products table
    op.add_column('products', sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), nullable=False, server_default='20.00'))
    
    # Add back tax_rate to invoice_items table
    op.add_column('invoice_items', sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), nullable=False, server_default='20.00'))
    
    # Add back subtotal and tax_total to invoices table
    op.add_column('invoices', sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'))
    op.add_column('invoices', sa.Column('tax_total', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'))
    
    # Add back tax_rate to quote_items table
    op.add_column('quote_items', sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), nullable=False, server_default='20.00'))
    
    # Add back subtotal and tax_total to quotes table
    op.add_column('quotes', sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'))
    op.add_column('quotes', sa.Column('tax_total', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'))

