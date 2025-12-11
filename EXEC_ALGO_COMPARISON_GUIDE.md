# Execution Algorithm Comparison Guide

This guide shows how to run and compare 4 different execution algorithms on the same time window.

## Quick Start

### Option 1: Using the Comparison Script (Recommended)

```bash
# From the project root directory
python3 backend/scripts/compare_exec_algorithms.py \
    temp_may24_config.json \
    BTCUSDT \
    2023-05-24T05:00:00Z \
    2023-05-24T05:05:00Z
```

Or use the shell script:
```bash
./RUN_EXEC_ALGO_COMPARISON.sh
```

### Option 2: Using Docker

```bash
# Run comparison inside Docker container
docker-compose exec backend python3 backend/scripts/compare_exec_algorithms.py \
    temp_may24_config.json \
    BTCUSDT \
    2023-05-24T05:00:00Z \
    2023-05-24T05:05:00Z
```

### Option 3: Manual Individual Runs

Run each algorithm individually:

```bash
# 1. NORMAL (Market Orders)
python3 backend/run_backtest.py \
    --instrument BTCUSDT \
    --config temp_may24_config.json \
    --start 2023-05-24T05:00:00Z \
    --end 2023-05-24T05:05:00Z \
    --exec_algorithm NORMAL \
    --fast

# 2. TWAP
python3 backend/run_backtest.py \
    --instrument BTCUSDT \
    --config temp_may24_config.json \
    --start 2023-05-24T05:00:00Z \
    --end 2023-05-24T05:05:00Z \
    --exec_algorithm TWAP \
    --exec_algorithm_params '{"horizon_secs": 60, "interval_secs": 10}' \
    --fast

# 3. VWAP
python3 backend/run_backtest.py \
    --instrument BTCUSDT \
    --config temp_may24_config.json \
    --start 2023-05-24T05:00:00Z \
    --end 2023-05-24T05:05:00Z \
    --exec_algorithm VWAP \
    --exec_algorithm_params '{"horizon_secs": 60, "intervals": 6}' \
    --fast

# 4. ICEBERG
python3 backend/run_backtest.py \
    --instrument BTCUSDT \
    --config temp_may24_config.json \
    --start 2023-05-24T05:00:00Z \
    --end 2023-05-24T05:05:00Z \
    --exec_algorithm ICEBERG \
    --exec_algorithm_params '{"visible_pct": 0.1}' \
    --fast
```

## Execution Algorithms Being Tested

1. **NORMAL**: Regular market orders (Fill or Kill) - baseline for comparison
2. **TWAP**: Time-weighted average price - splits orders evenly over time
   - Parameters: `horizon_secs=60`, `interval_secs=10` (6 child orders over 1 minute)
3. **VWAP**: Volume-weighted average price - executes proportionally to volume
   - Parameters: `horizon_secs=60`, `intervals=6` (6 intervals over 1 minute)
4. **ICEBERG**: Shows only small visible portion, hides the rest
   - Parameters: `visible_pct=0.1` (shows 10% at a time)

## Expected Output

The comparison script will:
1. Run all 4 backtests sequentially
2. Display a comparison table showing:
   - PnL (Profit and Loss)
   - Number of orders
   - Number of fills
   - Success status
3. Save detailed results to `backend/backtest_results/exec_algorithm_comparison.json`

## Interpreting Results

Compare the following metrics across algorithms:

- **PnL**: Which algorithm achieved better execution prices?
- **Order Count**: How many orders were placed? (TWAP/VWAP/ICEBERG should create more child orders)
- **Fill Rate**: What percentage of orders were filled?
- **Execution Time**: How long did each algorithm take to execute?

## Notes

- The time window is 5 minutes (05:00-05:05), so execution algorithms with longer horizons may not complete fully
- TWAP and VWAP parameters are tuned for the 5-minute window
- Results are saved in fast mode for quicker execution
- For detailed analysis, remove `--fast` flag to get full reports

