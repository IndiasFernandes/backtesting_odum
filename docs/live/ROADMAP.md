# Live Execution Implementation Roadmap

> Complete implementation roadmap with phases, timelines, and success criteria

## Quick Start

**Start Here**: This document (`ROADMAP.md`) - Complete implementation roadmap with all details

**File Organization**: See `FILE_ORGANIZATION.md` for directory structure and code organization

**Quick Reference**: Use `DEVELOPMENT_PROMPT.md` for concise development prompt

**Note**: All implementation details are consolidated in this ROADMAP.md document

---

## Implementation Phases (14 Weeks)

**Note**: Timeline includes Docker setup and structure migration phases

### Phase 1: Core Infrastructure & Docker Setup (Weeks 1-2) ✅ COMPLETE

**Goal**: Set up foundation for live execution system and Docker deployment

**Tasks**:
- [x] **Set up Git workflow** (see Git Workflow section below):
  - [x] Create `feature/live-execution` branch from `main`
  - [ ] Configure GitHub branch protection for `main` (deployment team)
  - [ ] Set up PR requirements (deployment team)
- [x] Create module structure: `backend/live/` (see `FILE_ORGANIZATION.md`)
- [x] **Set up PostgreSQL database layer**:
  - [x] Install dependencies: `sqlalchemy>=2.0`, `asyncpg>=0.29`, `alembic>=1.13` (added to pyproject.toml)
  - [x] Create SQLAlchemy models (`backend/live/models.py`) for `unified_orders`, `unified_positions`
  - [x] Set up Alembic migrations (`backend/live/alembic/`)
  - [x] Create asyncpg connection pool manager (`backend/live/database.py`)
  - [x] Use SQLAlchemy for schema definition and migrations
  - [x] Use asyncpg directly for execution-critical queries (raw SQL for performance)
  - [x] Enhanced schema with fields for OMS, Risk Engine, Smart Router:
    - [x] `order_type` (MARKET/LIMIT)
    - [x] `exec_algorithm` (TWAP/VWAP/ICEBERG/NORMAL)
    - [x] `exec_algorithm_params` (JSONB)
    - [x] `rejection_reason`, `error_message` (for risk engine)
    - [x] `time_in_force` (GTC/IOC/FOK)
    - [x] Performance indexes (strategy_id, created_at, status+strategy, venue+status)
  - [x] **Unified schema for all venue types** (CeFi, DeFi, TradFi, Sports):
    - [x] `operation` field (trade, supply, borrow, stake, withdraw, swap, transfer, bet)
    - [x] `side` expanded (BUY, SELL, SUPPLY, BORROW, STAKE, WITHDRAW, BACK, LAY)
    - [x] DeFi fields: `tx_hash`, `gas_used`, `gas_price_gwei`, `contract_address`, `source_token`, `target_token`, `max_slippage`
    - [x] Atomic transaction fields: `atomic_group_id`, `sequence_in_group`
    - [x] Sports betting fields: `odds`, `selection`, `potential_payout`
    - [x] Transfer fields: `source_venue`, `target_venue`
    - [x] Position tracking: `expected_deltas` (JSONB)
    - [x] Metadata: `metadata` (JSONB)
    - [x] Indexes: operation, atomic_group, tx_hash, operation+status
- [x] **Create configuration framework** (`backend/live/config/loader.py`):
  - [x] Load JSON configuration files
  - [x] Environment variable substitution (${VAR} and ${VAR:-default})
  - [x] Validate configuration structure
  - [x] Support for trading_node, risk_engine, router, external_adapters sections
- [x] Set up UCS integration (verify GCS bucket access) - **Already working via existing setup**
- [x] Create `backend/api/live_server.py` skeleton
- [x] **Create Docker Compose configuration with 3 profiles** (backward compatible):
  - [x] **Preserve current `docker-compose.yml`** - Keep existing setup working
  - [x] Add profiles to existing services (backward compatible)
  - [x] `backtest` profile (backtest service only)
  - [x] `live` profile (live service only)
  - [x] `both` profile (both services)
  - [x] No default profile - must specify (`docker-compose up` starts nothing)
- [x] Set up Docker services:
  - [x] Backtest service (port 8000) - **Existing `backend` service with `backtest` profile**
  - [x] Live service (port 8001) - **New `live-backend` service with `live` profile**
  - [x] PostgreSQL service - **New for live OMS/positions (port 54320)**
  - [x] Redis service - **New `redis-live` for live config updates (port 6380)**
  - [x] Frontend service (port 5173) - **Works with all profiles**

**Deliverables**:
- ✅ Git workflow established (`feature/live-execution` branch)
- ✅ `backend/live/` directory structure created (13 files)
- ✅ PostgreSQL database schema deployed (2 migrations applied)
- ✅ Enhanced database schema with OMS/Risk/Router fields (order_type, exec_algorithm, etc.)
- ✅ Performance indexes created (strategy_id, created_at, composite indexes)
- ✅ Database operations tested (asyncpg pool, raw SQL queries)
- ✅ Configuration framework created (`backend/live/config/loader.py`)
- ✅ UCS integration verified (GCS bucket access via existing setup)
- ✅ Basic API server responds on port 8001 (health check working)
- ✅ Docker Compose file with 3 profiles working (`backtest`, `live`, `both`)
- ✅ All 3 deployment modes tested and verified

