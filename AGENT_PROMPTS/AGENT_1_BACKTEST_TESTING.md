# Agent 1: Backtest Testing Agent

## Objective
Comprehensively test backtest execution, verify trade execution accuracy, and validate all calculation specifications (PnL, commissions, position statistics) to ensure production-ready accuracy.

## System Context
- **Backend API**: FastAPI server at `http://localhost:8000`
- **Data Location**: `data_downloads/raw_tick_data/by_date/day-YYYY-MM-DD/` (mounted at `/app/data_downloads` in container)
- **Configs**: `data_downloads/configs/*.json` (mounted at `/app/data_downloads/configs` in container) or `external/data_downloads/configs/*.json`
- **Results**: `backend/backtest_results/fast/` and `backend/backtest_results/report/`
- **Strategy**: Trade-driven, one order per trade row (`submission_mode="per_trade_tick"`)
- **OMS Type**: NETTING (positions can flip direction without fully closing)

## Key Files to Review
- `backend/backtest_engine.py` - Backtest execution logic
- `backend/strategy_evaluator.py` - PnL and performance calculations
- `backend/results.py` - Result serialization
- `BACKTEST_SPEC.md` - Complete specification
- `docs/REFERENCE.md` - PnL calculation details

## Testing Tasks

### 1. Fast Mode Testing

**Status**: ✅ Working

**Bug Found & Fixed**:
- ❌ `format_date` function not defined in `serialize_fast()` method (line 112 in `results.py`)
- ✅ Fixed: Added `format_date` helper function to `serialize_fast()` method
- ✅ Verified: Fast mode now works correctly

**Via API:**
- ✅ Execute backtest in fast mode via API
- ✅ Verify response structure matches spec:
  ```json
  {
    "run_id": "string",
    "mode": "fast",
    "summary": {
      "orders": 0,
      "fills": 0,
      "pnl": 0.0,
      "max_drawdown": 0.0,
      "pnl_breakdown": {...},
      "position_stats": {...},
      "trades": {...}
    }
  }
  ```
- Test with multiple instruments (BTCUSDT, ETHUSDT)
- Test with different time windows

**Via CLI:**
- Execute backtest in fast mode via CLI (`python backend/run_backtest.py`)
- Verify CLI produces same results as API
- Verify CLI flags match API parameters exactly
- Test all CLI flags: `--instrument`, `--dataset`, `--config`, `--start`, `--end`, `--fast`, `--snapshot_mode`

### 2. Report Mode Testing ✅

**Via API:**
- ✅ Execute backtest in report mode
- ✅ Verify full output structure (summary + timeline + orders + metadata)
- ✅ Files saved to: `backend/backtest_results/report/<run_id>/summary.json`, `orders.json`, `timeline.json`
- ✅ Timeline contains chronological events: Order events (when orders submitted) and Fill events (when orders filled)
- ✅ Timeline format: `[{ "ts": "ISO8601", "event": "Order|Fill", "data": {...} }]`
- ✅ Verify tick export (if `export_ticks=true`) - saves to `frontend/public/tickdata/<run_id>.json`
- ✅ **API Change**: Report mode now automatically saves files to disk (same as CLI)

**Via CLI:**
- ✅ Execute backtest in report mode via CLI
- ✅ Verify CLI produces same results as API
- ✅ Test CLI flags: `--report`, `--export_ticks`
- ✅ Verify output files match API results

**Verified Working:**
- Report mode saves files correctly (summary.json, orders.json, timeline.json)
- Both API and CLI save to same directory structure
- Response includes: `run_id`, `mode`, `summary`, `timeline`, `orders`, `ticks_path`, `metadata`

### 3. CLI-API Alignment Testing

**Critical Requirement:** CLI and API must produce identical results for the same inputs.

- ✅ Run same backtest via CLI and API with identical parameters
- ✅ Compare result JSONs (run_id, summary, all fields)
- ✅ Verify CLI flags map correctly to API parameters:
  - `--fast` → `fast: true`
  - `--report` → `report: true`
  - `--export_ticks` → `export_ticks: true`
  - `--snapshot_mode` → `snapshot_mode: <value>`
