# System Architecture

## High-Level Overview
- Purpose: containerized, trade-driven NautilusTrader backtesting stack with deterministic replay via `BacktestNode` (per Nautilus docs high-level API orchestrating multiple `BacktestEngine` instances).
- Everything is runtime-configured through an external JSON (no hardcoded backend params).
- Data is file-based (Parquet) to keep the system stateless and GCS FUSE–ready; `data_downloads/` emulates the future bucket mount.
- Two outputs paths: fast JSON summaries and full-mode JSON + tick exports for the UI.

## Core Components
- Backtest orchestration: Nautilus `BacktestNode` + `BacktestRunConfig` list (see https://nautilustrader.io/docs/latest/concepts/backtesting/). Node handles engine lifecycle, event replay, catalog hookups, and concurrency-safe runs.
- Data layer: `ParquetDataCatalog` for trade and L2 snapshot ingestion; catalog scan under `backend/data/parquet/`.
- Strategy: trade-driven `TempBacktestStrategy`, one order per trade row, `submission_mode="per_trade_tick"`, no indicators/external logic.
- Config: single external JSON defines instrument precision, venue/account, data catalog paths, time window, orders, risk, env flags, FX stub.

## Data & Unified Cloud Services (UCS) Model

**⚠️ PRIMARY DATA INTERFACE**: `unified-cloud-services` (UCS) is the **main interface** for all data operations:
- ✅ **Data Source**: GCS via UCS API (`download_from_gcs()`, `download_from_gcs_streaming()`)
- ✅ **Data Destination**: GCS via UCS API (`upload_to_gcs()`)
- ✅ `UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=true` ensures direct GCS API access (not FUSE)

**Current Implementation** (as of December 2025):
- `backend/ucs_data_loader.py` - Uses UCS for all data loading from GCS
- `backend/results.py` - Uses UCS for all result uploads to GCS
- Results written directly to `gs://execution-store-cefi-central-element-323112/` via UCS

**FUSE/Local Filesystem** (Fallback/Development Only):
- `data_downloads/` volume mount is **only** used as:
  - Development convenience (local testing)
  - FUSE mount fallback (if `USE_GCS_FUSE=true` and FUSE is mounted)
  - **NOT** the primary data source in production
- Local directory structure mirrors GCS for FUSE compatibility:
  - `data_downloads/raw_tick_data/by_date/day-YYYY-MM-DD/` (FUSE fallback)
  - `backend/data/parquet/` (converted Parquet catalog cache - can be regenerated)
  - `backend/backtest_results/` (temporary local writes, uploaded to GCS via UCS)
  - `frontend/public/tickdata/` (temporary local writes, uploaded to GCS via UCS)

## Data Conversion & Catalog Registration (Automatic)

**Data Source**: GCS via UCS (Primary):
- **Raw Parquet Files**: Located in GCS `gs://market-data-tick-cefi-central-element-323112/raw_tick_data/by_date/day-YYYY-MM-DD/data_type-trades/` and `data_type-book_snapshot_5/`
- **Access Method**: `UCSDataLoader` uses UCS `download_from_gcs()` or `download_from_gcs_streaming()` to load data from GCS
- **FUSE Fallback**: If `USE_GCS_FUSE=true` and FUSE is mounted, local `data_downloads/` path mirrors GCS structure

**Automatic Conversion**: On first backtest run, raw Parquet files are automatically converted to NautilusTrader catalog format:
  - Raw files loaded **from GCS via UCS** (or FUSE mount if available)
  - Raw files use common exchange schema (columns: `timestamp`, `local_timestamp`, `price`, `amount`, `side`, `id`, `exchange`, `symbol`).
  - Converter (`backend/data_converter.py`) handles schema mapping:
    - `timestamp` (microseconds) → `ts_event` (nanoseconds)
    - `local_timestamp` → `ts_init` (nanoseconds)
    - `side` (`"buy"`/`"sell"`) → `AggressorSide.BUYER`/`SELLER`
    - `amount` → `size` (Quantity)
    - `id` → `trade_id` (TradeId)
  - Converted data written to `backend/data/parquet/data/trade_tick/<instrument_id>/` using `catalog.write_data()` (local cache).
- **Caching**: Once converted, data is cached in local catalog. Subsequent runs skip conversion and query catalog directly.
- **Catalog Query**: Backtest queries catalog using time window filters; ParquetDataCatalog handles predicate pushdown for efficient time-range queries.
- Snapshot ingestion: include `book_snapshot_5` to rebuild depth; enable replay with sorted timestamps (avoid BacktestEngine warning about unsorted streams).

## Configuration (External JSON Only)
- No backend constants: instrument, precision, venue/account, catalog paths, time window, strategy orders, risk, env vars all come from JSON.
- Env switches (must be honored in container env):  
  **Primary Data Interface (UCS)**:
  - `UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=true` (default: uses direct GCS API via UCS, not FUSE mount)
  - `UNIFIED_CLOUD_SERVICES_GCS_BUCKET=market-data-tick-cefi-central-element-323112` (GCS bucket for market data)
  - `EXECUTION_STORE_GCS_BUCKET=execution-store-cefi-central-element-323112` (GCS bucket for results)
  - `GOOGLE_APPLICATION_CREDENTIALS=/app/.secrets/gcs/gcs-service-account.json` (GCS credentials)
  
  **Fallback/Development**:
  - `UNIFIED_CLOUD_LOCAL_PATH=/app/data_downloads` (FUSE mount fallback path, not primary)
  - `USE_GCS_FUSE=false` (set to `true` only if using FUSE mount)
  
  **Catalog**:
  - `UNIFIED_CLOUD_SERVICES_USE_PARQUET=true`  
  - `DATA_CATALOG_PATH=<dynamic>` (point to Parquet catalog root - local cache)
- FX stub: inject USDT/USD price if valuation needed; keep isolated to config.

## Backtesting Flow (BacktestNode)
1) **Load Configuration**: Read external JSON config file (instrument, venue, data paths, time window, strategy, risk).
2) **Initialize Catalog**: Create `ParquetDataCatalog` at `DATA_CATALOG_PATH` (default: `backend/data/parquet/`).
3) **Register Instrument**: Create and register instrument definition (CryptoPerpetual) in catalog from config.
4) **Automatic Data Conversion & Registration** (CRITICAL STEP):
   - **PRIMARY**: Load raw Parquet files from GCS via UCS (`UCSDataLoader.download_from_gcs()` or `download_from_gcs_streaming()`)
   - **FALLBACK**: If FUSE mounted, check local `data_downloads/` path
   - Check if data exists in local catalog cache (`backend/data/parquet/`)
   - If data doesn't exist in catalog, automatically convert raw Parquet files to catalog format:
     - Read raw Parquet files **from GCS via UCS** (or FUSE mount if available)
     - Supports multiple schemas: NautilusTrader format or common exchange format
     - Convert timestamps (microseconds/milliseconds → nanoseconds)
     - Map columns (e.g., `timestamp` → `ts_event`, `side` → `aggressor_side`, `amount` → `size`)
     - Create `TradeTick` or `OrderBookDeltas` objects
     - Write to local catalog cache using `catalog.write_data()`
   - If data already exists in catalog, skip conversion (cached for subsequent runs)
