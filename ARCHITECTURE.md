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

## Data & FUSE Model
- `data_downloads/` is treated as a FUSE-mounted bucket (future GCS FUSE). Backend scans it to discover datasets and map them into catalogs. The logical alias `@data_downloads` refers to the GCS bucket folder; mounting via FUSE makes it appear locally at `data_downloads/`.
- Directory scan targets:
  - `data_downloads/raw_tick_data/by_date/day-YYYY-MM-DD/` (raw trades + `book_snapshot_5` inputs, future @data_downloads bucket)
  - `backend/data/parquet/` (converted Parquet catalog - **this is where converted data is stored**)
  - `backend/backtest_results/` (fast/full result JSONs)
  - `frontend/public/tickdata/` (full-mode tick JSON exports)

## Data Conversion & Catalog Registration (Automatic)
- **Raw Parquet Files**: Located in `data_downloads/raw_tick_data/by_date/day-YYYY-MM-DD/data_type-trades/` and `data_type-book_snapshot_5/`.
- **Automatic Conversion**: On first backtest run, raw Parquet files are automatically converted to NautilusTrader catalog format:
  - Raw files use common exchange schema (columns: `timestamp`, `local_timestamp`, `price`, `amount`, `side`, `id`, `exchange`, `symbol`).
  - Converter (`backend/data_converter.py`) handles schema mapping:
    - `timestamp` (microseconds) → `ts_event` (nanoseconds)
    - `local_timestamp` → `ts_init` (nanoseconds)
    - `side` (`"buy"`/`"sell"`) → `AggressorSide.BUYER`/`SELLER`
    - `amount` → `size` (Quantity)
    - `id` → `trade_id` (TradeId)
  - Converted data written to `backend/data/parquet/data/trade_tick/<instrument_id>/` using `catalog.write_data()`.
- **Caching**: Once converted, data is cached in catalog. Subsequent runs skip conversion and query catalog directly.
- **Catalog Query**: Backtest queries catalog using time window filters; ParquetDataCatalog handles predicate pushdown for efficient time-range queries.
- Snapshot ingestion: include `book_snapshot_5` to rebuild depth; enable replay with sorted timestamps (avoid BacktestEngine warning about unsorted streams).

## Configuration (External JSON Only)
- No backend constants: instrument, precision, venue/account, catalog paths, time window, strategy orders, risk, env vars all come from JSON.
- Env switches (must be honored in container env):  
  `UNIFIED_CLOUD_LOCAL_PATH=/app/data_downloads`  
  `UNIFIED_CLOUD_SERVICES_USE_PARQUET=true`  
  `UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=false`  
  `DATA_CATALOG_PATH=<dynamic>` (point to Parquet catalog root)
- FX stub: inject USDT/USD price if valuation needed; keep isolated to config.

## Backtesting Flow (BacktestNode)
1) **Load Configuration**: Read external JSON config file (instrument, venue, data paths, time window, strategy, risk).
2) **Initialize Catalog**: Create `ParquetDataCatalog` at `DATA_CATALOG_PATH` (default: `backend/data/parquet/`).
3) **Register Instrument**: Create and register instrument definition (CryptoPerpetual) in catalog from config.
4) **Automatic Data Conversion & Registration** (CRITICAL STEP):
   - Check if raw Parquet files exist at paths specified in config (`data_catalog.trades_path`, `data_catalog.book_snapshot_5_path`).
   - If data doesn't exist in catalog, automatically convert raw Parquet files to catalog format:
     - Read raw Parquet files from `data_downloads/` (supports multiple schemas: NautilusTrader format or common exchange format).
     - Convert timestamps (microseconds/milliseconds → nanoseconds).
     - Map columns (e.g., `timestamp` → `ts_event`, `side` → `aggressor_side`, `amount` → `size`).
     - Create `TradeTick` or `OrderBookDeltas` objects.
     - Write to catalog using `catalog.write_data()`.
   - If data already exists in catalog, skip conversion (cached for subsequent runs).
5) Build `BacktestRunConfig` from JSON (instrument, venue, time window, strategy orders, risk).
6) `BacktestNode` executes run, queries catalog for data in time window, replays events, produces summary JSON; optionally exports ticks.
7) Persist outputs: fast -> `backend/backtest_results/fast/<run_id>.json`; full -> `backend/backtest_results/full/<run_id>/` plus ticks under `frontend/public/tickdata/<run_id>.json`.

**Note**: Data conversion happens automatically on first run. Subsequent runs use cached catalog data, making them faster.

## Docker Compose Architecture
- **backend**: Python 3.11 + NautilusTrader, mounts `data_downloads/` (read-only) and `backend/data/parquet/` (read-write); runs FastAPI server on port 8000; exposes CLI entrypoint `python backend/run_backtest.py ...`.
- **frontend**: Vite + React + TypeScript + Tailwind; development server on port 5173; consumes JSON summaries/ticks via API proxy.
- **redis** (optional): only enable if benchmarked to improve repeated catalog lookups/result caching; default disabled (profiles: batch-processing).
- **Postgres**: intentionally omitted; file-based Parquet catalogs and JSON artifacts are sufficient per current design.
- **Volumes**: 
  - `data_downloads/` (read-only, FUSE-ready)
  - `backend/data/parquet/` (read-write, catalog storage)
  - `backend/backtest_results/` (read-write, result storage)
  - `frontend/public/tickdata/` (read-write, tick exports)
  - `external/data_downloads/configs/` (read-only, config files)

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
- **docs/REFERENCE.md**: Technical reference (data conversion, PnL calculation, testing, troubleshooting)
