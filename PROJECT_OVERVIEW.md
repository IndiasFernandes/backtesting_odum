# Project Overview: Odum Trader Backtest System

## Executive Summary

**Odum Trader Backtest** is a production-grade, containerized cryptocurrency backtesting system built on **NautilusTrader**. It provides a complete solution for testing trading strategies using historical market data with realistic execution simulation. The system features a modern React frontend, FastAPI backend, and is designed for cloud deployment with GCS FUSE integration.

---

## 🎯 Core Purpose

The system enables traders and developers to:
- **Backtest trading strategies** using historical cryptocurrency market data
- **Validate strategy performance** before risking real capital
- **Compare multiple backtest runs** side-by-side
- **Analyze detailed execution timelines** and order history
- **Export tick-level data** for further analysis

---

## 🏗️ System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React/Vite)                    │
│  Port: 5173 | React Router | Tailwind CSS | Recharts       │
│  - Backtest Runner Page                                     │
│  - Comparison Dashboard                                     │
│  - Definitions/Config Editor                                │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST API
┌──────────────────────▼──────────────────────────────────────┐
│              Backend API (FastAPI)                           │
│  Port: 8000 | Python 3.11 | NautilusTrader                 │
│  - REST API Endpoints                                       │
│  - Backtest Orchestration                                   │
│  - Result Management                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│          NautilusTrader Backtest Engine                     │
│  - BacktestNode (High-level API)                           │
│  - ParquetDataCatalog                                      │
│  - Trade-driven Strategy Execution                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              Data Layer (Parquet Files)                     │
│  - Raw Data: data_downloads/raw_tick_data/                 │
│  - Catalog: backend/data/parquet/                           │
│  - Results: backend/backtest_results/                       │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend:**
- **Python 3.11**
- **NautilusTrader** (>=1.220.0) - Professional-grade trading framework
- **FastAPI** - Modern async web framework
- **Pandas** - Data manipulation
- **PyArrow** - Parquet file handling
- **Pydantic** - Data validation

**Frontend:**
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **Recharts** - Data visualization
- **React Query** - Data fetching and caching
- **React Router** - Navigation

**Infrastructure:**
- **Docker** & **Docker Compose** - Containerization
- **GCS FUSE** (optional) - Cloud storage mounting
- **Redis** (optional) - Caching for batch processing

---

## 📁 Project Structure

```
data_downloads/
├── README.md                    # Main documentation
├── ARCHITECTURE.md              # System architecture details
├── BACKTEST_SPEC.md             # Complete backtest specification
├── FRONTEND_UI_SPEC.md          # Frontend component specs
├── MONETIZATION_GUIDE.md        # Strategy validation guide
├── docker-compose.yml           # Docker services configuration
│
├── backend/                     # Python backend
│   ├── run_backtest.py         # CLI entrypoint
│   ├── backtest_engine.py      # BacktestNode orchestration
│   ├── config_loader.py        # JSON config loader
│   ├── data_converter.py       # Parquet → Catalog converter
│   ├── catalog_manager.py      # Catalog management
│   ├── strategy.py             # Trade-driven strategy
│   ├── strategy_evaluator.py   # Performance analysis
│   ├── results.py              # Result serialization
│   ├── api/
│   │   ├── server.py           # FastAPI endpoints
│   │   └── mount_status.py     # GCS mount checking
│   ├── data/parquet/           # Converted catalog data
│   ├── backtest_results/       # Backtest outputs
│   │   ├── fast/               # Fast mode JSON summaries
│   │   └── report/             # Report mode directories
│   └── scripts/                # Utility scripts
│
├── frontend/                    # React frontend
│   ├── src/
│   │   ├── pages/              # Page components
│   │   │   ├── BacktestRunnerPage.tsx
│   │   │   ├── BacktestComparisonPage.tsx
│   │   │   └── DefinitionsPage.tsx
│   │   ├── components/        # Reusable components
│   │   │   ├── BacktestCharts.tsx
│   │   │   ├── ResultDetailModal.tsx
│   │   │   ├── OHLCChart.tsx
│   │   │   ├── PnLChart.tsx
│   │   │   └── Toast.tsx
│   │   ├── hooks/             # Custom hooks
│   │   │   └── useToast.ts
│   │   └── services/          # API clients
│   │       └── api.ts
│   └── public/tickdata/       # Tick JSON exports
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
└── docs/                       # Additional documentation
    ├── REFERENCE.md
    ├── DOCKER_INSTALLATION.md
    └── ...
```

---

## 🔄 Data Flow

### 1. Data Ingestion Pipeline

