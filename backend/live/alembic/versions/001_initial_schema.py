"""initial_schema

Revision ID: 001_initial
Revises: 
Create Date: 2025-12-12 11:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create unified_orders table
    op.create_table(
        'unified_orders',
        sa.Column('operation_id', sa.String(length=255), nullable=False),
        sa.Column('canonical_id', sa.String(length=255), nullable=False),
        sa.Column('venue', sa.String(length=100), nullable=False),
        sa.Column('venue_type', sa.String(length=20), nullable=False),
        sa.Column('venue_order_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=36, scale=18), nullable=False),
        sa.Column('price', sa.Numeric(precision=36, scale=18), nullable=True),
        sa.Column('fills', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('strategy_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('operation_id')
    )
    
    # Create unified_positions table
    op.create_table(
        'unified_positions',
        sa.Column('canonical_id', sa.String(length=255), nullable=False),
        sa.Column('base_asset', sa.String(length=10), nullable=False),
        sa.Column('aggregated_quantity', sa.Numeric(precision=36, scale=18), nullable=False),
        sa.Column('venue_positions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('venue_types', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('average_entry_price', sa.Numeric(precision=36, scale=18), nullable=True),
        sa.Column('current_price', sa.Numeric(precision=36, scale=18), nullable=True),
        sa.Column('unrealized_pnl', sa.Numeric(precision=36, scale=18), nullable=True),
        sa.Column('realized_pnl', sa.Numeric(precision=36, scale=18), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('canonical_id')
    )
    
    # Create indexes for performance
    op.create_index('idx_orders_status', 'unified_orders', ['status'])
    op.create_index('idx_orders_instrument', 'unified_orders', ['canonical_id'])
    op.create_index('idx_orders_venue', 'unified_orders', ['venue'])
    op.create_index('idx_positions_instrument', 'unified_positions', ['canonical_id'])
    op.create_index('idx_positions_base_asset', 'unified_positions', ['base_asset'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_positions_base_asset', table_name='unified_positions')
    op.drop_index('idx_positions_instrument', table_name='unified_positions')
    op.drop_index('idx_orders_venue', table_name='unified_orders')
    op.drop_index('idx_orders_instrument', table_name='unified_orders')
    op.drop_index('idx_orders_status', table_name='unified_orders')
    
    # Drop tables
    op.drop_table('unified_positions')
    op.drop_table('unified_orders')

