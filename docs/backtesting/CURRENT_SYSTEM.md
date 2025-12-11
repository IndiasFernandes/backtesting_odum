# Backtesting System - Current State

> **Source of Truth (SSOT)** for the current backtesting system architecture and implementation.
> 

**See also:**
- `docs/backtesting/COMPLETION_ROADMAP.md` - What's needed to finish CeFi + TradFi
- `docs/backtesting/EXECUTION_ALGORITHMS.md` - Execution algorithms guide

---

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
   - **Data Source Selection**: Determined by `--data_source` CLI flag (default: `"gcs"`):
     - `"gcs"` (default): Uses UCS to load from GCS bucket (PRIMARY)
     - `"local"`: Uses local filesystem directly (fallback/development)
     - `"auto"`: Defaults to `"gcs"` (UCS)
   - **PRIMARY (GCS mode)**: Load raw Parquet files from GCS via UCS (`UCSDataLoader.load_trades()`, `load_book_snapshots()`)
   - **FALLBACK (Local mode)**: If `data_source="local"` or FUSE mounted, check local `data_downloads/` path
   - Check if data exists in local catalog cache (`backend/data/parquet/`)
   - If data doesn't exist in catalog, automatically convert raw Parquet files to catalog format:
     - Read raw Parquet files **from GCS via UCS** (when `data_source="gcs"`) or FUSE mount/local filesystem (when `data_source="local"`)
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
- **UCS is the primary interface** when `data_source="gcs"` (default) - all data operations go through UCS to/from GCS.
- Use `--data_source local` only for local development/testing without GCS access.

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
# Backtest Specification

## Modes
- **Fast mode** (`--fast`): Minimal JSON summary only, no tick export. Output: `backend/backtest_results/fast/<run_id>.json`.
- **Report mode** (`--report` or default): Full details including summary + timeline + orders + ticks + metadata. Output: `backend/backtest_results/report/<run_id>/` directory. With `--export_ticks`, also exports ticks to `frontend/public/tickdata/<run_id>.json`.

## CLI (complete list)
Example:
```
python backend/run_backtest.py \
  --instrument BTCUSDT \
  --dataset day-2023-05-23 \
  --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \
  --start 2023-05-23T02:00:00Z \
  --end 2023-05-23T02:30:00Z \
  --fast \
  --snapshot_mode both
```

Flags:
- `--instrument` string (required); logical instrument tag used by CLI/UI (must align with config instrument id).
- `--dataset` string (optional); dataset folder under `data_downloads/` to scan. Auto-detected from time window if not provided.
- `--config` path (required); external JSON with ALL runtime params (see schema).
- `--start` ISO UTC (required); inclusive start time window (e.g., `2023-05-23T02:00:00Z`).
- `--end` ISO UTC (required); inclusive end time window (e.g., `2023-05-23T02:30:00Z`).
- `--fast` flag; run in fast mode (minimal JSON summary only). Mutually exclusive with `--report`.
- `--report` flag; run in report mode (full details: timeline, orders, ticks, metadata). Default if neither `--fast` nor `--report` specified.
- `--export_ticks` flag; export tick JSON (requires `--report`).
- `--snapshot_mode` enum [`trades`,`book`,`both`]; controls ingestion of trades, `book_snapshot_5`, or both. Default: `both`.
- `--data_source` enum [`local`,`gcs`,`auto`]; data source selection. Default: `auto` (auto-detects).
- `--no_close_positions` flag; do not close open positions at end of backtest (default: positions are closed).