**Success Criteria**:
- [x] `feature/live-execution` branch created
- [x] SQLAlchemy models defined for `unified_orders` and `unified_positions`
- [x] Alembic migrations can create/update database schema
- [x] asyncpg connection pool initialized and working
- [x] Can execute raw SQL queries via asyncpg for performance-critical operations
- [x] Can load configuration from JSON with environment variable substitution
- [x] Database schema supports all OMS, Risk Engine, Smart Router requirements
- [x] Performance indexes optimized for risk engine queries (velocity, position limits)
- [x] Can access GCS buckets via UCS (via existing setup)
- [x] Basic API server responds on port 8001
- [x] **Profile structure**: 3 profiles (`backtest`, `live`, `both`) - no default
- [x] `docker-compose --profile backtest up -d` works (backtest only)
- [x] `docker-compose --profile live up -d` works (live only)
- [x] `docker-compose --profile both up -d` works (both services)
- [x] Existing volumes and environment variables preserved
- [x] Health checks working for all services

**Status**: ✅ **Phase 1 Complete** - Ready for Phase 2

---

### Phase 2: TradingNode Integration (Weeks 3-4)

**Goal**: Integrate NautilusTrader TradingNode for Binance, Bybit, OKX (CeFi)

**Tasks**:
- [x] Create `LiveTradingNode` wrapper class (`backend/live/trading_node.py`)
- [x] Implement `TradingNodeConfig` builder from JSON (`backend/live/config/trading_node_config.py`)
- [x] Register Binance, Bybit, OKX client factories
- [x] Subscribe to order events (`OrderSubmitted`, `OrderFilled`, `OrderCancelled`) - framework ready
- [x] Implement position sync from NautilusTrader Portfolio - framework ready
- [ ] Test with paper trading accounts
- [ ] **Prepare for TradFi**: Design adapter interface to support future TradFi venues (IB, etc.)

**Deliverables**:
- ✅ `LiveTradingNode` wrapper class (`backend/live/trading_node.py`)
- ✅ TradingNode configuration from JSON (`backend/live/config/trading_node_config.py`)
- ✅ Client factory registration (Binance, Bybit, OKX)
- ✅ Event subscription framework (ready for Unified OMS integration)
- ✅ Position sync framework (ready for Unified Position Tracker integration)
- ✅ Adapter interface designed for TradFi/DeFi/Sports (via unified schema)

**Success Criteria**:
- TradingNode connects to Binance/Bybit/OKX
- Order events received and logged
- Positions synced from NautilusTrader Portfolio
- Paper trading test successful
- Adapter interface ready for TradFi integration

---

### Phase 3: External Adapter Framework (Weeks 5-6)

**Goal**: Build framework for venues not in NautilusTrader (Deribit, TradFi, future DeFi/Sports)

**Tasks**:
- [ ] Create `ExternalAdapter` abstract base class (`backend/live/adapters/base.py`)
  - [ ] Design interface to support CeFi (Deribit), TradFi (IB), DeFi (future), Sports (future)
  - [ ] Unified interface for all external venues
- [ ] **Priority**: Complete core system first (OMS, Risk Engine, Router) before Deribit
- [ ] Create adapter registry (`backend/live/adapters/registry.py`)
- [ ] Implement adapter lifecycle (connect, disconnect, reconnect)
- [ ] **After core system complete**: Implement `DeribitAdapter` (reference implementation)
- [ ] Test Deribit adapter with demo account
- [ ] **Future**: TradFi adapter (Interactive Brokers) - after Deribit
- [ ] **Future**: DeFi and Sports adapters - after TradFi

**Deliverables**:
- ✅ `ExternalAdapter` base class (supports all venue types)
- ✅ Adapter registry
- ✅ Adapter lifecycle management
- ✅ `DeribitAdapter` implementation (after core system)
- ⏳ TradFi adapter (future)
- ⏳ DeFi/Sports adapters (future)

**Success Criteria**:
- External adapter interface defined (supports CeFi, TradFi, DeFi, Sports)
- Adapter registry manages multiple adapters
- Deribit adapter connects and authenticates (after core system)
- Can submit orders via Deribit adapter
- Framework ready for TradFi/DeFi/Sports integration

---

### Phase 4: Unified OMS & Position Tracker (Weeks 7-8)

**Goal**: Track all orders and positions across all venues

**Tasks**:
- [ ] Implement `UnifiedOrderManager` (`backend/live/oms.py`)
  - Create, update, query orders
  - Use asyncpg for execution-critical operations (raw SQL)
  - Use SQLAlchemy models for schema validation
  - PostgreSQL persistence via asyncpg connection pool
