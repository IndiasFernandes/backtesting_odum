# Frontend Service Detection & Status Page Implementation Plan

## Overview

This document outlines the implementation plan for service detection and status monitoring in the frontend UI. The system will automatically detect which backend services are running (backtest, live execution) and show/hide pages accordingly.

---

## 1. Service Architecture

### 1.1 Service Components

| Service | Port | Health Endpoint | Purpose |
|---------|------|----------------|---------|
| **Backtest Backend** | 8000 | `/api/health` | Backtest execution engine |
| **Live Backend** | 8001 | `/api/health` | Live execution orchestrator |
| **PostgreSQL** | 5432 | `/api/health/database` (via live backend) | Unified OMS & Position Tracker DB |
| **Redis (Live)** | 6380 | `/api/health/redis` (via live backend) | Live config updates |
| **Frontend** | 5173 | `/` | React UI |

### 1.2 Docker Compose Profiles

Three deployment modes:

```bash
# Backtest only
docker-compose --profile backtest up -d

# Live only  
docker-compose --profile live up -d

# Both
docker-compose --profile backtest --profile live up -d
```

---

## 2. Service Detection Hook

### 2.1 File: `frontend/src/hooks/useServiceDetection.ts`

**Purpose**: React hook that detects which services are running and their health status.

**Features**:
- Checks backtest backend health (`http://localhost:8000/api/health`)
- Checks live backend health (`http://localhost:8001/api/health`)
- Checks PostgreSQL health (via live backend)
- Checks GCS bucket accessibility
- Auto-refreshes every 30 seconds
- Returns structured status object

