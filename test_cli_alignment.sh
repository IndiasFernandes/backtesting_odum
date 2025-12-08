#!/bin/bash
# CLI-Frontend Alignment Test Script
# This script helps verify that CLI commands from UI produce identical results
#
# Usage:
#   ./test_cli_alignment.sh [fast|report]
#
# Examples:
#   ./test_cli_alignment.sh fast      # Test fast mode
#   ./test_cli_alignment.sh report    # Test report mode (default)
#   ./test_cli_alignment.sh           # Test report mode

set -e

MODE=${1:-report}

echo "========================================="
echo "CLI-Frontend Alignment Test"
echo "Mode: $MODE"
echo "========================================="
echo ""

# Test configuration (matches UI example)
INSTRUMENT="BTCUSDT"
DATASET="day-2023-05-23"
CONFIG="external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json"
START="2023-05-23T19:23:00Z"
END="2023-05-23T19:28:00Z"
SNAPSHOT_MODE="both"

if [ "$MODE" = "fast" ]; then
    FAST_MODE="--fast"
    REPORT_MODE=""
    EXPORT_TICKS=""
    OUTPUT_DIR="fast"
else
    FAST_MODE=""
    REPORT_MODE="--report"
    EXPORT_TICKS="--export_ticks"
    OUTPUT_DIR="report"
fi

echo "Test Configuration:"
echo "  Instrument: $INSTRUMENT"
echo "  Dataset: $DATASET"
echo "  Config: $CONFIG"
echo "  Start: $START"
echo "  End: $END"
echo "  Snapshot Mode: $SNAPSHOT_MODE"
echo "  Mode: $MODE"
echo ""

# Build CLI command
CLI_CMD="python backend/run_backtest.py \\
  --instrument $INSTRUMENT \\
  --dataset $DATASET \\
  --config $CONFIG \\
  --start $START \\
  --end $END \\
  --snapshot_mode $SNAPSHOT_MODE"

if [ -n "$FAST_MODE" ]; then
    CLI_CMD="$CLI_CMD $FAST_MODE"
fi

if [ -n "$REPORT_MODE" ]; then
    CLI_CMD="$CLI_CMD $REPORT_MODE"
fi

if [ -n "$EXPORT_TICKS" ]; then
    CLI_CMD="$CLI_CMD $EXPORT_TICKS"
fi

echo "CLI Command:"
echo "$CLI_CMD"
echo ""

# Check if running in Docker
if [ -f "docker-compose.yml" ]; then
    echo "Executing CLI command in Docker container..."
    echo ""
    
    # Execute command and capture output
    OUTPUT=$(docker-compose exec -T backend bash -c "cd /app && $CLI_CMD" 2>&1)
    echo "$OUTPUT"
    
    # Extract run_id from output
    RUN_ID=$(echo "$OUTPUT" | grep -oP 'Run ID: \K[^\s]+' | head -1 || echo "")
    
    echo ""
    echo "========================================="
    echo "Test Complete"
    echo "========================================="
    echo ""
    
    if [ -n "$RUN_ID" ]; then
        echo "Run ID: $RUN_ID"
        echo ""
        echo "Result file location:"
        if [ "$MODE" = "fast" ]; then
            echo "  backend/backtest_results/fast/${RUN_ID}.json"
        else
            echo "  backend/backtest_results/report/${RUN_ID}/summary.json"
        fi
        echo ""
    fi
    
    echo "Next steps for alignment verification:"
    echo "1. Copy the CLI command above"
    echo "2. Navigate to http://localhost:5173/run"
    echo "3. Fill the form with the same values:"
    echo "   - Instrument: $INSTRUMENT"
    echo "   - Dataset: $DATASET"
    echo "   - Config: binance_futures_btcusdt_l2_trades_config.json"
    echo "   - Start: 2023-05-23T19:23"
    echo "   - End: 2023-05-23T19:28"
    echo "   - Snapshot Mode: $SNAPSHOT_MODE"
    if [ "$MODE" = "fast" ]; then
        echo "   - Fast Mode: ✓"
    else
        echo "   - Report Mode: ✓"
        echo "   - Export Ticks: ✓"
    fi
    echo "4. Verify CLI preview matches the command above"
    echo "5. Run backtest via UI"
    echo "6. Compare results:"
    echo "   - Both should have identical summary metrics"
    echo "   - Only run_id should differ (timestamp-based)"
    echo "7. Verify both results appear in comparison page"
    echo ""
    echo "Expected: Results should match (except for run_id timestamp)"
else
    echo "Not in Docker environment. Execute manually:"
    echo ""
    echo "$CLI_CMD"
    echo ""
    echo "Or run in Docker:"
    echo "docker-compose exec backend bash -c \"cd /app && $CLI_CMD\""
fi

