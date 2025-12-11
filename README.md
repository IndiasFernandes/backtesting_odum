# Odum Trader Backtest

Production-grade, containerized backtesting system built on NautilusTrader with external JSON configuration and GCS FUSE-ready architecture.

## Overview

This system provides a complete backtesting solution using NautilusTrader's high-level API (`BacktestNode`) for orchestrating multiple backtest runs. All runtime parameters are configured via external JSON files—nothing is hardcoded. The system is designed to be portable, stateless, and ready for cloud storage integration via GCS FUSE mounts.

## Key Features

- **Trade-Driven Backtesting**: One order per trade row using `submission_mode="per_trade_tick"`
- **External JSON Configuration**: All parameters (instrument, venue, data paths, time windows) defined in JSON
- **Automatic Data Conversion**: Raw Parquet files automatically converted to NautilusTrader catalog format
- **Fast & Report Modes**: Minimal summaries or full detailed results with timeline, orders, and tick exports
- **GCS FUSE Integration**: Mount Google Cloud Storage buckets directly (see `FUSE_SETUP.md`)
- **Docker Compose Stack**: Complete containerized backend (Python) and frontend (React/Vite)
- **Production UI**: React dashboard with comparison tables, backtest runner, and config editor

## Quick Start

### Prerequisites

- Docker and Docker Compose (Docker 20.10+, Docker Compose 2.0+)
- Raw Parquet data files in `data_downloads/raw_tick_data/by_date/day-YYYY-MM-DD/`
- At least 5GB free disk space, 4GB RAM recommended

### Start Services

```bash
# Start all services (backend API + frontend UI)
docker-compose up -d

# View backend logs
docker-compose logs -f backend

# Check service status
docker-compose ps

# Run infrastructure tests
./backend/scripts/tests/test_docker_infrastructure.sh
```

### Access UI

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Docker Services

- **Backend** (port 8000): Python FastAPI server with NautilusTrader
- **Frontend** (port 5173): React/Vite development server
- **Redis** (port 6379): Optional, enabled with `--profile batch-processing`

### Docker Volumes

- `data_downloads/` → `/app/data_downloads` (read-only, raw data)
- `backend/data/parquet/` → `/app/backend/data/parquet` (read-write, catalog)
- `backend/backtest_results/` → `/app/backend/backtest_results` (read-write, results)
- `frontend/public/tickdata/` → `/app/frontend/public/tickdata` (read-write, tick exports)
- `external/data_downloads/configs/` → `/app/external/data_downloads/configs` (read-only, configs)

### Common Docker Commands

```bash
# Stop services
docker-compose stop

# Restart services
docker-compose restart

# Rebuild after code changes
docker-compose up -d --build

# Stop and remove containers
docker-compose down

# Execute commands in containers
docker-compose exec backend bash
docker-compose exec frontend sh

# View health status
docker inspect --format='{{.State.Health.Status}}' nautilus-backend
docker inspect --format='{{.State.Health.Status}}' nautilus-frontend
```

### Run a Backtest

#### Via Frontend UI (Recommended)

1. Open http://localhost:5173/run
2. Form is pre-filled with example values (Binance Futures BTCUSDT, May 23, 19:23-19:28 UTC)
3. Click "Run Backtest" and watch status updates
4. View results at http://localhost:5173/compare

#### Via CLI

**Fast Mode (minimal summary):**
```bash
docker-compose exec backend python backend/run_backtest.py \
  --instrument BTCUSDT \
  --dataset day-2023-05-23 \
  --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \
  --start 2023-05-23T02:00:00Z \
  --end 2023-05-23T02:01:00Z \
  --fast \
  --snapshot_mode trades
```

**Report Mode (full details with timeline):**
```bash
docker-compose exec backend python backend/run_backtest.py \
  --instrument BTCUSDT \
  --dataset day-2023-05-23 \
  --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \
  --start 2023-05-23T02:00:00Z \
  --end 2023-05-23T02:01:00Z \
  --report \
  --snapshot_mode trades \
  --export_ticks
```

**Available CLI Flags:**
- `--fast`: Fast mode (minimal JSON summary)
- `--report`: Report mode (full details: timeline, orders, metadata). Default if neither `--fast` nor `--report` specified.
- `--export_ticks`: Export tick data (requires `--report`)
- `--snapshot_mode`: `trades`, `book`, or `both` (default: `both`)
- `--data_source`: `local`, `gcs`, or `auto` (default: `auto`)
- `--no_close_positions`: Don't close positions at end (default: positions are closed)
- `--dataset`: Optional dataset name (auto-detected from time window if not provided)

#### Via API

