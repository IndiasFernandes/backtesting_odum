#!/bin/bash
# CLI-Frontend Alignment Test Script
# This script helps verify that CLI commands from UI produce identical results

set -e

echo "========================================="
echo "CLI-Frontend Alignment Test"
echo "========================================="
echo ""

# Test configuration (matches UI example)
INSTRUMENT="BTCUSDT"
DATASET="day-2023-05-23"
CONFIG="external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json"
START="2023-05-23T19:23:00Z"
END="2023-05-23T19:28:00Z"
SNAPSHOT_MODE="both"
FAST_MODE=""
REPORT_MODE="--report"
EXPORT_TICKS="--export_ticks"

echo "Test Configuration:"
echo "  Instrument: $INSTRUMENT"
echo "  Dataset: $DATASET"
echo "  Config: $CONFIG"
echo "  Start: $START"
echo "  End: $END"
echo "  Snapshot Mode: $SNAPSHOT_MODE"
echo "  Mode: Report with Export Ticks"
echo ""

# Build CLI command
CLI_CMD="python backend/run_backtest.py \\
  --instrument $INSTRUMENT \\
  --dataset $DATASET \\
  --config $CONFIG \\
  --start $START \\
  --end $END \\
  --snapshot_mode $SNAPSHOT_MODE \\
  $REPORT_MODE \\
  $EXPORT_TICKS"

echo "CLI Command:"
echo "$CLI_CMD"
echo ""

# Check if running in Docker
if [ -f "docker-compose.yml" ]; then
    echo "Executing CLI command in Docker container..."
    docker-compose exec -T backend bash -c "cd /app && $CLI_CMD"
    
    echo ""
    echo "========================================="
    echo "Test Complete"
    echo "========================================="
    echo ""
    echo "Next steps:"
    echo "1. Note the run_id from the CLI output"
    echo "2. Run the same backtest via UI at http://localhost:5173/run"
    echo "3. Compare the two result JSON files:"
    echo "   - CLI result: backend/backtest_results/report/<run_id>/summary.json"
    echo "   - UI result: backend/backtest_results/report/<run_id>/summary.json"
    echo "4. Verify both results appear in comparison page"
    echo ""
    echo "Expected: Results should match (except for run_id timestamp)"
else
    echo "Not in Docker environment. Execute manually:"
    echo "$CLI_CMD"
fi