```
Raw Parquet Files (data_downloads/)
    ↓
Automatic Conversion (on first run)
    ↓
NautilusTrader Catalog Format (backend/data/parquet/)
    ↓
Catalog Registration
    ↓
Backtest Query (time window filtering)
```

**Key Features:**
- **Automatic conversion**: Raw Parquet files converted to NautilusTrader catalog format on first use
- **Caching**: Converted data cached for subsequent runs (faster execution)
- **Schema flexibility**: Supports multiple Parquet schemas (NautilusTrader format or common exchange format)
- **Timestamp conversion**: Handles microseconds/milliseconds → nanoseconds conversion

### 2. Backtest Execution Flow

```
1. Load JSON Configuration
    ↓
2. Initialize ParquetDataCatalog
    ↓
3. Register Instrument (CryptoPerpetual)
    ↓
4. Check/Convert Data (if needed)
    ↓
5. Build BacktestRunConfig
    ↓
6. Execute BacktestNode
    ↓
7. Collect Results
    ↓
8. Serialize Output (Fast or Report mode)
```

### 3. Result Storage

**Fast Mode:**
- Single JSON file: `backend/backtest_results/fast/<run_id>.json`
- Contains: Summary metrics (PnL, orders, fills, trades)

**Report Mode:**
- Directory: `backend/backtest_results/report/<run_id>/`
- Files:
  - `summary.json` - Performance metrics
  - `timeline.json` - Event timeline
  - `orders.json` - Complete order history
- Tick export: `frontend/public/tickdata/<run_id>.json`

---

## ⚙️ Configuration System

### External JSON Configuration

