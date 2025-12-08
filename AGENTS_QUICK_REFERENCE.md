# Agents Quick Reference Guide

## Overview

This document provides a quick reference for the 5 agents defined for testing and completing the backtesting system.

---

## Agent 1: Backtest Testing Agent

**Goal:** Verify backtest execution, trade verification, and calculation accuracy.

### Key Test Areas:
- ✅ Fast mode execution → verify summary JSON
- ✅ Report mode execution → verify full output
- ✅ Trade execution (one order per trade row)
- ✅ PnL calculations (realized + unrealized)
- ✅ Commission calculations
- ✅ Position statistics (NETTING OMS)
- ✅ Edge cases (empty windows, missing data)

### Test Commands:
```bash
# Fast mode
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{"instrument":"BTCUSDT","dataset":"day-2023-05-23","config":"binance_futures_btcusdt_l2_trades_config.json","start":"2023-05-23T19:23:00Z","end":"2023-05-23T19:28:00Z","fast":true}'

# Report mode
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{"instrument":"BTCUSDT","dataset":"day-2023-05-23","config":"binance_futures_btcusdt_l2_trades_config.json","start":"2023-05-23T19:23:00Z","end":"2023-05-23T19:28:00Z","report":true,"export_ticks":true}'
```

### Success Criteria:
- All modes execute successfully
- Calculations match expected values
- Trade execution matches strategy logic

---

## Agent 2: UI Testing Agent

**Goal:** Test all UI components, buttons, and functionalities.

### Key Test Areas:
- ✅ Dataset selector (scans `data_downloads/`)
- ✅ Config selector (lists JSON configs)
- ✅ Time window pickers (UTC conversion)
- ✅ Snapshot mode selector
- ✅ Mode toggles (fast/report/export_ticks)
- ✅ Run button (API calls)
- ✅ CLI preview accuracy
- ✅ Results display (summary cards)
- ✅ Error handling

### Test URLs:
- **Backtest Runner:** http://localhost:5173/run
- **Comparison:** http://localhost:5173/compare
- **Definitions:** http://localhost:5173/definitions

### Test Scenarios:
1. Fill form → Submit → Verify results appear
2. Test validation (empty fields)
3. Test error handling (invalid config)
4. Test mode toggles (fast ↔ report)
5. Verify CLI preview matches form inputs

### Success Criteria:
- All components function correctly
- Results display accurately
- Error handling works

---

## Agent 3: Docker & Infrastructure Agent

**Goal:** Ensure Docker setup works easily and containers are production-ready.

### Key Test Areas:
- ✅ Docker Compose startup
- ✅ Service health checks
- ✅ Volume mounts
- ✅ Network connectivity
- ✅ Environment variables
- ✅ Build process

### Test Commands:
```bash
# Fresh install
docker-compose up -d

# Check services
docker-compose ps

# Check health
curl http://localhost:8000/api/health

# Check logs
docker-compose logs backend
docker-compose logs frontend

# Rebuild
docker-compose up -d --build

# Restart
docker-compose restart
```

### Verify Volumes:
```bash
# Check mounts
docker-compose exec backend ls -la /app/data_downloads
docker-compose exec backend ls -la /app/backend/data/parquet
docker-compose exec backend ls -la /app/backend/backtest_results
```

### Success Criteria:
- Services start without errors
- Health checks pass
- Volumes mount correctly
- Build process works

---

## Agent 4: Data & FUSE Integration Agent

**Goal:** Implement and test GCS FUSE integration.

### Key Implementation Areas:
- ✅ Install gcsfuse in Docker
- ✅ Create mount script
- ✅ Configure authentication
- ✅ Mount verification
- ✅ Error handling

### Test Commands:
```bash
# Check mount status
curl http://localhost:8000/api/mount/status

# Check mount in container
docker-compose exec backend mount | grep gcsfuse

# Verify data access
docker-compose exec backend ls -la /app/data_downloads
```

