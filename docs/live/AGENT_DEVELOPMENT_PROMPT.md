# Live Execution Component - Development Prompt

## Mission

Develop a **production-grade live execution system** for Odum Execution Services that mirrors the existing backtesting infrastructure while supporting real-time trading across multiple venues (NautilusTrader-integrated and external SDK adapters).

---

## Context & Current State

### Existing Backtest System (Reference Implementation)

You are building on top of a well-organized, modular backtesting system:

**Key Components:**
- `backend/core/engine.py` - `BacktestEngine` orchestrator (uses `BacktestNode`)
- `backend/execution/algorithms.py` - Execution algorithms (TWAP, VWAP, Iceberg)
- `backend/strategies/base.py` - `TempBacktestStrategy` (trade-driven)
- `backend/data/` - Data management (catalog, converter, validator, loader)
- `backend/instruments/` - Instrument factory and registry
- `backend/results/` - Result processing (serializer, extractor, timeline)
- `backend/api/server.py` - FastAPI REST API
- `backend/config/loader.py` - JSON configuration loader

**Architecture Principles:**
- ✅ Modular design (SRP - Single Responsibility Principle)
- ✅ Dependency injection
- ✅ External JSON configuration (no hardcoded values)
- ✅ Unified cloud services (UCS) for GCS operations
- ✅ Event-driven architecture (NautilusTrader event loop)
- ✅ Execution algorithm support via `ExecAlgorithm` interface

**Project Structure:**
```
backend/
├── core/           # Core engine orchestration
├── execution/      # Execution algorithms
├── strategies/     # Trading strategies
├── data/          # Data management
├── instruments/   # Instrument management
├── results/       # Result processing
├── config/       # Configuration
├── api/          # REST API
└── utils/        # Utilities
```

### What Needs to Be Built

**Live Trading System** that:
1. Uses `TradingNode` instead of `BacktestNode`
2. Supports NautilusTrader venues (Binance, Bybit, OKX)
3. Supports external SDK adapters (Deribit, Interactive Brokers)
4. Implements unified OMS and position tracking
5. Integrates pre-trade risk engine
6. Reuses existing execution algorithms
7. Maintains consistency with backtest output schemas

---

## Architecture Requirements

### 1. Core Components to Build

#### 1.1 Live Execution Engine (`backend/live/engine.py`)
**Purpose**: Main orchestrator for live trading (mirrors `BacktestEngine`)

**Responsibilities:**
- Initialize `TradingNode` with live data/exec clients
- Coordinate risk checks, OMS, routing, execution
- Handle real-time event subscriptions
- Manage execution lifecycle
- Error recovery and graceful degradation

**Key Differences from BacktestEngine:**
- Uses `TradingNode` instead of `BacktestNode`
- Real-time market data subscriptions (not historical replay)
- Live order execution (not simulated)
- Continuous operation (not time-bounded)
- External signal integration (from `strategy-service`)

**Interface:**
```python
class LiveEngine:
    def __init__(
        self,
        config_loader: ConfigLoader,
        risk_engine: RiskEngine,
        unified_oms: UnifiedOMS,
        position_tracker: PositionTracker,
        smart_router: SmartOrderRouter
    ):
        ...
    
    def start(self) -> None:
        """Start live trading node and subscribe to events."""
        ...
    
    def execute_order(self, order_request: OrderRequest) -> OrderResponse:
        """Execute order through orchestrator workflow."""
        ...
    
    def stop(self) -> None:
        """Gracefully stop live trading."""
        ...
```

#### 1.2 TradingNode Integration (`backend/live/trading_node.py`)
**Purpose**: Configure and manage NautilusTrader `TradingNode`

**Requirements:**
- Configure `TradingNodeConfig` with live data/exec clients
- Register client factories: `BinanceLiveDataClientFactory`, `BinanceLiveExecClientFactory`
- Support Binance Spot/Futures, Bybit, OKX
- Subscribe to real-time market data
- Handle live execution events

**Reference:**
- Use `backend/core/node_builder.py` as reference for configuration patterns
- Follow NautilusTrader `TradingNode` documentation

#### 1.3 External SDK Adapter Framework (`backend/live/adapters/`)
**Purpose**: Abstract interface for venues not in NautilusTrader

**Structure:**
```
backend/live/adapters/
├── __init__.py
├── base.py              # Abstract adapter interface
├── deribit.py          # Deribit adapter (reference implementation)
├── interactive_brokers.py  # IB adapter
└── registry.py          # Adapter registry
```

