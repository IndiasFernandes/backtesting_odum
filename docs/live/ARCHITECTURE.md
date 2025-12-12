# Live Execution Mechanism - Architecture & Implementation Plan

## Executive Summary

This document outlines the architecture and implementation plan for a production-grade live execution mechanism that mirrors the backtest system's design while supporting both NautilusTrader-integrated venues (CeFi: Binance, Bybit, OKX) and external SDK adapters (CeFi: Deribit, TradFi: Interactive Brokers, future DeFi/Sports venues). The system will be deployed separately from backtesting but share core execution mechanisms for consistency.

**SSOT Document**: This document is part of the SSOT (Single Source of Truth) documentation. Always refer to `docs/live/ROADMAP.md` for implementation phases and decisions, `docs/live/FILE_ORGANIZATION.md` for file structure, and update all SSOT documents as implementation progresses to keep them coherent.

**Context7**: Always use Context7 for NautilusTrader documentation and external library references.

---

## 1. Current State Analysis

### 1.1 Backtest Architecture (Reference Implementation)

**Core Components:**
- **BacktestEngine**: Orchestrates backtest execution using `BacktestNode`
- **BacktestNode**: NautilusTrader high-level API for deterministic event replay
- **Strategy**: Trade-driven `TempBacktestStrategy` (one order per trade tick)
- **Data Layer**: `ParquetDataCatalog` for historical data ingestion
- **Execution Algorithms**: TWAP, VWAP, Iceberg (via `ExecAlgorithm` interface)
- **Smart Router**: Venue selection based on fees, liquidity, latency

**Key Patterns:**
- External JSON configuration (no hardcoded parameters)
- Event-driven architecture (NautilusTrader event loop)
- Unified order/position tracking
- Execution algorithm support (child order spawning)

### 1.2 User Guide Execution Orchestrator Pattern

The user guide (`COMPLETE_USER_GUIDE.html`) describes an ideal execution orchestrator pattern:

```
Strategy → Execution Orchestrator → Risk Engine → Unified OMS → Smart Router → Venue
                                                                                    ↓
                                                                    Position Tracker ←
```

**Components:**
- **Execution Orchestrator**: Main entry point, coordinates workflow
- **Pre-Trade Risk Engine**: Validates orders before execution
- **Unified OMS**: Tracks orders across all venues (NautilusTrader + External)
- **Unified Position Tracker**: Aggregates positions across venues
- **Smart Router**: Routes to optimal venue (NautilusTrader or External SDK)
- **Order Adapter**: Converts JSON Order messages ↔ NautilusTrader orders
- **Instrument Converter**: Canonical ID parsing and conversion

**Key Features:**
- Supports both NautilusTrader venues and external SDK adapters (Deribit)
- Unified tracking regardless of execution venue
- Real-time configuration updates
- Database persistence (PostgreSQL)

### 1.3 Gap Analysis

**What Exists:**
- ✅ Backtest execution engine (`BacktestEngine`)
- ✅ Execution algorithms (TWAP, VWAP, Iceberg)
- ✅ Smart router (basic venue selection)
- ✅ Strategy framework (`TempBacktestStrategy`)
- ✅ Data conversion utilities
- ✅ Configuration loader

**What's Missing:**
- ❌ Live `TradingNode` integration
- ❌ External SDK adapter framework (Deribit, IB, etc.)
- ❌ Unified OMS for live trading
- ❌ Unified Position Tracker for live trading
- ❌ Pre-Trade Risk Engine integration
- ❌ Execution Orchestrator for live trading
- ❌ Real-time market data subscriptions
- ❌ Order reconciliation and state sync
- ❌ External system synchronization mechanism

---

## 2. Architecture Design

### 2.1 High-Level Architecture

**Data Flow (UCS as Primary Interface)**:

```
┌─────────────────────┐     ┌──────────────────────┐
│  instruments-service │     │ market-tick-data-    │
│  (Static Reference)  │     │ handler (Tick Data)  │
└──────────┬──────────┘     └──────────┬───────────┘
           │                           │
           ▼                           ▼
    ┌──────────────────────────────────────────────────┐
    │         Google Cloud Storage (GCS)               │
    │  • instruments-store-cefi-central-element-323112│
    │  • market-data-tick-cefi-central-element-323112 │
    └──────────────────────────────────────────────────┘
           │                           │
           ▼                           ▼
    ┌──────────────────────────────────────────────────┐
    │   unified-cloud-services (PRIMARY INTERFACE)      │
    │   • download_from_gcs()                          │
    │   • download_from_gcs_streaming()                 │
    │   • upload_to_gcs()                               │
    └──────────────────────────────────────────────────┘
           │                           │
           ▼                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Strategy Service (External)                  │
│              (Sends JSON Order messages via REST API)          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Live Execution Orchestrator                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Pre-Trade Risk Engine                                   │   │
│  │  - Velocity checks                                        │   │
│  │  - Position limits                                        │   │
│  │  - Exposure limits                                        │   │
│  │  - Order size validation                                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                             │                                     │
│                             ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Unified Order Management System (OMS)                    │   │
│  │  - Create order (status: PENDING)                         │   │
│  │  - Track order lifecycle                                  │   │
│  │  - Sync with NautilusTrader Cache                          │   │
│  │  - Sync with External Adapters                            │   │
│  │  - PostgreSQL persistence                                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                             │                                     │
│                             ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Smart Order Router                                       │   │
│  │  - Venue selection (NautilusTrader vs External)           │   │
│  │  - Execution cost calculation                             │   │
│  │  - Multi-venue routing                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│   NautilusTrader Path    │  │   External SDK Path      │
│                          │  │                          │
│  ┌────────────────────┐  │  │  ┌────────────────────┐ │
│  │  TradingNode       │  │  │  │  External Adapter   │ │
│  │  - LiveDataEngine  │  │  │  │  Framework         │ │
│  │  - LiveExecEngine  │  │  │  │  - DeribitAdapter   │ │
│  │  - Portfolio       │  │  │  │  - IBAdapter       │ │
│  │  - Cache           │  │  │  │  - Future: DeFi    │ │
│  └────────────────────┘  │  │  │  - Future: Sports   │ │
│         │                │  │  └────────────────────┘ │
│         │                │  │         │                │
│         ▼                │  │         ▼                │
│  ┌────────────────────┐  │  │  ┌────────────────────┐ │
│  │  Execution Clients  │  │  │  │  Venue APIs         │ │
│  │  - BinanceSpot     │  │  │  │  - Deribit REST/WS  │ │
│  │  - BinanceFutures  │  │  │  │  - IB TWS API       │ │
│  │  - Bybit           │  │  │  │  - Future APIs       │ │
│  │  - OKX             │  │  │  └────────────────────┘ │
│  └────────────────────┘  │  │                          │
│         │                │  │                          │
│         └────────────────┴──┴──────────────────────────┘
│                          │
│                          ▼
│         ┌────────────────────────────────┐
│         │  Unified Position Tracker      │
│         │  - Aggregate NautilusTrader    │
│         │  - Aggregate External Adapters │
│         │  - PostgreSQL persistence      │
│         └────────────────────────────────┘
│                          │
│                          ▼
│         ┌────────────────────────────────┐
│         │  unified-cloud-services         │
│         │  (PRIMARY OUTPUT INTERFACE)     │
│         │  • upload_to_gcs()              │
│         └────────────────────────────────┘
│                          │
│                          ▼
│         ┌────────────────────────────────┐
│         │  Google Cloud Storage (GCS)    │
│         │  • execution-store-cefi-...    │
│         │  (Results written via UCS)     │
│         └────────────────────────────────┘
```