## External JSON Configuration (authoritative, nothing hardcoded)
```json
{
  "instrument": {
    "id": "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN",
    "price_precision": 2,
    "size_precision": 3
  },
  "venue": {
    "name": "BINANCE-FUTURES",
    "oms_type": "NETTING",
    "account_type": "MARGIN",
    "base_currency": "USDT",
    "starting_balance": 1000000,
    "maker_fee": 0.0002,
    "taker_fee": 0.0004
  },
  "data_catalog": {
    "trades_path": "raw_tick_data/by_date/day-*/data_type-trades/BINANCE-FUTURES:PERPETUAL:BTC-USDT.parquet",
    "book_snapshot_5_path": "raw_tick_data/by_date/day-*/data_type-book_snapshot_5/BINANCE-FUTURES:PERPETUAL:BTC-USDT.parquet",
    "auto_discover": true,
    "instrument_file_pattern": "BINANCE-FUTURES:PERPETUAL:BTC-USDT"
  },
  "time_window": {
    "start": "2025-01-01T00:00:00Z",
    "end": "2025-01-01T01:00:00Z"
  },
  "strategy": {
    "name": "TempBacktestStrategy",
    "submission_mode": "per_trade_tick",
    "orders": [
      { "side": "buy", "price": 50000.0, "amount": 0.1 }
      // one order per trade row will be generated; list may seed defaults
    ]
  },
  "risk": {
    "throttling_per_sec": 1000000
  },
  "environment": {
    "UNIFIED_CLOUD_LOCAL_PATH": "/app/data_downloads",
    "UNIFIED_CLOUD_SERVICES_USE_PARQUET": true,
    "UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS": true,
    "DATA_CATALOG_PATH": "backend/data/parquet/"
  },
  "fx_stub": {
    "USDT_USD": 1.0
  }
}
```
- All fields loaded dynamically; backend must fail fast if missing.
- Future GCS FUSE: only `data_catalog`/`trades_path`/`book_snapshot_5_path` change to mounted paths; rest unchanged.
- `@btcusdt_l2_trades_config.json` (example in `external/data_downloads/`) represents a ready-to-run config for BINANCE FUTURES BTCUSDT (23 May, 02:00–02:30 UTC) and can be duplicated/tweaked for ETHUSDT (23 May, 03:00–04:00 UTC) by swapping instrument/time window paths in the same schema.

## Strategy Logic (mandatory behavior)
- For every trade row ingested, submit exactly one order (`submission_mode="per_trade_tick"`); no indicators or derived signals.
- Order attributes derived from each trade row (side, price, amount) and optional seed list defaults.
- End-of-window: stop at `end` timestamp; ensure no trailing orders beyond catalog window.

## Data Loading & Catalog Rules

### Automatic Catalog Registration Process
1. **Catalog Initialization**: `ParquetDataCatalog` initialized at `DATA_CATALOG_PATH` (default: `backend/data/parquet/`).
2. **Instrument Registration**: Instrument (CryptoPerpetual) created from config and registered in catalog.
3. **Data Conversion Check**: Before building `BacktestDataConfig`, system checks if data exists in catalog:
   - Query catalog for any existing data of the required type (TradeTick/OrderBookDeltas) for the instrument.
   - If no data found, proceed to conversion step.
   - If data exists, skip conversion (use cached catalog data).
4. **Automatic Data Conversion** (if needed):
   - Read raw Parquet files from paths specified in config (`data_catalog.trades_path`, `data_catalog.book_snapshot_5_path`).
   - Convert using `DataConverter.convert_trades_parquet_to_catalog()` or `convert_orderbook_parquet_to_catalog()`:
     - Supports multiple Parquet schemas (NautilusTrader format or common exchange format).
     - Handles timestamp conversion (microseconds/milliseconds → nanoseconds).
     - Maps column names automatically.
     - Creates NautilusTrader data objects (`TradeTick`, `OrderBookDeltas`).
     - Writes to catalog using `catalog.write_data()`.
   - Conversion happens automatically on first run; subsequent runs use cached data.
5. **Catalog Query**: Backtest queries catalog using time window (`start_time`, `end_time`) and instrument filters.
6. **Data Replay**: NautilusTrader replays events from catalog data in chronological order.

### Catalog Structure
- **Raw Data**: `data_downloads/raw_tick_data/by_date/day-YYYY-MM-DD/data_type-trades/<VENUE>:<PRODUCT>.parquet`
- **Converted Catalog**: `backend/data/parquet/data/trade_tick/<instrument_id>/<timestamp_range>.parquet`
- **Instruments**: `backend/data/parquet/instruments/crypto_perpetual/<instrument_id>.parquet`

