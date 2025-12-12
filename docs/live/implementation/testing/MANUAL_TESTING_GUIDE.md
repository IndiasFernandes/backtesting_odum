# Manual Testing Guide - 3 Deployment Modes

**Purpose**: Test all deployment configurations to ensure backward compatibility and live execution setup.

---

## Deployment Modes

### Mode 1: Backtest Profile
**Command**: `docker-compose --profile backtest up -d`  
**Services**: `backend`, `frontend`  
**Purpose**: Run current backtest system (backend + frontend)

**Note**: This is the profile for the current/existing system. No default behavior - must specify a profile.

### Mode 2: Live Profile
**Command**: `docker-compose --profile live up -d`  
**Services**: `backend`, `frontend`, `postgres`, `redis-live`, `live-backend`  
**Purpose**: Run live execution system with all required services

### Mode 3: Both Profile
**Command**: `docker-compose --profile both up -d`  
**Services**: Same as Mode 2 (backend + frontend + live services)  
**Purpose**: Run both systems simultaneously

**Note**: `docker-compose up -d` (no profile) behaves the same as `--profile both` for backward compatibility.

---

## Pre-Testing Setup

### 1. Stop All Running Containers
```bash
# Stop and remove all containers
docker-compose down

# Remove volumes if needed (WARNING: deletes data)
# docker-compose down -v
```

### 2. Verify Clean State
```bash
# Check no containers are running
docker-compose ps

# Should show: "No containers"
```

---

## Mode 1: Backtest Profile Testing

### Step 1: Start Backtest Services
```bash
# Start backtest profile
docker-compose --profile backtest up -d

# Verify only backtest services started
docker-compose ps
```

**Expected Output**:
```
NAME                IMAGE                    STATUS
odum-backend        odum-trader-backend     Up
odum-frontend       odum-trader-frontend    Up
```

### Step 2: Verify Backtest API
```bash
# Check backend health
curl http://localhost:8000/api/health

# Expected response:
# {"status":"healthy","service":"Odum Trader Backtest API"}
```

### Step 3: Verify Frontend
```bash
# Check frontend is accessible
curl -I http://localhost:5173

# Expected: HTTP 200 or 304
```

### Step 4: Verify Live Services Are NOT Running
```bash
# Check live-backend is NOT running
curl http://localhost:8001/api/health

# Expected: Connection refused or timeout

# Check postgres is NOT running
docker-compose --profile backtest ps postgres

# Expected: No postgres container
```

### Step 5: Test Backtest Functionality
```bash
# Test a backtest endpoint (if available)
curl http://localhost:8000/api/algorithms

# Or check logs
docker-compose --profile backtest logs backend | tail -20
```

### Step 6: Cleanup
```bash
docker-compose --profile backtest down
```

**✅ Success Criteria**:
- [x] Backend API responds on port 8000
- [x] Frontend accessible on port 5173
- [x] Live services NOT running
- [x] No errors in logs

---

## Mode 2: Live Profile Testing

### Step 1: Start Live Services
```bash
# Start with live profile
docker-compose --profile live up -d

# Verify all services started
docker-compose ps
```

**Expected Output**:
```
NAME                IMAGE                    STATUS
odum-backend        odum-trader-backend     Up
odum-frontend       odum-trader-frontend    Up
odum-live-backend   odum-trader-backend     Up
odum-postgres       postgres:15             Up
odum-redis-live     redis:7-alpine          Up
```

### Step 2: Wait for Services to Be Ready
```bash
# Wait for health checks (30-60 seconds)
sleep 30

# Check service health
docker-compose ps
```

### Step 3: Verify Backtest API (Still Works)
```bash
# Backtest API should still work
curl http://localhost:8000/api/health

# Expected: {"status":"healthy","service":"Odum Trader Backtest API"}
```

### Step 4: Verify Live API
```bash
# Check live API health
curl http://localhost:8001/api/health

# Expected: {"status":"healthy","service":"live-execution"}
```

### Step 5: Verify PostgreSQL Database
```bash
# Check postgres is accessible
docker-compose exec postgres psql -U user -d execution_db -c "SELECT version();"

# Expected: PostgreSQL version info

# Check database exists
docker-compose exec postgres psql -U user -d execution_db -c "\l"

# Expected: execution_db in list
```

### Step 6: Run Database Migrations
```bash
# Run Alembic migrations
docker-compose exec live-backend bash -c "cd backend/live && alembic upgrade head"

# Expected output:
# INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial, initial_schema
```

### Step 7: Verify Database Schema
```bash
# Check tables were created
docker-compose exec postgres psql -U user -d execution_db -c "\dt"

# Expected output:
#                    List of relations
#  Schema |      Name            | Type  | Owner
# --------+----------------------+-------+-------
#  public | unified_orders       | table | user
#  public | unified_positions    | table | user

# Check indexes
docker-compose exec postgres psql -U user -d execution_db -c "\di"

# Expected: 5 indexes (idx_orders_*, idx_positions_*)
```

### Step 8: Verify Redis
```bash
# Check redis is accessible
docker-compose exec redis-live redis-cli ping

# Expected: PONG
```

### Step 9: Test Database Connection from Live Backend
```bash
# Test asyncpg pool connection
docker-compose exec live-backend python3 -c "
import asyncio
import sys
sys.path.insert(0, '/app')
from backend.live.database import get_pool

async def test():
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetch('SELECT COUNT(*) FROM unified_orders')
        print(f'Connection successful! Orders count: {result[0][0]}')

asyncio.run(test())
"

# Expected: Connection successful! Orders count: 0
```