**⚠️ Key Point**: All data operations go through `unified-cloud-services`:
- **Input**: GCS → UCS → Execution Engine (via `download_from_gcs()` / `download_from_gcs_streaming()`)
- **Output**: Execution Engine → UCS → GCS (via `upload_to_gcs()`)
- Local filesystem (`data_downloads/`, `backend/backtest_results/`) is fallback/development convenience only

### 2.2 Core Design Principles

1. **Consistency with Backtest**: Use same execution algorithms, order types, and routing logic
2. **Unified Abstraction**: Single interface for NautilusTrader and external venues
3. **Separation of Concerns**: Clear boundaries between execution, risk, OMS, and routing
4. **Extensibility**: Easy to add new venues (both NautilusTrader and external)
5. **State Synchronization**: Real-time sync between internal state and venue state
6. **Fault Tolerance**: Graceful degradation, error recovery, reconciliation

### 2.3 Component Architecture

#### 2.3.1 Live Execution Orchestrator

**Purpose**: Main entry point for live order execution, coordinates all components.

**Responsibilities:**
- Receive JSON Order messages from strategy service (via REST API)
- Coordinate risk checks, OMS, routing, and execution
- Handle error recovery and graceful degradation
- Provide unified order submission interface
- Track order lifecycle from submission to completion

**Key Methods:**
```python
class LiveExecutionOrchestrator:
    async def submit_order(order_data: dict) -> ExecutionResult  # JSON dict from REST API
    async def cancel_order(operation_id: str) -> CancellationResult
    async def get_order_status(operation_id: str) -> OrderStatus
    async def initialize() -> None
    async def close() -> None
```

**Dependencies:**
- `PreTradeRiskEngine`
- `UnifiedOrderManager`
- `UnifiedPositionTracker`
- `SmartOrderRouter`
- `TradingNode` (NautilusTrader)
- External adapters registry

#### 2.3.2 TradingNode Integration

**Purpose**: Integrate NautilusTrader `TradingNode` for CeFi venues (Binance, Bybit, OKX).

**NautilusTrader Multi-Venue Support**:
- ✅ **Native multi-venue support**: NautilusTrader TradingNode can connect to multiple venues simultaneously
- ✅ **Multiple account types**: Can configure multiple account types from same venue (e.g., BINANCE_SPOT + BINANCE_FUTURES)
- ✅ **Portfolio aggregation**: NautilusTrader Portfolio component automatically aggregates positions across all configured venues
- ✅ **Unified event loop**: Single event loop handles all venues, orders, and positions

**Components:**
- **LiveDataEngine**: Market data subscriptions (supports multiple venues)
- **LiveExecutionEngine**: Order execution and lifecycle management (supports multiple venues)
- **Portfolio**: Position and account tracking (aggregates across all venues)
- **Cache**: Instrument and market data cache (unified across venues)
- **Execution Clients**: BinanceSpot, BinanceFutures, Bybit, OKX (all can run simultaneously)

**Configuration:**
```python
# Similar to backtest config but for live trading
{
    "trading_node": {
        "data_clients": [
            {"name": "BINANCE_SPOT", "api_key": "...", "api_secret": "..."},
            {"name": "BINANCE_FUTURES", "api_key": "...", "api_secret": "..."},
            {"name": "BYBIT", "api_key": "...", "api_secret": "..."},
            {"name": "OKX", "api_key": "...", "api_secret": "..."}
        ],
        "exec_clients": [
            # Same as data_clients
        ],
        "portfolio": {
            "accounts": [
                {"account_id": "BINANCE_SPOT", "base_currency": "USDT"},
                {"account_id": "BINANCE_FUTURES", "base_currency": "USDT"}
            ]
        }
    }
}
```

**Integration Points:**
- Subscribe to order events (OrderSubmitted, OrderFilled, OrderCancelled) - works across all venues
- Subscribe to position updates - Portfolio aggregates positions from all venues
- Submit orders via `TradingNode.submit_order()` - specify venue in order
- Query positions via `Portfolio.positions()` - returns aggregated positions across all venues

**Note**: Our `UnifiedPositionTracker` builds on top of NautilusTrader's Portfolio, adding:
- External adapter position aggregation (Deribit, IB, etc.)
- PostgreSQL persistence
- Canonical instrument ID mapping
- Cross-venue exposure calculations

#### 2.3.3 External SDK Adapter Framework

**Purpose**: Abstract interface for venues not available in NautilusTrader (Deribit, IB, future DeFi/Sports).

**Base Adapter Interface:**
```python
class ExternalVenueAdapter(ABC):
    """Base class for external venue adapters."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to venue API."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from venue API."""
        pass
    
    @abstractmethod
    async def submit_order(self, order: UnifiedOrder) -> ExecutionResult:
        """Submit order to venue."""
        pass
    
    @abstractmethod
    async def cancel_order(self, venue_order_id: str) -> CancellationResult:
        """Cancel order on venue."""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get current positions from venue."""
        pass
    
    @abstractmethod
    async def get_open_orders(self) -> List[Order]:
        """Get open orders from venue."""
        pass
    
    @abstractmethod
    async def subscribe_market_data(self, instrument_id: str) -> None:
        """Subscribe to market data for instrument."""
        pass
```