- ✅ Verify CLI uses same backend code path as API
- ✅ Verify CLI error messages match API error responses
- ✅ Test CLI with invalid inputs (same validation as API)

### 4. Trade Execution Verification
- Verify one order is submitted per trade row
- Verify order status transitions (submitted → filled/cancelled)
- Verify fills match expected behavior
- Verify position changes (NETTING OMS allows position flipping)
- Verify timeline events are chronologically ordered

### 5. Calculation Verification (CRITICAL)

**PnL Calculation (NETTING OMS):**
- Primary method: Position snapshots (captures realized PnL from closed cycles)
- Verify realized PnL from current positions
- Verify realized PnL from historical position snapshots (critical for NETTING)
- Verify unrealized PnL calculation
- Verify total PnL = realized + unrealized

**Commission Calculation:**
- Primary method: `position.commissions()` 
- Verify commissions are always positive (costs)
- Verify commissions included in account balance change

**Position Statistics:**
- Verify long/short quantities
- Verify position cycles (NETTING allows flipping)
- Verify position closing at end of backtest

**Trade Statistics:**
- Verify total trades count
- Verify win rate calculation
- Verify trade distribution

### 6. Edge Cases
- Empty time window
- Time window outside data availability
- Missing data files
- Invalid config files
- Different snapshot modes (trades/book/both)

### 7. Performance Verification
- Measure execution time for different data sizes
- Verify data conversion caching (second run should be faster)
- Check memory usage during execution

## Test Commands

### API Testing

```bash
# Fast mode via API
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "instrument": "BTCUSDT",
    "dataset": "day-2023-05-23",
    "config": "binance_futures_btcusdt_l2_trades_config.json",
    "start": "2023-05-23T02:00:00Z",
    "end": "2023-05-23T02:05:00Z",
    "fast": true,
    "snapshot_mode": "trades"
  }'

# Report mode via API
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "instrument": "BTCUSDT",
    "dataset": "day-2023-05-23",
    "config": "binance_futures_btcusdt_l2_trades_config.json",
    "start": "2023-05-23T02:00:00Z",
    "end": "2023-05-23T02:05:00Z",
    "report": true,
    "export_ticks": true,
    "snapshot_mode": "trades"
  }'
```

### CLI Testing

```bash
# Fast mode via CLI
docker-compose exec backend python backend/run_backtest.py \
  --instrument BTCUSDT \
  --dataset day-2023-05-23 \
  --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \
  --start 2023-05-23T02:00:00Z \
  --end 2023-05-23T02:05:00Z \
  --fast \
  --snapshot_mode trades

# Report mode via CLI
docker-compose exec backend python backend/run_backtest.py \
  --instrument BTCUSDT \
  --dataset day-2023-05-23 \
  --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \
  --start 2023-05-23T02:00:00Z \
  --end 2023-05-23T02:05:00Z \
  --report \
  --export_ticks \
  --snapshot_mode trades

# Check results
curl http://localhost:8000/api/backtest/results
```

### CLI-API Alignment Test

```bash
# Run same backtest via CLI and API, compare results
# 1. Run via CLI, save result
docker-compose exec backend python backend/run_backtest.py \
  --instrument BTCUSDT \
  --dataset day-2023-05-23 \
  --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \
  --start 2023-05-23T02:00:00Z \
  --end 2023-05-23T02:05:00Z \
  --fast \
  --snapshot_mode trades > cli_result.json

# 2. Run via API, save result
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "instrument": "BTCUSDT",
    "dataset": "day-2023-05-23",
    "config": "binance_futures_btcusdt_l2_trades_config.json",
    "start": "2023-05-23T02:00:00Z",
    "end": "2023-05-23T02:05:00Z",
    "fast": true,
    "snapshot_mode": "trades"
  }' > api_result.json

# 3. Compare (should be identical except for run_id timestamp)
diff <(jq -S . cli_result.json) <(jq -S . api_result.json)
```

