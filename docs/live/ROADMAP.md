# Live Execution Implementation Roadmap

> Complete implementation roadmap with phases, timelines, and success criteria

## Quick Start

**Start Here**: This document (`ROADMAP.md`) - Complete implementation roadmap

**For Details**: Read `IMPLEMENTATION_GUIDE.md` for step-by-step implementation instructions

**File Organization**: See `FILE_ORGANIZATION.md` for directory structure and code organization

**Quick Reference**: Use `DEVELOPMENT_PROMPT.md` for concise development prompt

---

## Implementation Phases (14 Weeks)

**Note**: Timeline includes Docker setup and structure migration phases

### Phase 1: Core Infrastructure & Docker Setup (Weeks 1-2)

**Goal**: Set up foundation for live execution system and Docker deployment

**Tasks**:
- [ ] **Set up Git workflow** (see Git Workflow section below):
  - [ ] Create `feature/live-execution` branch from `main`
  - [ ] Configure GitHub branch protection for `main`
  - [ ] Set up PR requirements
- [ ] Create module structure: `backend/live/` (see `FILE_ORGANIZATION.md`)
- [ ] Set up PostgreSQL schema (`unified_orders`, `unified_positions`)
- [ ] Create configuration framework (external JSON, similar to backtest)
- [ ] Set up UCS integration (verify GCS bucket access)
- [ ] Create `backend/api/live_server.py` skeleton
- [ ] **Create Docker Compose configuration with 3 profiles** (backward compatible):
  - [ ] **Preserve current `docker-compose.yml`** - Keep existing setup working
  - [ ] Add profiles to existing services (backward compatible)
  - [ ] `backtest` profile (backtest service only)
  - [ ] `live` profile (live service only)
  - [ ] `both` profile (both services) - **Matches current behavior**
  - [ ] Ensure `docker-compose up` (no profile) still works like `both` profile
- [ ] Set up Docker services:
  - [ ] Backtest service (port 8000) - **Keep existing `backend` service**
  - [ ] Live service (port 8001) - **New `live-backend` service**
  - [ ] PostgreSQL service - **New for live OMS/positions**
  - [ ] Redis service (optional) - **New for live config updates**
  - [ ] Frontend service (port 5173) - **Update with service detection**
- [ ] **Frontend Service Detection**:
  - [ ] Create `useServiceDetection` React hook
  - [ ] Implement health check endpoints (`/api/health` for backtest, `/api/live/health` for live)
  - [ ] Frontend detects which services are active
  - [ ] Conditionally show/hide pages based on active services
  - [ ] Status page shows service health and GCS connectivity

**Deliverables**:
- ✅ Git workflow established (`feature/live-execution` branch)
- ✅ `backend/live/` directory structure created
- ✅ PostgreSQL database schema deployed
- ✅ Configuration loader for live execution
- ✅ UCS integration verified (GCS bucket access)
- ✅ Basic API server responds on port 8001
- ✅ Docker Compose file with 3 profiles working
- ✅ All 3 deployment modes tested (`backtest`, `live`, `both`)

**Success Criteria**:
- `feature/live-execution` branch created and protected
- Can connect to PostgreSQL
- Can load configuration from JSON
- Can access GCS buckets via UCS
- Basic API server responds on port 8001
- **Backward compatibility verified**: `docker-compose up` (no profile) still works
- `docker-compose --profile backtest up -d` works (backtest only)
- `docker-compose --profile live up -d` works (live only)
- `docker-compose --profile both up -d` works (both services)
- Existing volumes and environment variables preserved
- Health checks working for all services

---

### Phase 2: TradingNode Integration (Weeks 3-4)

**Goal**: Integrate NautilusTrader TradingNode for Binance, Bybit, OKX

**Tasks**:
- [ ] Create `LiveTradingNode` wrapper class (`backend/live/trading_node.py`)
- [ ] Implement `TradingNodeConfig` builder from JSON
- [ ] Register Binance, Bybit, OKX client factories
- [ ] Subscribe to order events (`OrderSubmitted`, `OrderFilled`, `OrderCancelled`)
- [ ] Implement position sync from NautilusTrader Portfolio
- [ ] Test with paper trading accounts

**Deliverables**:
- ✅ `LiveTradingNode` wrapper class
- ✅ TradingNode configuration from JSON
- ✅ Event subscriptions working
- ✅ Position sync from NautilusTrader

**Success Criteria**:
- TradingNode connects to Binance/Bybit/OKX
- Order events received and logged
- Positions synced from NautilusTrader Portfolio
- Paper trading test successful

---

### Phase 3: External Adapter Framework (Weeks 5-6)

**Goal**: Build framework for venues not in NautilusTrader (Deribit, IB)

**Tasks**:
- [ ] Create `ExternalAdapter` abstract base class (`backend/live/adapters/base.py`)
- [ ] Implement `DeribitAdapter` (reference implementation) (`backend/live/adapters/deribit.py`)
- [ ] Create adapter registry (`backend/live/adapters/registry.py`)
- [ ] Implement adapter lifecycle (connect, disconnect, reconnect)
- [ ] Test Deribit adapter with demo account

**Deliverables**:
- ✅ `ExternalAdapter` base class
- ✅ `DeribitAdapter` implementation
- ✅ Adapter registry
- ✅ Adapter lifecycle management

**Success Criteria**:
- External adapter interface defined
- Deribit adapter connects and authenticates
- Can submit orders via Deribit adapter
- Adapter registry manages multiple adapters

---

### Phase 4: Unified OMS & Position Tracker (Weeks 7-8)

**Goal**: Track all orders and positions across all venues

**Tasks**:
- [ ] Implement `UnifiedOrderManager` (`backend/live/oms.py`)
  - Create, update, query orders
  - PostgreSQL persistence
