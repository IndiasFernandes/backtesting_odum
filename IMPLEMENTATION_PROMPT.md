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

12. **Migration Strategy**:
    - Zero-downtime, backward-compatible migration
    - No breaking changes to existing functionality
    - Gradual rollout possible
    - Easy rollback if needed

---

## Reference Architecture Documents

### 1. `LIVE_EXECUTION_ARCHITECTURE.md`
**Purpose**: Detailed architecture and implementation plan

**Key Sections**:
- **Section 1**: Current State Analysis (backtest architecture, user guide pattern, gap analysis)
- **Section 2**: Architecture Design (high-level architecture, core design principles, component details)
- **Section 2.3**: Component Details:
  - 2.3.1: Live Execution Orchestrator
  - 2.3.2: TradingNode Integration
  - 2.3.3: External SDK Adapter Framework
  - 2.3.4: Unified OMS
  - 2.3.5: Unified Position Tracker
  - 2.3.6: Pre-Trade Risk Engine
  - 2.3.7: Smart Order Router
  - 2.3.8: Order Adapter
  - 2.3.9: Instrument Converter
  - 2.3.10: Unified Cloud Services Integration (PRIMARY interface)
  - 2.3.11: Signal-Driven Execution
- **Section 3**: Implementation Phases (12-week phased plan)
- **Section 4**: Key Design Decisions (consistency, unified abstraction, state sync, UCS as primary)
- **Section 5**: Configuration Examples (TradingNode config, external adapters, risk engine, router, GCS)
- **Section 6**: Output Schemas (aligned with spec)
- **Section 7**: Deployment Architecture (Docker Compose profiles, service components, frontend detection, migration)

**Critical Points**:
- UCS is PRIMARY interface (Section 2.3.10, Section 4.4)
- Signal-driven execution reduces I/O by 94% (Section 2.3.11)
- Output schemas match backtest spec exactly (Section 6)
- TradingNode configuration follows NautilusTrader patterns (Section 2.3.2)

### 2. `LIVE_EXECUTION_SUMMARY.md`
**Purpose**: Executive summary and high-level overview

**Key Sections**:
- Key Objectives (consistency, multi-venue, unified tracking, production-ready, spec alignment)
- Architecture Highlights (core components overview)
- Key Design Decisions (consistency, unified abstraction, state sync, deployment separation)
- Implementation Phases (6 phases, 12 weeks)
- Venue Support Matrix (CeFi, TradFi, DeFi, Sports)
- Configuration Example (JSON config structure)
- Output Schemas (aligned with spec)
- External System Integration (strategy service protocol, venue API management)
- GCS Buckets (from spec, UCS access method)
- Migration from Current System (zero-downtime strategy)

**Critical Points**:
- UCS is PRIMARY data interface (Section "GCS Buckets")
- Results uploaded to `gs://execution-store-cefi-central-element-323112/` via UCS
- Local `data_downloads/` is fallback only

### 3. `FRONTEND_SERVICE_DETECTION.md`
**Purpose**: Frontend service detection and status page implementation plan

**Key Sections**:
- Service Architecture (Backtest Backend, Live Backend, PostgreSQL, Redis, Frontend)
- Docker Compose Profiles (`backtest`, `live`, `both`)
- Service Detection Hook (`useServiceDetection.ts`)
- Status Page (`StatusPage.tsx`)
- Conditional Route Rendering (`App.tsx`)
- Conditional Navigation (`Layout.tsx`)
- Backend Health Endpoints (`/api/health`, `/api/health/database`, `/api/health/redis`, `/api/health/gcs`)
- Implementation Checklist (step-by-step guide)
- Migration from Current System (3-phase migration strategy)

**Critical Points**:
- Health endpoints check GCS bucket connectivity via UCS
- Frontend adapts to active services dynamically
- Status page shows all service health and GCS connectivity

### 4. `ARCHITECTURE.md`
**Purpose**: Current backtest system architecture (reference implementation)

**Key Sections**:
- Data & Unified Cloud Services Model (UCS as PRIMARY)
- Data Conversion & Catalog Registration (automatic conversion from GCS via UCS)
- Backtesting Flow (BacktestNode workflow)
- Configuration (external JSON, UCS env vars)

