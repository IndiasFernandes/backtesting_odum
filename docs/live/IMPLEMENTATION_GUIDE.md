# Live Execution Implementation Prompt

## Context & Requirements

You are implementing a **production-grade live execution mechanism** for a unified trading system that mirrors the existing backtesting infrastructure. This system must support both NautilusTrader-integrated venues (CeFi: Binance, Bybit, OKX) and external SDK adapters (TradFi: Interactive Brokers, Deribit, future DeFi/Sports venues).

### Key Requirements (from CeFi Backtesting Execution Infrastructure Spec)

1. **Data Integration**:
   - Use `unified-cloud-services` (UCS) as **PRIMARY** interface for all GCS operations
   - Input: `gs://instruments-store-cefi-central-element-323112/` (instruments)
   - Input: `gs://market-data-tick-cefi-central-element-323112/` (market tick data)
   - Output: `gs://execution-store-cefi-central-element-323112/` (execution results)
   - Use `download_from_gcs()`, `download_from_gcs_streaming()`, `upload_to_gcs()` from UCS
   - Local filesystem (`data_downloads/`) is **fallback only**, not primary

2. **Signal-Driven Execution**:
   - Load sparse signals from `strategy-service` (~29 signals/day)
   - Stream only 5-minute windows of tick data for each signal interval
   - Achieve 94% I/O reduction and 85% faster execution time
   - Only fetch tick data when signals change direction

3. **Output Schema Alignment**:
   - Match exact backtest output schemas:
     - `summary.json`: High-level results (PNL, metrics, execution stats)
     - `orders.parquet`: All order records with status tracking
     - `fills.parquet`: All execution fills with fees
     - `positions.parquet`: Position timeline with P&L
     - `equity_curve.parquet`: Portfolio value over time
   - Upload to: `gs://execution-store-cefi-central-element-323112/backtest_results/{run_id}/`

4. **Consistency with Backtest**:
   - Reuse same execution algorithms: `TWAPExecAlgorithm`, `VWAPExecAlgorithm`, `IcebergExecAlgorithm`
   - Same order types (MarketOrder, LimitOrder)
   - Same routing logic (fee-based, liquidity-based)
   - Same configuration schema (external JSON)

5. **NautilusTrader Integration**:
   - Use `TradingNode` for live trading (not `BacktestNode`)
   - Configure `TradingNodeConfig` with `data_clients` and `exec_clients`
   - Register client factories: `BinanceLiveDataClientFactory`, `BinanceLiveExecClientFactory`
   - Support Binance Spot/Futures, Bybit, OKX via NautilusTrader
   - Event-driven updates: subscribe to `OrderSubmitted`, `OrderFilled`, `OrderCancelled`

6. **External SDK Adapter Framework**:
   - Abstract interface for venues not in NautilusTrader (Deribit, IB, future DeFi/Sports)
   - Reference implementation: Deribit adapter
   - Unified interface: same API for NautilusTrader and external venues

7. **Unified Tracking**:
   - **Unified OMS**: Tracks all orders across all venues (NautilusTrader + External)
   - **Unified Position Tracker**: Aggregates positions across venues
   - PostgreSQL persistence for `unified_orders` and `unified_positions`
   - Real-time sync for NautilusTrader, periodic polling for external adapters

8. **Pre-Trade Risk Engine**:
   - Velocity checks (orders per second/minute)
   - Position limits (per-instrument, per-strategy, global)
   - Exposure limits (total notional value)
   - Order size validation
   - Price tolerance checks

9. **Smart Order Router**:
   - Routes orders to optimal venue (NautilusTrader or External)
   - Considers execution cost, fees, liquidity, latency
   - Supports multi-venue routing

10. **Execution Orchestrator**:
    - Main entry point: coordinates risk checks, OMS, routing, execution
    - Handles error recovery and graceful degradation
    - Integrates with `strategy-service` for signal-driven execution
    - Protobuf Order messages over gRPC or REST API

11. **Deployment Architecture**:
    - Docker Compose profiles: `backtest`, `live`, `both`
    - Separate services: `odum-backend` (port 8000) for backtest, `odum-live-backend` (port 8001) for live
    - Frontend service detection: dynamically show/hide pages based on active services
    - Status page: `/status` shows service health and GCS bucket connectivity

