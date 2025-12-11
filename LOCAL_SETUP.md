# Local Development Setup Guide

This guide helps you set up execution-services to run backtests locally using unified-cloud-services as a local package.

## Quick Reference

**Services and Ports:**
- **Frontend UI**: http://localhost:5173 (React/Vite dev server)
- **Backend API**: http://localhost:8000 (FastAPI server)
- **API Documentation**: http://localhost:8000/docs (Swagger UI)

**To run locally:**
1. Start backend API: `python -m uvicorn backend.api.server:app --reload --host 0.0.0.0 --port 8000` (from execution-services root)
2. Start frontend UI: `cd frontend && npm run dev` (from execution-services root)
3. Open http://localhost:5173 in your browser

## Quick Setup

Run the setup script:

```bash
./setup_local_dev.sh
```

This script will:
1. Check for Python and pip
2. Find unified-cloud-services (checks parent directory first, then `external/`)
3. Install unified-cloud-services in editable mode
4. Install all backend dependencies
5. Verify the installation

**Note**: unified-cloud-services should be in the parent directory (`../unified-cloud-services`) - it doesn't need to be copied into this repo.

## Manual Setup

If you prefer to set up manually:

### 1. Install unified-cloud-services in editable mode

```bash
# From execution-services directory, assuming unified-cloud-services is in parent directory
cd ../unified-cloud-services
pip install -e .
cd ../execution-services
```

### 2. Install execution-services as a package

```bash
# From execution-services root directory
pip install -e .
```

### 3. Install backend dependencies

```bash
cd backend
pip install -r requirements-local.txt
cd ..
```

Or if `requirements-local.txt` doesn't exist:

```bash
cd backend
pip install -r requirements.txt
# Override with local editable install (from parent directory)
pip install -e ../unified-cloud-services
cd ..
```

### 3. Verify installation

```bash
python3 -c "from unified_cloud_services import UnifiedCloudService, CloudTarget; print('✓ Success')"
```

## Running Backtests Locally

**Important**: execution-services is now installed as a package, so you can import `backend` modules from anywhere after running the setup script.

### Via CLI Command

After installation, you can use the `run-backtest` command from anywhere:

```bash
run-backtest \
  --instrument BTCUSDT \
  --dataset day-2023-05-23 \
  --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \
  --start 2023-05-23T02:00:00Z \
  --end 2023-05-23T02:05:00Z \
  --fast \
  --snapshot_mode trades
```

**Note**: Config paths are relative to where you run the command, so you may need to adjust paths or run from the execution-services root directory.

### Via Python Module

You can also run it as a Python module (from execution-services root directory):

```bash
# Make sure you're in the execution-services root directory
cd /path/to/execution-services

# Run backtest via Python module
python -m backend.run_backtest \
  --instrument BTCUSDT \
  --dataset day-2023-05-23 \
  --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \
  --start 2023-05-23T02:00:00Z \
  --end 2023-05-23T02:05:00Z \
  --fast \
  --snapshot_mode trades
```

### Via API Server

```bash
# Make sure you're in the execution-services root directory
cd /path/to/execution-services

# Start the API server (must be run from execution-services root for file paths)
python -m uvicorn backend.api.server:app --reload --host 0.0.0.0 --port 8000
```

The API server will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Via Frontend UI

The frontend is a separate React/Vite application. To start it:

```bash
# Make sure you're in the execution-services root directory
cd /path/to/execution-services

# Install frontend dependencies (first time only)
cd frontend
npm install
cd ..

# Start the frontend development server (in a separate terminal)
cd frontend
npm run dev
```

The frontend UI will be available at:
- **Frontend UI**: http://localhost:5173

**Note**: You need both the backend API server (port 8000) and frontend dev server (port 5173) running to use the UI.

### Using the API directly (without UI)

You can also use curl to test the API:

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

## Requirements Files

- **`requirements.txt`**: For Docker/production (installs from GitHub)
- **`requirements-local.txt`**: For local development (uses local editable install)

## Troubleshooting

### unified-cloud-services not found

The setup script looks for unified-cloud-services in:
1. `../unified-cloud-services/` (parent directory - **preferred**)
2. `external/unified-cloud-services/` (fallback)

Since unified-cloud-services is already a package, it should be in the parent directory alongside execution-services. If it's in a different location, you can:

**Option 1**: Install directly from its location:
```bash
pip install -e /path/to/unified-cloud-services
```

**Option 2**: Create a symlink in the parent directory:
```bash
ln -sfn /path/to/unified-cloud-services ../unified-cloud-services
```

### ModuleNotFoundError: No module named 'backend'

This error occurs if execution-services is not installed as a package. Run the setup script:

```bash
./setup_local_dev.sh
```

This will install execution-services in editable mode, making the `backend` module available everywhere.

### Import errors

If you get import errors, make sure unified-cloud-services is installed in editable mode:

```bash
# From parent directory
pip install -e ../unified-cloud-services

# Or from unified-cloud-services directory
cd ../unified-cloud-services
pip install -e .
cd ../execution-services
```

### Python version

unified-cloud-services requires Python 3.13+. Check your version:

```bash
python3 --version
```

If you need to use a different Python version, use a virtual environment:

```bash
python3.13 -m venv venv
source venv/bin/activate
./setup_local_dev.sh
```

## Environment Variables

Set these environment variables if needed:

```bash
export UNIFIED_CLOUD_LOCAL_PATH=/path/to/data_downloads
export UNIFIED_CLOUD_SERVICES_USE_PARQUET=true
export UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=false
export DATA_CATALOG_PATH=backend/data/parquet
```

## Next Steps

- See `README.md` for full documentation
- See `BACKTEST_SPEC.md` for backtest configuration details
- See `AGENT_PROMPTS/AGENT_1_BACKTEST_TESTING.md` for testing guide