## Success Criteria
- ✅ All backtest modes execute successfully (both CLI and API)
- ✅ Fast mode: Saves to `backend/backtest_results/fast/<run_id>.json`
- ✅ Report mode: Saves to `backend/backtest_results/report/<run_id>/summary.json`, `orders.json`, `timeline.json`
- ✅ CLI and API produce identical results for same inputs
- ✅ All CLI flags work correctly and map to API parameters:
  - `--fast` → `fast: true` ✅
  - `--report` → `report: true` ✅  
  - `--export_ticks` → `export_ticks: true` ✅
  - `--snapshot_mode` → `snapshot_mode: <value>` ✅
- ✅ All calculations match expected values (cross-check with NautilusTrader docs)
- ✅ Trade execution matches strategy logic (one order per trade)
- ✅ NETTING OMS behavior correct (position flipping, PnL from snapshots)
- ✅ Performance metrics within acceptable ranges
- ✅ Edge cases handled gracefully (both CLI and API)
- ✅ Results are reproducible

## Verified Working Commands

**Fast Mode (API)**:
```bash
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "instrument": "BTCUSDT",
    "dataset": "day-2023-05-23",
    "config": "binance_futures_btcusdt_l2_trades_config.json",
    "start": "2023-05-23T02:00:00Z",
    "end": "2023-05-23T02:05:00Z",
    "fast": true,
    "snapshot_mode": "trades"
  }'
```

**Report Mode (API)**:
```bash
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "instrument": "BTCUSDT",
    "dataset": "day-2023-05-23",
    "config": "binance_futures_btcusdt_l2_trades_config.json",
    "start": "2023-05-23T02:00:00Z",
    "end": "2023-05-23T02:05:00Z",
    "report": true,
    "snapshot_mode": "trades"
  }'
```

**CLI (Fast Mode)**:
```bash
docker-compose exec backend python backend/run_backtest.py \
  --instrument BTCUSDT \
  --dataset day-2023-05-23 \
  --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \
  --start 2023-05-23T02:00:00Z \
  --end 2023-05-23T02:05:00Z \
  --fast \
  --snapshot_mode trades
```

**CLI (Report Mode)**:
```bash
docker-compose exec backend python backend/run_backtest.py \
  --instrument BTCUSDT \
  --dataset day-2023-05-23 \
  --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \
  --start 2023-05-23T02:00:00Z \
  --end 2023-05-23T02:05:00Z \
  --report \
  --snapshot_mode trades
```

## Deliverables
1. Test execution report with results
2. Calculation verification (PnL, commissions, stats)
3. Performance benchmarks
4. Bug reports (if any) with reproduction steps
5. Recommendations for improvements

## Bugs Found & Fixed

### Bug 1: `format_date` not defined in `serialize_fast()`
- **File**: `backend/results.py`
- **Line**: 112
- **Issue**: `format_date()` function called but not defined in `serialize_fast()` method scope
- **Fix**: Added `format_date` helper function definition inside `serialize_fast()` method (same pattern as `serialize_report()`)
- **Status**: ✅ Fixed in code, ⚠️ Backend restart needed

### Bug 2: Missing `git` in Dockerfile
- **File**: `backend/Dockerfile`
- **Issue**: `git` package not installed, causing build failure when installing `git+https://github.com/IggyIkenna/unified-cloud-services.git`
- **Fix**: Added `git` to apt-get install list
- **Status**: ✅ Fixed in Dockerfile
- **Note**: Docker build still blocked by private GitHub repo authentication (separate issue)

## Known Issues

### Docker Build: Private GitHub Repo Authentication
- **Issue**: `unified-cloud-services` repository requires authentication
- **Error**: `fatal: could not read Username for 'https://github.com': No such device or address`
- **Solutions**:
  1. Use SSH URL instead of HTTPS (requires SSH keys in Docker)
  2. Use GitHub token in URL: `git+https://<token>@github.com/...`
  3. Copy package locally instead of cloning from git
  4. Use Docker build secrets for credentials
- **Status**: ⚠️ Needs resolution for Docker builds