**Critical Points**:
- `backend/ucs_data_loader.py` uses UCS for all data loading
- `backend/results.py` uses UCS for all result uploads
- `UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=true` ensures direct GCS API

### 5. `BACKTEST_SPEC.md`
**Purpose**: CeFi Backtesting Execution Infrastructure — Final Specification

**Key Sections**:
- System Architecture Overview (service responsibilities, data flow)
- Data Inputs (instrument definitions, market tick data, strategy signals)
- Execution Engine (NautilusTrader integration, backtest workflow, execution outputs)
- Unified Cloud Services (required functions, byte-range streaming)
- Output Schemas (summary.json, orders.parquet, fills.parquet, positions.parquet, equity_curve.parquet)
- GCS Bucket Reference (input/output buckets, file sizes)

**Critical Points**:
- UCS is required for all GCS operations
- Signal-driven execution reduces I/O by 94%
- Output schemas are mandatory and must match exactly
- GCS buckets: `instruments-store-cefi-central-element-323112`, `market-data-tick-cefi-central-element-323112`, `execution-store-cefi-central-element-323112`

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

### 1. `backend/ucs_data_loader.py`
**Purpose**: Unified Cloud Services data loader

**Key Functions**:
- `load_data_from_gcs()`: Loads data from GCS via UCS
- `load_data_from_local()`: Fallback to local filesystem
- Uses `UnifiedCloudService` for all GCS operations
- Checks FUSE mount status, falls back to direct GCS API

**Critical Points**:
- UCS is PRIMARY interface
- `UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=true` uses direct GCS API
- Local filesystem is fallback only

### 2. `backend/results.py`
**Purpose**: Result serialization and upload

**Key Functions**:
- `serialize_backtest_results()`: Converts results to JSON/Parquet
- `upload_results_to_gcs()`: Uploads to GCS via UCS
- Uses `UnifiedCloudService.upload_to_gcs()` for all uploads

**Critical Points**:
- Results uploaded directly to GCS via UCS
- No local persistence required for production
- Output schemas match spec exactly

### 3. `backend/backtest_engine.py`
**Purpose**: Backtest orchestration (reference for live execution)

**Key Patterns**:
- Uses `BacktestNode` for backtest execution
- External JSON configuration
- Automatic data conversion
- Execution algorithm support

**Critical Points**:
- Live execution should mirror this pattern but use `TradingNode` instead
- Same configuration schema
- Same execution algorithms

### 4. `backend/execution_algorithms.py`
**Purpose**: Execution algorithms (TWAP, VWAP, Iceberg)

**Key Classes**:
- `TWAPExecAlgorithm`
- `VWAPExecAlgorithm`
- `IcebergExecAlgorithm`

**Critical Points**:
- These algorithms must be reused in live execution
- Same interface (`ExecAlgorithm`) for both backtest and live

### 5. `backend/smart_router.py`
**Purpose**: Smart order routing

**Key Functions**:
- `select_optimal_venue()`: Selects best venue based on fees, liquidity, latency
- Supports both NautilusTrader and external venues

**Critical Points**:
- Must be extended for live execution
- Same routing logic as backtest

---

## Implementation Checklist

### Phase 1: Core Infrastructure (Weeks 1-2)
- [ ] Create module structure: `backend/live_execution/`
- [ ] Set up PostgreSQL schema (`unified_orders`, `unified_positions`)
- [ ] Create configuration framework (external JSON, similar to backtest)
- [ ] Set up UCS integration (verify GCS bucket access)

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

1. **Review Architecture**: Review `LIVE_EXECUTION_ARCHITECTURE.md` for detailed design
2. **Set Up Infrastructure**: Create module structure, database schema, configuration framework
3. **Begin Phase 1**: Start with core infrastructure setup
4. **Iterate**: Follow phased implementation plan, test incrementally
5. **Validate**: Ensure alignment with spec, NautilusTrader docs, and current implementation

---

*Last updated: December 2025*
*Aligned with: CeFi Backtesting Execution Infrastructure — Final Specification*
*NautilusTrader Version: Latest (as of December 2025)*

