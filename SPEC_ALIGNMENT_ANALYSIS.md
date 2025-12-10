# Specification Alignment Analysis

**Date:** December 2025  
**System:** CeFi Backtesting Execution Infrastructure  
**Spec Reference:** Final Specification Document

---

## Executive Summary

The current system is **partially aligned** with the specification. Core backtesting functionality is implemented, but several critical components required by the spec are missing or incomplete:

- ✅ **Core Backtest Engine**: Implemented using NautilusTrader BacktestNode
- ✅ **Data Conversion**: Automatic Parquet conversion to catalog format
- ✅ **Local File System**: Works with local files/FUSE mounts
- ❌ **GCS Output**: Results saved locally, not uploaded to GCS buckets
- ❌ **UCS Integration**: No UnifiedCloudService integration for GCS operations
- ❌ **Parquet Outputs**: Only JSON outputs, missing required Parquet files
- ❌ **Byte-Range Streaming**: Not implemented for tick data loading
- ❌ **Signal-Driven Streaming**: Not implemented

---

## Detailed Alignment Analysis

### 1. Data Inputs

#### 1.1 Instrument Definitions ✅ PARTIAL

**Spec Requirement:**
- Load from `gs://instruments-store-cefi-central-element-323112/instrument_availability/by_date/day-{YYYY-MM-DD}/instruments.parquet`
- Use UCS `download_from_gcs()` with full file load

**Current Implementation:**
- ✅ Instruments created from config and registered in catalog
- ❌ **NOT loading from GCS bucket** - instruments are created programmatically from config
- ❌ **No UCS integration** - no `UnifiedCloudService` usage

**Gap:** System creates instruments from config rather than loading from GCS bucket as specified.

**Files:**
- `backend/backtest_engine.py:50-140` - `_create_and_register_instrument()` creates instruments from config

---

#### 1.2 Market Tick Data ❌ MAJOR GAP

**Spec Requirement:**
- Load from `gs://market-data-tick-cefi-central-element-323112/raw_tick_data/by_date/day-{YYYY-MM-DD}/data_type-trades/{INSTRUMENT}.parquet`
- Use UCS `download_from_gcs_streaming()` with byte-range streaming for time windows
- Support column projection to reduce memory

**Current Implementation:**
- ✅ Reads from local files/FUSE mount at `data_downloads/raw_tick_data/by_date/...`
- ✅ Converts to NautilusTrader catalog format
- ❌ **No GCS direct access** - relies on FUSE mount only
- ❌ **No byte-range streaming** - loads full files
- ❌ **No UCS integration** - no `UnifiedCloudService` usage
- ❌ **No column projection** - loads all columns

**Gap:** System assumes FUSE-mounted files and doesn't implement byte-range streaming or UCS integration.

**Files:**
- `backend/backtest_engine.py:179-449` - `_build_data_config_with_book_check()` loads from local paths
- `backend/data_converter.py` - Converts Parquet files but doesn't use UCS

---

#### 1.3 Strategy Signals ⏳ NOT IMPLEMENTED

**Spec Requirement:**
- Load sparse signals from GCS (mock for milestone)
- Signal-driven tick data streaming (only fetch ticks for intervals with signals)
- ~10% data reduction through sparse signal approach

**Current Implementation:**
- ❌ **No signal loading** - strategy generates orders directly from trade ticks
- ❌ **No signal-driven streaming** - loads all tick data in time window
- ✅ Strategy uses `per_trade_tick` mode (one order per trade)

**Gap:** Signal-driven optimization not implemented. System processes all ticks rather than signal-driven intervals.

**Files:**
- `backend/strategy.py` - `TempBacktestStrategy` generates orders from ticks, not signals

---

### 2. Execution Engine

#### 2.1 NautilusTrader Integration ✅ ALIGNED

**Spec Requirement:**
- Use NautilusTrader BacktestNode
- Components: Execution Orchestrator, Unified OMS, Position Tracker, Pre-Trade Risk, Smart Router