**Deribit Adapter Example:**
```python
class DeribitAdapter(ExternalVenueAdapter):
    """Deribit options exchange adapter."""
    
    def __init__(self, api_key: str, api_secret: str):
        self.client = DeribitClient(api_key, api_secret)
        self.venue = "DERIBIT"
    
    async def submit_order(self, order: UnifiedOrder) -> ExecutionResult:
        # Convert UnifiedOrder to Deribit order format
        deribit_order = self._convert_to_deribit_format(order)
        # Submit via Deribit REST API
        response = await self.client.place_order(deribit_order)
        # Convert response to ExecutionResult
        return self._convert_to_execution_result(response)
    
    async def get_positions(self) -> List[Position]:
        # Query Deribit positions API
        positions = await self.client.get_positions()
        # Convert to unified Position format
        return [self._convert_to_unified_position(p) for p in positions]
```

**Adapter Registry:**
```python
class AdapterRegistry:
    """Registry for external venue adapters."""
    
    def __init__(self):
        self._adapters: Dict[str, ExternalVenueAdapter] = {}
    
    def register(self, venue: str, adapter: ExternalVenueAdapter):
        self._adapters[venue] = adapter
    
    def get(self, venue: str) -> Optional[ExternalVenueAdapter]:
        return self._adapters.get(venue)
    
    async def initialize_all(self):
        """Initialize all registered adapters."""
        for adapter in self._adapters.values():
            await adapter.connect()
```

#### 2.3.4 Unified Order Management System (OMS)

**Purpose**: Track all orders across all venues in a single system.

**Key Features:**
- Create order records (status: PENDING)
- Update order status (SUBMITTED, FILLED, CANCELLED, REJECTED)
- Sync with NautilusTrader Cache (for NautilusTrader venues)
- Sync with External Adapters (for external venues)
- PostgreSQL persistence for order recovery
- Query by operation_id, strategy, venue, instrument

**Database Schema** (SQLAlchemy Models + asyncpg Execution):

**SQLAlchemy Model** (`backend/live/models.py`):
```python
from sqlalchemy import Column, String, Numeric, DateTime, JSON, Integer
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class UnifiedOrder(Base):
    """Unified order tracking across all venues (CeFi, DeFi, TradFi, Sports)."""
    
    __tablename__ = 'unified_orders'
    
    # Core identification
    operation_id = Column(String(255), primary_key=True)
    operation = Column(String(20), nullable=False)  # trade, supply, borrow, stake, withdraw, swap, transfer, bet
    canonical_id = Column(String(255), nullable=False)
    venue = Column(String(100), nullable=False)
    venue_type = Column(String(20), nullable=False)  # 'NAUTILUS' or 'EXTERNAL_SDK'
    venue_order_id = Column(String(255))
    
    # Order status and execution
    status = Column(String(50), nullable=False)  # PENDING, SUBMITTED, FILLED, CANCELLED, REJECTED
    side = Column(String(20), nullable=False)  # BUY, SELL, SUPPLY, BORROW, STAKE, WITHDRAW, BACK, LAY
    quantity = Column(Numeric(36, 18), nullable=False)
    price = Column(Numeric(36, 18))
    order_type = Column(String(20), nullable=False)  # MARKET or LIMIT
    time_in_force = Column(String(20))
    exec_algorithm = Column(String(20))  # TWAP, VWAP, ICEBERG, NORMAL
    exec_algorithm_params = Column(JSON)  # JSONB: algorithm-specific parameters
    fills = Column(JSON)  # JSONB: array of fill objects
    expected_deltas = Column(JSON)  # JSONB: {instrument_key: delta} for position tracking
    
    # Atomic transactions (DeFi)
    atomic_group_id = Column(String(255))
    sequence_in_group = Column(Integer)
    
    # DeFi-specific fields
    tx_hash = Column(String(66))  # Blockchain transaction hash
    gas_used = Column(Integer)
    gas_price_gwei = Column(Numeric(18, 9))
    contract_address = Column(String(42))
    source_token = Column(String(20))
    target_token = Column(String(20))
    max_slippage = Column(Numeric(10, 6))
    
    # Sports betting specific
    odds = Column(Numeric(10, 4))
    selection = Column(String(50))  # Home/Draw/Away, Over/Under, Yes/No
    potential_payout = Column(Numeric(36, 18))
    
    # Transfer fields
    source_venue = Column(String(100))
    target_venue = Column(String(100))
    
    # Risk and strategy
    strategy_id = Column(String(255))
    rejection_reason = Column(String(500))
    error_message = Column(String(1000))
    order_metadata = Column('metadata', JSON)  # JSONB: Additional metadata
    
    # Timestamps
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
```

**Database Indexes** (for performance):
- `idx_orders_operation` - Operation type queries (trade, swap, bet, etc.)
- `idx_orders_atomic_group` - Atomic transaction queries
- `idx_orders_tx_hash` - DeFi transaction lookups
- `idx_orders_operation_status` - Composite index for operation+status queries
- `idx_orders_strategy` - Risk engine queries by strategy
- `idx_orders_created_at` - Velocity checks (orders per second/minute)
- `idx_orders_status_strategy` - Composite index for status+strategy queries
- `idx_orders_venue_status` - Composite index for venue+status queries
- `idx_orders_instrument` - Instrument-based queries
- `idx_orders_status` - Status-based queries

**asyncpg Execution** (`backend/live/oms.py`):
```python
import asyncpg
from backend.live.database import get_pool

async def create_order(order_data: dict):
    """Create order using asyncpg for performance."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO unified_orders 
            (operation_id, canonical_id, venue, venue_type, status, side, quantity, price, fills, strategy_id, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW())
            """,
            order_data['operation_id'],
            order_data['canonical_id'],
            # ... other fields
        )
```

**NautilusTrader Sync:**
- Subscribe to order events from TradingNode
- Update Unified OMS when orders change state
- Maintain bidirectional sync (Unified OMS ↔ NautilusTrader Cache)

**External Adapter Sync:**
- Poll external adapters for order status updates
- Handle webhook callbacks from external venues (if available)
- Maintain state consistency

#### 2.3.5 Unified Position Tracker

**Purpose**: Aggregate positions across all venues into a single view.