**Implementation**:
```typescript
import { useState, useEffect } from 'react'

export interface ServiceStatus {
  backtest: {
    healthy: boolean
    url: string
    lastChecked: Date | null
    error?: string
  }
  live: {
    healthy: boolean
    url: string
    lastChecked: Date | null
    error?: string
  }
  postgres: {
    healthy: boolean
    lastChecked: Date | null
    error?: string
  }
  redis: {
    healthy: boolean
    lastChecked: Date | null
    error?: string
  }
  gcs: {
    instruments: { 
      accessible: boolean
      bucket: string
      error?: string
    }
    marketData: { 
      accessible: boolean
      bucket: string
      error?: string
    }
    execution: { 
      accessible: boolean
      bucket: string
      error?: string
    }
  }
}

export const useServiceDetection = (): ServiceStatus => {
  const [status, setStatus] = useState<ServiceStatus>({
    backtest: { healthy: false, url: 'http://localhost:8000', lastChecked: null },
    live: { healthy: false, url: 'http://localhost:8001', lastChecked: null },
    postgres: { healthy: false, lastChecked: null },
    redis: { healthy: false, lastChecked: null },
    gcs: {
      instruments: { accessible: false, bucket: 'instruments-store-cefi-central-element-323112' },
      marketData: { accessible: false, bucket: 'market-data-tick-cefi-central-element-323112' },
      execution: { accessible: false, bucket: 'execution-store-cefi-central-element-323112' }
    }
  })

  useEffect(() => {
    const checkServices = async () => {
      const now = new Date()
      
      // Check backtest backend
      const backtestResult = await checkHealth('http://localhost:8000/api/health')
      
      // Check live backend
      const liveResult = await checkHealth('http://localhost:8001/api/health')
      
      // Check PostgreSQL (via live backend if available)
      let postgresResult = { healthy: false, error: undefined as string | undefined }
      if (liveResult.healthy) {
        postgresResult = await checkHealth('http://localhost:8001/api/health/database')
      }
      
      // Check Redis (via live backend if available)
      let redisResult = { healthy: false, error: undefined as string | undefined }
      if (liveResult.healthy) {
        redisResult = await checkHealth('http://localhost:8001/api/health/redis')
      }
      
      // Check GCS buckets (via backend APIs)
      const gcsStatus = await checkGCSStatus(backtestResult.healthy, liveResult.healthy)
      
      setStatus({
        backtest: { ...backtestResult, url: 'http://localhost:8000', lastChecked: now },
        live: { ...liveResult, url: 'http://localhost:8001', lastChecked: now },
        postgres: { ...postgresResult, lastChecked: now },
        redis: { ...redisResult, lastChecked: now },
        gcs: gcsStatus
      })
    }

    checkServices()
    const interval = setInterval(checkServices, 30000) // Check every 30s
    return () => clearInterval(interval)
  }, [])

  return status
}

interface HealthResult {
  healthy: boolean
  error?: string
}

async function checkHealth(url: string): Promise<HealthResult> {
  try {
    const response = await fetch(url, { 
      method: 'GET',
      signal: AbortSignal.timeout(5000) // 5s timeout
    })
    if (response.ok) {
      return { healthy: true }
    } else {
      return { healthy: false, error: `HTTP ${response.status}` }
    }
  } catch (error) {
    return { 
      healthy: false, 
      error: error instanceof Error ? error.message : 'Connection failed'
    }
  }
}

async function checkGCSStatus(
  backtestHealthy: boolean,
  liveHealthy: boolean
): Promise<ServiceStatus['gcs']> {
  // Try to check GCS via backtest backend first, then live backend
  const endpoints = []
  if (backtestHealthy) endpoints.push('http://localhost:8000/api/health/gcs')
  if (liveHealthy) endpoints.push('http://localhost:8001/api/health/gcs')
  
  if (endpoints.length === 0) {
    return {
      instruments: { 
        accessible: false, 
        bucket: 'instruments-store-cefi-central-element-323112',
        error: 'No backend available'
      },
      marketData: { 
        accessible: false, 
        bucket: 'market-data-tick-cefi-central-element-323112',
        error: 'No backend available'
      },
      execution: { 
        accessible: false, 
        bucket: 'execution-store-cefi-central-element-323112',
        error: 'No backend available'
      }
    }
  }
  
  try {
    const response = await fetch(endpoints[0])
    if (response.ok) {
      const data = await response.json()
      return {
        instruments: { 
          accessible: data.buckets?.instruments?.accessible || false,
          bucket: 'instruments-store-cefi-central-element-323112',
          error: data.buckets?.instruments?.error
        },
        marketData: { 
          accessible: data.buckets?.marketData?.accessible || false,
          bucket: 'market-data-tick-cefi-central-element-323112',
          error: data.buckets?.marketData?.error
        },
        execution: { 
          accessible: data.buckets?.execution?.accessible || false,
          bucket: 'execution-store-cefi-central-element-323112',
          error: data.buckets?.execution?.error
        }
      }
    }
  } catch (error) {
    // Fallback to all false
  }
  
  return {
    instruments: { 
      accessible: false, 
      bucket: 'instruments-store-cefi-central-element-323112',
      error: 'Check failed'
    },
    marketData: { 
      accessible: false, 
      bucket: 'market-data-tick-cefi-central-element-323112',
      error: 'Check failed'
    },
    execution: { 
      accessible: false, 
      bucket: 'execution-store-cefi-central-element-323112',
      error: 'Check failed'
    }
  }
}
```

---

## 3. Status Page Component

### 3.1 File: `frontend/src/pages/StatusPage.tsx`

**Purpose**: Dashboard showing all service health statuses and GCS bucket connectivity.

**Features**:
- Real-time service status display
- Color-coded indicators (green=healthy, red=unhealthy, yellow=checking)
- Last check timestamp
- GCS bucket connectivity status
- Auto-refresh every 30 seconds
- Manual refresh button
- Links to service-specific pages when available

**Design**:
- Card-based layout
- Service status cards with icons
- GCS bucket status table
- Refresh indicator
- Error messages display

---

## 4. Conditional Route Rendering

### 4.1 File: `frontend/src/App.tsx`

**Purpose**: Show/hide pages based on service availability.

**Logic**:
- Backtest pages only show if `backtest.healthy === true`
- Live execution pages only show if `live.healthy === true`
- Status page always available
- Fallback to status page if no services available