**Current Implementation:**
- ✅ Uses `BacktestNode` from NautilusTrader
- ✅ Creates `BacktestRunConfig` with proper data/venue/strategy configs
- ⚠️ **Simplified components** - uses NautilusTrader's built-in components rather than custom OMS/Risk/Router
- ✅ Position tracking via NautilusTrader portfolio

**Status:** Aligned for core functionality, but spec mentions custom components that may not be fully implemented.

**Files:**
- `backend/backtest_engine.py:808-1012` - `run()` method uses BacktestNode

---

#### 2.2 Backtest Workflow ✅ ALIGNED

**Spec Requirement:**
```
Signal → Execution Orchestrator → Pre-Trade Risk Engine → Unified OMS → Smart Router → NautilusTrader BacktestEngine → ExecutionResult
```

**Current Implementation:**
- ✅ Workflow implemented via BacktestNode
- ✅ Strategy generates orders from ticks
- ✅ NautilusTrader handles execution simulation
- ✅ Results extracted from engine

**Status:** Aligned.

---

#### 2.3 Latency & Fee Models ✅ ALIGNED

**Spec Requirement:**
- Configurable latency and fee models per exchange
- Maker/taker fees, funding rates

**Current Implementation:**
- ✅ Fees configured in venue config (`maker_fee`, `taker_fee`)
- ✅ NautilusTrader handles fee calculation
- ⚠️ **Latency model** - uses NautilusTrader defaults, not explicitly configured

**Status:** Mostly aligned, latency model could be more explicit.

**Files:**
- `backend/backtest_engine.py:114-135` - Instrument creation includes fee configuration

---

#### 2.4 Execution Outputs ❌ MAJOR GAP

**Spec Requirement:**
- Upload to `gs://execution-store-cefi-central-element-323112/backtest_results/{run_id}/`
- Files:
  - `summary.json` - High-level results
  - `orders.parquet` - All orders
  - `fills.parquet` - All fills/trades
  - `positions.parquet` - Position timeline
  - `equity_curve.parquet` - Portfolio value over time
- Use UCS `upload_to_gcs()` for all outputs

**Current Implementation:**
- ✅ Generates JSON summary (fast/report modes)
- ✅ Saves to local filesystem: `backend/backtest_results/fast/` and `backend/backtest_results/report/`
- ❌ **NOT uploading to GCS** - saves locally only
- ❌ **No Parquet outputs** - only JSON files
- ❌ **No UCS integration** - no `UnifiedCloudService` usage
- ❌ **Missing files**: No `orders.parquet`, `fills.parquet`, `positions.parquet`, `equity_curve.parquet`

**Gap:** Critical - results are not uploaded to GCS and Parquet outputs are missing.

**Files:**
- `backend/results.py` - `ResultSerializer` only saves JSON
- `backend/run_backtest.py:156-165` - Saves to local filesystem only

**Required Schema (from spec):**

**orders.parquet:**
- `order_id`, `operation_id`, `instrument_key`, `side`, `order_type`, `quantity`, `price`, `status`, `created_at`, `updated_at`, `rejection_reason`

**fills.parquet:**
- `fill_id`, `order_id`, `instrument_key`, `side`, `quantity`, `price`, `fee`, `fee_currency`, `ts_event`, `venue`

**positions.parquet:**
- `ts_event`, `instrument_key`, `quantity`, `avg_entry_price`, `current_price`, `unrealized_pnl`, `realized_pnl`

**equity_curve.parquet:**
- `ts_event`, `portfolio_value`, `cash_balance`, `margin_used`, `unrealized_pnl`, `drawdown_pct`

---

#### 2.5 Performance Requirements ⚠️ UNKNOWN

**Spec Requirement:**
- 3-day backtest: < 5 minutes
- 5-year backtest: < 30 minutes
- Parallel backtests: 100+ concurrent

**Current Implementation:**
- ⚠️ **Not benchmarked** - no performance metrics available
- ✅ Uses NautilusTrader which is optimized for performance
- ❌ **No parallel execution** - runs single backtest at a time