**Fast Mode:**
```bash
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "instrument": "BTCUSDT",
    "dataset": "day-2023-05-23",
    "config": "binance_futures_btcusdt_l2_trades_config.json",
    "start": "2023-05-23T02:00:00Z",
    "end": "2023-05-23T02:01:00Z",
    "fast": true,
    "snapshot_mode": "trades"
  }'
```

**Report Mode:**
```bash
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "instrument": "BTCUSDT",
    "dataset": "day-2023-05-23",
    "config": "binance_futures_btcusdt_l2_trades_config.json",
    "start": "2023-05-23T02:00:00Z",
    "end": "2023-05-23T02:01:00Z",
    "report": true,
    "snapshot_mode": "trades",
    "export_ticks": true
  }'
```

**API Parameters:**
- `fast`: boolean - Fast mode (minimal summary). Mutually exclusive with `report`.
- `report`: boolean - Report mode (full details). Default if neither `fast` nor `report` specified.
- `export_ticks`: boolean - Export tick data (requires `report: true`)
- `snapshot_mode`: string - `"trades"`, `"book"`, or `"both"` (default: `"both"`)
- `data_source`: string - `"local"`, `"gcs"`, or `"auto"` (default: `"auto"`)
- `dataset`: string (optional) - Dataset name (auto-detected from time window if not provided)

## Project Structure

```
.
├── README.md                    # This file
├── ARCHITECTURE.md              # System architecture documentation
├── BACKTEST_SPEC.md             # Backtest specification and CLI reference
├── FRONTEND_UI_SPEC.md          # Frontend UI specification
├── docker-compose.yml           # Docker Compose configuration
│
├── backend/                     # Python backend
│   ├── run_backtest.py         # CLI entrypoint
│   ├── backtest_engine.py      # BacktestNode orchestration
│   ├── config_loader.py        # JSON config loader
│   ├── data_converter.py       # Parquet → Catalog converter
│   ├── strategy.py             # Trade-driven strategy
│   ├── strategy_evaluator.py   # Performance analysis
│   ├── results.py              # Result serialization
│   ├── api/                    # REST API server
│   │   └── server.py           # FastAPI endpoints
│   ├── scripts/                # Backend scripts
│   │   ├── start.sh            # Container startup script
│   │   ├── mount_gcs.sh        # GCS FUSE mounting script
│   │   ├── tests/              # Test scripts
│   │   └── tools/              # Utility scripts
│   ├── data/parquet/           # Converted catalog data (auto-generated)
│   └── backtest_results/       # Backtest outputs
│       ├── fast/               # Fast mode JSON summaries
│       └── report/             # Report mode directories
│
├── frontend/                    # React frontend
│   ├── src/
│   │   ├── pages/              # Page components
│   │   │   ├── BacktestRunnerPage.tsx
│   │   │   ├── BacktestComparisonPage.tsx
│   │   │   └── DefinitionsPage.tsx
│   │   ├── components/        # Reusable components
│   │   └── services/          # API clients
│   └── public/tickdata/       # Tick JSON exports (full mode)
│
├── external/data_downloads/
│   └── configs/                # JSON configuration files
│       ├── binance_futures_btcusdt_l2_trades_config.json
│       ├── binance_futures_ethusdt_l2_trades_config.json
│       └── ...                 # Other venue/instrument configs
│
├── data_downloads/             # Raw data (FUSE mount point)
│   └── raw_tick_data/
│       └── by_date/
│           └── day-YYYY-MM-DD/
│               ├── data_type-trades/
│               └── data_type-book_snapshot_5/
│
└── FUSE_SETUP.md               # GCS FUSE integration guide
```

## Configuration

All runtime parameters are specified in external JSON files located in `external/data_downloads/configs/`. See `BACKTEST_SPEC.md` for complete JSON schema.

### Key Configuration Sections

- **instrument**: ID, price/size precision
- **venue**: Name, OMS type, account type, base currency, starting balance, maker/taker fees
- **data_catalog**: Paths to raw Parquet files (supports wildcards for auto-discovery)
- **time_window**: Start/end UTC timestamps
- **strategy**: Strategy name, submission mode
- **environment**: Environment variables (paths, Parquet flags)

### Example Config

```json
{
  "instrument": {
    "id": "BTC-USDT.BINANCE-FUTURES",
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
    "auto_discover": true
  },
  "time_window": {
    "start": "2023-05-23T19:23:00Z",
    "end": "2023-05-23T19:28:00Z"
  }
}
```

## Backtest Modes

### Fast Mode (`--fast`)