**Implementation**:
```typescript
import { useServiceDetection } from './hooks/useServiceDetection'
import StatusPage from './pages/StatusPage'

function App() {
  const serviceStatus = useServiceDetection()
  
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          {/* Status page always available */}
          <Route path="/status" element={<StatusPage />} />
          
          {/* Backtest pages - only show if backtest service is healthy */}
          {serviceStatus.backtest.healthy && (
            <>
              <Route path="/" element={<BacktestComparisonPage />} />
              <Route path="/run" element={<BacktestRunnerPage />} />
              <Route path="/definitions" element={<DefinitionsPage />} />
              <Route path="/algorithms" element={<AlgorithmManagerPage />} />
            </>
          )}
          
          {/* Live execution pages - only show if live service is healthy */}
          {serviceStatus.live.healthy && (
            <>
              <Route path="/live" element={<LiveDashboardPage />} />
              <Route path="/live/orders" element={<LiveOrdersPage />} />
              <Route path="/live/positions" element={<LivePositionsPage />} />
            </>
          )}
          
          {/* Fallback if no services are available */}
          {!serviceStatus.backtest.healthy && !serviceStatus.live.healthy && (
            <Route path="*" element={<StatusPage />} />
          )}
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
```

---

## 5. Navigation Menu Updates

### 5.1 File: `frontend/src/components/Layout.tsx`

**Purpose**: Update navigation to show/hide menu items based on service status.

**Implementation**:
```typescript
import { useServiceDetection } from '../hooks/useServiceDetection'

export default function Layout({ children }: LayoutProps) {
  const serviceStatus = useServiceDetection()
  
  return (
    <div className="min-h-screen bg-gray-900">
      <nav className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <Link to="/status" className="text-white font-bold">
                Execution Services
              </Link>
            </div>
            <div className="flex space-x-4">
              {/* Status link always visible */}
              <Link to="/status" className="text-gray-300 hover:text-white">
                Status
              </Link>
              
              {/* Backtest links - only if backtest is healthy */}
              {serviceStatus.backtest.healthy && (
                <>
                  <Link to="/" className="text-gray-300 hover:text-white">
                    Backtests
                  </Link>
                  <Link to="/run" className="text-gray-300 hover:text-white">
                    Run Backtest
                  </Link>
                  <Link to="/definitions" className="text-gray-300 hover:text-white">
                    Definitions
                  </Link>
                  <Link to="/algorithms" className="text-gray-300 hover:text-white">
                    Algorithms
                  </Link>
                </>
              )}
              
              {/* Live execution links - only if live is healthy */}
              {serviceStatus.live.healthy && (
                <>
                  <Link to="/live" className="text-gray-300 hover:text-white">
                    Live Dashboard
                  </Link>
                  <Link to="/live/orders" className="text-gray-300 hover:text-white">
                    Orders
                  </Link>
                  <Link to="/live/positions" className="text-gray-300 hover:text-white">
                    Positions
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>
      
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  )
}
```

---

## 6. Backend Health Endpoints

### 6.1 Backtest Backend (`backend/api/server.py`)

**Required Endpoints**:
- `GET /api/health` - Basic health check
- `GET /api/health/gcs` - GCS bucket connectivity check

### 6.2 Live Backend (`backend/api/live_execution_server.py`)

**Required Endpoints**:
- `GET /api/health` - Basic health check
- `GET /api/health/database` - PostgreSQL connectivity check
- `GET /api/health/redis` - Redis connectivity check
- `GET /api/health/gcs` - GCS bucket connectivity check