5) Build `BacktestRunConfig` from JSON (instrument, venue, time window, strategy orders, risk)
6) `BacktestNode` executes run, queries catalog for data in time window, replays events, produces summary JSON; optionally exports ticks
7) **Persist outputs** (PRIMARY: GCS via UCS):
   - Fast mode: Upload `summary.json` to GCS via UCS `upload_to_gcs()`
   - Full mode: Upload `summary.json`, `orders.parquet`, `fills.parquet`, `positions.parquet`, `equity_curve.parquet` to GCS via UCS
   - **Destination**: `gs://execution-store-cefi-central-element-323112/backtest_results/<run_id>/`
   - **Local writes**: Temporary local files (`backend/backtest_results/`, `frontend/public/tickdata/`) are uploaded to GCS and can be cleaned up

**Note**: 
- Data conversion happens automatically on first run. Subsequent runs use cached catalog data, making them faster.
- **UCS is the primary interface** - all data operations go through UCS to/from GCS.

## Docker Compose Architecture
- **backend**: Python 3.13 + NautilusTrader, mounts `data_downloads/` (read-only) and `backend/data/parquet/` (read-write); runs FastAPI server on port 8000; exposes CLI entrypoint `python backend/run_backtest.py ...`.
- **frontend**: Vite + React + TypeScript + Tailwind; development server on port 5173; consumes JSON summaries/ticks via API proxy.
- **redis** (optional): only enable if benchmarked to improve repeated catalog lookups/result caching; default disabled (profiles: batch-processing).
- **Postgres**: intentionally omitted; file-based Parquet catalogs and JSON artifacts are sufficient per current design.
- **Volumes**: 
  - `data_downloads/` (read-only, FUSE-ready)
  - `backend/data/parquet/` (read-write, catalog storage)
  - `backend/backtest_results/` (read-write, result storage)
  - `frontend/public/tickdata/` (read-write, tick exports)
  - `external/data_downloads/configs/` (read-only, config files)
- **Scripts**: Located in `backend/scripts/`:
  - `start.sh` - Container startup script (handles FUSE mounting and API server)
  - `mount_gcs.sh` - GCS FUSE mounting script
  - `tests/` - Test scripts for infrastructure and CLI alignment
  - `tools/` - Utility scripts for data validation and GCS operations

## Caching & Redis Stance
- Default: no Redis; Parquet + local filesystem is usually faster for bounded backtests. Enable Redis only after measuring cache hit benefits (e.g., repeated UI reads of large summary JSONs).
- If enabled: cache run metadata and catalog discovery results; avoid storing tick blobs in Redis.

## Frontend Contract
- Reads run lists from `backend/backtest_results/`.
- In full mode, fetches tick JSON from `frontend/public/tickdata/`.
- Dataset selector reflects `data_downloads/` scan; config selector points to JSON files (no hardcoded presets).

## Why Trade-Driven / Why External JSON
- Trade-driven keeps deterministic mapping: one order per trade row with `per_trade_tick`; aligns with Nautilus event replay.
- External JSON ensures reproducibility, portable configs for future GCS FUSE migration, and avoids image rebuilds for parameter changes.

## Non-Goals / Exclusions
- No indicators, no external feeds, no Postgres.
- Redis optional; enable only with evidence.
- All instrumentation/paths stay file-based to remain cloud-portable.

## Additional Documentation

- **BACKTEST_SPEC.md**: Complete CLI reference, JSON schema, strategy logic
- **FRONTEND_UI_SPEC.md**: Frontend component architecture, UI patterns
- **FUSE_SETUP.md**: GCS FUSE integration guide