- Minimal JSON summary
- Quick performance metrics (PnL, orders, fills, trades)
- No tick export
- Output: `backend/backtest_results/fast/<run_id>.json`

### Report Mode (`--report`)

- Full timeline of events
- Complete order history
- Tick data export (optional with `--export_ticks`)
- Detailed metadata
- Output: `backend/backtest_results/report/<run_id>/` directory

## Run ID Format

Run IDs are short and readable:
```
BNF_BTC_20230523_192312_018dd7_c54988
```

Format: `VENUE_INSTRUMENT_DATE_TIME_CONFIGHASH_UUID`
- Venue: Shortened (BINANCE-FUTURES → BNF)
- Instrument: Shortened (BTCUSDT → BTC)
- Date: YYYYMMDD
- Time: HHMMSS + 2-digit microseconds
- Config hash: 6 characters
- UUID: 6 characters (ensures uniqueness)

## Data Flow

1. **Raw Data**: Parquet files in `data_downloads/raw_tick_data/by_date/day-YYYY-MM-DD/`
2. **Automatic Conversion**: On first run, raw files converted to NautilusTrader catalog format
3. **Catalog Storage**: Converted data stored in `backend/data/parquet/data/trade_tick/<instrument_id>/`
4. **Backtest Query**: NautilusTrader queries catalog for time window
5. **Results**: Saved to `backend/backtest_results/` (fast or report mode)

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/backtest/run` - Execute backtest
- `GET /api/backtest/results` - List all results
- `GET /api/backtest/results/{run_id}` - Get specific result
- `GET /api/datasets` - Scan available datasets
- `GET /api/configs` - List config files
- `GET /api/configs/{config_name}` - Get config content
- `POST /api/configs` - Save config file

## Environment Variables

- `UNIFIED_CLOUD_LOCAL_PATH` - Base path for data (default: `/app/data_downloads`)
- `UNIFIED_CLOUD_SERVICES_USE_PARQUET` - Use Parquet format (default: `true`)
- `UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS` - Direct GCS access (default: `false`)
- `DATA_CATALOG_PATH` - Parquet catalog root (default: `/app/backend/data/parquet`)

## Status Updates

The system provides detailed status updates during backtest execution:

- Data validation and file discovery
- Catalog registration progress (file sizes, conversion counts)
- Backtest execution progress
- Performance evaluation steps

Watch logs: `docker-compose logs -f backend`

## Documentation

- **ARCHITECTURE.md**: System architecture, data flow, Docker setup
- **BACKTEST_SPEC.md**: Complete CLI reference, JSON schema, strategy logic
- **FRONTEND_UI_SPEC.md**: Frontend component architecture, UI patterns
- **FUSE_SETUP.md**: GCS FUSE integration guide

## Development

### Local Setup (Without Docker)

The project is now a Python package, so you can install it locally with `pip install -e .` instead of manually setting PYTHONPATH.

#### Prerequisites

- Python 3.13+
- pip

#### Installation

```bash
# Install unified-cloud-services first (if you have a local copy)
# Option 1: From local copy
pip install -e external/unified-cloud-services

# Option 2: From GitHub (requires GITHUB_TOKEN for private repos)
pip install "git+https://${GITHUB_TOKEN}@github.com/IggyIkenna/unified-cloud-services.git"

# Install execution-services package in editable mode
pip install -e .

# This installs all dependencies and makes 'backend' importable
# No need to set PYTHONPATH manually!
```

#### Running Locally

```bash
# Run CLI (using the installed entry point)
run-backtest --help

# Or run directly
python -m backend.run_backtest --help

# Run API server
python -m uvicorn backend.api.server:app --reload
```

### Backend (Docker)

The Dockerfile now uses `pip install -e .` instead of setting PYTHONPATH, making it consistent with local development.

### Frontend

```bash
# Install dependencies
cd frontend
npm install

# Development server
npm run dev

# Production build
npm run build
```

## Troubleshooting

### Services Not Starting

```bash
# Rebuild containers
docker-compose up -d --build

# Check logs
docker-compose logs backend
docker-compose logs frontend
```

### No Data Found

1. Verify data files exist: `ls data_downloads/raw_tick_data/by_date/`
2. Check config paths match actual file locations
3. Verify time window matches data availability
4. Check backend logs for validation errors

### Catalog Issues

```bash
# Clear catalog and reconvert
rm -rf backend/data/parquet/*
# Next backtest run will reconvert data
```

## Best Practices

- Use fast mode for quick validation
- Use report mode for detailed analysis
- Keep config files version-controlled
- Monitor disk space (catalog data can grow large)
- Use wildcard paths in configs for auto-discovery across date folders

## License

MIT