**Relationship to NautilusTrader Portfolio**:
- NautilusTrader Portfolio already aggregates positions across all NautilusTrader venues (Binance, Bybit, OKX)
- Our Unified Position Tracker extends this by:
  - Adding external adapter positions (Deribit, IB, etc.)
  - Providing canonical instrument ID mapping
  - Adding PostgreSQL persistence
  - Enabling cross-venue exposure calculations

**Key Features:**
- Aggregate positions from NautilusTrader Portfolio (which already aggregates Binance/Bybit/OKX)
- Aggregate positions from external adapters (Deribit, IB, etc.)
- Unified queries by canonical ID, strategy, venue, base asset
- Aggregated exposure calculations (total notional value across all venues)
- Position deltas from fill events
- PostgreSQL persistence

**Database Schema** (SQLAlchemy Models + asyncpg Execution):

**SQLAlchemy Model** (`backend/live/models.py`):
```python
class UnifiedPosition(Base):
    __tablename__ = 'unified_positions'
    
    canonical_id = Column(String(255), primary_key=True)
    base_asset = Column(String(10), nullable=False)
    aggregated_quantity = Column(Numeric(36, 18), nullable=False)
    venue_positions = Column(JSON, nullable=False)  # JSONB in PostgreSQL: {venue: quantity}
    venue_types = Column(JSON, nullable=False)  # JSONB: {venue: 'NAUTILUS' | 'EXTERNAL_SDK'}
    average_entry_price = Column(Numeric(36, 18))
    current_price = Column(Numeric(36, 18))
    unrealized_pnl = Column(Numeric(36, 18))
    realized_pnl = Column(Numeric(36, 18))
    updated_at = Column(DateTime, nullable=False)
```

**asyncpg Execution** (`backend/live/positions.py`):
```python
import asyncpg
from backend.live.database import get_pool

async def update_position(canonical_id: str, position_data: dict):
    """Update position using asyncpg for performance."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO unified_positions 
            (canonical_id, base_asset, aggregated_quantity, venue_positions, venue_types, updated_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            ON CONFLICT (canonical_id) 
            DO UPDATE SET 
                aggregated_quantity = EXCLUDED.aggregated_quantity,
                venue_positions = EXCLUDED.venue_positions,
                updated_at = NOW()
            """,
            canonical_id,
            position_data['base_asset'],
            # ... other fields
        )
```

**Refresh Strategy:**
- Real-time updates from NautilusTrader Portfolio events
- Periodic polling of external adapters (configurable interval)
- On-demand refresh via API call

#### 2.3.6 Smart Order Router (Enhanced)

**Purpose**: Route orders to optimal venue based on execution cost, availability, and venue type.

**Routing Logic:**
1. Determine instrument type (SPOT_PAIR, PERPETUAL, FUTURE, OPTION)
2. Filter available venues (NautilusTrader vs External)
3. Calculate execution cost for each venue:
   - Fees (maker/taker)
   - Estimated slippage
   - Latency impact
4. Select best venue
5. Route to appropriate execution path:
   - NautilusTrader → TradingNode
   - External → External Adapter

**Venue Selection:**
```python
def route_order(order: UnifiedOrder) -> VenueRoute:
    # Get available venues for instrument type
    venues = get_available_venues(order.instrument_type)
    
    # Calculate scores for each venue
    scores = {}
    for venue in venues:
        if venue.type == "NAUTILUS":
            score = calculate_nautilus_score(venue, order)
        else:
            score = calculate_external_score(venue, order)
        scores[venue] = score
    
    # Select best venue
    best_venue = max(scores.items(), key=lambda x: x[1])[0]
    
    return VenueRoute(
        venue=best_venue.name,
        venue_type=best_venue.type,
        execution_path=best_venue.execution_path
    )
```

#### 2.3.7 Pre-Trade Risk Engine

**Purpose**: Validate orders before execution using Unified OMS and Position Tracker.

**Risk Checks:**
- **Velocity**: Orders per second/minute limits
- **Order Size**: Min/max order size validation
- **Position Limits**: Per-instrument, per-strategy, global limits
- **Exposure Limits**: Total notional value limits
- **Price Tolerance**: Limit order price deviation checks
- **Account Balance**: Sufficient balance/margin checks

**Integration:**
- Uses Unified OMS for velocity checks
- Uses Unified Position Tracker for position/exposure checks
- Real-time configuration updates

#### 2.3.8 Order Adapter

**Purpose**: Convert between JSON Order messages (from REST API) and NautilusTrader Order objects.

**Key Functions:**
- `json_to_nautilus_order()`: Convert JSON dict → NautilusTrader Order
- `nautilus_order_to_execution_result()`: Convert NautilusTrader Order + Fills → ExecutionResult
- Handle Deribit orders (reject, route to external adapter)

#### 2.3.9 Instrument Converter

**Purpose**: Parse canonical instrument IDs and convert to venue-specific formats.

**Canonical ID Format:**
```
[ASSET_CLASS:]VENUE:INSTRUMENT_TYPE:PAYLOAD[@CHAIN]
```

**Examples:**
- `BINANCE-SPOT:SPOT_PAIR:BTC-USDT`
- `BINANCE-FUTURES:PERPETUAL:BTC-USDT`
- `DERIBIT:PERPETUAL:BTC-USD@INV`
- `DERIBIT:OPTION:BTC-USD-50000-20241231-C`

**Functions:**
- `parse_canonical_id()`: Parse canonical ID into components
- `canonical_to_nautilus()`: Convert to NautilusTrader InstrumentId
- `canonical_to_deribit_symbol()`: Convert to Deribit symbol format

---

## 3. Implementation Plan

### 3.1 Phase 1: Core Infrastructure (Weeks 1-2) ✅ COMPLETE

**Goal**: Set up foundation for live execution.

**Status**: ✅ Complete - All infrastructure and Docker setup finished