### Setup for Testing:
```bash
# Set environment variables
export USE_GCS_FUSE=true
export GCS_FUSE_BUCKET=your-bucket-name
export GCS_SERVICE_ACCOUNT_KEY=$(cat gcs-key-base64.txt)

# Start with FUSE
docker-compose -f docker-compose.yml -f docker-compose.fuse.yml up -d
```

### Success Criteria:
- GCS FUSE mounts successfully
- Data accessible via FUSE
- Backtests work with FUSE-mounted data
- Error handling robust

---

## Agent 5: Performance & Optimization Agent

**Goal:** Optimize system performance and identify bottlenecks.

### Key Optimization Areas:
- ✅ Use `BacktestEngine.reset()` for parameter sweeps
- ✅ Implement Redis caching
- ✅ Optimize data conversion
- ✅ Optimize catalog queries
- ✅ Frontend virtualization
- ✅ Web Workers for tick parsing

### Performance Tests:
```bash
# Measure execution time
time curl -X POST http://localhost:8000/api/backtest/run ...

# Profile memory usage
docker stats nautilus-backend

# Check API response times
curl -w "@curl-format.txt" http://localhost:8000/api/health
```

### Optimization Checklist:
- [ ] Profile backtest execution
- [ ] Implement `reset()` for sweeps
- [ ] Add Redis caching
- [ ] Optimize frontend rendering
- [ ] Stream large files
- [ ] Benchmark improvements

### Success Criteria:
- Performance improvements measurable
- No functionality regressions
- Memory usage reasonable

---

## Agent Execution Order

### Phase 1: Foundation (Agents 1, 2, 3)
1. **Agent 3** → Verify Docker setup works
2. **Agent 1** → Test backtest execution
3. **Agent 2** → Test UI functionality

### Phase 2: Integration (Agent 4)
4. **Agent 4** → Implement FUSE integration

### Phase 3: Optimization (Agent 5)
5. **Agent 5** → Optimize performance

---

## Quick Test Checklist

### Before Starting:
- [ ] Docker and Docker Compose installed
- [ ] Data files in `data_downloads/`
- [ ] Config files in `external/data_downloads/configs/`

### Agent 3 (Docker):
- [ ] `docker-compose up -d` succeeds
- [ ] All services healthy
- [ ] API accessible at http://localhost:8000
- [ ] UI accessible at http://localhost:5173

### Agent 1 (Backtest):
- [ ] Fast mode backtest runs
- [ ] Report mode backtest runs
- [ ] Results contain expected fields
- [ ] Calculations are correct

### Agent 2 (UI):
- [ ] Form submission works
- [ ] Results display correctly
- [ ] Error handling works
- [ ] All buttons functional

### Agent 4 (FUSE):
- [ ] Mount script exists
- [ ] gcsfuse installed
- [ ] Mount succeeds
- [ ] Data accessible

### Agent 5 (Performance):
- [ ] Baseline measurements taken
- [ ] Optimizations implemented
- [ ] Improvements verified

---

## Troubleshooting

### Agent 3 Issues:
- **Services won't start:** Check Docker logs, verify ports not in use
- **Health checks fail:** Check service logs, verify dependencies

### Agent 1 Issues:
- **Backtest fails:** Check config paths, verify data exists, check logs
- **Calculations wrong:** Verify PnL logic, check position snapshots

### Agent 2 Issues:
- **UI not loading:** Check frontend logs, verify API is running
- **Form not submitting:** Check browser console, verify API endpoint

### Agent 4 Issues:
- **Mount fails:** Check authentication, verify bucket name, check logs
- **Permission denied:** Verify service account permissions

### Agent 5 Issues:
- **No improvements:** Profile first, identify bottlenecks, measure baseline

---

## Resources

- **System Review:** `SYSTEM_REVIEW_AND_AGENTS.md`
- **FUSE Setup:** `FUSE_SETUP.md`
- **Architecture:** `ARCHITECTURE.md`
- **Backtest Spec:** `BACKTEST_SPEC.md`
- **Frontend Spec:** `FRONTEND_UI_SPEC.md`

