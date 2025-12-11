# Backtest Specification

## Modes
- Fast mode (default): summary JSON only, no tick export.
- Full mode: summary + timeline + orders + ticks + metadata; exports ticks to `frontend/public/tickdata/<run_id>.json`.

## CLI (complete list)
Example:
```
python run_backtest.py \
  --instrument BTCUSDT \
  --dataset example01 \
  --config configs/btcusdt_config.json \
  --start 2025-01-01T00:00:00Z \
  --end 2025-01-01T01:00:00Z \
  --full false \
  --export_ticks false \
  --snapshot_mode both
```
Flags:
- `--instrument` string; logical instrument tag used by CLI/UI (must align with config instrument id).
- `--dataset` string; dataset folder under `data_downloads/` to scan.
- `--config` path; external JSON with ALL runtime params (see schema).
- `--start` ISO UTC; inclusive start time window.
- `--end` ISO UTC; inclusive end time window.
- `--full` bool; enable full mode outputs.
- `--export_ticks` bool; export tick JSON (implied true when `--full true`).
- `--snapshot_mode` enum [`trades`,`book`,`both`]; controls ingestion of trades, `book_snapshot_5`, or both.

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
    "UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS": false,
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
- Fast: `backend/backtest_results/fast/<run_id>.json`.
- Report: `backend/backtest_results/report/<run_id>/summary.json`, `.../timeline.json`, `.../orders.json`, ticks at `frontend/public/tickdata/<run_id>.json`.
- Each run_id includes metadata (instrument, dataset, start/end, hash of config) for reproducibility.
- Run ID format: `VENUE_INSTRUMENT_DATE_TIME_CONFIGHASH_UUID` (short and readable, e.g., `BNF_BTC_20230523_192312_018dd7_c54988`)

## Result JSON Shape
- Fast (minimum):
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
    "max_drawdown": 0.0
  },
  "metadata": {
    "config_path": "string",
    "snapshot_mode": "both"
  }
}
```
- Full (adds detail):
```json
{
  "run_id": "string",
  "mode": "full",
  "instrument": "string",
  "dataset": "string",
  "start": "ISO8601",
  "end": "ISO8601",
  "summary": { "...": "same keys as fast" },
  "timeline": [{ "ts": "ISO8601", "event": "Trade|Order|Fill", "data": {} }],
  "orders": [{ "id": "string", "side": "buy|sell", "price": 0.0, "amount": 0.0, "status": "submitted|filled|cancelled" }],
  "ticks_path": "frontend/public/tickdata/<run_id>.json",
  "metadata": {
    "config_path": "string",
    "snapshot_mode": "both",
    "catalog_root": "string"
  }
}
```

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