**Tasks:**
1. **Create Live Execution Module Structure**
   
   **File Organization**: Clear separation between live and backtest code (see `docs/live/FILE_ORGANIZATION.md`)
   
   ```
   backend/
   ├── backtest/                # Backtest-specific (existing)
   │   └── engine.py           # BacktestEngine
   │
   ├── live/                    # Live-specific (NEW)
   │   ├── __init__.py
   │   ├── engine.py           # LiveEngine wrapper
   │   ├── orchestrator.py     # LiveExecutionOrchestrator
   │   ├── trading_node.py     # TradingNode wrapper/integration
   │   ├── oms.py              # UnifiedOrderManager
   │   ├── positions.py        # UnifiedPositionTracker
   │   ├── risk.py             # PreTradeRiskEngine
   │   ├── router.py           # Live-specific Smart Router
   │   └── adapters/           # External SDK adapters
   │       ├── __init__.py
   │       ├── base.py         # ExternalVenueAdapter base class
   │       ├── registry.py     # AdapterRegistry
   │       └── deribit.py      # DeribitAdapter (example)
   │
   ├── execution/               # Shared execution components
   │   ├── algorithms.py       # TWAP, VWAP, Iceberg (shared)
   │   └── router.py           # Base router logic (shared)
   │
   ├── api/                     # API endpoints
   │   ├── server.py           # Backtest API (port 8000)
   │   └── live_server.py      # Live API (port 8001) - NEW
   │
   └── ... (other shared modules: data/, instruments/, config/, results/)
   ```
   
   **Key Principles**:
   - ✅ Clear separation: `backend/backtest/` vs `backend/live/`
   - ✅ Shared components: `backend/execution/`, `backend/data/`, etc.
   - ✅ No cross-imports: Shared code never imports from backtest/ or live/
   - ✅ Service-specific entry points: Separate API servers
   
   See `docs/live/FILE_ORGANIZATION.md` for complete file organization strategy.

2. **Database Schema Setup**
   - **SQLAlchemy** for schema definition and migrations:
     - Create SQLAlchemy models (`backend/live/models.py`)
     - Set up Alembic migrations (`backend/live/alembic/`)
     - Define database schema declaratively
   - **asyncpg** for execution-critical operations:
     - Create asyncpg connection pool manager (`backend/live/database.py`)
     - Use raw SQL queries via asyncpg for performance-critical paths
     - Connection pooling with asyncpg (`min_size=10`, `max_size=20`)
   - **Hybrid Approach**:
     - SQLAlchemy models for schema definition and validation
     - asyncpg for all database operations (faster than SQLAlchemy ORM)
     - Alembic for schema migrations

3. **Configuration Framework**
   - Live trading config schema (similar to backtest config)
   - Environment variable support
   - Real-time config updates (Redis/API)

### 3.2 Phase 2: TradingNode Integration (Weeks 3-4)

**Goal**: Integrate NautilusTrader TradingNode for CeFi venues.

**Tasks:**
1. **TradingNode Wrapper**
   - Create `LiveTradingNode` wrapper class
   - Initialize TradingNode with data/exec clients
   - Handle TradingNode lifecycle (start, stop, reconnect)

2. **Event Subscriptions**
   - Subscribe to order events (OrderSubmitted, OrderFilled, OrderCancelled)
   - Subscribe to position updates
   - Subscribe to account updates

3. **Order Submission**
   - Convert UnifiedOrder → NautilusTrader Order
   - Submit via TradingNode
   - Handle execution results

4. **Position Sync**
   - Query NautilusTrader Portfolio for positions
   - Update Unified Position Tracker

### 3.3 Phase 3: External Adapter Framework (Weeks 5-6)

**Goal**: Build framework for external venue adapters.

**Tasks:**
1. **Base Adapter Interface**
   - Define `ExternalVenueAdapter` ABC
   - Standardize adapter interface
   - Error handling and retry logic

2. **Deribit Adapter (Reference Implementation)**
   - Implement Deribit REST/WebSocket client
   - Convert UnifiedOrder ↔ Deribit order format
   - Handle Deribit-specific features (options, inverse contracts)

3. **Adapter Registry**
   - Register/unregister adapters
   - Initialize all adapters on startup
   - Health checks and reconnection logic

4. **Integration with Smart Router**
   - Route orders to external adapters
   - Handle execution results from external adapters

### 3.4 Phase 4: Unified OMS & Position Tracker (Weeks 7-8)

**Goal**: Implement unified tracking across all venues.

**Tasks:**
1. **Unified OMS**
   - Create order records
   - Update order status
   - Sync with NautilusTrader Cache
   - Sync with external adapters
   - Query interface

2. **Unified Position Tracker**
   - Aggregate positions from NautilusTrader
   - Aggregate positions from external adapters
   - Exposure calculations
   - Query interface

3. **State Synchronization**
   - Real-time sync from NautilusTrader events
   - Periodic polling of external adapters
   - Reconciliation on startup

### 3.5 Phase 5: Risk Engine & Router Integration (Weeks 9-10)

**Goal**: Integrate risk checks and smart routing.

**Tasks:**
1. **Pre-Trade Risk Engine**
   - Velocity checks (using Unified OMS)
   - Position limits (using Unified Position Tracker)
   - Exposure limits
   - Order size validation
   - Price tolerance checks

2. **Enhanced Smart Router**
   - Venue selection logic
   - Execution cost calculation
   - Multi-venue routing
   - Integration with both NautilusTrader and external adapters

3. **Execution Orchestrator**
   - Coordinate all components
   - Handle order workflow
   - Error recovery
   - Unified API interface

### 3.6 Phase 6: Testing & Validation (Weeks 11-12)

**Goal**: Comprehensive testing and validation.

**Tasks:**
1. **Unit Tests**
   - Component-level tests
   - Mock external APIs
   - Test error scenarios

2. **Integration Tests**
   - End-to-end order flow
   - Multi-venue routing
   - State synchronization
   - Error recovery

3. **Paper Trading**
   - Test with demo accounts
   - Validate execution quality
   - Monitor performance

4. **Production Readiness**
   - Performance optimization
   - Monitoring and alerting
   - Documentation

---

## 4. Key Design Decisions

### 4.1 Consistency with Backtest

**Decision**: Use same execution algorithms, order types, and routing logic as backtest.

**Rationale**: Ensures backtest results are predictive of live performance.

**Implementation**:
- Reuse `TWAPExecAlgorithm`, `VWAPExecAlgorithm`, `IcebergExecAlgorithm`
- Same order types (MarketOrder, LimitOrder)
- Same routing logic (fee-based, liquidity-based)

### 4.2 Unified Abstraction

**Decision**: Single interface for NautilusTrader and external venues.

**Rationale**: Simplifies strategy code and enables venue-agnostic routing.