**Base Adapter Interface:**
```python
class ExternalAdapter(ABC):
    @abstractmethod
    def connect(self) -> None:
        """Connect to venue API."""
        ...
    
    @abstractmethod
    def submit_order(self, order: Order) -> OrderResponse:
        """Submit order to venue."""
        ...
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> None:
        """Cancel order."""
        ...
    
    @abstractmethod
    def get_position(self, instrument_id: str) -> Position:
        """Get current position."""
        ...
    
    @abstractmethod
    def subscribe_market_data(self, instrument_id: str) -> None:
        """Subscribe to market data."""
        ...
```

#### 1.4 Unified Order Management System (`backend/live/oms.py`)
**Purpose**: Track all orders across all venues (NautilusTrader + External)

**Requirements:**
- Unified order tracking regardless of execution venue
- PostgreSQL persistence (`unified_orders` table)
- Real-time sync with NautilusTrader cache
- Periodic polling for external adapters
- Order lifecycle management (PENDING → SUBMITTED → FILLED/CANCELLED)

**Schema:**
```python
class UnifiedOrder:
    order_id: str
    client_order_id: str
    instrument_id: str
    venue: str
    side: OrderSide
    quantity: Decimal
    price: Optional[Decimal]
    order_type: OrderType
    status: OrderStatus
    venue_type: Literal["nautilus", "external"]
    created_at: datetime
    updated_at: datetime
    fills: List[Fill]
```

#### 1.5 Unified Position Tracker (`backend/live/positions.py`)
**Purpose**: Aggregate positions across all venues

**Requirements:**
- Real-time position aggregation
- PostgreSQL persistence (`unified_positions` table)
- Per-instrument, per-venue, and aggregate views
- P&L calculation
- Position reconciliation

#### 1.6 Pre-Trade Risk Engine (`backend/live/risk.py`)
**Purpose**: Validate orders before execution

**Checks:**
- Velocity limits (orders per second/minute)
- Position limits (per-instrument, per-strategy, global)
- Exposure limits (total notional value)
- Order size validation (min/max)
- Price tolerance checks (slippage limits)

**Interface:**
```python
class RiskEngine:
    def validate_order(self, order: Order, context: OrderContext) -> RiskResult:
        """Validate order against risk rules."""
        ...
    
    def check_velocity(self, strategy_id: str) -> bool:
        """Check if strategy is within velocity limits."""
        ...
    
    def check_position_limits(self, instrument_id: str, side: OrderSide, quantity: Decimal) -> bool:
        """Check if order would exceed position limits."""
        ...
```

#### 1.7 Smart Order Router (`backend/live/router.py`)
**Purpose**: Route orders to optimal venue

**Enhancement**: Extend existing `backend/execution/router.py` for live trading

**Requirements:**
- Route to NautilusTrader venues or external adapters
- Consider execution cost, fees, liquidity, latency
- Support multi-venue routing
- Fallback logic if primary venue fails

#### 1.8 Execution Orchestrator (`backend/live/orchestrator.py`)
**Purpose**: Main entry point coordinating all components

**Workflow:**
```
Order Request
    ↓
Pre-Trade Risk Engine (validate)
    ↓
Unified OMS (create order, status: PENDING)
    ↓
Smart Router (select venue)
    ↓
Execute (NautilusTrader or External Adapter)
    ↓
Unified OMS (update status)
    ↓
Position Tracker (update positions)
    ↓
Return Response
```

---

## Implementation Guidelines

### 2. Code Organization

**Follow existing patterns:**
- ✅ Use dependency injection (pass dependencies via constructor)
- ✅ Single Responsibility Principle (one class, one purpose)
- ✅ Type hints throughout
- ✅ External JSON configuration (no hardcoded values)
- ✅ Comprehensive error handling
- ✅ Logging at appropriate levels

**New Directory Structure:**
```
backend/live/
├── __init__.py
├── engine.py              # LiveEngine (main orchestrator)
├── trading_node.py        # TradingNode configuration
├── orchestrator.py         # Execution orchestrator
├── oms.py                 # Unified OMS
├── positions.py           # Position tracker
├── risk.py                # Risk engine
├── router.py              # Smart router (extends execution/router.py)
├── adapters/              # External SDK adapters
│   ├── __init__.py
│   ├── base.py
│   ├── deribit.py
│   └── registry.py
└── api/                   # Live trading API endpoints
    ├── __init__.py
    └── live_server.py    # FastAPI endpoints for live trading
```

