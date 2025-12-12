"""
SQLAlchemy models for live execution system.

Purpose: Schema definition for unified_orders and unified_positions tables.
Service: Live service only (port 8001)

Note: These models are used for schema definition and Alembic migrations.
Actual database operations use asyncpg directly for performance.
"""
from sqlalchemy import Column, String, Numeric, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all live execution models."""
    pass


class UnifiedOrder(Base):
    """Unified order tracking across all venues."""
    
    __tablename__ = 'unified_orders'
    
    operation_id = Column(String(255), primary_key=True)
    canonical_id = Column(String(255), nullable=False)
    venue = Column(String(100), nullable=False)
    venue_type = Column(String(20), nullable=False)  # 'NAUTILUS' or 'EXTERNAL_SDK'
    venue_order_id = Column(String(255))
    status = Column(String(50), nullable=False)
    side = Column(String(10), nullable=False)
    quantity = Column(Numeric(36, 18), nullable=False)
    price = Column(Numeric(36, 18))
    fills = Column(JSON)  # JSONB in PostgreSQL
    strategy_id = Column(String(255))
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