### Configuration Requirements
- Instrument + precision: read from config; instrument created and registered before data conversion.
- Venue/account: configured from JSON; base currency USDT; starting balance 1,000,000 USDT.
- Snapshot mode: `trades` loads trades only, `book` loads snapshots only, `both` loads both for richer replay.
- FUSE-ready: `data_downloads/` treated as GCS FUSE mount; paths remain POSIX and relative to container env.
- **Data paths in config**: Must point to raw Parquet files in `data_downloads/` structure (relative to `UNIFIED_CLOUD_LOCAL_PATH`).

## Outputs & Paths
- **Fast mode**: `backend/backtest_results/fast/<run_id>.json` (single JSON file with summary).
- **Report mode**: `backend/backtest_results/report/<run_id>/` directory containing:
  - `summary.json` - Summary metrics
  - `timeline.json` - Event timeline
  - `orders.json` - Order history
  - `metadata.json` - Run metadata
  - With `--export_ticks`: `frontend/public/tickdata/<run_id>.json` (tick data export)
- Each run_id includes metadata (instrument, dataset, start/end, hash of config) for reproducibility.
- Run ID format: `VENUE_INSTRUMENT_DATE_TIME_CONFIGHASH_UUID` (short and readable, e.g., `BNF_BTC_20230523_192312_018dd7_c54988`)

## Result JSON Shape
- **Fast mode** (single JSON file):
```json
{
  "run_id": "string",
  "mode": "fast",
  "instrument": "string",
  "dataset": "string",
  "start": "ISO8601",
  "end": "ISO8601",
  "summary": {
    "orders": 0,
    "fills": 0,
    "pnl": 0.0,
    "max_drawdown": 0.0,
    "trades": 0
  },
  "metadata": {
    "config_path": "string",
    "snapshot_mode": "both"
  }
}
```

- **Report mode** (directory with multiple JSON files):
  - `summary.json`: Same structure as fast mode summary
  - `timeline.json`: Array of events
  - `orders.json`: Array of orders
  - `metadata.json`: Extended metadata including catalog paths, data source, etc.
  - `ticks_path`: Path to tick export (if `--export_ticks` was used)

## Risk & Performance Constraints
- Throttling: disabled or effectively unlimited (`1_000_000/sec`).
- Sorting: enforce monotonic timestamps before feeding BacktestEngine to avoid replay drift.
- Caching: Redis optional; default off. If enabled, cache catalog listings and result manifests only.

## Validation
- Reject run if any of: missing env vars, missing config keys, instrument mismatch between config and catalog, missing `book_snapshot_5` when snapshot_mode requires it, unsorted timestamps.

## CLI & UI Alignment
- UI must render exact CLI invocation preview using the same flags and paths.
- All params originate from JSON + UI selections; backend never substitutes defaults silently.

## BacktestEngine.reset() - Detailed Usage Guide

### Understanding BacktestEngine.reset()