**Example Implementation**:
```python
from fastapi import APIRouter, HTTPException
from unified_cloud_services import UnifiedCloudService, CloudTarget

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "live-execution"}

@router.get("/health/database")
async def database_health():
    try:
        # Check PostgreSQL connection
        # ... database check logic ...
        return {"status": "healthy", "database": "postgresql"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.get("/health/redis")
async def redis_health():
    try:
        # Check Redis connection
        # ... redis check logic ...
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.get("/health/gcs")
async def gcs_health():
    try:
        ucs = UnifiedCloudService()
        buckets = {
            "instruments": {
                "accessible": await check_bucket_access(
                    ucs, "instruments-store-cefi-central-element-323112"
                )
            },
            "marketData": {
                "accessible": await check_bucket_access(
                    ucs, "market-data-tick-cefi-central-element-323112"
                )
            },
            "execution": {
                "accessible": await check_bucket_access(
                    ucs, "execution-store-cefi-central-element-323112"
                )
            }
        }
        return {"status": "healthy", "buckets": buckets}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

---

## 7. Implementation Checklist

### Phase 1: Backend Health Endpoints
- [ ] Add `/api/health` endpoint to backtest backend
- [ ] Add `/api/health/gcs` endpoint to backtest backend
- [ ] Create live execution backend server (`live_execution_server.py`)
- [ ] Add `/api/health` endpoint to live backend
- [ ] Add `/api/health/database` endpoint to live backend
- [ ] Add `/api/health/redis` endpoint to live backend
- [ ] Add `/api/health/gcs` endpoint to live backend

### Phase 2: Docker Compose Profiles
- [ ] Create `docker-compose.profiles.yml` with profile definitions
- [ ] Add `backend` service with `backtest` and `both` profiles
- [ ] Add `live-backend` service with `live` and `both` profiles
- [ ] Add `postgres` service with `live` and `both` profiles
- [ ] Add `redis-live` service with `live` and `both` profiles
- [ ] Update `frontend` service to always run (no profile)

### Phase 3: Frontend Service Detection
- [ ] Create `useServiceDetection.ts` hook
- [ ] Implement health check functions
- [ ] Implement GCS bucket check function
- [ ] Add auto-refresh logic (30s interval)

### Phase 4: Status Page
- [ ] Create `StatusPage.tsx` component
- [ ] Design service status cards
- [ ] Design GCS bucket status table
- [ ] Add refresh button
- [ ] Add error message display
- [ ] Add loading states

### Phase 5: Conditional Routing
- [ ] Update `App.tsx` with conditional routes
- [ ] Update `Layout.tsx` with conditional navigation
- [ ] Test route visibility based on service status
- [ ] Add fallback to status page

### Phase 6: Testing
- [ ] Test with backtest-only profile
- [ ] Test with live-only profile
- [ ] Test with both profiles
- [ ] Test service detection accuracy
- [ ] Test GCS bucket connectivity checks
- [ ] Test error handling (services down)

---

## 8. Migration from Current System

### 8.1 Current State Analysis

**Current Setup** (as shown in Docker Desktop):
- `odum-backend` (port 8000) - Backtest execution engine ✅ Running
- `odum-frontend` (port 5173) - React UI ✅ Running
- `data_downloads` - Data volume container ✅ Running
- `odum-redis` (port 6379) - Optional, profile-based ⏳ Not running

**Current docker-compose.yml**:
- No profiles defined (all services run by default)
- Backend and frontend always start together
- Redis only runs with `--profile batch-processing`

### 8.2 Migration Strategy

The migration is **backward compatible** and can be done gradually:

#### Phase 1: Add Profiles to Existing Services (Zero Downtime)

**Step 1: Update docker-compose.yml to add profiles**

**Current docker-compose.yml** (before migration):
```yaml
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: odum-backend
    ports:
      - "8000:8000"
    # ... rest of config ...
    # No profiles - runs by default

  frontend:
    # ... config ...
    # No profiles - runs by default

  redis:
    # ... config ...
    profiles:
      - batch-processing
    # Only runs with --profile batch-processing
```

**Updated docker-compose.yml** (after migration):
```yaml
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: odum-backend
    ports:
      - "8000:8000"
    # ... existing config unchanged ...
    profiles: ['backtest', 'both']  # ADD THIS LINE
    # Now runs with --profile backtest or --profile both

  frontend:
    # ... existing config unchanged ...
    profiles: []  # ADD THIS LINE (empty = always run)
    # Always runs regardless of profile

  redis:
    # ... existing config unchanged ...
    profiles: ['batch-processing', 'live', 'both']  # UPDATE THIS LINE
    # Runs with batch-processing, live, or both profiles
```

**Important**: To maintain backward compatibility, Docker Compose will run services without profiles if no profile is specified. However, to be explicit and future-proof:

**Option A: Keep backward compatibility (recommended)**
```yaml
# Don't add profiles to backend/frontend initially
# They will run by default when no profile is specified
# Only add profiles when ready to use profile-based deployment
```

**Option B: Explicit profiles (cleaner long-term)**
```yaml
# Add profiles to all services
# Use --profile backtest explicitly going forward
# This is cleaner but requires changing workflow
```

**Step 2: Test backward compatibility**

```bash
# Current behavior (no profile) - should still work
docker-compose up -d
# Backend and frontend start (backward compatible)

# New behavior (explicit profile)
docker-compose --profile backtest up -d
# Same services start, but explicitly via profile