**Implementation**:
- `UnifiedOrder` model (venue-agnostic)
- `ExecutionResult` model (standardized)
- Adapter pattern for venue-specific conversions

### 4.3 State Synchronization

**Decision**: Real-time sync for NautilusTrader, periodic polling for external adapters.

**Rationale**: NautilusTrader provides event-driven updates; external APIs may not.

**Implementation**:
- Subscribe to NautilusTrader events
- Poll external adapters every N seconds (configurable)
- Reconciliation on startup

### 4.4 Unified Cloud Services as Primary Interface

**Decision**: `unified-cloud-services` (UCS) is the **PRIMARY** interface for all data operations, not local filesystem.

**Rationale**: 
- Production systems should use GCS directly via UCS API
- Local filesystem (`data_downloads/`) is only for development/FUSE fallback
- Results should be written directly to GCS, not local filesystem
- Ensures consistency between backtest and live execution

**Current Implementation** (as of December 2025):
- ✅ `backend/ucs_data_loader.py` - Uses UCS `download_from_gcs()` / `download_from_gcs_streaming()` for all data loading
- ✅ `backend/results.py` - Uses UCS `upload_to_gcs()` for all result uploads
- ✅ `UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=true` - Direct GCS API (not FUSE)
- ✅ Results written to `gs://execution-store-cefi-central-element-323112/` via UCS

**Implementation**:
- All data reads: GCS → UCS → Execution Engine
- All data writes: Execution Engine → UCS → GCS
- Local filesystem: Fallback only (FUSE mount or development convenience)
- No local data persistence required for production

### 4.4 Error Recovery

**Decision**: Graceful degradation with automatic retry and reconciliation.

**Rationale**: Live trading requires high reliability.

**Implementation**:
- Retry logic with exponential backoff
- Circuit breakers for failing venues
- Reconciliation on reconnection
- Fallback to alternative venues

### 4.5 Deployment Separation

**Decision**: Deploy live execution separately from backtest, but share core mechanisms.

**Rationale**: Different scaling requirements and operational concerns.

**Implementation**:
- Shared library for execution algorithms, routing logic
- Separate deployment containers
- Independent configuration and databases

---

## 5. External System Synchronization

### 5.1 Strategy Service Integration

**Protocol**: **REST API** (JSON) for strategy service → live execution. Simple, easy to debug, sufficient for most use cases.

**Message Format** (JSON):
```json
{
    "operation_id": "OP-12345",
    "instrument_key": "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN",
    "side": "BUY",
    "quantity": "1.0",
    "price": null,  // Optional for market orders
    "order_type": "MARKET",  // or "LIMIT"
    "strategy_id": "momentum-btc-v1",
    "exec_algorithm": "TWAP",  // Optional: TWAP, VWAP, Iceberg, NORMAL
    "exec_algorithm_params": {
        "duration_sec": 300,
        "max_slices": 10
    }
}
```

**Response Format** (JSON):
```json
{
    "operation_id": "OP-12345",
    "order_id": "ORD-67890",
    "status": "ACCEPTED",  // "ACCEPTED", "REJECTED", "FILLED", "CANCELED"
    "rejection_reason": null,  // If rejected, reason here
    "fills": [
        {
            "fill_id": "FILL-001",
            "quantity": "0.5",
            "price": "45000.0",
            "fee": "2.25",
            "timestamp": "2025-12-08T10:30:00Z"
        }
    ]
}
```

**API Endpoint**: `POST /api/orders` (FastAPI)

**Future Improvement**: Consider migrating to **gRPC** if order volume exceeds 100 orders/sec or latency requirements become critical (<5ms). gRPC provides lower latency (~2-5ms vs ~10-20ms) and smaller payloads, but requires more setup and is harder to debug.

**Message Format (Legacy Protobuf reference - if migrating to gRPC):**
```protobuf
message Order {
    string operation_id = 1;
    string instrument_key = 2;  // Canonical ID
    string side = 3;  // "BUY" or "SELL"
    string amount = 4;
    string price = 5;  // Optional for market orders
    string strategy_id = 6;
    map<string, string> exec_algorithm_params = 7;  // TWAP, VWAP, etc.
}

message ExecutionResult {
    string operation_id = 1;
    string status = 2;  // "FILLED", "REJECTED", "CANCELLED", etc.
    string venue = 3;
    repeated Fill fills = 4;
    string error_message = 5;
}
```

### 5.2 Venue API Management

**NautilusTrader Venues:**
- Managed by TradingNode
- Automatic reconnection and error handling
- Event-driven updates

**External Venues:**
- Managed by adapters
- Custom reconnection logic per adapter
- Polling or webhook-based updates

**Unified Interface:**
- All venues exposed through same interface
- Router selects venue transparently
- OMS tracks all orders uniformly

---

## 6. Configuration Schema

### 6.1 Live Trading Configuration

```json
{
    "trading_node": {
        "data_clients": [
            {
                "name": "BINANCE_SPOT",
                "api_key": "${BINANCE_SPOT_API_KEY}",
                "api_secret": "${BINANCE_SPOT_API_SECRET}",
                "base_url": "https://api.binance.com"
            },
            {
                "name": "BINANCE_FUTURES",
                "api_key": "${BINANCE_FUTURES_API_KEY}",
                "api_secret": "${BINANCE_FUTURES_API_SECRET}",
                "base_url": "https://fapi.binance.com"
            }
        ],
        "exec_clients": [
            // Same as data_clients
        ],
        "portfolio": {
            "accounts": [
                {
                    "account_id": "BINANCE_SPOT",
                    "base_currency": "USDT"
                }
            ]
        }
    },
    "external_adapters": {
        "DERIBIT": {
            "api_key": "${DERIBIT_API_KEY}",
            "api_secret": "${DERIBIT_API_SECRET}",
            "base_url": "https://www.deribit.com"
        },
        "INTERACTIVE_BROKERS": {
            "host": "127.0.0.1",
            "port": 7497,
            "client_id": 1,
            "account_id": "DU123456"
        }
    },
    "risk_engine": {
        "enabled": true,
        "max_orders_per_second": 10,
        "max_orders_per_minute": 100,
        "max_position_per_instrument": {
            "BINANCE-SPOT:SPOT_PAIR:BTC-USDT": "1.0"
        },
        "max_total_notional": "10000000"
    },
    "router": {
        "smart_execution_enabled": true,
        "deribit_routing_enabled": true,
        "nautilus_routing_enabled": true
    },
    "database": {
        "url": "${DATABASE_URL}",
        "pool_size": 10
    },
    "logging": {
        "level": "INFO",
        "log_orders": true,
        "log_fills": true
    }
}
```

