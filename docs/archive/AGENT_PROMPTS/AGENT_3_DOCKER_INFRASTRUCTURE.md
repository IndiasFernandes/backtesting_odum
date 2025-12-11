# Agent 3: Docker & Infrastructure Agent

## Objective
Ensure Docker installation is easy, containers work correctly, and infrastructure is production-ready with proper health checks, volume management, and service orchestration.

## System Context
- **Docker Compose**: `docker-compose.yml`
- **Backend Dockerfile**: `backend/Dockerfile`
- **Frontend Dockerfile**: `frontend/Dockerfile`
- **Services**: backend (port 8000), frontend (port 5173), redis (optional, port 6379)
- **Volumes**: data_downloads, parquet catalog, results, tickdata, configs

## Key Files to Review
- `docker-compose.yml` - Service orchestration
- `backend/Dockerfile` - Backend container definition
- `frontend/Dockerfile` - Frontend container definition
- `backend/scripts/start.sh` - Startup script
- `ARCHITECTURE.md` - Architecture documentation

## Testing Tasks

### 1. Docker Setup & Installation

**Fresh Install:**
- ✅ Verify `docker-compose up -d` works without errors
- ✅ Verify all services start successfully
- ✅ Verify no port conflicts
- ✅ Verify containers are running: `docker-compose ps`
- ✅ Verify logs show no errors: `docker-compose logs`

**Dependencies:**
- ✅ Verify Docker and Docker Compose are installed
- ✅ Verify sufficient disk space
- ✅ Verify sufficient memory

### 2. Service Health Checks

**Backend Service:**
- ✅ Health check endpoint: `curl http://localhost:8000/api/health`
- ✅ API docs accessible: `http://localhost:8000/docs`
- ✅ Verify health check passes in docker-compose

**Frontend Service:**
- ✅ Frontend accessible: `http://localhost:5173`
- ✅ Verify health check passes in docker-compose
- ✅ Verify frontend can reach backend API

**Redis Service (if enabled):**
- ✅ Redis accessible: `docker-compose exec redis redis-cli ping`
- ✅ Verify health check passes

### 3. Volume Management

**Data Volumes:**
- ✅ `data_downloads/` mounts correctly (read-only) - contains `raw_tick_data/` and `configs/`
- ✅ `backend/data/parquet/` mounts correctly (read-write)
- ✅ `backend/backtest_results/` mounts correctly (read-write)
- ✅ `frontend/public/tickdata/` mounts correctly (read-write)
- ✅ `external/data_downloads/configs/` mounts correctly (read-only)

**Volume Persistence:**
- ✅ Stop containers: `docker-compose stop`
- ✅ Start containers: `docker-compose start`
- ✅ Verify data persists across restarts
- ✅ Verify catalog data persists
- ✅ Verify results persist

**Volume Permissions:**
- ✅ Verify read-only volumes are read-only
- ✅ Verify read-write volumes are writable
- ✅ Verify file permissions are correct

### 4. Network Connectivity

**Service Communication:**
- ✅ Backend can access data volumes
- ✅ Frontend can reach backend API
- ✅ Verify network isolation (services on same network)
- ✅ Verify external access (ports exposed correctly)

**Network Testing:**
```bash
# Test backend API from host
curl http://localhost:8000/api/health

# Test frontend from host
curl http://localhost:5173

# Test backend from frontend container
docker-compose exec frontend wget -O- http://backend:8000/api/health
```

### 5. Build Process

**Backend Build:**
- ✅ `docker-compose build backend` succeeds
- ✅ Verify image builds without errors
- ✅ Verify dependencies install correctly
- ✅ Verify image size is reasonable

**Frontend Build:**
- ✅ `docker-compose build frontend` succeeds
- ✅ Verify image builds without errors
- ✅ Verify dependencies install correctly
- ✅ Verify image size is reasonable

**Rebuild:**
- ✅ `docker-compose up -d --build` works
- ✅ Verify build caching works
- ✅ Verify incremental builds are faster

### 6. Environment Variables

**Backend Environment:**
- ✅ `UNIFIED_CLOUD_LOCAL_PATH` set correctly
- ✅ `UNIFIED_CLOUD_SERVICES_USE_PARQUET` set correctly
- ✅ `DATA_CATALOG_PATH` set correctly
- ✅ `PYTHONPATH` set correctly

**Frontend Environment:**
- ✅ `VITE_API_URL` set correctly
- ✅ Verify API URL points to backend

### 7. Container Configuration

**Resource Limits:**
- ✅ Verify memory limits (if set)
- ✅ Verify CPU limits (if set)
- ✅ Verify container resource usage is reasonable

**Security:**
- ✅ Verify containers run as non-root (if configured)
- ✅ Verify minimal base images used
- ✅ Verify no sensitive data in images

**Logging:**
- ✅ Verify logs are accessible
- ✅ Verify log rotation (if configured)
- ✅ Verify structured logging (if implemented)

### 8. Production Readiness

**Startup:**
- ✅ Verify services start in correct order (dependencies)
- ✅ Verify startup scripts work correctly
- ✅ Verify error handling on startup

**Restart Policies:**
- ✅ Verify restart policies (if set)
- ✅ Verify containers restart on failure
- ✅ Verify containers don't restart unnecessarily

**Monitoring:**
- ✅ Verify health checks are effective
- ✅ Verify logs are useful for debugging
- ✅ Verify metrics are accessible (if implemented)

## Test Commands

```bash
# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Check health
curl http://localhost:8000/api/health
curl http://localhost:5173

# Test volumes
docker-compose exec backend ls -la /app/data_downloads
docker-compose exec backend ls -la /app/backend/data/parquet

# Restart services
docker-compose restart

# Rebuild
docker-compose up -d --build

# Stop and remove
docker-compose down
docker-compose down -v  # Remove volumes
```

## Success Criteria
- ✅ Docker Compose setup works out-of-the-box
- ✅ All services start and remain healthy
- ✅ Volumes mount and persist correctly
- ✅ Network connectivity works
- ✅ Build process is reliable
- ✅ Environment variables are correct
- ✅ Production-ready configuration
- ✅ No security issues
- ✅ Logs are useful

## Deliverables
1. Installation guide with step-by-step instructions
2. Test execution report
3. Configuration recommendations
4. Security audit results
5. Performance benchmarks (startup time, resource usage)
6. Troubleshooting guide

