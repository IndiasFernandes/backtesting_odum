# Phase 1: Core Infrastructure & Docker Setup - Implementation Plan

> **SSOT Reference**: This plan follows `ROADMAP.md` Phase 1 requirements and ensures backward compatibility with existing backtest system.

## Overview

Set up foundation for live execution system while **preserving existing backtest functionality**. All changes must be non-breaking and backward compatible.

---

## Step 0: Git Workflow Setup

**Purpose**: Create feature branch to protect main branch and enable parallel development.

**Actions**:
1. Verify current branch: `git branch` (should be on `main` or current working branch)
2. Ensure main is up to date: `git checkout main && git pull`
3. Create feature branch: `git checkout -b feature/live-execution`
4. Push branch: `git push --set-upstream origin feature/live-execution`

**GitHub Configuration** (if not already done):
- Protect `main` branch (Settings → Branches)
- Require PR review before merging
- Block direct pushes to main
- Require checks to pass

**Verification**:
- [ ] Feature branch created
- [ ] Branch pushed to remote
- [ ] Main branch protection configured (if applicable)

---

## Step 1: Verify Current Backtest System Works

**Critical**: Before making any changes, establish baseline that backtest system is fully functional.

**Pre-change verification**:
1. **Check backtest API**:
   ```bash
   curl http://localhost:8000/api/health
   ```
   - [ ] API responds successfully

2. **Verify Docker Compose**:
   ```bash
   docker-compose ps
   docker-compose logs backend | tail -20
   ```
   - [ ] Backend service running
   - [ ] No errors in logs

3. **Test backtest endpoints**:
   - [ ] `GET /api/health` works
   - [ ] Other backtest endpoints accessible

4. **Verify imports**:
   ```python
   # Test in Python shell
   from backend.core.engine import BacktestEngine
   from backend.api.server import app
   ```
   - [ ] No import errors

5. **Document current state**:
   - [ ] Note current working configuration
   - [ ] Document any known issues

**After each subsequent step, re-verify**:
- [ ] Backtest API still responds on port 8000
- [ ] No import errors in backtest code
- [ ] Existing backtest functionality unchanged

---

## Step 2: Create Directory Structure (Non-Breaking)

**Purpose**: Create new directories for live execution without affecting existing code.

**Files to create**:
```bash
mkdir -p backend/live/adapters
touch backend/live/__init__.py
touch backend/live/adapters/__init__.py
touch backend/live/models.py
touch backend/live/database.py
touch backend/api/live_server.py
```

**Directory structure**:
```
backend/
├── live/                    # NEW - does not affect existing code
│   ├── __init__.py
│   ├── models.py           # SQLAlchemy models (empty initially)
│   ├── database.py         # asyncpg pool manager (empty initially)
│   └── adapters/
│       └── __init__.py
└── api/
    ├── server.py           # EXISTING - unchanged
    └── live_server.py      # NEW - separate file, no impact on server.py
```

**Verification**:
- [ ] All directories created
- [ ] No import errors in existing code
- [ ] `from backend.core.engine import BacktestEngine` still works
- [ ] Backtest API still responds

---

## Step 3: Update Dependencies (Non-Breaking)

**File**: `backend/requirements.txt`

