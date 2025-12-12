"""add_order_fields

Revision ID: 002_add_order_fields
Revises: 001_initial
Create Date: 2025-12-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_order_fields'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to unified_orders
    op.add_column('unified_orders', sa.Column('order_type', sa.String(length=20), nullable=False, server_default='MARKET'))
    op.add_column('unified_orders', sa.Column('time_in_force', sa.String(length=20), nullable=True))
    op.add_column('unified_orders', sa.Column('exec_algorithm', sa.String(length=20), nullable=True))
    op.add_column('unified_orders', sa.Column('exec_algorithm_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('unified_orders', sa.Column('rejection_reason', sa.String(length=500), nullable=True))
    op.add_column('unified_orders', sa.Column('error_message', sa.String(length=1000), nullable=True))
    
    # Add indexes for risk engine and OMS queries
    op.create_index('idx_orders_strategy', 'unified_orders', ['strategy_id'])
    op.create_index('idx_orders_created_at', 'unified_orders', ['created_at'])
    op.create_index('idx_orders_status_strategy', 'unified_orders', ['status', 'strategy_id'])
    op.create_index('idx_orders_venue_status', 'unified_orders', ['venue', 'status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_orders_venue_status', table_name='unified_orders')
    op.drop_index('idx_orders_status_strategy', table_name='unified_orders')
    op.drop_index('idx_orders_created_at', table_name='unified_orders')
    op.drop_index('idx_orders_strategy', table_name='unified_orders')
    
    # Drop columns
    op.drop_column('unified_orders', 'error_message')
    op.drop_column('unified_orders', 'rejection_reason')
    op.drop_column('unified_orders', 'exec_algorithm_params')
    op.drop_column('unified_orders', 'exec_algorithm')
    op.drop_column('unified_orders', 'time_in_force')
    op.drop_column('unified_orders', 'order_type')