**All runtime parameters** are specified in external JSON files (nothing hardcoded):

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
    "trades_path": "raw_tick_data/by_date/day-*/data_type-trades/...",
    "book_snapshot_5_path": "raw_tick_data/by_date/day-*/data_type-book_snapshot_5/...",
    "auto_discover": true
  },
  "time_window": {
    "start": "2023-05-23T19:23:00Z",
    "end": "2023-05-23T19:28:00Z"
  },
  "strategy": {
    "name": "TempBacktestStrategy",
    "submission_mode": "per_trade_tick",
    "orders": [...]
  }
}
```

**Benefits:**
- **Reproducibility**: Same config = same results
- **Portability**: Easy to version control and share
- **GCS FUSE Ready**: Only data paths change for cloud deployment
- **No rebuilds**: Parameter changes don't require Docker rebuilds

---

## 🚀 Key Features

### 1. Trade-Driven Backtesting

- **One order per trade row** using `submission_mode="per_trade_tick"`
- Deterministic mapping between trades and orders
- No indicators or external logic (pure trade replay)

### 2. Dual Output Modes

**Fast Mode (`--fast`):**
- Minimal JSON summary
- Quick performance metrics
- No tick export
- Ideal for: Quick validation, parameter sweeps

**Report Mode (`--report`):**
- Full timeline of events
- Complete order history
- Optional tick data export
- Detailed metadata
- Ideal for: Deep analysis, stakeholder reports

### 3. Realistic Execution Simulation

- **Fill models**: Configurable fill probabilities (`prob_fill_on_limit`)
- **Slippage**: Realistic slippage simulation (`prob_slippage`)
- **Commissions**: Maker/taker fees applied
- **Position management**: Automatic position closing (configurable)

### 4. Production UI

**Backtest Runner Page:**
- Form-based backtest configuration
- Real-time status updates
- Pre-filled example values
- Comprehensive validation

**Comparison Dashboard:**
- Side-by-side result comparison
- Sortable metrics table
- Detailed result modals
- Download functionality
- Chart visualizations (PnL, OHLC, Tick prices)

**Definitions Page:**
- Config file editor
- JSON validation
- Save/load configurations

### 5. GCS FUSE Integration

- **Cloud-ready**: Designed for Google Cloud Storage FUSE mounts
- **Local development**: Works with local `data_downloads/` directory
- **Seamless migration**: Only data paths change, rest stays the same
- **Mount status API**: Check GCS mount status via `/api/mount/status`

---

## 🔌 API Endpoints

### Core Endpoints

- `GET /api/health` - Health check
- `POST /api/backtest/run` - Execute backtest
- `GET /api/backtest/results` - List all results
- `GET /api/backtest/results/{run_id}` - Get specific result
- `GET /api/backtest/results/{run_id}/stream` - Stream backtest logs
- `GET /api/datasets` - Scan available datasets
- `GET /api/configs` - List config files
- `GET /api/configs/{config_name}` - Get config content
- `POST /api/configs` - Save config file
- `GET /api/mount/status` - Check GCS mount status

### API Features

- **Async execution**: Backtests run asynchronously
- **Log streaming**: Real-time log streaming via Server-Sent Events
- **CORS enabled**: Frontend can access from any origin
- **Error handling**: Comprehensive error responses

---

## 🐳 Docker Architecture

### Services

**Backend (`nautilus-backend`):**
- Python 3.11 + NautilusTrader
- FastAPI server on port 8000
- Health checks enabled
- Volume mounts for data, results, configs

**Frontend (`nautilus-frontend`):**
- React + Vite dev server
- Port 5173
- Hot module replacement
- Proxy to backend API

**Redis (`nautilus-redis`):**
- Optional (profile: `batch-processing`)
- Port 6379
- Used for caching in batch scenarios

### Volumes

- `data_downloads/` → `/app/data_downloads` (read-only, raw data)
- `backend/data/parquet/` → `/app/backend/data/parquet` (read-write, catalog)
- `backend/backtest_results/` → `/app/backend/backtest_results` (read-write, results)
- `frontend/public/tickdata/` → `/app/frontend/public/tickdata` (read-write, tick exports)
- `external/data_downloads/configs/` → `/app/external/data_downloads/configs` (read-only, configs)

### Environment Variables

- `UNIFIED_CLOUD_LOCAL_PATH` - Base path for data (default: `/app/data_downloads`)
- `UNIFIED_CLOUD_SERVICES_USE_PARQUET` - Use Parquet format (default: `true`)
- `DATA_CATALOG_PATH` - Parquet catalog root (default: `/app/backend/data/parquet`)
- `USE_GCS_FUSE` - Enable GCS FUSE mounting (default: `false`)
- `GCS_FUSE_BUCKET` - GCS bucket name (optional)

---

## 📊 Run ID Format

Run IDs are short and readable:
```
BNF_BTC_20230523_192312_018dd7_c54988
```

**Format:** `VENUE_INSTRUMENT_DATE_TIME_CONFIGHASH_UUID`
- **Venue**: Shortened (BINANCE-FUTURES → BNF)
- **Instrument**: Shortened (BTCUSDT → BTC)
- **Date**: YYYYMMDD
- **Time**: HHMMSS + 2-digit microseconds
- **Config hash**: 6 characters (ensures config uniqueness)
- **UUID**: 6 characters (ensures run uniqueness)

---

## 🎮 Usage Examples

### Via CLI

**Fast Mode:**
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

**Report Mode:**
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

### Via API

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

### Via UI

1. Navigate to http://localhost:5173/run
2. Fill in the form (pre-filled with example values)
3. Click "Run Backtest"
4. View results at http://localhost:5173/compare

---

## 📈 Performance Characteristics

### Data Conversion

- **First run**: Automatic conversion (30-60 seconds for typical dataset)
- **Subsequent runs**: Uses cached catalog data (instant)
- **Conversion caching**: Data persists across runs

### Backtest Execution

- **Fast mode**: ~5-15 seconds for 1-minute window
- **Report mode**: ~10-30 seconds (includes timeline generation)
- **Tick export**: Adds ~5-10 seconds

### Optimization Options

1. **Data granularity**: Bars > Trades > L1 > L2 > L3 (10-100x difference)
2. **Book type**: L1_MBP > L2_MBP > L3_MBO (5-10x difference)
3. **Fill model**: Realistic fills add ~5-10% overhead
4. **Logging level**: DEBUG adds 20-50% overhead
5. **Snapshot mode**: `trades` only is ~50% faster than `both`

---

## 🔒 Validation & Quality Assurance

### Strategy Validation

The system includes a **Strategy Validator** (`backend/scripts/strategy_validator.py`) that checks:
- Overfitting detection
- Out-of-sample testing
- Walk-forward analysis
- Monte Carlo simulation
- Key performance metrics

### Data Validation

- ISO8601 timestamp validation
- Instrument precision validation
- Config schema validation
- Data file existence checks
- Time window validation

### Testing Infrastructure

- Docker infrastructure tests (`backend/scripts/test_docker_infrastructure.sh`)
- Service health checks
- CLI-frontend alignment tests (`test_cli_alignment.sh`)
- Backtest verification guides

---

## 📚 Documentation

### Core Documentation

- **README.md** - Quick start and common operations
- **ARCHITECTURE.md** - System architecture deep dive
- **BACKTEST_SPEC.md** - Complete backtest specification and CLI reference
- **FRONTEND_UI_SPEC.md** - Frontend component architecture
- **MONETIZATION_GUIDE.md** - Strategy validation and profit-making guide

### Additional Guides

- **FUSE_SETUP.md** - GCS FUSE integration guide
- **DOCKER_INSTALLATION.md** - Docker setup instructions
- **TEST_GUIDE_MAY_23_2023.md** - Testing procedures
- **CLI_ALIGNMENT_TEST_GUIDE.md** - CLI/UI alignment testing
- **docs/REFERENCE.md** - Technical reference

### Agent Documentation

- **AGENTS_QUICK_REFERENCE.md** - Quick reference for testing agents
- **SYSTEM_REVIEW_AND_AGENTS.md** - System review and agent definitions
- **AGENT_PROMPTS/** - Individual agent prompt files

---

## 🎯 Use Cases

### 1. Strategy Development

- Test new trading strategies on historical data
- Validate strategy logic before live trading
- Compare multiple strategy variants

### 2. Parameter Optimization

- Sweep parameter ranges
- Find optimal configuration
- Avoid overfitting with proper validation

### 3. Performance Analysis

- Detailed execution analysis
- Order fill analysis
- PnL attribution
- Drawdown analysis

### 4. Research & Education

- Understand market microstructure
- Study historical market behavior
- Educational tool for learning trading

### 5. Production Validation

- Final validation before live deployment
- Stress testing under various conditions
- Regulatory compliance documentation

---

## 🚦 Getting Started

### Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- 5GB free disk space
- 4GB RAM recommended
- Raw Parquet data files in `data_downloads/raw_tick_data/by_date/`

### Quick Start

```bash
# Start all services
docker-compose up -d