- [ ] Implement `UnifiedPositionTracker` (`backend/live/positions.py`)
  - Aggregate positions across venues
  - Use asyncpg for execution-critical operations (raw SQL)
  - Use SQLAlchemy models for schema validation
  - PostgreSQL persistence via asyncpg connection pool
- [ ] Implement real-time sync from NautilusTrader
- [ ] Implement periodic polling for external adapters
- [ ] Add reconciliation on startup

**Deliverables**:
- ✅ `UnifiedOrderManager` class
- ✅ `UnifiedPositionTracker` class
- ✅ PostgreSQL persistence layer
- ✅ Real-time sync from NautilusTrader
- ✅ Periodic polling for external adapters

**Success Criteria**:
- Orders tracked in PostgreSQL
- Positions aggregated correctly
- Real-time sync works (NautilusTrader)
- Periodic polling works (external adapters)
- Reconciliation on startup successful

---

### Phase 5: Risk Engine & Router Integration (Weeks 9-10)

**Goal**: Implement pre-trade risk checks and smart order routing

**Tasks**:
- [ ] Implement `PreTradeRiskEngine` (`backend/live/risk.py`)
  - Velocity checks (orders per second/minute)
  - Position limits (per-instrument, per-strategy, global)
  - Exposure limits (total notional value)
  - Order size validation
  - Price tolerance checks
- [ ] Extend `SmartOrderRouter` for live execution (`backend/live/router.py`)
  - Routes orders to optimal venue
  - Considers execution cost, fees, liquidity, latency
- [ ] Create `LiveExecutionOrchestrator` (`backend/live/orchestrator.py`)
  - Coordinate all components
  - Handle error recovery and graceful degradation
- [ ] Add monitoring and logging

**Deliverables**:
- ✅ `PreTradeRiskEngine` class
- ✅ `LiveSmartRouter` class
- ✅ `LiveExecutionOrchestrator` class
- ✅ Error recovery mechanisms
- ✅ Monitoring and logging

**Success Criteria**:
- Risk checks reject invalid orders
- Router selects optimal venue
- Orchestrator coordinates all components
- Error recovery works
- Monitoring shows system health

---

### Phase 6: Structure Migration & Deployment (Weeks 11-12)

**Goal**: Migrate to target structure and finalize deployment

**Tasks**:
- [ ] **Migrate current structure to target structure**:
  - [ ] Create `backend/backtest/` directory (optional, for clarity)
  - [ ] Optionally move `BacktestEngine` from `backend/core/engine.py` to `backend/backtest/engine.py`
  - [ ] Update all imports to reflect new structure
  - [ ] Update Docker services to use new import paths