**Status:** Unknown - needs benchmarking.

---

#### 2.6 Multi-Day Streaming ✅ ALIGNED

**Spec Requirement:**
- Stream files in chronological order
- Maintain state across day boundaries
- Handle timestamp continuity

**Current Implementation:**
- ✅ Auto-discovers files across multiple date folders
- ✅ Uses time window queries that span multiple days
- ✅ NautilusTrader handles chronological replay

**Status:** Aligned.

**Files:**
- `backend/backtest_engine.py:227-265` - Auto-discovery across date folders

---

### 3. Unified Cloud Services (UCS)

#### 3.1 Required Functions ❌ NOT IMPLEMENTED

**Spec Requirement:**
- `download_from_gcs()` - Download files with optional byte-range
- `upload_to_gcs()` - Upload files/DataFrames
- `list_files()` - List files in bucket/prefix
- `read_parquet()` - Read Parquet with row group selection

**Current Implementation:**
- ❌ **No UCS integration** - no `UnifiedCloudService` imports or usage
- ❌ **No GCS operations** - relies on FUSE mount only
- ❌ **No byte-range streaming** - loads full files

**Gap:** Critical - UCS integration is completely missing.

**Required Implementation:**
```python
from unified_cloud_services import UnifiedCloudService, CloudTarget

ucs = UnifiedCloudService()
target = CloudTarget(
    gcs_bucket='market-data-tick-cefi-central-element-323112',
    bigquery_dataset='market_tick_data'
)

# Download with byte-range streaming
df = await ucs.download_from_gcs_streaming(
    target=target,
    gcs_path='raw_tick_data/by_date/day-2023-05-23/data_type-trades/...',
    timestamp_range=(start_ts, end_ts),
    timestamp_column='ts_event',
    use_byte_range=True
)

# Upload results
await ucs.upload_to_gcs(
    target=target,
    gcs_path=f'backtest_results/{run_id}/summary.json',
    data=summary,
    format='json'
)
```

---

#### 3.2 Byte-Range Streaming ❌ NOT IMPLEMENTED

**Spec Requirement:**
- Use byte-range reads for large tick data files
- Support row group selection
- Column projection to reduce memory

**Current Implementation:**
- ❌ **No byte-range streaming** - loads full Parquet files
- ❌ **No row group selection** - reads entire files
- ❌ **No column projection** - loads all columns

**Gap:** Critical for performance with large files (48 MB+ per day per instrument).

---

### 4. Cloud Deployment

#### 4.1 GCS FUSE Mount ✅ PARTIAL

**Spec Requirement:**
- Mount buckets for fast I/O (>200 MB/s)
- Support both FUSE and direct GCS access

**Current Implementation:**
- ✅ FUSE mount support via `USE_GCS_FUSE` env var
- ✅ Scripts for FUSE mounting (`backend/scripts/mount_gcs.sh`)
- ❌ **No direct GCS access** - only FUSE mount path
- ❌ **No UCS direct access** - doesn't use UCS for GCS operations

**Status:** FUSE support exists, but direct GCS access via UCS is missing.

**Files:**
- `docker-compose.yml:28-30` - FUSE environment variables
- `backend/scripts/mount_gcs.sh` - FUSE mounting script

---

#### 4.2 Parallel Execution ❌ NOT IMPLEMENTED

**Spec Requirement:**
- Orchestrate 100+ concurrent backtests
- T+1 scheduled job

**Current Implementation:**
- ❌ **No parallel execution** - runs single backtest at a time
- ❌ **No scheduling** - no T+1 job implementation
- ✅ FastAPI backend could support concurrent requests, but not batch orchestration

**Gap:** No batch processing or parallel execution infrastructure.

---

### 5. Output Format Compliance

#### 5.1 Summary JSON ✅ ALIGNED (Partial)