**Add (append to existing, don't modify existing lines)**:
```txt
sqlalchemy>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0
```

**Verification**:
- [ ] Existing dependencies still present and unchanged
- [ ] New dependencies don't conflict with existing ones
- [ ] Test installation: `pip install -r backend/requirements.txt`
- [ ] Backtest system still works after installing new dependencies
- [ ] No breaking changes to existing imports

---

## Step 4: Create SQLAlchemy Models

**File**: `backend/live/models.py`

**Create models based on ARCHITECTURE.md Section 2.3.4 and 2.3.5**:

```python
from sqlalchemy import Column, String, Numeric, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class UnifiedOrder(Base):
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
```

**Verification**:
- [ ] Models can be imported: `from backend.live.models import UnifiedOrder, UnifiedPosition`
- [ ] No import errors
- [ ] Backtest system still works (models are in separate module)

---

## Step 5: Set Up Alembic Migrations

**Commands**:
```bash
cd backend/live
alembic init alembic
```

**Files to create/modify**:
1. **`backend/live/alembic/env.py`** - Configure SQLAlchemy engine:
   ```python
   from sqlalchemy.ext.asyncio import create_async_engine
   from backend.live.models import Base
   
   # Use asyncpg dialect
   engine = create_async_engine(
       "postgresql+asyncpg://user:pass@postgres:5432/execution_db",
       echo=True
   )
   ```

2. **`backend/live/alembic/script.py.mako`** - Migration template (default is fine)

3. **Create initial migration**: `alembic revision --autogenerate -m "initial_schema"`

4. **Edit migration file** (`backend/live/alembic/versions/001_initial_schema.py`):
   - Add table creation for `unified_orders` and `unified_positions`
   - Add indexes: `idx_orders_status`, `idx_orders_instrument`, `idx_positions_instrument`

**Verification**:
- [ ] Alembic initialized
- [ ] Migration file created
- [ ] Migration can be reviewed (don't run yet - need database first)

---

## Step 6: Create asyncpg Connection Pool Manager

**File**: `backend/live/database.py`

**Implement**:
```python
import asyncpg
import os
from typing import Optional

_pool: Optional[asyncpg.Pool] = None

async def get_pool() -> asyncpg.Pool:
    """Get or create asyncpg connection pool."""
    global _pool
    if _pool is None:
        await init_pool()
    return _pool

async def init_pool():
    """Initialize asyncpg connection pool."""
    global _pool
    database_url = os.getenv("DATABASE_URL", "postgresql://user:pass@postgres:5432/execution_db")
    
    # Parse connection string for asyncpg
    # asyncpg uses different format than SQLAlchemy
    _pool = await asyncpg.create_pool(
        database='execution_db',
        user='user',
        password='pass',
        host='postgres',
        port=5432,
        min_size=10,
        max_size=20,
        max_queries=50000,
        max_inactive_connection_lifetime=300.0,
        command_timeout=60
    )

async def close_pool():
    """Close connection pool gracefully."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
```

**Verification**:
- [ ] File created
- [ ] Can be imported: `from backend.live.database import get_pool`
- [ ] No import errors
- [ ] Backtest system still works

---

## Step 7: Create Live API Server Skeleton

**File**: `backend/api/live_server.py`

**Structure** (follow `backend/api/server.py` pattern):
```python
"""REST API server for live execution operations."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.live.database import init_pool, close_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage database pool lifecycle."""
    # Startup
    await init_pool()
    yield
    # Shutdown
    await close_pool()

app = FastAPI(
    title="Odum Trader Live Execution API",
    lifespan=lifespan
)

# CORS middleware (same as backtest API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "live-execution"}
```

**Verification**:
- [ ] File created
- [ ] Can be imported: `from backend.api.live_server import app`
- [ ] No import errors
- [ ] Backtest API (`backend/api/server.py`) still works unchanged

---

## Step 8: Update Docker Compose (Backward Compatible)

**File**: `docker-compose.yml`

**Critical**: All changes must preserve existing behavior for backtest system.

**Changes**:

1. **Add profiles to existing `backend` service** (preserve ALL existing config):
   ```yaml
   backend:
     profiles: ["backtest", "both"]  # ADD THIS LINE
     # Keep ALL existing configuration unchanged:
     build: ...
     container_name: odum-backend
     ports:
       - "8000:8000"
     volumes: ...  # Keep all existing volumes
     environment: ...  # Keep all existing env vars
     command: bash /app/backend/scripts/start.sh  # Keep existing command
     networks: ...
     healthcheck: ...
   ```

2. **Add new `live-backend` service** (separate service):
   ```yaml
   live-backend:
     profiles: ["live", "both"]
     build:
       context: .
       dockerfile: backend/Dockerfile
     container_name: odum-live-backend
     ports:
       - "8001:8001"
     volumes:
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
   ```

3. **Add `postgres` service** (only for live execution):
   ```yaml
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
   ```

4. **Add `redis-live` service** (optional):
   ```yaml
   redis-live:
     profiles: ["live", "both"]
     image: redis:7-alpine
     container_name: odum-redis
     ports:
       - "6380:6379"
     networks:
       - backtest-network
   ```

5. **Update `frontend` service** (add profiles, preserve existing):
   ```yaml
   frontend:
     profiles: ["backtest", "live", "both"]  # ADD THIS LINE
     # Keep ALL existing configuration unchanged:
     build: ...
     container_name: odum-frontend
     ports:
       - "5173:5173"
     volumes: ...  # Keep all existing volumes
     environment:
       - VITE_API_URL=http://localhost:8000
       - VITE_BACKTEST_API_URL=http://backend:8000
       - VITE_LIVE_API_URL=http://live-backend:8001  # ADD THIS LINE
       - DOCKER=true
       - BACKEND_PROXY_URL=http://backend:8000
     networks: ...
   ```

6. **Add volume definition** (if not exists):
   ```yaml
   volumes:
     postgres_data:
   ```

**Backward compatibility verification**:
- [ ] `docker-compose up -d` (no profile) = same as `--profile both` (both services)
- [ ] `docker-compose up -d backend` = backtest only (existing behavior preserved)
- [ ] `docker-compose --profile backtest up -d` = backtest only
- [ ] Existing backtest API still works on port 8000
- [ ] Existing frontend still works on port 5173
- [ ] No changes to existing service configurations
- [ ] All existing volumes and environment variables preserved

---

## Step 9: Test Docker Compose Profiles

**Test all deployment modes**:

1. **Backtest only**:
   ```bash
   docker-compose --profile backtest up -d
   ```
   - [ ] Only backend and frontend services start
   - [ ] Backtest API responds on port 8000
   - [ ] Frontend accessible on port 5173
   - [ ] No PostgreSQL or Redis containers

2. **Live only**:
   ```bash
   docker-compose --profile live up -d
   ```
   - [ ] Only live-backend, postgres, redis-live, and frontend start
   - [ ] Live API responds on port 8001
   - [ ] PostgreSQL accessible
   - [ ] Frontend accessible

3. **Both services**:
   ```bash
   docker-compose --profile both up -d
   ```
   - [ ] All services start
   - [ ] Backtest API on port 8000
   - [ ] Live API on port 8001
   - [ ] Both work independently

4. **Backward compatible (no profile)**:
   ```bash
   docker-compose up -d
   ```
   - [ ] Same as `--profile both`
   - [ ] Existing behavior preserved

---

## Step 10: Run Database Migrations

**After PostgreSQL is running**:

1. **Connect to live-backend container**:
   ```bash
   docker-compose exec live-backend bash
   ```

2. **Run migrations**:
   ```bash
   cd backend/live
   alembic upgrade head
   ```

3. **Verify schema**:
   ```bash
   # Connect to PostgreSQL
   docker-compose exec postgres psql -U user -d execution_db
   # In psql:
   \dt  # List tables
   \d unified_orders  # Describe table
   \d unified_positions  # Describe table
   ```

**Verification**:
- [ ] Migrations run successfully
- [ ] Tables created: `unified_orders`, `unified_positions`
- [ ] Indexes created
- [ ] Schema matches models

---

## Step 11: Test Live API Server

**After all services are running**:

1. **Health check**:
   ```bash
   curl http://localhost:8001/api/health
   ```
   - [ ] Returns: `{"status": "healthy", "service": "live-execution"}`

2. **Check logs**:
   ```bash
   docker-compose logs live-backend | tail -20
   ```
   - [ ] No errors
   - [ ] Database pool initialized
   - [ ] Server started successfully

3. **Verify database connection**:
   - [ ] Pool created successfully
   - [ ] Can connect to PostgreSQL

---

## Step 12: Verify UCS Integration

**Action**: Verify GCS bucket access using existing UCS integration.

**Check**: `backend/data/loader.py` uses UCS - verify same pattern works for live execution.

**Verification**:
- [ ] UCS imports work: `from unified_cloud_services import UnifiedCloudService`
- [ ] GCS bucket access verified
- [ ] Same UCS pattern can be used in live execution

---

## Final Verification Checklist

**Pre-change baseline**:
- [x] Current backtest system fully functional
- [x] Backtest API responds on port 8000
- [x] Existing Docker Compose setup works
- [x] All existing imports work correctly

**After all changes**:
- [ ] Directory structure created correctly
- [ ] Dependencies install successfully
- [ ] **Backtest system still works** (critical):
  - [ ] Backtest API still responds on port 8000
  - [ ] No import errors in `backend/api/server.py`
  - [ ] `from backend.core.engine import BacktestEngine` still works
  - [ ] Existing backtest endpoints unchanged
- [ ] SQLAlchemy models can be imported (from live module only)
- [ ] Alembic migrations run successfully
- [ ] asyncpg pool connects to PostgreSQL
- [ ] Live API server starts on port 8001
- [ ] Health check endpoint responds (`/api/health` on port 8001)
- [ ] Docker Compose profiles work:
  - [ ] `docker-compose up -d` (backward compatible, same as both)
  - [ ] `docker-compose --profile backtest up -d` (backtest only, existing behavior)
  - [ ] `docker-compose --profile live up -d` (live only)
  - [ ] `docker-compose --profile both up -d` (both services)
- [ ] PostgreSQL database accessible from live-backend container
- [ ] Database schema deployed correctly
- [ ] **No breaking changes** to existing backtest functionality

---

## Success Criteria

From ROADMAP.md Phase 1:

- [x] Git workflow established (`feature/live-execution` branch)
- [ ] `backend/live/` directory structure created
- [ ] PostgreSQL database schema deployed
- [ ] Configuration loader for live execution
- [ ] UCS integration verified (GCS bucket access)
- [ ] Basic API server responds on port 8001
- [ ] Docker Compose file with 3 profiles working
- [ ] All 3 deployment modes tested (`backtest`, `live`, `both`)
- [ ] **Backward compatibility verified**: `docker-compose up` (no profile) still works
- [ ] Existing volumes and environment variables preserved
- [ ] Health checks working for all services

---

## Notes

- All changes are additive - no existing code is modified
- Backtest system remains completely functional throughout
- Docker Compose profiles ensure backward compatibility
- Database only used by live execution (not backtest)
- Separate API servers (ports 8000 and 8001) prevent conflicts

---

*This plan follows SSOT documents: ROADMAP.md, ARCHITECTURE.md, FILE_ORGANIZATION.md*