- [ ] **Finalize Docker deployment**:
  - [ ] **Verify backward compatibility**: `docker-compose up` (no profile) works
  - [ ] Test all 3 Docker profiles (`backtest`, `live`, `both`)
  - [ ] Verify service health endpoints work (`/api/health` for both services)
  - [ ] Verify frontend service detection works
  - [ ] Test independent service restarts (backtest can restart without affecting live)
  - [ ] Test resource isolation (backtest CPU spikes don't affect live latency)
  - [ ] Verify existing volumes and environment variables still work
  - [ ] Test migration from current setup to new profiles (zero downtime)
- [ ] **Local deployment setup**:
  - [ ] Environment variable configuration
  - [ ] Health check configurations
  - [ ] Local monitoring and logging setup
  - [ ] Documentation for local testing procedures

**Deliverables**:
- ✅ Target file structure implemented
- ✅ All imports updated
- ✅ Docker Compose fully tested
- ✅ Local deployment documentation
- ✅ Local testing ready

**Success Criteria**:
- Target structure matches `FILE_ORGANIZATION.md`
- All Docker profiles work correctly
- Services can be deployed independently
- Local deployment procedures documented

### Phase 7: Frontend Integration & Testing (Weeks 13-14)

**Goal**: Frontend integration for live execution testing and comprehensive validation

**Tasks**:
- [ ] **Frontend Service Detection**:
  - [ ] Create `useServiceDetection` React hook
  - [ ] Implement health check endpoints (`/api/health` for backtest, `/api/live/health` for live)
  - [ ] Frontend detects which services are active (backtest only, live only, or both)
  - [ ] Conditionally show/hide pages based on active services
  - [ ] Status page shows service health and GCS connectivity
- [ ] **Live Execution UI - Trade Testing**:
  - [ ] Create live execution page (`/live/execute`)
  - [ ] Trade submission form with all options:
    - Instrument selection (canonical ID)
    - Side (BUY/SELL)
    - Quantity
    - Order type (MARKET/LIMIT)
    - Price (if LIMIT)
    - Execution algorithm (TWAP, VWAP, Iceberg, NORMAL)
    - Algorithm parameters (horizon_secs, interval_secs, etc.)
  - [ ] **CLI Output Display**: Shows exactly what's being sent (matches CLI output format)
  - [ ] Real-time order status display (matches CLI output format)
  - [ ] Position monitoring dashboard (matches CLI format)
  - [ ] Order history and fills display (matches CLI format)
- [ ] **Strategy Deployment Interface**:
  - [ ] Strategy upload page (`/live/strategies`)
  - [ ] Upload strategy configuration (JSON)
  - [ ] Deploy strategy to live execution
  - [ ] Monitor strategy performance
  - [ ] Start/stop strategy execution
  - [ ] View strategy logs (matches CLI output format)
- [ ] **CLI Alignment**:
  - [ ] Ensure frontend displays match CLI output exactly
  - [ ] Same order status format, position format, fill format
  - [ ] Real-time updates via WebSocket or polling
- [ ] **Testing**:
  - [ ] Unit tests for all components
  - [ ] Integration tests (end-to-end order flow)
  - [ ] Frontend-backend integration tests
  - [ ] Paper trading validation
  - [ ] Performance testing
  - [ ] Production readiness review
  - [ ] Documentation completion

**Deliverables**:
- ✅ Service detection hook working
- ✅ Live execution UI page
- ✅ Trade submission interface with CLI output display
- ✅ Real-time order/position monitoring (CLI-aligned)
- ✅ Strategy deployment interface
- ✅ Unit test suite
- ✅ Integration test suite
- ✅ Paper trading validation report
- ✅ Performance test results
- ✅ Production readiness checklist
- ✅ Complete documentation

**Success Criteria**:
- Can submit trades via frontend UI
- Frontend displays match CLI output exactly
- Service detection works (shows/hides pages correctly)
- Strategy deployment works
- All unit tests pass
- Integration tests pass
- Paper trading successful
- Performance meets requirements
- Production ready

---

## Git Workflow — Stable Backtest + Live Execution Development

This workflow ensures the **backtesting system stays stable** while developing the Live Execution system.

### Branch Structure

```
main → stable, production-ready backtesting system
├── hotfix/* → urgent patches applied directly to main
└── feature/live-execution → long-lived branch for new Live Execution implementation
    ├── feature/live-node
    ├── feature/oms
    ├── feature/router
    ├── feature/adapters
    └── feature/risk-engine
```

**Key Principles**:
- `main` is **protected** and cannot be broken
- All development happens in `feature/live-execution` and its sub-branches
- Ongoing fixes flow **main → feature/live-execution**
- Only final, validated work flows **feature/live-execution → main**

### Creating the Live Execution Branch

```bash
git checkout main
git pull
git checkout -b feature/live-execution
git push --set-upstream origin feature/live-execution
```

This branch becomes the workspace for the entire live trading stack.

### Keeping Development in Sync With `main`

When bug fixes or improvements land in main, update your live branch:

```bash
git checkout feature/live-execution
git pull origin main
```

Or cleaner:

```bash
git checkout feature/live-execution
git rebase main
```

**Never merge `feature/live-execution` into `main` directly.**

### Hotfix Workflow for Production

When minor fixes are needed on the stable system:

```bash
git checkout main
git pull
git checkout -b hotfix/<name>
# fix code...
git commit -m "fix: <description>"
git push
git checkout main
git merge hotfix/<name>
```

Then update the live branch:

```bash
git checkout feature/live-execution
git pull origin main
```

### Merging Live Execution Into Main (When Ready)

All final integrations must happen through a Pull Request:

```
feature/live-execution → main (via PR)
```

**Requirements**:
- Must pass tests
- Must be manually reviewed
- Squash-merge recommended for clean history

### Protecting `main` (GitHub Settings)

Enable in GitHub → *Settings → Branches*:
- ✔ Protect main
- ✔ Require PR review
- ✔ Block direct pushes
- ✔ Require checks to pass
- ✔ Require branch up-to-date before merging

This guarantees **nobody can break the stable version**.

### Rollback Strategy

If something ever breaks:

```bash
git checkout main
git reset --hard <LAST-KNOWN-GOOD-COMMIT>
git push --force-with-lease
```

Because development happens in feature branches, **main is always recoverable**.

---

## Critical Implementation Guidelines

### 1. UCS as PRIMARY Interface ✅
- ✅ **ALWAYS** use `unified-cloud-services` for GCS operations
- ✅ Use `download_from_gcs()` / `download_from_gcs_streaming()` for data loading
- ✅ Use `upload_to_gcs()` for result uploads
- ❌ **NEVER** write to local filesystem for production (only fallback/dev)
- ❌ **NEVER** assume `data_downloads/` is primary data source

### 2. Signal-Driven Execution ✅
- ✅ Load sparse signals from `strategy-service` first
- ✅ Stream only 5-minute windows of tick data for each signal
- ✅ Skip intervals without signal changes
- ❌ **NEVER** load full day files unless necessary

### 3. Output Schema Alignment ✅
- ✅ Match exact schemas from spec (`summary.json`, `orders.parquet`, `fills.parquet`, `positions.parquet`, `equity_curve.parquet`)
- ✅ Upload to `gs://execution-store-cefi-central-element-323112/backtest_results/{run_id}/`
- ✅ Use UCS `upload_to_gcs()` for all uploads

### 4. Consistency with Backtest ✅
- ✅ Reuse same execution algorithms (`TWAPExecAlgorithm`, `VWAPExecAlgorithm`, `IcebergExecAlgorithm`)
- ✅ Same order types (MarketOrder, LimitOrder)
- ✅ Same routing logic (fee-based, liquidity-based)
- ✅ Same configuration schema (external JSON)

### 5. File Organization ✅
- ✅ Follow `FILE_ORGANIZATION.md` structure
- ✅ Clear separation: `backend/live/` vs `backend/backtest/` vs shared modules
- ✅ No cross-imports between live and backtest
- ✅ Shared components in `backend/execution/`, `backend/data/`, etc.

---

## Deployment Architecture

**See**: `ARCHITECTURE.md` Section 7 for detailed deployment architecture and component structure.

**Recommended**: Separate Services (Docker Compose Profiles) ⭐

**Why This Is Best**:
- ✅ Perfect alignment with NautilusTrader (separate `BacktestNode` and `TradingNode`)
- ✅ Resource isolation (CPU-intensive backtests don't affect live latency)
- ✅ Independent scaling and failure domains
- ✅ Production-ready without over-engineering
- ✅ Cost-effective for current scale

**Services** (Local Development):
- `odum-backend` (port 8000) - Backtest service
- `odum-live-backend` (port 8001) - Live service
- `odum-frontend` (port 5173) - Frontend with service detection
- PostgreSQL (Docker) - Local database for live OMS/positions only
- Redis - Optional (for live config updates)

**Note**: Production deployment is handled by deployment team, not included in this documentation.

**Deployment**:
```bash
# Backtest profile
docker-compose --profile backtest up -d

# Live profile
docker-compose --profile live up -d

# Both profile
docker-compose --profile both up -d

# Default (backward compatible - same as both)
docker-compose up -d
```

**Docker Compose Profile Structure** (Backward Compatible):

**Migration Strategy**: Add profiles to existing services without breaking current setup

```yaml
services:
  # Backtest Service (port 8000) - EXISTING SERVICE, ADD PROFILES
  backend:
    profiles: ["backtest", "both"]  # Add profiles, keep existing config
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: odum-backend
    ports:
      - "8000:8000"
    volumes:
      # Keep all existing volumes
      - ./backend:/app/backend
      - ./data_downloads:/app/data_downloads:ro
      - ./backend/data/parquet:/app/backend/data/parquet
      - ./backend/backtest_results:/app/backend/backtest_results
      - ./external/data_downloads/configs:/app/external/data_downloads/configs:ro
      - ./external/unified-cloud-services:/app/external/unified-cloud-services:ro
      - ./frontend/public/tickdata:/app/frontend/public/tickdata
      - ./.secrets:/app/.secrets:ro
    environment:
      # Keep all existing environment variables
      - UNIFIED_CLOUD_LOCAL_PATH=/app/data_downloads
      - UNIFIED_CLOUD_SERVICES_USE_PARQUET=true
      - UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=true
      - DATA_CATALOG_PATH=/app/backend/data/parquet
      - GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS:-/app/.secrets/gcs/gcs-service-account.json}
    command: bash /app/backend/scripts/start.sh  # Keep existing command
    networks:
      - backtest-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  # Live Service (port 8001) - NEW SERVICE
  live-backend:
    profiles: ["live", "both"]
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: odum-live-backend
    ports:
      - "8001:8001"
    volumes:
      # Same volumes as backend
      - ./backend:/app/backend
      - ./data_downloads:/app/data_downloads:ro
      - ./backend/data/parquet:/app/backend/data/parquet
      - ./external/data_downloads/configs:/app/external/data_downloads/configs:ro
      - ./external/unified-cloud-services:/app/external/unified-cloud-services:ro
      - ./.secrets:/app/.secrets:ro
    environment:
      - UNIFIED_CLOUD_LOCAL_PATH=/app/data_downloads
      - UNIFIED_CLOUD_SERVICES_USE_PARQUET=true
      - UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=true
      - DATA_CATALOG_PATH=/app/backend/data/parquet
      - GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS:-/app/.secrets/gcs/gcs-service-account.json}
      - DATABASE_URL=postgresql://user:pass@postgres:5432/execution_db
      - REDIS_URL=redis://redis-live:6379/0
    command: uvicorn backend.api.live_server:app --host 0.0.0.0 --port 8001
    depends_on:
      - postgres
      - redis-live
    networks:
      - backtest-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  # PostgreSQL Database - NEW SERVICE (Local Development Only)
  postgres:
    profiles: ["live", "both"]
    image: postgres:15
    container_name: odum-postgres
    environment:
      - POSTGRES_DB=execution_db
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - backtest-network
    # Note: Production database setup handled by deployment team
  
  # Redis (Optional) - NEW SERVICE
  redis-live:
    profiles: ["live", "both"]
    image: redis:7-alpine
    container_name: odum-redis
    ports:
      - "6380:6379"
    networks:
      - backtest-network
  
  # Frontend - UPDATE EXISTING SERVICE
  frontend:
    profiles: ["backtest", "live", "both"]  # Add profiles
    build:
      context: .
      dockerfile: frontend/Dockerfile
    container_name: odum-frontend
    ports:
      - "5173:5173"
    volumes:
      # Keep existing volumes
      - ./frontend:/app
      - ./backend/backtest_results:/app/backend/backtest_results:ro
      - ./frontend/public/tickdata:/app/public/tickdata
      - ./external/data_downloads/configs:/app/external/data_downloads/configs:ro
    environment:
      - VITE_API_URL=http://localhost:8000
      - VITE_BACKTEST_API_URL=http://backend:8000
      - VITE_LIVE_API_URL=http://live-backend:8001
      - DOCKER=true
      - BACKEND_PROXY_URL=http://backend:8000
    networks:
      - backtest-network
    depends_on:
      - backend
      - live-backend

networks:
  backtest-network:
    driver: bridge

volumes:
  postgres_data:
```

**Profile Structure**:
- ✅ **3 Profiles Only**: `backtest`, `live`, `both`
- ✅ **Current System**: Runs with `--profile backtest` (backend + frontend)
- ✅ **No Default**: `docker-compose up -d` (no profile) starts nothing - must specify a profile
- ✅ All existing volumes and environment variables preserved
- ✅ Health checks maintained

**Deployment Commands**:
```bash
# Backtest profile - current system (backend + frontend)
docker-compose --profile backtest up -d

# Live profile - live execution system (frontend + live-backend + postgres + redis-live)
docker-compose --profile live up -d

# Both profile - both systems running (all services)
docker-compose --profile both up -d

# No profile - starts nothing (must specify a profile)
docker-compose up -d  # Empty - no services started

# Stop services
docker-compose --profile <profile> down

# View logs
docker-compose --profile <profile> logs -f backend
docker-compose --profile <profile> logs -f live-backend
```

---

## Success Criteria (Overall)

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
12. ✅ Trade testing UI works (submit trades, see CLI output)
13. ✅ Strategy deployment interface works
14. ✅ Frontend displays match CLI output exactly
15. ✅ Zero-downtime migration from current system

---

## Architecture Decisions (Resolved)

### 1. API Protocol ✅

**Decision**: **REST API** (JSON) - Simple, practical, sufficient for most use cases

**Rationale**:
- Simple to implement and debug
- Easy to test (curl, Postman, browser dev tools)
- Works with any language/framework
- Sufficient latency for most volumes (<100 orders/sec)
- Human-readable JSON format
- Universal support

**Implementation**:
- Strategy service → Live Execution: REST API (FastAPI) with JSON Order messages
- Frontend → Live API: REST API (for UI compatibility)
- Internal components: Direct function calls (no API needed)

**Future Improvement**: Consider migrating to **gRPC** if:
- Order volume exceeds 100 orders/sec
- Latency requirements become critical (<5ms)
- Need bidirectional streaming support

gRPC provides lower latency (~2-5ms vs ~10-20ms) and smaller payloads, but requires more setup (.proto files, code generation) and is harder to debug.

### 2. Database ✅

**Decision**: **PostgreSQL** with **SQLAlchemy** (schema/migrations) + **asyncpg** (execution-critical operations)

**Implementation Approach**:
- **SQLAlchemy 2.0+**: Schema definition, model validation, Alembic migrations
- **asyncpg**: Raw SQL queries for all database operations (performance-critical)
- **Hybrid Pattern**: SQLAlchemy models define schema, asyncpg executes queries

**Local Development**:
- PostgreSQL server in Docker (for local development)
- Minimal schema: only orders and positions
- **NOT persisted**: Market data, signals, backtest results (handled by GCS via UCS)

**Dependencies**:
```txt
sqlalchemy>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0
```

**Database Connection** (`backend/live/database.py`):
```python
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine

# SQLAlchemy engine for Alembic migrations
engine = create_async_engine("postgresql+asyncpg://user:pass@postgres:5432/execution_db")

# asyncpg pool for execution-critical operations
pool = await asyncpg.create_pool(
    database='execution_db',
    user='user',
    password='pass',
    host='postgres',
    min_size=10,
    max_size=20,
    max_queries=50000,
    max_inactive_connection_lifetime=300.0,
    command_timeout=60
)
```

**Schema Definition** (SQLAlchemy Models):
- `backend/live/models.py` - SQLAlchemy declarative models
- Alembic migrations in `backend/live/alembic/`
- Models used for schema validation and migrations only

**Query Execution** (asyncpg):
- All database operations use asyncpg directly (raw SQL)
- Connection pool managed via asyncpg
- Prepared statements for frequently executed queries
- Transactions via `async with conn.transaction()`

**Why This Approach**:
- **SQLAlchemy**: Industry-standard schema management, Alembic migrations, type safety
- **asyncpg**: Fastest PostgreSQL driver for Python, optimized for async operations
- **Hybrid**: Best of both worlds - schema management + performance
- Only persist what's needed for live execution (orders, positions)
- Market data, signals, results → GCS via UCS (not database)

**Note**: Production deployment (including database setup) is handled by deployment team, not included in this documentation.

### 3. Monitoring ✅

**Decision**: **Prometheus + Grafana** (for local development and testing)

**Rationale**:
- **Prometheus**: Industry standard, best for metrics collection
- **Grafana**: Best visualization, practical dashboards
- **Combined**: Fast, practical, best approach for monitoring

**Local Implementation**:
- Metrics: Prometheus exporters for order latency, fill rates, position tracking
- Dashboards: Grafana for visualization
- Logging: Structured logs (local files or stdout)

**Note**: Production monitoring setup (including Google Cloud Operations) is handled by deployment team, not included in this documentation.

### 4. External Venues Priority ✅

**Priority Order**:
1. **Core System First** (Weeks 1-10):
   - Complete OMS, Risk Engine, Router, Orchestrator
   - Ensure system works end-to-end
2. **Deribit (CeFi)** (Weeks 11-12):
   - After core system is complete
   - Reference implementation for external adapters
3. **TradFi (Interactive Brokers)** (Future):
   - After Deribit is stable
   - Uses same adapter framework
4. **DeFi & Sports** (Future):
   - After TradFi integration
   - Extends adapter framework

**Rationale**: System must be complete and stable before adding venues. Deribit serves as reference implementation.

### 5. Deployment Environment ✅

**Local Development**:
- Docker Compose for local services
- PostgreSQL server in Docker
- Services run locally (backend, live-backend, frontend)

**Production Deployment**:
- **Note**: Production deployment (GCP, Cloud SQL, etc.) is handled by deployment team
- This documentation focuses on local development and implementation
- Deployment team will handle: GCP setup, Cloud SQL, production monitoring, etc.

### Component Decisions ✅
- **Main Engine**: `LiveExecutionOrchestrator` (not `LiveEngine`)
- **TradingNode Wrapper**: `LiveTradingNode`
- **OMS**: `UnifiedOrderManager`
- **Position Tracker**: `UnifiedPositionTracker`
- **Risk Engine**: `PreTradeRiskEngine`
- **File Organization**: Clear separation (`backend/live/` vs `backend/backtest/`) - See `FILE_ORGANIZATION.md`
- **Data Interface**: UCS as PRIMARY interface (not `data_downloads/`)
- **NautilusTrader**: Use `TradingNode` for live (not `BacktestNode`)

---

## Current Backend Structure (December 2025)

**Key File Locations**:
- `backend/core/engine.py` - BacktestEngine (CURRENT)
- `backend/api/server.py` - Backtest API (port 8000)
- `backend/data/loader.py` - UCSDataLoader (UCS integration)
- `backend/results/serializer.py` - ResultSerializer (UCS upload)
- `backend/execution/algorithms.py` - Shared execution algorithms

**Target Structure** (for live execution):
- `backend/live/` - Live-specific components (to be created)
- `backend/api/live_server.py` - Live API (port 8001) (to be created)
- `backend/backtest/` - Optional: Move BacktestEngine here for clarity

**See**: `FILE_ORGANIZATION.md` for complete file organization strategy

## Documentation References

- **Architecture**: `ARCHITECTURE.md` - Complete architecture design and component specifications
- **File Organization**: `FILE_ORGANIZATION.md` - Directory structure and code organization
- **Development Prompt**: `DEVELOPMENT_PROMPT.md` - Quick reference prompt

**Note**: 
- `ARCHITECTURE.md` contains detailed component specifications and system design
- `ROADMAP.md` contains implementation phases, decisions, and requirements
- Both documents are SSOT and should be kept aligned and coherent

---

## Structure Migration Plan

### Current Structure → Target Structure

**Current** (December 2025):
```
backend/
├── core/
│   └── engine.py           # BacktestEngine
├── api/
│   └── server.py           # Backtest API (port 8000)
└── ... (shared components)
```

**Target** (After Migration):
```
backend/
├── backtest/               # NEW: Backtest-specific
│   └── engine.py           # Move from core/engine.py
├── live/                   # NEW: Live-specific
│   ├── orchestrator.py
│   ├── trading_node.py
│   └── ...
├── core/                   # Keep: Shared core
│   └── node_builder.py
├── api/
│   ├── server.py           # Backtest API (port 8000)
│   └── live_server.py      # NEW: Live API (port 8001)
└── ... (shared components unchanged)
```

**Migration Steps** (Phase 6):
1. Create `backend/backtest/` directory
2. Optionally move `BacktestEngine` to `backend/backtest/engine.py`
3. Create `backend/live/` directory structure
4. Update imports in `backend/api/server.py`
5. Create `backend/api/live_server.py`
6. Update Docker Compose services
7. Test all 3 Docker profiles

**See**: `FILE_ORGANIZATION.md` for complete migration strategy

---

## Frontend Service Detection & UI Management

### How UI Manages Active Services

**Service Detection Hook** (`useServiceDetection.ts`):
- Checks health endpoints every 5 seconds
- Returns: `backtestAvailable`, `liveAvailable`, `services`, `lastCheck`
- Frontend adapts dynamically to active services

**Conditional Route Rendering**:
- **Backtest Only** (`--profile backtest`): Shows backtest pages (`/run`, `/compare`, `/algorithms`), hides live pages
- **Live Only** (`--profile live`): Shows live pages (`/live/execute`, `/live/positions`, etc.), hides backtest pages
- **Both** (`--profile both` or no profile): Shows all pages
- **Neither**: Shows status page with connection instructions

**Status Page** (`/status`):
- Shows which services are active
- Displays health status for each service
- Shows GCS bucket connectivity
- Provides connection instructions if services unavailable

**Navigation**:
- Backtest pages only visible when `backtestAvailable === true`
- Live pages only visible when `liveAvailable === true`
- Status page always accessible

### Frontend Live Execution UI Pages

**1. Trade Execution Page** (`/live/execute`):
- **Purpose**: Submit trades via form, generates CLI command according to specs
- **Form Fields**:
  - Venue selector (Binance, Bybit, OKX, Deribit, etc.)
  - Instrument selector (canonical ID format)
  - Trade type (BUY/SELL)
  - Order type (MARKET/LIMIT)
  - Quantity
  - Price (if LIMIT order)
  - Execution Algorithm (TWAP, VWAP, Iceberg, NORMAL)
  - Algorithm parameters (duration, slices, etc.)
- **CLI Command Display**: Shows the exact CLI command being generated (matches specs)
- **Submit**: Sends order to live API (`POST /api/orders`)
- **Real-time Updates**: Order status updates displayed in CLI format

**2. OMS/Positions Page** (`/live/positions`):
- **Purpose**: View all positions across venues (like backtest positions view)
- **Display**:
  - Aggregated positions by instrument (canonical ID)
  - Position breakdown by venue
  - Quantity, average entry price, current price
  - Unrealized PnL, realized PnL
  - Position status (open, closed, partial)
- **Real-time Updates**: Polling every 5 seconds
- **Filters**: By instrument, venue, strategy

**3. Execution Log Page** (`/live/logs`):
- **Purpose**: Full log of all execution actions (like backtest jobs run/not run)
- **Display**:
  - **Orders Executed**: Which orders went forward, status (FILLED, PARTIAL_FILLED)
  - **Orders Rejected**: Which orders didn't go forward, rejection reasons
  - **Execution Layer Logs**: Real-time log of what's happening in execution layer
  - **Timeline View**: Chronological log of all actions
  - **Filters**: By status (executed/rejected), venue, instrument, time range
- **Log Format**: Matches CLI output format exactly
- **Real-time Updates**: Streaming log updates (polling or WebSocket)

**4. Order Details/History Page** (`/live/orders`):
- **Purpose**: Detailed view of individual orders and order history
- **Display**:
  - **Order List Table**: All orders with columns (Order ID, Operation ID, Instrument, Side, Quantity, Status, Venue, Created At)
  - **Order Details View** (click order):
    - Order timeline (submitted → risk check → routed → filled/rejected)
    - Fill details (price, quantity, fee, timestamp for each fill)
    - Venue-specific order ID
    - Risk check results (if rejected, show reason)
    - Routing decision (why this venue was chosen)
  - **Filters**: By status (PENDING, FILLED, REJECTED, CANCELED), venue, instrument, date range
  - **Search**: By order ID, operation ID
- **Real-time Updates**: Order status updates via polling
- **CLI Format**: Matches CLI output format exactly

**5. Status Page** (`/status`):
- **Purpose**: Service health and connectivity status
- **Display**:
  - Service health (backtest backend, live backend, PostgreSQL, Redis)
  - GCS bucket connectivity status
  - Last check timestamp
  - Connection instructions if services unavailable
- **Always Accessible**: Available regardless of service status

**CLI Alignment**:
- All pages display data in CLI output format exactly
- Same order status format, position format, fill format, log format
- Ensures consistency between CLI and UI

---

## Next Steps

1. **Set Up Git Workflow**: Create `feature/live-execution` branch
2. **Review**: Read this ROADMAP.md for complete context
3. **Set Up**: Create `backend/live/` directory structure
4. **Begin Phase 1**: Start with core infrastructure and Docker setup
5. **Follow Phases**: Implement incrementally, test as you go
6. **Frontend Integration**: Add service detection and live execution UI (Phase 7)
7. **Migrate Structure**: Complete structure migration in Phase 6
8. **Deploy**: Test all 3 Docker profiles
9. **Validate**: Ensure alignment with spec and current implementation

---

*Last updated: December 2025*
*Timeline: 14 weeks (7 phases)*
*Status: Planning Phase - Ready for Implementation*