**Spec Requirement:**
```json
{
  "run_id": "BT-20231223-001",
  "status": "COMPLETED",
  "created_at": "2025-12-08T11:04:16Z",
  "config": {...},
  "pnl": {
    "gross_pnl": 1234.56,
    "net_pnl": 1200.00,
    "total_fees": 34.56,
    "funding_paid": 12.34
  },
  "metrics": {
    "sharpe_ratio": 1.8,
    "sortino_ratio": 2.1,
    "max_drawdown_pct": -5.2,
    "win_rate": 0.55,
    "profit_factor": 1.65,
    "total_trades": 87
  },
  "execution_stats": {...}
}
```

**Current Implementation:**
- ✅ Generates summary JSON with run_id, pnl, metrics
- ⚠️ **Different structure** - uses `mode`, `instrument`, `dataset`, `start`, `end` fields
- ⚠️ **Missing fields**: `status`, `created_at`, `config`, `execution_stats`
- ⚠️ **Metrics differ** - has `orders`, `fills`, `pnl`, `max_drawdown` but missing `sharpe_ratio`, `sortino_ratio`, `win_rate`, `profit_factor`

**Status:** Partially aligned - structure differs from spec.

**Files:**
- `backend/results.py:63-118` - `serialize_fast()` and `serialize_report()`

---

#### 5.2 Parquet Outputs ❌ NOT IMPLEMENTED

**Spec Requirement:**
- `orders.parquet` - Order records with schema
- `fills.parquet` - Execution fills with schema
- `positions.parquet` - Position timeline with schema
- `equity_curve.parquet` - Portfolio value over time with schema

**Current Implementation:**
- ❌ **No Parquet outputs** - only JSON files
- ✅ Has order/fill data in JSON format (report mode)
- ❌ **No position timeline** - not tracked over time
- ❌ **No equity curve** - not generated

**Gap:** Critical - Parquet outputs are required by spec but not implemented.

---

### 6. GCS Bucket Reference

#### 6.1 Input Buckets ❌ NOT USED

**Spec Requirement:**
- `gs://instruments-store-cefi-central-element-323112/` - Instrument definitions
- `gs://market-data-tick-cefi-central-element-323112/` - Market tick data

**Current Implementation:**
- ❌ **Not using GCS buckets** - uses local files/FUSE mount
- ✅ Path structure matches (`data_downloads/raw_tick_data/by_date/...`)
- ❌ **No direct GCS access** - relies on FUSE mount

**Status:** Path structure aligned, but not using GCS directly.

---

#### 6.2 Output Bucket ❌ NOT USED

**Spec Requirement:**
- `gs://execution-store-cefi-central-element-323112/` OR
- `gs://results-central-element-3-backtest-cefi/`

**Current Implementation:**
- ❌ **Not uploading to GCS** - saves locally only
- ✅ Local path structure: `backend/backtest_results/`

**Gap:** Critical - results not uploaded to GCS as required.

---

## Critical Gaps Summary

### 🔴 Critical (Must Fix)

1. **GCS Output Upload**
   - Results saved locally only
   - Must upload to `gs://execution-store-cefi-central-element-323112/backtest_results/{run_id}/`
   - Use UCS `upload_to_gcs()`

2. **Parquet Output Files**
   - Missing: `orders.parquet`, `fills.parquet`, `positions.parquet`, `equity_curve.parquet`
   - Currently only JSON outputs

3. **UCS Integration**
   - No `UnifiedCloudService` usage
   - No `download_from_gcs()` or `upload_to_gcs()` calls
   - Must integrate UCS for all GCS operations

4. **Byte-Range Streaming**
   - Loads full files instead of streaming time windows
   - Must implement `download_from_gcs_streaming()` with byte-range support

5. **Instrument Loading from GCS**
   - Creates instruments from config instead of loading from GCS bucket
   - Must load from `gs://instruments-store-cefi-central-element-323112/...`

### 🟡 Important (Should Fix)

6. **Signal-Driven Streaming**
   - Not implemented
   - Should only fetch tick data for intervals with signals