12. **Frontend Integration**:
    - Live execution UI: Trade submission form, order monitoring, position tracking
    - Strategy deployment interface: Upload and deploy strategies
    - CLI alignment: Frontend displays match CLI output exactly
    - Service detection: UI adapts to active services (backtest only, live only, or both)
    - Real-time updates: WebSocket or polling for order status, positions, fills

12. **Migration Strategy**:
    - Zero-downtime, backward-compatible migration
    - No breaking changes to existing functionality
    - Gradual rollout possible
    - Easy rollback if needed

---

## Related Documentation

**Core Documents**:
- `ROADMAP.md` - Complete implementation roadmap (6 phases, 12 weeks)
- `FILE_ORGANIZATION.md` - File organization strategy and directory structure
- `DEVELOPMENT_PROMPT.md` - Quick reference development prompt

**Key Architecture Decisions**:
- **Deployment**: Separate Services (Docker Compose Profiles) - See `ROADMAP.md` Deployment Architecture section
- **File Organization**: Clear separation (`backend/live/` vs `backend/backtest/`) - See `FILE_ORGANIZATION.md`
- **Data Interface**: UCS as PRIMARY interface (not `data_downloads/`)
- **NautilusTrader**: Use `TradingNode` for live (not `BacktestNode`)

**Critical Points**:
- UCS is PRIMARY interface for all GCS operations
- Signal-driven execution reduces I/O by 94%
- Output schemas match backtest spec exactly
- TradingNode configuration follows NautilusTrader patterns
- Results uploaded to `gs://execution-store-cefi-central-element-323112/` via UCS

---

## NautilusTrader Documentation Alignment

### TradingNode Configuration (from NautilusTrader docs)

**Key Pattern**:
```python
from nautilus_trader.live.node import TradingNode, TradingNodeConfig
from nautilus_trader.adapters.binance import (
    BINANCE,
    BinanceLiveDataClientFactory,
    BinanceLiveExecClientFactory
)

# Configure TradingNode
config = TradingNodeConfig(
    trader_id="TRADER-001",
    data_clients={
        BINANCE: {
            "api_key": "YOUR_API_KEY",
            "api_secret": "YOUR_API_SECRET",
            "account_type": "spot",  # or "usdt_future", "coin_future"
        },
    },
    exec_clients={
        BINANCE: {
            "api_key": "YOUR_API_KEY",
            "api_secret": "YOUR_API_SECRET",
            "account_type": "spot",
        },
    },
)

# Create and build TradingNode
node = TradingNode(config=config)
node.add_data_client_factory(BINANCE, BinanceLiveDataClientFactory)
node.add_exec_client_factory(BINANCE, BinanceLiveExecClientFactory)
node.build()

# Start trading node
node.start()
```

**Critical Points**:
- `TradingNodeConfig` requires `trader_id`, `data_clients`, `exec_clients`
- Client factories must be registered before building
- `node.build()` prepares the node, `node.start()` begins execution
- Event-driven: subscribe to order events, position updates, account updates

### Event Subscriptions (from NautilusTrader docs)

**Key Pattern**:
```python
from nautilus_trader.core.events import OrderFilled, OrderSubmitted, OrderCancelled

# Subscribe to events
node.subscribe("order.filled", on_order_filled)
node.subscribe("order.submitted", on_order_submitted)
node.subscribe("order.cancelled", on_order_cancelled)
```

**Critical Points**:
- Events are asynchronous and event-driven
- Portfolio updates automatically when orders fill
- Cache maintains current state (orders, positions, account)

---

## Current Implementation Reference

### 1. `backend/data/loader.py` (UCSDataLoader)
**Purpose**: Unified Cloud Services data loader

**Current Location**: `backend/data/loader.py`

**Key Functions**:
- `load_trades()`: Loads trade data from GCS via UCS
- `load_book_snapshots()`: Loads book snapshot data from GCS via UCS
- Uses `UnifiedCloudService` for all GCS operations
- Checks FUSE mount status, falls back to direct GCS API

**Critical Points**:
- UCS is PRIMARY interface
- `UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=true` uses direct GCS API
- Local filesystem is fallback only

### 2. `backend/results/serializer.py` (ResultSerializer)
**Purpose**: Result serialization and upload

**Current Location**: `backend/results/serializer.py`

**Key Functions**:
- `serialize_backtest_results()`: Converts results to JSON/Parquet
- `upload_results_to_gcs()`: Uploads to GCS via UCS
- Uses `UnifiedCloudService.upload_to_gcs()` for all uploads

