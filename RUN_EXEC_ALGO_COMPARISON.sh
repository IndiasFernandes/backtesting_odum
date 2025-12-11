#!/bin/bash
# Script to run execution algorithm comparison tests
# Usage: ./RUN_EXEC_ALGO_COMPARISON.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Execution Algorithm Comparison Test"
echo "=========================================="
echo ""
echo "Running 4 backtests on May 24, 2023 05:00-05:05"
echo "Algorithms: NORMAL, TWAP, VWAP, ICEBERG"
echo ""

# Run comparison script
python3 backend/scripts/compare_exec_algorithms.py \
    temp_may24_config.json \
    BTCUSDT \
    2023-05-24T05:00:00Z \
    2023-05-24T05:05:00Z

echo ""
echo "=========================================="
echo "Comparison complete!"
echo "=========================================="

