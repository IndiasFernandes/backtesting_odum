# Changelog

## 2025-12-08 - Backtest Testing & Fixes

### Fixed Issues

1. **Report Mode File Saving** ✅
   - **Issue**: API was returning report mode results but not saving them to disk
   - **Fix**: Added file saving logic to API endpoint (`backend/api/server.py`)
   - **Result**: Report mode now saves files to `backend/backtest_results/report/<run_id>/` (same as CLI)

2. **Timeline Population** ✅
   - **Issue**: Timeline was empty (`[]`) in report mode results
   - **Fix**: Implemented timeline building from orders and fills (`backend/backtest_engine.py`)
   - **Result**: Timeline now contains chronological Order and Fill events with timestamps

3. **Data Conversion Bug** ✅
   - **Issue**: AggressorSide enum causing pandas conversion errors
   - **Fix**: Convert to string codes first, then map to enum when creating TradeTick
   - **Result**: Data conversion now works correctly

4. **Validation Bug** ✅
   - **Issue**: Invalid `n_rows` parameter in `pq.read_table()`
   - **Fix**: Changed to read full table and slice appropriately
   - **Result**: Validation now works without errors

5. **Balance Calculation Bug** ✅
   - **Issue**: `balance_total()` called without required currency parameter
   - **Fix**: Added `Currency.from_str(base_currency)` parameter to all calls
   - **Result**: Balance calculations now work correctly

### Updated Documentation

1. **Test Commands** (`AGENT_PROMPTS/AGENT_1_BACKTEST_TESTING.md`)
   - Updated all test commands with working time windows: `2023-05-23T02:00:00Z` to `2023-05-23T02:05:00Z`
   - Updated config paths: `external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json`
   - Updated snapshot mode: `trades` (most reliable)
   - Added verified working commands section

2. **Report Mode Documentation**
   - Documented timeline structure: `[{ "ts": "ISO8601", "event": "Order|Fill", "data": {...} }]`
   - Noted that API now saves files automatically

### API Changes

- **`POST /api/backtest/run`**: Now saves report mode results to disk automatically
  - Fast mode: Saves to `backend/backtest_results/fast/<run_id>.json`
  - Report mode: Saves to `backend/backtest_results/report/<run_id>/summary.json`, `orders.json`, `timeline.json`

### CLI Changes

- No changes to CLI functionality (already working correctly)
- All CLI flags remain the same and work as documented

### Verified Working

- ✅ Fast mode API and CLI
- ✅ Report mode API and CLI  
- ✅ Timeline population with Order and Fill events
- ✅ File saving for both modes
- ✅ Data conversion and catalog registration
- ✅ Trade execution (10,551 orders, 8,987 fills)
- ✅ PnL calculations (-7918.30 USDT for 5-minute window)