### 3. Integration Points

#### 3.1 Reuse Existing Components
- ✅ `backend/execution/algorithms.py` - Execution algorithms (TWAP, VWAP, Iceberg)
- ✅ `backend/instruments/factory.py` - Instrument creation
- ✅ `backend/config/loader.py` - Configuration loading
- ✅ `backend/data/loader.py` - UCS data loader
- ✅ `backend/utils/` - Utility functions

#### 3.2 External Dependencies
- **NautilusTrader**: Use `TradingNode`, `LiveDataEngine`, `LiveExecEngine`
- **unified-cloud-services**: Use for GCS operations (already integrated)
- **PostgreSQL**: For OMS and position persistence
- **strategy-service**: gRPC/REST API for signal-driven execution

#### 3.3 Configuration Schema
**Extend existing JSON config format:**
```json
{
  "mode": "live",
  "trading": {
    "venues": ["BINANCE-FUTURES", "BYBIT", "DERIBIT"],
    "risk_limits": {
      "max_position_size": 1000000,
      "max_orders_per_minute": 60,
      "max_exposure": 5000000
    },
    "routing": {
      "prefer_nautilus": true,
      "fallback_enabled": true
    }
  },
  "database": {
    "postgres": {
      "host": "localhost",
      "port": 5432,
      "database": "odum_live",
      "user": "odum",
      "password": "${POSTGRES_PASSWORD}"
    }
  },
  "strategy_service": {
    "url": "http://strategy-service:8080",
    "api_key": "${STRATEGY_SERVICE_API_KEY}"
  }
}
```

### 4. API Endpoints

**New FastAPI endpoints** (`backend/live/api/live_server.py`):
- `POST /api/live/orders` - Submit order
- `GET /api/live/orders/{order_id}` - Get order status
- `POST /api/live/orders/{order_id}/cancel` - Cancel order
- `GET /api/live/positions` - Get all positions
- `GET /api/live/positions/{instrument_id}` - Get position for instrument
- `GET /api/live/status` - Get live trading status
- `POST /api/live/start` - Start live trading node
- `POST /api/live/stop` - Stop live trading node

**Integration with existing API:**
- Extend `backend/api/server.py` to include live endpoints (or create separate service)
- Use Docker Compose profiles to run backtest-only, live-only, or both

### 5. Testing Strategy

**Unit Tests:**
- Test each component in isolation
- Mock external dependencies (NautilusTrader, adapters, database)
- Test error handling and edge cases

**Integration Tests:**
- Test component interactions
- Test with mock venues (paper trading)
- Test order lifecycle end-to-end

**Paper Trading:**
- Use testnet/sandbox environments
- Validate against backtest results
- Monitor for discrepancies

---

## Implementation Phases

### Phase 1: Infrastructure & TradingNode (Week 1-2)
**Goal**: Basic live trading with NautilusTrader venues

**Tasks:**
1. Create `backend/live/` directory structure
2. Implement `LiveEngine` with `TradingNode` integration
3. Configure Binance live data/exec clients
4. Implement basic order submission
5. Create live trading API endpoints
6. Add Docker Compose profile for live service

**Deliverables:**
- ✅ Live trading node connects to Binance
- ✅ Can submit orders via API
- ✅ Orders execute on Binance testnet
- ✅ Basic order status tracking

### Phase 2: Unified OMS & Position Tracking (Week 3)
**Goal**: Unified order and position tracking

**Tasks:**
1. Design PostgreSQL schema (`unified_orders`, `unified_positions`)
2. Implement `UnifiedOMS` class
3. Implement `PositionTracker` class
4. Integrate with `LiveEngine`
5. Add persistence layer

**Deliverables:**
- ✅ All orders tracked in unified OMS
- ✅ Positions aggregated across venues
- ✅ PostgreSQL persistence working
- ✅ Real-time position updates

### Phase 3: Risk Engine & Smart Router (Week 4)
**Goal**: Pre-trade risk checks and intelligent routing

**Tasks:**
1. Implement `RiskEngine` with all checks
2. Enhance `SmartOrderRouter` for live trading
3. Integrate risk checks into orchestrator
4. Add routing logic (NautilusTrader vs External)
5. Test with multiple venues

**Deliverables:**
- ✅ Risk checks prevent invalid orders
- ✅ Orders routed to optimal venue
- ✅ Multi-venue routing works
- ✅ Fallback logic tested