# Verify both work the same
docker-compose ps
# Should show same containers running
```

**Result**: Existing containers continue working. No changes needed to current workflow. Migration is gradual and non-breaking.

#### Phase 2: Add Live Execution Services (Non-Breaking)

**Step 1: Add live services to docker-compose.yml**

**Option A: Add to main docker-compose.yml** (Recommended for simplicity)

Add these services to your existing `docker-compose.yml`:

```yaml
services:
  # ... existing backend, frontend, redis services ...

  # NEW: Live execution backend
  live-backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: odum-live-backend
    ports:
      - "8001:8001"
    profiles: ['live', 'both']  # Only runs with these profiles
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@odum-postgres:5432/live_execution
      - REDIS_URL=redis://odum-redis-live:6379
      # ... other env vars ...
    depends_on:
      - postgres
      - redis-live
    networks:
      - backtest-network  # Use same network or create new
    command: python -m backend.api.live_execution_server
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # NEW: PostgreSQL for live execution
  postgres:
    image: postgres:15-alpine
    container_name: odum-postgres
    ports:
      - "5432:5432"
    profiles: ['live', 'both']
    environment:
      - POSTGRES_DB=live_execution
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - backtest-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # NEW: Redis for live execution (separate from backtest redis)
  redis-live:
    image: redis:7-alpine
    container_name: odum-redis-live
    ports:
      - "6380:6379"
    profiles: ['live', 'both']
    volumes:
      - redis-live-data:/data
    networks:
      - backtest-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  redis-data:  # Existing
  postgres-data:  # NEW
  redis-live-data:  # NEW

networks:
  backtest-network:  # Existing (reuse or create separate)
    driver: bridge
```

**Option B: Use docker-compose.override.yml** (Alternative)

Create `docker-compose.override.yml` (auto-loaded by Docker Compose):

```yaml
# docker-compose.override.yml
# This file is automatically merged with docker-compose.yml
services:
  live-backend:
    # ... same as Option A ...
```

**Step 2: Test that existing services still work**

```bash
# Current services should still work
docker-compose up -d

# Verify backtest backend still running
curl http://localhost:8000/api/health

# Verify frontend still accessible
curl http://localhost:5173
```

**Step 3: Test live-only mode**

```bash
# Stop current services
docker-compose down

# Start only live execution
docker-compose --profile live up -d

# Verify live backend is running
curl http://localhost:8001/api/health

# Verify PostgreSQL is running
docker-compose exec postgres pg_isready -U postgres

# Verify Redis is running
docker-compose exec redis-live redis-cli ping
```

**Step 4: Test both modes together**

```bash
# Stop everything
docker-compose down

# Start both backtest and live
docker-compose --profile backtest --profile live up -d

# Verify all services running
docker-compose ps
# Should show: odum-backend, odum-frontend, odum-live-backend, odum-postgres, odum-redis-live

# Verify both APIs work
curl http://localhost:8000/api/health  # Backtest
curl http://localhost:8001/api/health  # Live
```

**Result**: New services added without affecting existing backtest setup. All services can run independently or together.

#### Phase 3: Update Frontend for Service Detection (Gradual Rollout)

**Step 1: Add service detection hook (non-breaking)**

```typescript
// frontend/src/hooks/useServiceDetection.ts
// New file - doesn't affect existing pages
```

**Step 2: Add status page (new route, doesn't break existing routes)**

```typescript
// frontend/src/pages/StatusPage.tsx
// New page - accessible at /status
```

**Step 3: Update App.tsx with conditional routing**

```typescript
// frontend/src/App.tsx
// Add conditional routes while keeping existing routes
// Existing routes still work, new routes added conditionally
```

**Step 4: Deploy frontend update**

```bash
# Rebuild frontend
docker-compose build frontend

# Restart frontend (zero downtime with health checks)
docker-compose up -d frontend
```

**Result**: Frontend gains new capabilities while maintaining backward compatibility.

### 8.3 Migration Scenarios

#### Scenario 1: Keep Backtest Running, Add Live Execution

```bash
# Current state: backtest running
docker-compose ps
# Shows: odum-backend, odum-frontend

# Add live execution without stopping backtest
docker-compose --profile live up -d

# Verify both are running
docker-compose ps
# Shows: odum-backend, odum-frontend, odum-live-backend, odum-postgres, odum-redis-live

# Frontend automatically detects both services
# Visit http://localhost:5173/status to see status
```

#### Scenario 2: Migrate to Profile-Based Deployment

```bash
# Step 1: Stop current services
docker-compose down

# Step 2: Start with explicit profile
docker-compose --profile backtest up -d

