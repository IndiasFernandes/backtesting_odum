"""unified_venue_fields

Revision ID: 003_unified_venue_fields
Revises: 002_add_order_fields
Create Date: 2025-12-12 13:00:00.000000

Adds unified fields to support all venue types: CeFi, DeFi, TradFi, Sports Betting
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_unified_venue_fields'
down_revision = '002_add_order_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add operation field (required for routing)
    op.add_column('unified_orders', sa.Column('operation', sa.String(length=20), nullable=False, server_default='trade'))
    
    # Expand side field to support all operations
    op.alter_column('unified_orders', 'side',
                    existing_type=sa.String(length=10),
                    type_=sa.String(length=20),
                    existing_nullable=False)
    
    # Add expected_deltas for position tracking
    op.add_column('unified_orders', sa.Column('expected_deltas', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Add atomic transaction fields (DeFi)
    op.add_column('unified_orders', sa.Column('atomic_group_id', sa.String(length=255), nullable=True))
    op.add_column('unified_orders', sa.Column('sequence_in_group', sa.Integer(), nullable=True))
    
    # Add DeFi-specific fields
    op.add_column('unified_orders', sa.Column('tx_hash', sa.String(length=66), nullable=True))
    op.add_column('unified_orders', sa.Column('gas_used', sa.Integer(), nullable=True))
    op.add_column('unified_orders', sa.Column('gas_price_gwei', sa.Numeric(precision=18, scale=9), nullable=True))
    op.add_column('unified_orders', sa.Column('contract_address', sa.String(length=42), nullable=True))
    op.add_column('unified_orders', sa.Column('source_token', sa.String(length=20), nullable=True))
    op.add_column('unified_orders', sa.Column('target_token', sa.String(length=20), nullable=True))
    op.add_column('unified_orders', sa.Column('max_slippage', sa.Numeric(precision=10, scale=6), nullable=True))
    
    # Add Sports betting fields
    op.add_column('unified_orders', sa.Column('odds', sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column('unified_orders', sa.Column('selection', sa.String(length=50), nullable=True))
    op.add_column('unified_orders', sa.Column('potential_payout', sa.Numeric(precision=36, scale=18), nullable=True))
    
    # Add transfer fields
    op.add_column('unified_orders', sa.Column('source_venue', sa.String(length=100), nullable=True))
    op.add_column('unified_orders', sa.Column('target_venue', sa.String(length=100), nullable=True))
    
    # Add metadata field
    op.add_column('unified_orders', sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Add indexes for new fields
    op.create_index('idx_orders_operation', 'unified_orders', ['operation'])
    op.create_index('idx_orders_atomic_group', 'unified_orders', ['atomic_group_id'])
    op.create_index('idx_orders_tx_hash', 'unified_orders', ['tx_hash'])
    op.create_index('idx_orders_operation_status', 'unified_orders', ['operation', 'status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_orders_operation_status', table_name='unified_orders')
    op.drop_index('idx_orders_tx_hash', table_name='unified_orders')
    op.drop_index('idx_orders_atomic_group', table_name='unified_orders')
    op.drop_index('idx_orders_operation', table_name='unified_orders')
    
    # Drop columns
    op.drop_column('unified_orders', 'metadata')
    op.drop_column('unified_orders', 'target_venue')
    op.drop_column('unified_orders', 'source_venue')
    op.drop_column('unified_orders', 'potential_payout')
    op.drop_column('unified_orders', 'selection')
    op.drop_column('unified_orders', 'odds')
    op.drop_column('unified_orders', 'max_slippage')
    op.drop_column('unified_orders', 'target_token')
    op.drop_column('unified_orders', 'source_token')
    op.drop_column('unified_orders', 'contract_address')
    op.drop_column('unified_orders', 'gas_price_gwei')
    op.drop_column('unified_orders', 'gas_used')
    op.drop_column('unified_orders', 'tx_hash')
    op.drop_column('unified_orders', 'sequence_in_group')
    op.drop_column('unified_orders', 'atomic_group_id')
    op.drop_column('unified_orders', 'expected_deltas')
    
    # Revert side field
    op.alter_column('unified_orders', 'side',
                    existing_type=sa.String(length=20),
                    type_=sa.String(length=10),
                    existing_nullable=False)
    
    # Drop operation field
    op.drop_column('unified_orders', 'operation')