---

## 7. Deployment Architecture

**Note**: This section covers **local development** deployment only. Production deployment (GCP, Cloud SQL, etc.) is handled by deployment team, not included in this documentation.

### 7.1 Service Separation Strategy (Local Development)

The system supports three deployment modes using Docker Compose profiles:

1. **Backtest Only**: Run backtesting infrastructure (`odum-backend` on port 8000)
2. **Live Execution Only**: Run live trading infrastructure (`odum-live-backend` on port 8001, PostgreSQL in Docker for local development, Redis)
3. **Both**: Run both systems simultaneously

**Docker Compose Profiles:**
```bash
# Backtest only
docker-compose --profile backtest up -d

# Live only
docker-compose --profile live up -d

# Both
docker-compose --profile backtest --profile live up -d
```

### 7.2 Container Structure

**File Organization**: Clear separation between live and backtest code (see `docs/live/FILE_ORGANIZATION.md`)

```
execution-services/
├── docker-compose.yml              # Base services
├── docker-compose.profiles.yml     # Profile-based deployment
├── backend/
│   ├── Dockerfile                  # Shared Dockerfile
│   │
│   ├── backtest/                   # Backtest-specific code
│   │   └── engine.py              # BacktestEngine
│   │
│   ├── live/                       # Live-specific code
│   │   ├── engine.py              # LiveEngine
│   │   ├── orchestrator.py        # LiveExecutionOrchestrator
│   │   ├── trading_node.py        # TradingNode wrapper
│   │   ├── oms.py                 # UnifiedOrderManager
│   │   ├── positions.py           # UnifiedPositionTracker
│   │   ├── risk.py                # PreTradeRiskEngine
│   │   ├── router.py              # Live-specific router
│   │   └── adapters/              # External SDK adapters
│   │       ├── base.py
│   │       ├── deribit.py
│   │       └── registry.py
│   │
│   ├── execution/                  # Shared execution components
│   │   ├── algorithms.py          # TWAP, VWAP, Iceberg
│   │   └── router.py              # Base router logic
│   │
│   ├── api/                        # API endpoints
│   │   ├── server.py              # Backtest API (port 8000)
│   │   └── live_server.py         # Live API (port 8001)
│   │
│   ├── data/                       # Shared data management
│   ├── instruments/                # Shared instrument management
│   ├── config/                     # Shared configuration
│   ├── results/                    # Shared result processing
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── hooks/
│       │   └── useServiceDetection.ts  # Detect active services
│       └── pages/
│           ├── BacktestComparisonPage.tsx
│           ├── BacktestRunnerPage.tsx
│           ├── LiveExecutePage.tsx          # Trade execution form
│           ├── LiveOrdersPage.tsx           # Order details/history
│           ├── LivePositionsPage.tsx        # OMS/Positions view
│           ├── LiveLogsPage.tsx            # Execution logs
│           └── StatusPage.tsx               # Service status
└── config/
    └── live_trading_config.json
```

**Service Entry Points**:
- **Backtest Service**: `uvicorn backend.api.server:app --port 8000`
- **Live Service**: `uvicorn backend.api.live_server:app --port 8001`

**Import Boundaries**:
- Backtest API imports from: `backend.backtest.*`, `backend.execution.*`, `backend.data.*`, etc.
- Live API imports from: `backend.live.*`, `backend.execution.*`, `backend.instruments.*`, etc.
- Shared modules never import from `backend.backtest.*` or `backend.live.*`

### 7.3 Service Components

| Service | Port | Purpose | Required For |
|---------|------|---------|--------------|
| `odum-backend` | 8000 | Backtest execution engine | Backtest |
| `odum-live-backend` | 8001 | Live execution orchestrator | Live Execution |
| `odum-frontend` | 5173 | React UI (detects active services) | Both |
| `odum-postgres` | 5432 | Unified OMS & Position Tracker DB | Live Execution |
| `odum-redis-live` | 6380 | Live config updates | Live Execution |

### 7.4 Frontend Architecture

**Framework**: React (TypeScript) with Vite  
**Communication**: REST API (JSON) - Same protocol as strategy service integration  
**Real-time Updates**: Polling (every 2-5 seconds) - Simple, reliable, sufficient for most use cases

**Frontend Pages**:

1. **Trade Execution Page** (`/live/execute`):
   - Form-based trade submission (venue, instrument, trade type, order type, quantity, price, execution algorithm)
   - Generates CLI command according to specs (displayed in real-time)
   - Submit order via REST API (`POST /api/orders`)
   - Real-time order status updates in CLI format

2. **OMS/Positions Page** (`/live/positions`):
   - View all positions across venues (aggregated by instrument)
   - Position breakdown by venue, PnL, status
   - Real-time updates via polling

3. **Execution Log Page** (`/live/logs`):
   - Full log of execution actions
   - Orders executed vs rejected (with reasons)
   - Execution layer activity logs
   - Timeline view, filters by status/venue/instrument/time
   - Real-time streaming log updates

4. **Order Details/History Page** (`/live/orders`):
   - Order list table (all orders with status, venue, instrument, quantity, timestamp)
   - Order details view (click order):
     - Order timeline (submitted → risk check → routed → filled/rejected)
     - Fill details (price, quantity, fee, timestamp for each fill)
     - Venue-specific order ID
     - Risk check results (if rejected, show reason)
     - Routing decision (why venue was chosen)
   - Filters: by status, venue, instrument, date range
   - Search: by order ID, operation ID
   - Real-time order status updates

5. **Status Page** (`/status`):
   - Service health (backtest, live, PostgreSQL, Redis)
   - GCS bucket connectivity
   - Connection instructions

**Service Detection**:
- Automatic detection of active services (backtest, live, or both)
- Conditional route rendering based on service availability
- Navigation menu adapts to available services

### 7.5 Migration from Current System

**Current State** (as of December 2025):
- `odum-backend` (port 8000) - Backtest execution engine ✅ Running
- `odum-frontend` (port 5173) - React UI ✅ Running
- `data_downloads` - Data volume container ✅ Running (fallback only, not primary)
- `odum-redis` (port 6379) - Optional, profile-based ⏳ Not running