# Step 3: Verify same behavior
curl http://localhost:8000/api/health
# Should work exactly as before
```

#### Scenario 3: Switch to Live-Only Mode

```bash
# Step 1: Stop backtest
docker-compose --profile backtest down

# Step 2: Start live execution
docker-compose --profile live up -d

# Step 3: Frontend automatically shows only live pages
# Visit http://localhost:5173
# Only live execution pages visible
```

### 8.4 Data Migration

**No data migration required**:
- **Primary data source**: GCS via `unified-cloud-services` (UCS) - unchanged
- **Primary data destination**: GCS via UCS - unchanged
- Backtest data accessed via UCS from GCS (not local filesystem)
- Results written via UCS to GCS (not local filesystem)
- Live execution uses separate PostgreSQL database
- No conflicts between backtest and live data storage

**Important**: The system uses UCS as the **primary interface**:
- ✅ Data reading: `UCSDataLoader` → GCS via UCS API
- ✅ Data writing: `ResultSerializer` → GCS via UCS API
- ✅ Local volumes (`data_downloads/`, `backend/backtest_results/`) are:
  - Development convenience (local testing)
  - FUSE mount fallback (if mounted)
  - **NOT** the primary data source/destination

**Volume Preservation** (for development/fallback only):
```bash
# Local volumes (fallback/development only, not primary)
- data_downloads/ (FUSE mount fallback, dev convenience)
- backend/data/parquet (catalog cache, can be regenerated)
- backend/backtest_results (temporary, uploaded to GCS via UCS)
- frontend/public/tickdata (temporary, uploaded to GCS via UCS)

# New live execution volumes
- postgres-data (PostgreSQL) - required for live execution
- redis-live-data (Redis for live) - required for live execution
```

**GCS Buckets** (Primary Storage):
- `gs://instruments-store-cefi-central-element-323112/` - Instrument definitions
- `gs://market-data-tick-cefi-central-element-323112/` - Market tick data
- `gs://execution-store-cefi-central-element-323112/` - Execution results (backtest + live)

### 8.5 Backward Compatibility Guarantees

**What Stays the Same**:
- ✅ Backtest API endpoints (`http://localhost:8000/api/*`) unchanged
- ✅ Frontend routes (`/`, `/run`, `/definitions`, `/algorithms`) still work
- ✅ Backtest data storage locations unchanged
- ✅ CLI commands (`python backend/run_backtest.py`) unchanged
- ✅ Environment variables for backtest unchanged

**What's New**:
- ➕ Live execution API (`http://localhost:8001/api/*`)
- ➕ New frontend routes (`/live/*`, `/status`)
- ➕ Service detection and conditional routing
- ➕ PostgreSQL and Redis for live execution

**Rollback Plan**:
```bash
# If issues occur, rollback is simple:
docker-compose --profile live down  # Stop live services
docker-compose --profile backtest up -d  # Restore backtest-only

# Frontend automatically adapts (shows only backtest pages)
```

### 8.6 Migration Checklist

**Pre-Migration**:
- [ ] Backup current `docker-compose.yml`
- [ ] Verify current backtest system is working (`docker-compose ps`)
- [ ] Test backtest API (`curl http://localhost:8000/api/health`)
- [ ] Test frontend (`curl http://localhost:5173`)
- [ ] Document current environment variables
- [ ] Take snapshot of current container state

**Phase 1: Add Profiles (Zero Downtime)**:
- [ ] Add `profiles: ['backtest', 'both']` to backend service
- [ ] Add `profiles: []` to frontend service (always run)
- [ ] Update redis profiles: `['batch-processing', 'live', 'both']`
- [ ] Test: `docker-compose up -d` (should work as before)
- [ ] Test: `docker-compose --profile backtest up -d` (should work same)
- [ ] Verify containers: `docker-compose ps`
- [ ] Verify API: `curl http://localhost:8000/api/health`
- [ ] Verify frontend: `curl http://localhost:5173`