# View backend logs
docker-compose logs -f backend

# Access UI
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### First Backtest

1. Ensure data files exist in `data_downloads/raw_tick_data/by_date/day-2023-05-23/`
2. Open http://localhost:5173/run
3. Form is pre-filled with example values
4. Click "Run Backtest"
5. View results at http://localhost:5173/compare

---

## 🔮 Future Enhancements

### Planned Features

- **Multi-instrument backtesting**: Test strategies across multiple instruments
- **Portfolio backtesting**: Test portfolio of strategies
- **Real-time backtesting**: Live data integration
- **Advanced analytics**: More performance metrics and visualizations
- **Strategy marketplace**: Share and discover strategies
- **Cloud deployment**: Kubernetes deployment guides
- **Machine learning integration**: ML-based strategy generation

### Extensibility

The system is designed to be extensible:
- **Custom strategies**: Implement custom strategy classes
- **Custom data sources**: Add support for new data formats
- **Custom metrics**: Add custom performance metrics
- **Custom visualizations**: Extend frontend with new charts

---

## 🤝 Contributing

### Development Setup

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python backend/run_backtest.py --help
python -m uvicorn backend.api.server:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Code Organization

- **Backend**: Follow Python PEP 8 style guide
- **Frontend**: Use TypeScript strict mode, ESLint rules
- **Documentation**: Keep docs updated with code changes
- **Testing**: Add tests for new features

---

## 📝 License

MIT License

---

## 🆘 Support & Troubleshooting

### Common Issues

**Services not starting:**
```bash
docker-compose up -d --build
docker-compose logs backend
```

**No data found:**
1. Verify data files exist: `ls data_downloads/raw_tick_data/by_date/`
2. Check config paths match actual file locations
3. Verify time window matches data availability

**Catalog issues:**
```bash
# Clear catalog and reconvert
rm -rf backend/data/parquet/*
# Next backtest run will reconvert data
```

### Getting Help

- Check documentation in `docs/` directory
- Review `ARCHITECTURE.md` for system details
- Check `BACKTEST_SPEC.md` for configuration details
- Review logs: `docker-compose logs -f backend`

---

## 📊 System Statistics

- **Lines of Code**: ~15,000+ (backend + frontend)
- **Dependencies**: 20+ Python packages, 15+ npm packages
- **Test Coverage**: Infrastructure tests, validation scripts
- **Documentation**: 10+ comprehensive guides
- **API Endpoints**: 10+ REST endpoints
- **UI Pages**: 3 main pages (Runner, Comparison, Definitions)
- **Components**: 7+ reusable React components

---

## 🎓 Learning Resources

### NautilusTrader

- Official docs: https://nautilustrader.io/docs/
- Backtesting guide: https://nautilustrader.io/docs/latest/concepts/backtesting/
- High-level API: `BacktestNode` documentation

### Related Concepts

- **Backtesting**: Testing strategies on historical data
- **Walk-forward analysis**: Time-series cross-validation
- **Overfitting**: Strategy curve-fitting to noise
- **Execution simulation**: Realistic fill models
- **Market microstructure**: Order book dynamics

---

*Last Updated: 2024*
*Version: 1.0.0*