**Current Data Flow** (UCS as Primary):
- ✅ **Data Source**: GCS via `unified-cloud-services` (UCS)
  - `backend/ucs_data_loader.py` uses UCS for all data loading
  - `UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=true` (direct GCS API)
  - Local `data_downloads/` is fallback only (FUSE mount or dev convenience)
- ✅ **Data Destination**: GCS via `unified-cloud-services` (UCS)
  - `backend/results.py` uses UCS `upload_to_gcs()` for all results
  - Results written directly to `gs://execution-store-cefi-central-element-323112/`
  - Local filesystem writes are temporary (for upload), then cleaned up

**Migration Path** (Zero Downtime, Backward Compatible):

1. **Phase 1: Add Profiles** (No breaking changes)
   - Add `profiles: ['backtest', 'both']` to existing backend service
   - Existing `docker-compose up -d` continues to work
   - New `docker-compose --profile backtest up -d` also works
   - **UCS data flow unchanged** (already primary)

2. **Phase 2: Add Live Services** (Non-breaking addition)
   - Create `docker-compose.profiles.yml` with live services
   - Add PostgreSQL and Redis for live execution
   - Existing backtest services unaffected
   - **Live execution will also use UCS** for data access

3. **Phase 3: Update Frontend** (Gradual rollout)
   - Add service detection hook
   - Add status page
   - Update routing with conditional logic
   - Existing pages continue to work

**Backward Compatibility**:
- ✅ All existing backtest functionality preserved
- ✅ Existing API endpoints unchanged
- ✅ Existing frontend routes still work
- ✅ **UCS remains primary data interface** (no change)
- ✅ No data migration required
- ✅ Easy rollback if needed

See `FRONTEND_SERVICE_DETECTION.md` Section 8 for detailed migration steps.

### 7.2 Environment Variables

```bash
# Unified Cloud Services (PRIMARY DATA INTERFACE)
UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=true  # Use direct GCS API (not FUSE)
UNIFIED_CLOUD_SERVICES_GCS_BUCKET=market-data-tick-cefi-central-element-323112
EXECUTION_STORE_GCS_BUCKET=execution-store-cefi-central-element-323112
GOOGLE_APPLICATION_CREDENTIALS=/app/.secrets/gcs/gcs-service-account.json

# TradingNode Configuration
BINANCE_SPOT_API_KEY=...
BINANCE_SPOT_API_SECRET=...
BINANCE_FUTURES_API_KEY=...
BINANCE_FUTURES_API_SECRET=...

# External Adapters
DERIBIT_API_KEY=...
DERIBIT_API_SECRET=...
IB_HOST=127.0.0.1
IB_PORT=7497

# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/execution_db  # Local PostgreSQL in Docker

# Configuration
LIVE_TRADING_CONFIG_PATH=/app/config/live_trading_config.json

# Note: UNIFIED_CLOUD_LOCAL_PATH is only for FUSE fallback, not primary data source
```

### 7.3 Deployment Steps

1. **Build Container**
   ```bash
   docker build -t live-execution-service:latest .
   ```

2. **Run Container**
   ```bash
   docker run -d \
     --name live-execution \
     -e DATABASE_URL=... \
     -e BINANCE_SPOT_API_KEY=... \
     -v ./config:/app/config \
     live-execution-service:latest
   ```

3. **Health Check**
   ```bash
   curl http://localhost:8001/api/health
   ```

---

## 8. Monitoring & Observability

**Decision**: **Prometheus + Grafana** (for local development and testing)

**Note**: Production monitoring setup is handled by deployment team, not included in this documentation.

### 8.1 Metrics (Local Development)

- Order submission rate
- Order fill rate
- Latency (submission → fill)
- Venue selection distribution
- Risk rejections
- Position exposure
- Error rates

**Implementation**: Prometheus exporters for order latency, fill rates, position tracking

### 8.2 Logging

- All order submissions
- All fills
- Risk check results
- Routing decisions
- State synchronization events
- Errors and warnings

**Implementation**: Structured logs (local files or stdout)

### 8.3 Dashboards (Local Development)

- Grafana dashboards for visualization
- Real-time metrics display
- Historical performance tracking

**Note**: Production dashboards and alerting handled by deployment team.

---

## 9. Future Enhancements

### 9.1 DeFi Integration

- Uniswap adapter (AMM swaps)
- AAVE adapter (lending/borrowing)
- Chain-specific adapters (Ethereum, Solana, etc.)

### 9.2 Sports Betting Integration

- Betfair adapter
- Sports-specific order types (match winner, total goals, etc.)

### 9.3 Advanced Features

- Order splitting across venues
- Dynamic venue selection based on real-time liquidity
- Cross-venue arbitrage detection
- Advanced execution algorithms (adaptive TWAP, etc.)

---

## 10. File Organization

### 10.1 Separation Strategy

**Clear separation** between live and backtest code ensures maintainability and clarity:

- **Backtest Code**: `backend/backtest/` - All backtest-specific components
- **Live Code**: `backend/live/` - All live-specific components  
- **Shared Code**: `backend/execution/`, `backend/data/`, `backend/instruments/`, etc. - Used by both

**Key Principles**:
1. ✅ Clear directory boundaries (`backend/backtest/` vs `backend/live/`)
2. ✅ No cross-imports (shared code never imports from backtest/ or live/)
3. ✅ Service-specific entry points (`backend/api/server.py` vs `backend/api/live_server.py`)
4. ✅ Shared components clearly identified and documented

**See**: 
- `docs/live/FILE_ORGANIZATION.md` - Complete file organization strategy, import patterns, and migration guide
- `docs/live/ROADMAP.md` - Implementation phases, architecture decisions, and requirements
- `docs/live/README.md` - Documentation overview and quick start

---

## 11. Conclusion

This architecture provides a robust, extensible foundation for live execution that:

1. **Mirrors Backtest Design**: Ensures consistency between backtest and live execution
2. **Supports Multiple Venues**: Both NautilusTrader-integrated and external SDK venues
3. **Unified Tracking**: Single source of truth for orders and positions
4. **Extensible**: Easy to add new venues and features
5. **Production-Ready**: Fault tolerance, monitoring, and observability built-in
6. **Clear Organization**: Well-separated file structure for maintainability

The phased implementation plan allows for incremental development and testing, reducing risk and enabling early validation of key components.