**Phase 2: Add Live Services (Non-Breaking)**:
- [ ] Add `live-backend` service to docker-compose.yml
- [ ] Add `postgres` service to docker-compose.yml
- [ ] Add `redis-live` service to docker-compose.yml
- [ ] Add new volumes: `postgres-data`, `redis-live-data`
- [ ] Test: `docker-compose --profile live up -d`
- [ ] Verify live backend: `curl http://localhost:8001/api/health`
- [ ] Verify PostgreSQL: `docker-compose exec postgres pg_isready -U postgres`
- [ ] Verify Redis: `docker-compose exec redis-live redis-cli ping`
- [ ] Test: `docker-compose --profile backtest --profile live up -d`
- [ ] Verify all services running: `docker-compose ps`

**Phase 3: Update Frontend (Gradual Rollout)**:
- [ ] Create `frontend/src/hooks/useServiceDetection.ts`
- [ ] Create `frontend/src/pages/StatusPage.tsx`
- [ ] Update `frontend/src/App.tsx` with conditional routing
- [ ] Update `frontend/src/components/Layout.tsx` with conditional navigation
- [ ] Rebuild frontend: `docker-compose build frontend`
- [ ] Restart frontend: `docker-compose up -d frontend`
- [ ] Test status page: `http://localhost:5173/status`
- [ ] Test service detection (start/stop services, verify UI updates)
- [ ] Test conditional page visibility
- [ ] Verify GCS bucket connectivity checks

**Post-Migration Verification**:
- [ ] Backtest-only mode: `docker-compose --profile backtest up -d`
  - [ ] Verify backtest pages visible
  - [ ] Verify live pages hidden
  - [ ] Test backtest functionality
- [ ] Live-only mode: `docker-compose --profile live up -d`
  - [ ] Verify live pages visible
  - [ ] Verify backtest pages hidden
  - [ ] Test live execution functionality
- [ ] Both modes: `docker-compose --profile backtest --profile live up -d`
  - [ ] Verify all pages visible
  - [ ] Test both systems independently
  - [ ] Verify no conflicts
- [ ] Monitor service health checks (30s intervals)
- [ ] Test error scenarios (stop services, verify UI updates)
- [ ] Document new deployment commands for team

### 8.7 Quick Reference: Migration Commands

**Current State → Profile-Based (No Breaking Changes)**:
```bash
# Step 1: Update docker-compose.yml (add profiles)
# Edit file: add profiles to services

# Step 2: Test backward compatibility
docker-compose up -d
# Should work exactly as before

# Step 3: Test explicit profile
docker-compose --profile backtest up -d
# Should work same as above
```

**Add Live Execution (Non-Breaking)**:
```bash
# Step 1: Add live services to docker-compose.yml
# Edit file: add live-backend, postgres, redis-live services

# Step 2: Start live execution
docker-compose --profile live up -d

# Step 3: Verify
curl http://localhost:8001/api/health
```

**Run Both Systems**:
```bash
# Start both backtest and live
docker-compose --profile backtest --profile live up -d

# Verify all services
docker-compose ps
curl http://localhost:8000/api/health  # Backtest
curl http://localhost:8001/api/health  # Live
```

**Switch Between Modes**:
```bash
# Stop everything
docker-compose down

# Backtest only
docker-compose --profile backtest up -d

# Live only
docker-compose --profile live up -d

# Both
docker-compose --profile backtest --profile live up -d
```

**Rollback**:
```bash
# If issues occur, rollback is simple
docker-compose --profile live down  # Stop live services
docker-compose --profile backtest up -d  # Restore backtest-only

# Or revert docker-compose.yml changes
git checkout docker-compose.yml
docker-compose up -d
```

### 8.8 Troubleshooting Migration

**Issue: Services not starting with profiles**
```bash
# Check profile syntax
docker-compose config --profiles

# Verify services are defined
docker-compose config | grep -A 5 "profiles:"
```

**Issue: Frontend not detecting services**
```bash
# Check health endpoints
curl http://localhost:8000/api/health
curl http://localhost:8001/api/health

# Check browser console for errors
# Verify CORS is enabled on backends
```

**Issue: Port conflicts**
```bash
# Check if ports are in use
lsof -i :8000
lsof -i :8001
lsof -i :5432
lsof -i :6380

# Stop conflicting services or change ports
```

---

## 9. Future Enhancements

- **WebSocket Updates**: Real-time service status updates via WebSocket
- **Service Metrics**: Display CPU, memory, request rates
- **Historical Status**: Show service uptime history
- **Alerts**: Notify when services go down
- **Service Restart**: UI button to restart services (if authorized)

---

*Last updated: December 2025*

