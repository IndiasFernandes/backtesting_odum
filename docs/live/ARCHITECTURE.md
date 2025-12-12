# Live Execution Mechanism - Architecture & Implementation Plan

## Executive Summary

This document outlines the architecture and implementation plan for a production-grade live execution mechanism that mirrors the backtest system's design while supporting both NautilusTrader-integrated venues (CeFi: Binance, Bybit, OKX) and external SDK adapters (TradFi: Interactive Brokers, future DeFi/Sports venues). The system will be deployed separately from backtesting but share core execution mechanisms for consistency.

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
- **Order Adapter**: Converts protobuf ↔ NautilusTrader orders
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
│              (Sends protobuf Order messages)                    │
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
- Receive protobuf Order messages from strategy service
- Coordinate risk checks, OMS, routing, and execution
- Handle error recovery and graceful degradation
- Provide unified order submission interface
- Track order lifecycle from submission to completion

**Key Methods:**
```python
class LiveExecutionOrchestrator:
    async def submit_order(proto_order: order_pb2.Order) -> ExecutionResult
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

**Components:**
- **LiveDataEngine**: Market data subscriptions
- **LiveExecutionEngine**: Order execution and lifecycle management
- **Portfolio**: Position and account tracking
- **Cache**: Instrument and market data cache
- **Execution Clients**: BinanceSpot, BinanceFutures, Bybit, OKX

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
- Subscribe to order events (OrderSubmitted, OrderFilled, OrderCancelled)
- Subscribe to position updates
- Submit orders via `TradingNode.submit_order()`
- Query positions via `Portfolio.positions()`

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

**Database Schema:**
```sql
CREATE TABLE unified_orders (
    operation_id VARCHAR(255) PRIMARY KEY,
    canonical_id VARCHAR(255) NOT NULL,
    venue VARCHAR(100) NOT NULL,
    venue_type VARCHAR(20) NOT NULL,  -- 'NAUTILUS' or 'EXTERNAL_SDK'
    venue_order_id VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(36, 18) NOT NULL,
    price DECIMAL(36, 18),
    fills JSONB,
    strategy_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
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

**Key Features:**
- Aggregate positions from NautilusTrader Portfolio
- Aggregate positions from external adapters
- Unified queries by canonical ID, strategy, venue, base asset
- Aggregated exposure calculations (total notional value)
- Position deltas from fill events
- PostgreSQL persistence

**Database Schema:**
```sql
CREATE TABLE unified_positions (
    canonical_id VARCHAR(255) PRIMARY KEY,
    base_asset VARCHAR(10) NOT NULL,
    aggregated_quantity DECIMAL(36, 18) NOT NULL,
    venue_positions JSONB NOT NULL,  -- {venue: quantity}
    venue_types JSONB NOT NULL,  -- {venue: 'NAUTILUS' | 'EXTERNAL_SDK'}
    average_entry_price DECIMAL(36, 18),
    current_price DECIMAL(36, 18),
    unrealized_pnl DECIMAL(36, 18),
    realized_pnl DECIMAL(36, 18),
    updated_at TIMESTAMP NOT NULL
);
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

**Purpose**: Convert between protobuf Order messages and NautilusTrader Order objects.

**Key Functions:**
- `proto_to_nautilus_order()`: Convert protobuf → NautilusTrader Order
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

### 3.1 Phase 1: Core Infrastructure (Weeks 1-2)

**Goal**: Set up foundation for live execution.

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
   - Create PostgreSQL tables (`unified_orders`, `unified_positions`)
   - Alembic migrations
   - Connection pooling

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

**Protocol**: Protobuf Order messages over gRPC or REST API.

**Message Format:**
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
```

**Response Format:**
```protobuf
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

### 7.1 Service Separation Strategy

The system supports three deployment modes using Docker Compose profiles:

1. **Backtest Only**: Run backtesting infrastructure (`odum-backend` on port 8000)
2. **Live Execution Only**: Run live trading infrastructure (`odum-live-backend` on port 8001, PostgreSQL, Redis)
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
│           ├── LiveDashboardPage.tsx
│           ├── LiveOrdersPage.tsx
│           ├── LivePositionsPage.tsx
│           └── StatusPage.tsx          # Service status dashboard
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

### 7.4 Frontend Service Detection

The frontend automatically detects which services are active and shows/hides pages accordingly. See `FRONTEND_SERVICE_DETECTION.md` for detailed implementation plan.

**Key Features:**
- Service health checks every 30 seconds
- Conditional route rendering based on service availability
- Status page showing all service health and GCS bucket connectivity
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
DATABASE_URL=postgresql://user:pass@host:5432/live_execution

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

### 8.1 Metrics

- Order submission rate
- Order fill rate
- Latency (submission → fill)
- Venue selection distribution
- Risk rejections
- Position exposure
- Error rates

### 8.2 Logging

- All order submissions
- All fills
- Risk check results
- Routing decisions
- State synchronization events
- Errors and warnings

### 8.3 Alerts

- High rejection rate
- Venue connectivity issues
- Position limit breaches
- Unusual latency
- State synchronization failures

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

**See**: `docs/live/FILE_ORGANIZATION.md` for complete file organization strategy, import patterns, and migration guide.

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