### Step 10: Check Service Logs
```bash
# Check live-backend logs
docker-compose logs live-backend | tail -30

# Check postgres logs
docker-compose logs postgres | tail -20

# Check for errors
docker-compose logs | grep -i error
```

### Step 11: Cleanup
```bash
docker-compose --profile live down
```

**✅ Success Criteria**:
- [x] All 5 services running
- [x] Backtest API responds on port 8000
- [x] Live API responds on port 8001
- [x] PostgreSQL accessible and migrations run successfully
- [x] Database schema created correctly
- [x] Redis accessible
- [x] asyncpg connection pool works
- [x] No errors in logs

---

## Mode 3: Both Profile Testing

### Step 1: Start Both Services
```bash
# Start with both profile (same as live)
docker-compose --profile both up -d

# Verify all services
docker-compose ps
```

**Expected**: Same as Mode 2 (all 5 services)

### Step 2: Verify Both APIs Work Simultaneously
```bash
# Test backtest API
curl http://localhost:8000/api/health

# Test live API
curl http://localhost:8001/api/health

# Both should respond successfully
```

### Step 3: Test Resource Isolation
```bash
# Verify services use different ports
netstat -an | grep -E "(8000|8001|5432|6380)" | grep LISTEN

# Expected:
# *:8000 (backtest API)
# *:8001 (live API)
# *:5432 (postgres)
# *:6380 (redis-live)
```

### Step 4: Test Independent Restart
```bash
# Restart only live-backend
docker-compose restart live-backend

# Verify backtest still works
curl http://localhost:8000/api/health

# Verify live comes back
sleep 5
curl http://localhost:8001/api/health
```

### Step 5: Test Volume Isolation
```bash
# Verify postgres data persists
docker-compose exec postgres psql -U user -d execution_db -c "SELECT COUNT(*) FROM unified_orders;"

# Restart postgres
docker-compose restart postgres

# Wait for restart
sleep 10

# Verify data still exists
docker-compose exec postgres psql -U user -d execution_db -c "SELECT COUNT(*) FROM unified_orders;"

# Should show same count
```

### Step 6: Cleanup
```bash
docker-compose --profile both down
```

**✅ Success Criteria**:
- [x] Both APIs work simultaneously
- [x] Services use different ports (no conflicts)
- [x] Services can restart independently
- [x] Data persists across restarts
- [x] No resource conflicts

---

## Complete Test Sequence

### Run All Tests in Sequence
```bash
#!/bin/bash
set -e

echo "=== Testing Mode 1: Backtest Profile ==="
docker-compose --profile backtest down
docker-compose --profile backtest up -d
sleep 10
curl -f http://localhost:8000/api/health || exit 1
docker-compose --profile backtest down
echo "✅ Mode 1 passed"

echo ""
echo "=== Testing Mode 2: Live Profile ==="
docker-compose --profile live up -d
sleep 30
curl -f http://localhost:8000/api/health || exit 1
curl -f http://localhost:8001/api/health || exit 1
docker-compose exec postgres psql -U user -d execution_db -c "\dt" || exit 1
docker-compose --profile live down
echo "✅ Mode 2 passed"

echo ""
echo "=== Testing Mode 3: Both Profile ==="
docker-compose --profile both up -d
sleep 30
curl -f http://localhost:8000/api/health || exit 1
curl -f http://localhost:8001/api/health || exit 1
docker-compose --profile both down
echo "✅ Mode 3 passed"

echo ""
echo "🎉 All tests passed!"
```

The script is located at `backend/scripts/tests/test_deployments.sh`. Make it executable and run:
```bash
chmod +x backend/scripts/tests/test_deployments.sh
./backend/scripts/tests/test_deployments.sh
```

---

## Troubleshooting

### Issue: Port Already in Use
```bash
# Check what's using the port
lsof -i :8000
lsof -i :8001
lsof -i :5432
lsof -i :6380

# Stop conflicting services or change ports in docker-compose.yml
```

### Issue: Database Connection Failed
```bash
# Check postgres logs
docker-compose logs postgres

# Verify DATABASE_URL environment variable
docker-compose exec live-backend env | grep DATABASE_URL

# Test connection manually
docker-compose exec postgres psql -U user -d execution_db
```

### Issue: Migrations Fail
```bash
# Check Alembic configuration
docker-compose exec live-backend cat backend/live/alembic.ini | grep sqlalchemy.url

# Run migrations with verbose output
docker-compose exec live-backend bash -c "cd backend/live && alembic upgrade head --verbose"
```

### Issue: Services Won't Start
```bash
# Check Docker Compose syntax
docker-compose config

# Check service logs
docker-compose logs

# Verify profiles are correct
docker-compose --profile live config --services
```

---

## Quick Reference Commands

```bash
# Start backtest profile
docker-compose --profile backtest up -d

# Start live profile
docker-compose --profile live up -d

# Start both profile
docker-compose --profile both up -d

# Default (backward compatible - same as both)
docker-compose up -d

# Stop all
docker-compose down

# View logs
docker-compose logs -f [service-name]

# Check status
docker-compose ps

# Restart service
docker-compose restart [service-name]

# Execute command in container
docker-compose exec [service-name] [command]
```

---

*Last updated: December 12, 2025*

