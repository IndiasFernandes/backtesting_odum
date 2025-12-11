#!/bin/bash
# Test backtest with GCS data source for May 25, 2023

set -e

echo "🧪 Testing Backtest with GCS Data Source"
echo "=========================================="
echo ""

# Set environment variables
export DATA_SOURCE="gcs"
export UNIFIED_CLOUD_SERVICES_GCS_BUCKET="${UNIFIED_CLOUD_SERVICES_GCS_BUCKET:-market-data-tick-cefi-central-element-323112}"

echo "📋 Configuration:"
echo "   Data Source: GCS"
echo "   GCS Bucket: ${UNIFIED_CLOUD_SERVICES_GCS_BUCKET}"
echo "   Date: 2023-05-25"
echo "   Instrument: BTC-USDT.BINANCE"
echo "   Time Window: 2023-05-25T02:00:00Z to 2023-05-25T02:05:00Z (5 minutes)"
echo ""

# Run backtest
docker-compose exec backend python3 -m backend.run_backtest \
    --instrument "BTC-USDT.BINANCE" \
    --config "external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json" \
    --start "2023-05-25T02:00:00Z" \
    --end "2023-05-25T02:05:00Z" \
    --snapshot_mode "trades" \
    --data_source "gcs" \
    --fast

echo ""
echo "✅ Backtest completed!"

