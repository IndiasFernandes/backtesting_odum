#!/bin/bash
# Quick test script to compare execution algorithms

CONFIG="external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json"
START="2023-05-24T05:00:00Z"
END="2023-05-24T05:05:00Z"

echo "=========================================="
echo "Testing Execution Algorithms"
echo "=========================================="
echo ""

echo "1. Testing NORMAL (Market Orders)..."
docker-compose exec -T backend python3 backend/run_backtest.py \
  --instrument BTCUSDT \
  --config "$CONFIG" \
  --start "$START" \
  --end "$END" \
  --exec_algorithm NORMAL \
  --fast > /tmp/normal_result.json 2>&1

if [ $? -eq 0 ]; then
    echo "✓ NORMAL completed"
    NORMAL_ORDERS=$(grep -o '"orders": [0-9]*' /tmp/normal_result.json | head -1 | grep -o '[0-9]*')
    NORMAL_FILLS=$(grep -o '"fills": [0-9]*' /tmp/normal_result.json | head -1 | grep -o '[0-9]*')
    NORMAL_PNL=$(grep -o '"pnl": [-0-9.]*' /tmp/normal_result.json | head -1 | grep -o '[-0-9.]*')
    echo "  Orders: $NORMAL_ORDERS, Fills: $NORMAL_FILLS, P&L: $NORMAL_PNL"
else
    echo "✗ NORMAL failed"
fi

echo ""
echo "2. Testing TWAP..."
docker-compose exec -T backend python3 backend/run_backtest.py \
  --instrument BTCUSDT \
  --config "$CONFIG" \
  --start "$START" \
  --end "$END" \
  --exec_algorithm TWAP \
  --exec_algorithm_params '{"horizon_secs": 60, "interval_secs": 10}' \
  --fast > /tmp/twap_result.json 2>&1

if [ $? -eq 0 ]; then
    echo "✓ TWAP completed"
    TWAP_ORDERS=$(grep -o '"orders": [0-9]*' /tmp/twap_result.json | head -1 | grep -o '[0-9]*')
    TWAP_FILLS=$(grep -o '"fills": [0-9]*' /tmp/twap_result.json | head -1 | grep -o '[0-9]*')
    TWAP_PNL=$(grep -o '"pnl": [-0-9.]*' /tmp/twap_result.json | head -1 | grep -o '[-0-9.]*')
    echo "  Orders: $TWAP_ORDERS, Fills: $TWAP_FILLS, P&L: $TWAP_PNL"
else
    echo "✗ TWAP failed"
    tail -20 /tmp/twap_result.json
fi

echo ""
echo "3. Testing VWAP..."
docker-compose exec -T backend python3 backend/run_backtest.py \
  --instrument BTCUSDT \
  --config "$CONFIG" \
  --start "$START" \
  --end "$END" \
  --exec_algorithm VWAP \
  --exec_algorithm_params '{"horizon_secs": 60, "intervals": 6}' \
  --fast > /tmp/vwap_result.json 2>&1

if [ $? -eq 0 ]; then
    echo "✓ VWAP completed"
    VWAP_ORDERS=$(grep -o '"orders": [0-9]*' /tmp/vwap_result.json | head -1 | grep -o '[0-9]*')
    VWAP_FILLS=$(grep -o '"fills": [0-9]*' /tmp/vwap_result.json | head -1 | grep -o '[0-9]*')
    VWAP_PNL=$(grep -o '"pnl": [-0-9.]*' /tmp/vwap_result.json | head -1 | grep -o '[-0-9.]*')
    echo "  Orders: $VWAP_ORDERS, Fills: $VWAP_FILLS, P&L: $VWAP_PNL"
else
    echo "✗ VWAP failed"
    tail -20 /tmp/vwap_result.json
fi

echo ""
echo "=========================================="
echo "Comparison Summary"
echo "=========================================="
echo "Algorithm | Orders | Fills  | P&L"
echo "----------|--------|--------|--------"
echo "NORMAL    | $NORMAL_ORDERS | $NORMAL_FILLS | $NORMAL_PNL"
echo "TWAP      | $TWAP_ORDERS | $TWAP_FILLS | $TWAP_PNL"
echo "VWAP      | $VWAP_ORDERS | $VWAP_FILLS | $VWAP_PNL"
echo ""