### Phase 4: External Adapter Framework (Week 5-6)
**Goal**: Support external SDK adapters (Deribit, IB)

**Tasks:**
1. Design adapter interface (`ExternalAdapter`)
2. Implement Deribit adapter (reference)
3. Implement Interactive Brokers adapter
4. Create adapter registry
5. Integrate with orchestrator
6. Test with external venues

**Deliverables:**
- ✅ Deribit adapter working
- ✅ IB adapter working (if applicable)
- ✅ Adapters integrate seamlessly
- ✅ Unified tracking works for external venues

### Phase 5: Execution Orchestrator & Polish (Week 7-8)
**Goal**: Complete orchestrator and production readiness

**Tasks:**
1. Implement `ExecutionOrchestrator` with full workflow
2. Add error recovery and retry logic
3. Implement graceful shutdown
4. Add monitoring and alerting
5. Performance optimization
6. Documentation and examples

**Deliverables:**
- ✅ Complete orchestrator workflow
- ✅ Error handling robust
- ✅ Production-ready code
- ✅ Comprehensive documentation

---

## Success Criteria

### Functional Requirements
- ✅ Can execute orders on Binance, Bybit, OKX (NautilusTrader)
- ✅ Can execute orders on Deribit (external adapter)
- ✅ All orders tracked in unified OMS
- ✅ Positions aggregated correctly
- ✅ Risk checks prevent invalid orders
- ✅ Smart routing selects optimal venue
- ✅ Execution algorithms work (TWAP, VWAP, Iceberg)
- ✅ API endpoints functional
- ✅ Real-time updates work

### Non-Functional Requirements
- ✅ Code follows existing patterns and style
- ✅ Modular, testable, maintainable
- ✅ Comprehensive error handling
- ✅ Logging and monitoring
- ✅ Performance acceptable (<100ms order submission latency)
- ✅ Database queries optimized
- ✅ Documentation complete

### Integration Requirements
- ✅ Works with existing backtest system (no breaking changes)
- ✅ Uses existing execution algorithms
- ✅ Uses existing configuration format
- ✅ Uses UCS for GCS operations
- ✅ Frontend can detect and use live service

---

## Reference Documents

1. **`docs/live/ARCHITECTURE.md`** - Complete architecture design
2. **`docs/live/IMPLEMENTATION_GUIDE.md`** - Detailed implementation guide
3. **`docs/live/SUMMARY.md`** - Executive summary
4. **`backend/core/engine.py`** - Reference: BacktestEngine implementation
5. **`backend/execution/algorithms.py`** - Reference: Execution algorithms
6. **`backend/strategies/base.py`** - Reference: Strategy implementation
7. **NautilusTrader Docs**: TradingNode, LiveDataEngine, LiveExecEngine

---

## Key Design Decisions

1. **Separate Service**: Live trading runs as separate service (port 8001) from backtest (port 8000)
2. **Shared Components**: Reuse execution algorithms, instruments, config loader
3. **Unified Tracking**: Single OMS and position tracker for all venues
4. **Adapter Pattern**: Abstract interface for external venues
5. **Event-Driven**: Use NautilusTrader event loop for real-time updates
6. **PostgreSQL**: Use database for persistence (not just in-memory)
7. **Signal-Driven**: Integrate with external strategy-service for signals

---

## Questions to Resolve During Development

1. **Database Schema**: Finalize `unified_orders` and `unified_positions` schemas
2. **Adapter Protocol**: Define exact interface for external adapters
3. **Error Recovery**: Define retry logic and failure handling
4. **Monitoring**: Define metrics and alerting requirements
5. **Testing**: Define paper trading and testnet strategy
6. **Deployment**: Define Docker Compose profiles and deployment strategy

---

## Getting Started

1. **Read Architecture Docs**: Review `docs/live/ARCHITECTURE.md` thoroughly
2. **Study Backtest Code**: Understand `backend/core/engine.py` patterns
3. **Set Up Environment**: Docker Compose with PostgreSQL
4. **Start Phase 1**: Implement TradingNode integration
5. **Iterate**: Follow phases, test incrementally, get feedback

---

**Remember**: This is a production system handling real money. Prioritize:
- ✅ Safety and risk management
- ✅ Error handling and recovery
- ✅ Testing and validation
- ✅ Monitoring and observability
- ✅ Code quality and maintainability

Good luck! 🚀

