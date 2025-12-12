#!/bin/bash
# Setup script for local development with unified-cloud-services as a package
# This installs unified-cloud-services from the parent directory (../unified-cloud-services)
# unified-cloud-services doesn't need to be copied into this repo - it's already a package

set -e  # Exit on error

echo "=========================================="
echo "Local Development Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: python3 not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python found: $(python3 --version)"
echo ""

# Check if pip is available
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    echo -e "${RED}ERROR: pip not found${NC}"
    exit 1
fi

PIP_CMD="pip3"
if ! command -v pip3 &> /dev/null; then
    PIP_CMD="pip"
fi

echo -e "${GREEN}✓${NC} pip found: $PIP_CMD"
echo ""

# Get the absolute path of execution-services directory
EXECUTION_SERVICES_DIR=$(cd "$(dirname "$0")" && pwd)

# Find unified-cloud-services (check parent directory first, then external/)
PARENT_UCS="../unified-cloud-services"
UCS_LOCAL_PATH="external/unified-cloud-services"

if [ -d "$PARENT_UCS" ]; then
    echo -e "${GREEN}✓${NC} Found unified-cloud-services in parent directory"
    UCS_PATH="$PARENT_UCS"
elif [ -d "$UCS_LOCAL_PATH" ]; then
    echo -e "${GREEN}✓${NC} Found unified-cloud-services in external/ directory"
    UCS_PATH="$UCS_LOCAL_PATH"
else
    echo -e "${RED}✗${NC} unified-cloud-services not found"
    echo "   Please ensure unified-cloud-services is available at:"
    echo "   - $PARENT_UCS (parent directory - preferred)"
    echo "   - $UCS_LOCAL_PATH (external/ directory)"
    exit 1
fi

echo ""
echo "Installing unified-cloud-services in editable mode from $UCS_PATH..."
cd "$UCS_PATH"
$PIP_CMD install -e .
cd - > /dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} unified-cloud-services installed successfully"
else
    echo -e "${RED}✗${NC} unified-cloud-services installation failed"
    exit 1
fi

echo ""
echo "Installing execution-services as a package (editable mode)..."
cd "$EXECUTION_SERVICES_DIR"
$PIP_CMD install -e .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} execution-services installed successfully"
else
    echo -e "${RED}✗${NC} execution-services installation failed"
    exit 1
fi

echo ""
echo "Installing backend dependencies..."
cd backend

# Use requirements-local.txt if it exists, otherwise use requirements.txt
if [ -f "requirements-local.txt" ]; then
    echo "Using requirements-local.txt (local development mode)"
    $PIP_CMD install -r requirements-local.txt
else
    echo "Using requirements.txt (will install unified-cloud-services from GitHub)"
    $PIP_CMD install -r requirements.txt
    # Override with local editable install
    echo "Installing unified-cloud-services from local package..."
    if [ -d "../unified-cloud-services" ]; then
        $PIP_CMD install -e ../unified-cloud-services
    elif [ -d "../external/unified-cloud-services" ]; then
        $PIP_CMD install -e ../external/unified-cloud-services
    fi
fi

cd - > /dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Backend dependencies installed successfully"
else
    echo -e "${RED}✗${NC} Backend dependencies installation failed"
    exit 1
fi

echo ""
echo "Verifying installation..."
python3 -c "from unified_cloud_services import UnifiedCloudService, CloudTarget; print('✓ unified-cloud-services imported successfully')" 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Import test passed"
else
    echo -e "${RED}✗${NC} Import test failed"
    exit 1
fi

# Get the absolute path of execution-services directory
EXECUTION_SERVICES_DIR=$(cd "$(dirname "$0")" && pwd)

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo -e "${GREEN}✓${NC} execution-services is now installed as a package"
echo ""
echo "You can now run backtests locally:"
echo ""
echo "  # Run a backtest via CLI (from anywhere)"
echo "  run-backtest \\"
echo "    --instrument BTCUSDT \\"
echo "    --dataset day-2023-05-23 \\"
echo "    --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \\"
echo "    --start 2023-05-23T02:00:00Z \\"
echo "    --end 2023-05-23T02:05:00Z \\"
echo "    --fast \\"
echo "    --snapshot_mode trades"
echo ""
echo "  # Or use Python module syntax (from execution-services root)"
echo "  python -m backend.run_backtest \\"
echo "    --instrument BTCUSDT \\"
echo "    --dataset day-2023-05-23 \\"
echo "    --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \\"
echo "    --start 2023-05-23T02:00:00Z \\"
echo "    --end 2023-05-23T02:05:00Z \\"
echo "    --fast \\"
echo "    --snapshot_mode trades"
echo ""
echo "  # Or start the API server (from execution-services root)"
echo "  python -m uvicorn backend.api.server:app --reload --host 0.0.0.0 --port 8000"
echo ""