**Critical Points**:
- Results uploaded directly to GCS via UCS
- No local persistence required for production
- Output schemas match spec exactly

### 3. `backend/core/engine.py` (BacktestEngine)
**Purpose**: Backtest orchestration (reference for live execution)

**Current Location**: `backend/core/engine.py`

**Key Patterns**:
- Uses `BacktestNode` for backtest execution
- External JSON configuration
- Automatic data conversion
- Execution algorithm support
- Coordinates: validation, data loading, instrument creation, node configuration, execution, result extraction

**Critical Points**:
- Live execution should mirror this pattern but use `TradingNode` instead
- Same configuration schema
- Same execution algorithms
- Current location: `backend/core/engine.py` (may move to `backend/backtest/engine.py` later)

### 4. `backend/execution/algorithms.py`
**Purpose**: Execution algorithms (TWAP, VWAP, Iceberg)

**Current Location**: `backend/execution/algorithms.py`

**Key Classes**:
- `TWAPExecAlgorithm`
- `VWAPExecAlgorithm`
- `IcebergExecAlgorithm`

**Critical Points**:
- These algorithms must be reused in live execution
- Same interface (`ExecAlgorithm`) for both backtest and live
- Shared component - used by both backtest and live

### 5. `backend/execution/router.py`
**Purpose**: Smart order routing (base logic)

**Current Location**: `backend/execution/router.py`

**Key Functions**:
- Base routing logic for venue selection
- Fee, liquidity, latency calculations

**Critical Points**:
- Shared base logic - used by both backtest and live
- Live execution will extend this in `backend/live/router.py` with live-specific logic
- Same routing principles as backtest

---

## Implementation Checklist

### Phase 1: Core Infrastructure (Weeks 1-2)
- [ ] Create module structure: `backend/live/` (see `docs/live/FILE_ORGANIZATION.md`)
- [ ] Set up PostgreSQL schema (`unified_orders`, `unified_positions`)
- [ ] Create configuration framework (external JSON, similar to backtest)
- [ ] Set up UCS integration (verify GCS bucket access)

**File Organization**: Follow clear separation strategy:
- `backend/live/` - Live-specific components
- `backend/backtest/` - Backtest-specific components (existing)
- `backend/execution/`, `backend/data/`, etc. - Shared components
- See `docs/live/FILE_ORGANIZATION.md` for complete structure

### Phase 2: TradingNode Integration (Weeks 3-4)
- [ ] Create `LiveTradingNode` wrapper class
- [ ] Implement `TradingNodeConfig` builder from JSON
- [ ] Register Binance, Bybit, OKX client factories
- [ ] Subscribe to order events (`OrderSubmitted`, `OrderFilled`, `OrderCancelled`)
- [ ] Implement position sync from NautilusTrader Portfolio
- [ ] Test with paper trading accounts

### Phase 3: External Adapter Framework (Weeks 5-6)
- [ ] Create `ExternalAdapter` abstract base class
- [ ] Implement `DeribitAdapter` (reference implementation)
- [ ] Create adapter registry
- [ ] Implement adapter lifecycle (connect, disconnect, reconnect)
- [ ] Test Deribit adapter with demo account

### Phase 4: Unified OMS & Position Tracker (Weeks 7-8)
- [ ] Implement `UnifiedOrderManager` (create, update, query orders)
- [ ] Implement `UnifiedPositionTracker` (aggregate positions)
- [ ] Set up PostgreSQL persistence
- [ ] Implement real-time sync from NautilusTrader
- [ ] Implement periodic polling for external adapters
- [ ] Add reconciliation on startup

### Phase 5: Risk Engine & Router Integration (Weeks 9-10)
- [ ] Implement `PreTradeRiskEngine` (velocity, position limits, exposure, order size, price tolerance)
- [ ] Extend `SmartOrderRouter` for live execution
- [ ] Create `LiveExecutionOrchestrator` (coordinate all components)
- [ ] Implement error recovery and graceful degradation
- [ ] Add monitoring and logging

### Phase 6: Testing & Validation (Weeks 11-12)
- [ ] Unit tests for all components
- [ ] Integration tests (end-to-end order flow)
- [ ] Paper trading validation
- [ ] Performance testing
- [ ] Production readiness review

---

## Critical Implementation Guidelines