7. **Summary JSON Schema**
   - Structure differs from spec
   - Missing fields: `status`, `created_at`, `config`, `execution_stats`
   - Missing metrics: `sharpe_ratio`, `sortino_ratio`, `win_rate`, `profit_factor`

8. **Performance Benchmarking**
   - Not benchmarked against spec requirements
   - Need to verify 3-day backtest < 5 minutes

9. **Parallel Execution**
   - No batch processing infrastructure
   - No T+1 scheduled job

### 🟢 Minor (Nice to Have)

10. **Direct GCS Access**
    - Currently FUSE-only
    - Could add direct GCS access via UCS as fallback

11. **Latency Model Configuration**
    - Uses NautilusTrader defaults
    - Could be more explicit in config

---

## Recommended Implementation Plan

### Phase 1: Critical Fixes (Required for Spec Compliance)

1. **Integrate UnifiedCloudService**
   - Add `unified_cloud_services` dependency
   - Create UCS wrapper/service class
   - Replace local file reads with UCS `download_from_gcs()`

2. **Implement Byte-Range Streaming**
   - Add `download_from_gcs_streaming()` calls
   - Implement time window filtering
   - Add column projection support

3. **Generate Parquet Outputs**
   - Extract orders/fills/positions data from engine
   - Convert to DataFrames
   - Write Parquet files with correct schemas
   - Generate equity curve timeline

4. **Upload Results to GCS**
   - Use UCS `upload_to_gcs()` for all outputs
   - Upload JSON summary
   - Upload Parquet files
   - Upload config and logs

5. **Load Instruments from GCS**
   - Use UCS to download instrument definitions
   - Parse and register instruments from Parquet file

### Phase 2: Important Enhancements

6. **Align Summary JSON Schema**
   - Add missing fields (`status`, `created_at`, `config`, `execution_stats`)
   - Calculate missing metrics (`sharpe_ratio`, `sortino_ratio`, etc.)
   - Align structure with spec

7. **Implement Signal-Driven Streaming**
   - Load signals from GCS (mock for milestone)
   - Only fetch tick data for signal intervals
   - Optimize I/O by 90%+

8. **Performance Benchmarking**
   - Benchmark 3-day backtest
   - Optimize if needed to meet < 5 minute requirement

### Phase 3: Future Enhancements

9. **Parallel Execution Infrastructure**
   - Batch processing system
   - T+1 scheduled job
   - 100+ concurrent backtests

10. **Direct GCS Access Fallback**
    - Add direct GCS access option
    - Fallback when FUSE unavailable

---

## Files Requiring Changes

### High Priority

1. `backend/backtest_engine.py`
   - Add UCS integration for data loading
   - Add Parquet output generation
   - Add GCS upload functionality

2. `backend/results.py`
   - Add Parquet serialization methods
   - Align JSON schema with spec
   - Add UCS upload integration

3. `backend/catalog_manager.py`
   - Add UCS integration for instrument loading
   - Add byte-range streaming support

### Medium Priority

4. `backend/data_converter.py`
   - Add UCS integration for data loading
   - Add byte-range streaming support

5. `backend/run_backtest.py`
   - Add GCS upload after backtest completion
   - Add Parquet file generation

### New Files Needed

6. `backend/gcs_uploader.py` (NEW)
   - UCS wrapper for GCS operations
   - Upload results to GCS
   - Handle retries and errors

7. `backend/parquet_exporter.py` (NEW)
   - Generate orders.parquet
   - Generate fills.parquet
   - Generate positions.parquet
   - Generate equity_curve.parquet

---

## Conclusion

The system has a solid foundation with NautilusTrader integration and local file processing, but **is not fully aligned with the specification**. The critical gaps are:

1. **No GCS integration** - Results not uploaded, data not loaded from GCS
2. **No Parquet outputs** - Missing required Parquet files
3. **No UCS integration** - UnifiedCloudService not used
4. **No byte-range streaming** - Performance optimization missing

**Recommendation:** Implement Phase 1 critical fixes to achieve spec compliance before the December 12 deadline.

---

*Last Updated: December 2025*