- [ ] Implement `UnifiedPositionTracker` (`backend/live/positions.py`)
  - Aggregate positions across venues
  - PostgreSQL persistence
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
- [ ] **Production deployment setup**:
  - [ ] Environment variable configuration
  - [ ] Health check configurations
  - [ ] Monitoring and logging setup
  - [ ] Documentation for deployment procedures

**Deliverables**:
- ✅ Target file structure implemented
- ✅ All imports updated
- ✅ Docker Compose fully tested
- ✅ Deployment documentation
- ✅ Production deployment ready

**Success Criteria**:
- Target structure matches `FILE_ORGANIZATION.md`
- All Docker profiles work correctly
- Services can be deployed independently
- Production deployment procedures documented

### Phase 7: Frontend Integration & Testing (Weeks 13-14)

**Goal**: Frontend integration for live execution testing and comprehensive validation

**Tasks**:
- [ ] **Frontend Live Execution UI**:
  - [ ] Create live execution page (`/live/execute`)
  - [ ] Trade submission form (instrument, side, quantity, order type, price)
  - [ ] Real-time order status display (matches CLI output)
  - [ ] Position monitoring dashboard
  - [ ] Order history and fills display
  - [ ] Strategy deployment interface
  - [ ] Live execution logs viewer (matches CLI output)
- [ ] **Frontend Service Detection** (if not completed in Phase 1):
  - [ ] Implement `useServiceDetection` hook
  - [ ] Conditional route rendering (show/hide pages based on active services)
  - [ ] Status page with service health indicators
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
- ✅ Live execution UI page
- ✅ Trade submission interface
- ✅ Real-time order/position monitoring
- ✅ Strategy deployment interface
- ✅ Service detection working
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

**Recommended**: Separate Services (Docker Compose Profiles) ⭐

**Why This Is Best**:
- ✅ Perfect alignment with NautilusTrader (separate `BacktestNode` and `TradingNode`)
- ✅ Resource isolation (CPU-intensive backtests don't affect live latency)
- ✅ Independent scaling and failure domains
- ✅ Production-ready without over-engineering
- ✅ Cost-effective for current scale

**Services**:
- `odum-backend` (port 8000) - Backtest service
- `odum-live-backend` (port 8001) - Live service
- `odum-frontend` (port 5173) - Frontend with service detection
- PostgreSQL - Shared database for live OMS/positions
- Redis - Optional (for live config updates)

**Deployment**:
```bash
# Backtest only
docker-compose --profile backtest up -d

# Live only
docker-compose --profile live up -d

# Both
docker-compose --profile both up -d
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
  
  # PostgreSQL Database - NEW SERVICE
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

**Backward Compatibility**:
- ✅ `docker-compose up` (no profile) = **Same as `--profile both`** (backward compatible)
- ✅ Existing `docker-compose.yml` continues to work
- ✅ All existing volumes and environment variables preserved
- ✅ Health checks maintained

**Deployment Commands**:
```bash
# Current behavior (backward compatible) - runs both services
docker-compose up -d

# Backtest only (new)
docker-compose --profile backtest up -d

# Live only (new)
docker-compose --profile live up -d

# Both services (explicit, same as no profile)
docker-compose --profile both up -d

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
12. ✅ Zero-downtime migration from current system

---

## Key Decisions

### Architecture Decisions ✅
- **Deployment**: Separate Services (Docker Compose Profiles) - See `DEPLOYMENT_ANALYSIS.md`
- **File Organization**: Clear separation (`backend/live/` vs `backend/backtest/`) - See `FILE_ORGANIZATION.md`
- **Data Interface**: UCS as PRIMARY interface (not `data_downloads/`)
- **NautilusTrader**: Use `TradingNode` for live (not `BacktestNode`)

### Component Decisions ✅
- **Main Engine**: `LiveExecutionOrchestrator` (not `LiveEngine`)
- **TradingNode Wrapper**: `LiveTradingNode`
- **OMS**: `UnifiedOrderManager`
- **Position Tracker**: `UnifiedPositionTracker`
- **Risk Engine**: `PreTradeRiskEngine`

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

- **Implementation Guide**: `IMPLEMENTATION_GUIDE.md` - Detailed step-by-step instructions
- **File Organization**: `FILE_ORGANIZATION.md` - Directory structure and code organization
- **Development Prompt**: `DEVELOPMENT_PROMPT.md` - Quick reference prompt

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

### Frontend Live Execution UI Features

**Trade Submission Page** (`/live/execute`):
- Form fields: Instrument, Side (BUY/SELL), Quantity, Order Type (MARKET/LIMIT), Price (if LIMIT)
- Execution Algorithm selection (TWAP, VWAP, Iceberg, NORMAL)
- Algorithm parameters configuration
- Submit button sends order to live API
- **CLI Output Display**: Shows exactly what's being sent (matches CLI output)
- Real-time order status updates (matches CLI output format)

**Order Monitoring**:
- Real-time order status display (matches CLI format)
- Order history table
- Fill details (price, quantity, fee, timestamp) - matches CLI
- Position updates - matches CLI format

**Strategy Deployment** (`/live/strategies`):
- Upload strategy configuration (JSON)
- Deploy strategy to live execution
- Monitor strategy performance
- Start/stop strategy execution
- View strategy logs (matches CLI output)

**CLI Alignment**:
- Frontend displays match CLI output format exactly
- Same order status format
- Same position format
- Same fill format
- Same log format
- Real-time updates via WebSocket or polling

**See**: `FRONTEND_SERVICE_DETECTION.md` for detailed implementation guide

---

## Next Steps

1. **Set Up Git Workflow**: Create `feature/live-execution` branch
2. **Review**: Read `IMPLEMENTATION_GUIDE.md` for complete context
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