### 1. UCS as PRIMARY Interface
- ✅ **ALWAYS** use `unified-cloud-services` for GCS operations
- ✅ Use `download_from_gcs()` / `download_from_gcs_streaming()` for data loading
- ✅ Use `upload_to_gcs()` for result uploads
- ❌ **NEVER** write to local filesystem for production (only fallback/dev)
- ❌ **NEVER** assume `data_downloads/` is primary data source

### 2. Signal-Driven Execution
- ✅ Load sparse signals from `strategy-service` first
- ✅ Stream only 5-minute windows of tick data for each signal
- ✅ Skip intervals without signal changes
- ❌ **NEVER** load full day files unless necessary

### 3. Output Schema Alignment
- ✅ Match exact schemas from spec (`summary.json`, `orders.parquet`, `fills.parquet`, `positions.parquet`, `equity_curve.parquet`)
- ✅ Upload to `gs://execution-store-cefi-central-element-323112/backtest_results/{run_id}/`
- ✅ Use UCS `upload_to_gcs()` for all uploads

### 4. Consistency with Backtest
- ✅ Reuse same execution algorithms (`TWAPExecAlgorithm`, `VWAPExecAlgorithm`, `IcebergExecAlgorithm`)
- ✅ Same order types (MarketOrder, LimitOrder)
- ✅ Same routing logic (fee-based, liquidity-based)
- ✅ Same configuration schema (external JSON)

### 5. NautilusTrader Integration
- ✅ Use `TradingNode` (not `BacktestNode`) for live trading
- ✅ Configure `TradingNodeConfig` with `data_clients` and `exec_clients`
- ✅ Register client factories before building
- ✅ Subscribe to events for real-time updates

### 6. External SDK Adapter Framework
- ✅ Abstract interface for venues not in NautilusTrader
- ✅ Reference implementation: Deribit adapter
- ✅ Unified interface: same API for NautilusTrader and external venues

### 7. Unified Tracking
- ✅ Unified OMS tracks all orders (NautilusTrader + External)
- ✅ Unified Position Tracker aggregates positions
- ✅ PostgreSQL persistence for `unified_orders` and `unified_positions`
- ✅ Real-time sync for NautilusTrader, periodic polling for external

### 8. Deployment Architecture
- ✅ Docker Compose profiles: `backtest`, `live`, `both`
- ✅ Separate services: `odum-backend` (8000), `odum-live-backend` (8001)
- ✅ Frontend service detection: dynamically show/hide pages
- ✅ Status page: `/status` shows service health and GCS connectivity

---

## Questions to Resolve

1. **API Protocol**: Prefer gRPC or REST API for strategy service integration?
2. **Database**: PostgreSQL confirmed? Any specific requirements (connection pooling, migrations)?
3. **Monitoring**: Preferred monitoring stack? (Prometheus, Datadog, etc.)
4. **External Venues**: Priority order for external adapter development? (Deribit first, then IB?)
5. **Deployment Environment**: Where will live execution service be deployed? (Cloud, on-premise, hybrid)

---

## Success Criteria

1. ✅ Live execution runs E2E with provided data
2. ✅ Signal-driven execution reduces I/O by 94%
3. ✅ Output schemas match backtest spec exactly
4. ✅ Results uploaded to GCS via UCS
5. ✅ TradingNode integration works with Binance, Bybit, OKX
6. ✅ External adapter framework supports Deribit
7. ✅ Unified OMS and Position Tracker track all venues
8. ✅ Pre-Trade Risk Engine validates all orders
9. ✅ Smart Router selects optimal venue
10. ✅ Frontend detects services and shows/hides pages dynamically
11. ✅ Status page shows service health and GCS connectivity
12. ✅ Zero-downtime migration from current system

---

## Next Steps

1. **Review Roadmap**: See `ROADMAP.md` for complete implementation roadmap
2. **Review File Organization**: See `FILE_ORGANIZATION.md` for directory structure
3. **Set Up Infrastructure**: Create module structure, database schema, configuration framework
4. **Begin Phase 1**: Start with core infrastructure setup
5. **Iterate**: Follow phased implementation plan, test incrementally
6. **Validate**: Ensure alignment with spec, NautilusTrader docs, and current implementation

---

*Last updated: December 2025*
*Aligned with: CeFi Backtesting Execution Infrastructure — Final Specification*
*NautilusTrader Version: Latest (as of December 2025)*