`BacktestEngine.reset()` is a critical method for optimizing multiple backtest runs. According to [NautilusTrader documentation](https://nautilustrader.io/docs/latest/concepts/backtesting/), it returns all stateful fields to their initial values while preserving data and instruments.

### What Gets Reset

**Reset (Cleared)**:
- All trading state:
  - Orders (submitted, pending, filled)
  - Positions (open positions, PnL)
  - Account balances (reset to starting balance)
- Strategy state:
  - Strategy internal variables
  - Strategy indicators (if any)
  - Strategy event handlers
- Engine counters and timestamps:
  - Event counters
  - Execution timestamps
  - Performance metrics

**Persists (Not Reset)**:
- Data added via `.add_data()`:
  - Historical trade ticks
  - Order book snapshots
  - Bar data
  - All time-series data
- Instruments:
  - Instrument definitions
  - Instrument metadata
  - Price/size precision
- Venue configurations:
  - Venue settings
  - Account configurations
  - Margin models

### When to Use BacktestEngine.reset()

**Use `reset()` for**:
1. **Parameter Optimization**: Test multiple strategy parameters on the same dataset
   ```python
   # Setup once
   engine = BacktestEngine()
   engine.add_venue(...)
   engine.add_instrument(BTCUSDT)
   engine.add_data(trade_data)  # Load data once
   
   # Test parameter set 1
   strategy1 = MyStrategy(config={"param": 0.1})
   engine.add_strategy(strategy1)
   engine.run()
   results1 = engine.get_results()
   
   # Reset and test parameter set 2
   engine.reset()  # Fast reset, data persists
   strategy2 = MyStrategy(config={"param": 0.2})
   engine.add_strategy(strategy2)
   engine.run()
   results2 = engine.get_results()
   ```

2. **Strategy Comparison**: Compare multiple strategies on identical data
   ```python
   strategies = [StrategyA(), StrategyB(), StrategyC()]
   results = []
   
   for strategy in strategies:
       engine.reset()  # Clean slate for each strategy
       engine.add_strategy(strategy)
       engine.run()
       results.append(engine.get_results())
   ```

3. **Monte Carlo Simulations**: Run multiple iterations with different random seeds
   ```python
   for seed in range(100):
       engine.reset()
       strategy = MyStrategy(random_seed=seed)
       engine.add_strategy(strategy)
       engine.run()
       # Collect results
   ```

4. **Sensitivity Analysis**: Test how strategy performs with different configurations
   ```python
   configs = [
       {"risk_level": "low", "leverage": 1},
       {"risk_level": "medium", "leverage": 2},
       {"risk_level": "high", "leverage": 5}
   ]
   
   for config in configs:
       engine.reset()
       strategy = MyStrategy(**config)
       engine.add_strategy(strategy)
       engine.run()
   ```

### When NOT to Use BacktestEngine.reset()

**Use `BacktestNode` (high-level API) instead when**:
1. **Different Datasets**: Each run uses different data
   ```python
   # Use BacktestNode - creates fresh engine per run
   configs = [
       BacktestRunConfig(data=dataset1, ...),
       BacktestRunConfig(data=dataset2, ...),
       BacktestRunConfig(data=dataset3, ...)
   ]
   node = BacktestNode(configs=configs)
   results = node.run()
   ```

2. **Different Instruments**: Each run tests different instruments
3. **Production Runs**: Clean, isolated runs for final validation
4. **Different Time Windows**: Each run covers different date ranges

### Performance Benefits of reset()

**Time Savings**:
- **Data Loading**: Skip data loading on subsequent runs (~5-30 seconds saved per run)
- **Instrument Setup**: Skip instrument registration (~0.5-2 seconds saved)
- **Venue Setup**: Skip venue initialization (~0.5-1 second saved)
- **Total**: ~6-33 seconds saved per run after the first

**Memory Benefits**:
- Data stays in memory (no reload)
- Instruments cached
- Catalog remains loaded

**Example Performance Comparison**:
```python
# Without reset() - 3 runs, 3x data loading
# Run 1: 45 seconds (30s data load + 15s execution)
# Run 2: 45 seconds (30s data load + 15s execution)
# Run 3: 45 seconds (30s data load + 15s execution)
# Total: 135 seconds

# With reset() - 3 runs, 1x data loading
# Run 1: 45 seconds (30s data load + 15s execution)
# Run 2: 16 seconds (1s reset + 15s execution)
# Run 3: 16 seconds (1s reset + 15s execution)
# Total: 77 seconds (43% faster)
```

### Best Practices for reset()

1. **Setup Once, Reset Many**:
   ```python
   # Good: Setup once
   engine = BacktestEngine()
   engine.add_venue(...)
   engine.add_instrument(...)
   engine.add_data(data)  # Expensive operation, do once
   
   # Then reset and reuse
   for i in range(100):
       engine.reset()
       # Add strategy and run
   ```

2. **Clear Data When Needed**:
   ```python
   # If you need to change data, clear first
   engine.clear_data()  # Remove old data
   engine.add_data(new_data)  # Add new data
   ```

3. **Reset Before Adding New Strategy**:
   ```python
   # Always reset before adding new strategy
   engine.reset()
   engine.add_strategy(new_strategy)  # Clean state
   engine.run()
   ```

4. **Don't Reset Between Runs of Same Strategy**:
   ```python
   # If testing same strategy with same config, no reset needed
   # (unless you need clean state)
   ```

5. **Handle Reset Errors**:
   ```python
   try:
       engine.reset()
   except Exception as e:
       # Log error, may need to recreate engine
       engine = BacktestEngine()  # Fallback
   ```

### Configuration for reset() Behavior

**CacheConfig.drop_instruments_on_reset**:
- `False` (default): Instruments persist across resets
- `True`: Instruments cleared on reset (rarely needed)

**Example**:
```python
from nautilus_trader.config import BacktestEngineConfig, CacheConfig

config = BacktestEngineConfig(
    cache=CacheConfig(
        drop_instruments_on_reset=False  # Default, recommended
    )
)
engine = BacktestEngine(config=config)
```

### Common Patterns

**Pattern 1: Parameter Sweep**
```python
engine = BacktestEngine()
# Setup once
engine.add_venue(...)
engine.add_instrument(BTCUSDT)
engine.add_data(trade_data)

# Sweep parameters
for param_value in [0.1, 0.2, 0.3, 0.4, 0.5]:
    engine.reset()
    strategy = MyStrategy(threshold=param_value)
    engine.add_strategy(strategy)
    engine.run()
    # Collect results
```

**Pattern 2: Strategy Portfolio**
```python
engine = BacktestEngine()
# Setup once
engine.add_venue(...)
engine.add_instrument(BTCUSDT)
engine.add_data(trade_data)

strategies = [StrategyA(), StrategyB(), StrategyC()]
results = {}

for strategy in strategies:
    engine.reset()
    engine.add_strategy(strategy)
    engine.run()
    results[strategy.name] = engine.get_results()
```

**Pattern 3: Monte Carlo**
```python
engine = BacktestEngine()
# Setup once
engine.add_venue(...)
engine.add_instrument(BTCUSDT)
engine.add_data(trade_data)

monte_carlo_results = []
for iteration in range(1000):
    engine.reset()
    strategy = MyStrategy(random_seed=iteration)
    engine.add_strategy(strategy)
    engine.run()
    monte_carlo_results.append(engine.get_results())
```

## Performance Tuning Options - Complete Guide

### 1. Data Granularity Selection

**Impact**: Most significant performance factor (10-100x difference)

**Options** (from most detailed to least):
1. **L3 Order Book (Market-by-Order)**: Individual orders
2. **L2 Order Book (Market-by-Price)**: Price level aggregation
3. **L1 Quote Ticks**: Best bid/ask only
4. **Trade Ticks**: Executed trades
5. **Bars**: OHLC aggregation

**Configuration**:
```json
{
  "data_catalog": {
    "data_type": "bars",
    "bar_aggregation": "1min"
  }
}
```

**Performance Impact**:
- Bars: Fastest (~100x faster than L3)
- Trades: ~10x faster than L3
- L1: ~5x faster than L3
- L2: ~2x faster than L3
- L3: Slowest, most accurate

**When to Use**:
- **Bars**: Initial development, parameter optimization
- **Trades**: Quick validation, simple strategies
- **L2**: Production backtesting (recommended)
- **L3**: Final validation, maximum accuracy needed

### 2. Book Type Configuration

**Impact**: Memory and processing speed (5-10x difference)

**Options**:
- `L1_MBP`: Top level only (~10x faster than L2)
- `L2_MBP`: Full depth, aggregated (recommended)
- `L3_MBO`: Full depth, individual orders (~5-10x slower than L2)

**Configuration**:
```json
{
  "venue": {
    "book_type": "L2_MBP"
  }
}
```

**Memory Usage**:
- L1_MBP: ~1 KB per instrument
- L2_MBP: ~10-100 KB per instrument
- L3_MBO: ~100 KB - 1 MB per instrument

### 3. Fill Model Configuration

**Impact**: Execution realism vs speed (5-10% difference)

**Parameters**:
- `prob_fill_on_limit`: 0.0-1.0 (default: 1.0)
  - `1.0`: Always fill (fastest, optimistic)
  - `0.9`: Realistic fill rate (~5% slower)
  - `0.8`: Conservative fill rate (~10% slower)
  
- `prob_slippage`: 0.0-1.0 (default: 0.0)
  - `0.0`: No slippage (fastest)
  - `0.1`: Realistic slippage (~2% slower)
  - `0.3`: High slippage (~5% slower)

**Configuration**:
```json
{
  "execution": {
    "fill_model": {
      "prob_fill_on_limit": 0.9,
      "prob_slippage": 0.1,
      "random_seed": 42
    }
  }
}
```

### 4. Logging Level

**Impact**: I/O overhead (1-50% difference)

**Options**:
- `DEBUG`: All events (~20-50% slower)
- `INFO`: Standard logging (~5-10% slower)
- `WARNING`: Errors and warnings (~1-2% slower)
- `ERROR`: Errors only (fastest)

**Configuration**:
```json
{
  "environment": {
    "log_level": "INFO"
  }
}
```

**When to Use**:
- `DEBUG`: Debugging issues only
- `INFO`: Development and testing
- `WARNING`: Production runs
- `ERROR`: Maximum performance needed

### 5. Report Generation

**Impact**: Post-processing time (10-30% difference)

**Configuration**:
- CLI: `--report_mode none|report|full`
- Config: `"engine.run_analysis": true|false`

**When to Disable**:
- Batch parameter sweeps
- Monte Carlo simulations
- CI/CD pipelines
- Quick validation runs

**When to Enable**:
- Final analysis
- Stakeholder reports
- Detailed performance review

### 6. Preflight Checks

**Impact**: Startup time (1-2 seconds)

**Configuration**:
```json
{
  "engine": {
    "bypass_preflight": true
  }
}
```

**When to Bypass**:
- Trusted, validated configurations
- Repeated runs with same config
- Performance-critical scenarios

**When to Keep**:
- New configurations
- Untested data sources
- Production validation

### 7. Cache Configuration

**Impact**: Repeated catalog scans (1-5 seconds per run)

**Configuration**:
```json
{
  "engine": {
    "cache": true
  }
}
```

**Requirements**: Redis must be enabled

**When to Enable**:
- Parameter sweeps (many runs)
- Strategy comparisons
- Monte Carlo simulations

**When to Disable**:
- Single runs
- Different datasets per run
- Memory-constrained environments

### 8. Snapshot Mode

**Impact**: Data loading time (2x difference)

**Options**:
- `trades`: Trades only (~50% faster loading)
- `book`: Book snapshots only
- `both`: Both trades and book (~2x slower loading)

**Configuration**:
- CLI: `--snapshot_mode trades|book|both`

**When to Use**:
- `trades`: Simple strategies, quick testing
- `both`: Production backtests (recommended)

### Performance Optimization Presets

**Preset 1: Maximum Speed (Development)**
```json
{
  "data_catalog": {
    "data_type": "bars",
    "bar_aggregation": "1min"
  },
  "venue": {
    "book_type": "L1_MBP"
  },
  "execution": {
    "fill_model": {
      "prob_fill_on_limit": 1.0,
      "prob_slippage": 0.0
    }
  },
  "engine": {
    "bypass_preflight": true,
    "run_analysis": false
  },
  "environment": {
    "log_level": "ERROR"
  }
}
```
**Expected**: 10-50x faster than full L2 backtest

**Preset 2: Balanced (Production)**
```json
{
  "data_catalog": {
    "data_type": "book_snapshot_5"
  },
  "venue": {
    "book_type": "L2_MBP"
  },
  "execution": {
    "fill_model": {
      "prob_fill_on_limit": 0.9,
      "prob_slippage": 0.1
    }
  },
  "engine": {
    "run_analysis": true
  },
  "environment": {
    "log_level": "INFO"
  }
}
```
**Expected**: 2-5x faster than L3, maintains good accuracy

**Preset 3: Maximum Accuracy (Final Validation)**
```json
{
  "data_catalog": {
    "data_type": "book_snapshot_5"
  },
  "venue": {
    "book_type": "L3_MBO"
  },
  "execution": {
    "fill_model": {
      "prob_fill_on_limit": 0.85,
      "prob_slippage": 0.15
    }
  },
  "environment": {
    "log_level": "INFO"
  }
}
```
**Expected**: Slowest but most realistic execution simulation

