"""
SQLAlchemy models for live execution system.

Purpose: Schema definition for unified_orders and unified_positions tables.
Service: Live service only (port 8001)

Note: These models are used for schema definition and Alembic migrations.
Actual database operations use asyncpg directly for performance.
"""
from sqlalchemy import Column, String, Numeric, DateTime, JSON, Integer
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all live execution models."""
    pass


class UnifiedOrder(Base):
    """
    Unified order tracking across all venues (CeFi, DeFi, TradFi, Sports).
    
    Supports all operation types:
    - CeFi: trade (BUY/SELL)
    - DeFi: swap, supply, borrow, stake, withdraw, transfer
    - TradFi: trade (BUY/SELL)
    - Sports: bet (BACK/LAY)
    """
    
    __tablename__ = 'unified_orders'
    
    # Core identification
    operation_id = Column(String(255), primary_key=True)
    operation = Column(String(20), nullable=False)  # trade, supply, borrow, stake, withdraw, swap, transfer, bet
    canonical_id = Column(String(255), nullable=False)
    venue = Column(String(100), nullable=False)
    venue_type = Column(String(20), nullable=False)  # 'NAUTILUS' or 'EXTERNAL_SDK'
    venue_order_id = Column(String(255))  # Venue-specific order ID
    
    # Order status and execution
    status = Column(String(50), nullable=False)  # PENDING, SUBMITTED, FILLED, CANCELLED, REJECTED
    side = Column(String(20), nullable=False)  # BUY, SELL, SUPPLY, BORROW, STAKE, WITHDRAW, BACK, LAY
    quantity = Column(Numeric(36, 18), nullable=False)
    price = Column(Numeric(36, 18))  # None for market orders
    order_type = Column(String(20), nullable=False)  # MARKET or LIMIT
    time_in_force = Column(String(20))  # GTC, IOC, FOK, etc.
    
    # Smart execution
    exec_algorithm = Column(String(20))  # TWAP, VWAP, ICEBERG, NORMAL
    exec_algorithm_params = Column(JSON)  # JSONB: algorithm-specific parameters
    
    # Execution results
    fills = Column(JSON)  # JSONB: array of fill objects
    expected_deltas = Column(JSON)  # JSONB: {instrument_key: delta} for position tracking
    
    # Atomic transactions (DeFi)
    atomic_group_id = Column(String(255))  # Groups operations that must execute together
    sequence_in_group = Column(Integer)  # Order of execution within atomic group
    
    # DeFi-specific fields
    tx_hash = Column(String(66))  # Blockchain transaction hash (0x...)
    gas_used = Column(Integer)  # Gas consumed (for on-chain operations)
    gas_price_gwei = Column(Numeric(18, 9))  # Gas price in gwei
    contract_address = Column(String(42))  # Smart contract address (0x...)
    source_token = Column(String(20))  # Source token code (for swaps)
    target_token = Column(String(20))  # Target token code (for swaps)
    max_slippage = Column(Numeric(10, 6))  # Max slippage tolerance (decimal or bps)
    
    # Sports betting specific
    odds = Column(Numeric(10, 4))  # Betting odds (for sports betting)
    selection = Column(String(50))  # Selection: Home/Draw/Away, Over/Under, Yes/No
    potential_payout = Column(Numeric(36, 18))  # Calculated payout (stake × odds)
    
    # Transfer fields
    source_venue = Column(String(100))  # Source venue (for transfers)
    target_venue = Column(String(100))  # Target venue (for transfers)
    
    # Risk and strategy
    strategy_id = Column(String(255))  # For risk engine queries
    rejection_reason = Column(String(500))  # If rejected by risk engine
    error_message = Column(String(1000))  # Error details if any
    
    # Metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    order_metadata = Column('metadata', JSON)  # JSONB: Additional order metadata
    
    # Timestamps
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class UnifiedPosition(Base):
    """Unified position tracking across all venues."""
    
    __tablename__ = 'unified_positions'
    
    canonical_id = Column(String(255), primary_key=True)
    base_asset = Column(String(10), nullable=False)
    aggregated_quantity = Column(Numeric(36, 18), nullable=False)
    venue_positions = Column(JSON, nullable=False)  # JSONB: {venue: quantity}
    venue_types = Column(JSON, nullable=False)  # JSONB: {venue: 'NAUTILUS' | 'EXTERNAL_SDK'}
    average_entry_price = Column(Numeric(36, 18))
    current_price = Column(Numeric(36, 18))
    unrealized_pnl = Column(Numeric(36, 18))
    realized_pnl = Column(Numeric(36, 18))
    updated_at = Column(DateTime, nullable=False)

