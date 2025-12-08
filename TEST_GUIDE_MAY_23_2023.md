# Backtest Testing Guide - May 23, 2023 (5 Minutes)

## Overview
This guide provides instructions for testing backtests on May 23, 2023 with a 5-minute window (02:00:00 to 02:05:00 UTC).

## Test Configuration

### UI Test (Recommended First)
1. **Open the UI**: Navigate to the backtest runner page
2. **Form is pre-filled with**:
   - Instrument: `BTCUSDT`
   - Dataset: `day-2023-05-23`
   - Config: `binance_futures_btcusdt_l2_trades_config.json`
   - Start Time: `2023-05-23T02:00` (UTC)
   - End Time: `2023-05-23T02:05` (UTC)
   - Mode: Report Mode (checked)
   - Snapshot Mode: `both`

3. **Click "Run Backtest"** and monitor the logs

4. **Expected Results**:
   - Backtest should complete successfully
   - Should see logs showing:
     - Configuration loading
     - Data conversion/registration
     - Backtest execution
     - Results saving
   - Summary should show:
     - Orders count > 0
     - Fills count > 0
     - PnL value (can be positive or negative)
     - Other metrics

### CLI Test Commands

#### Test 1: Binance Futures BTCUSDT (5 minutes)
```bash
python backend/run_backtest.py \
  --instrument BTCUSDT \
  --dataset day-2023-05-23 \
  --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \
  --start 2023-05-23T02:00:00Z \
  --end 2023-05-23T02:05:00Z \
  --report \
  --snapshot_mode both
```

#### Test 2: Fast Mode (Quick Test)
```bash
python backend/run_backtest.py \
  --instrument BTCUSDT \
  --dataset day-2023-05-23 \
  --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \
  --start 2023-05-23T02:00:00Z \
  --end 2023-05-23T02:05:00Z \
  --fast \
  --snapshot_mode trades
```

#### Test 3: With Tick Export
```bash
python backend/run_backtest.py \
  --instrument BTCUSDT \
  --dataset day-2023-05-23 \
  --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \
  --start 2023-05-23T02:00:00Z \
  --end 2023-05-23T02:05:00Z \
  --report \
  --export_ticks \
  --snapshot_mode both
```

## Verification Checklist

After running each test, verify:

- [ ] Backtest completes without errors
- [ ] Results are saved to `backend/backtest_results/report/<run_id>/` or `backend/backtest_results/fast/`
- [ ] Summary JSON contains:
  - `run_id`: Non-empty string
  - `instrument`: "BTCUSDT"
  - `dataset`: "day-2023-05-23"
  - `start`: "2023-05-23T02:00:00Z"
  - `end`: "2023-05-23T02:05:00Z"
  - `summary.orders`: > 0
  - `summary.fills`: > 0
  - `summary.pnl`: Valid number
- [ ] Logs show successful data conversion/registration
- [ ] Logs show backtest execution progress
- [ ] No error messages in logs

## Expected Terminal Output

When running through CLI, you should see output like:

```
Status: Validating data availability...
Status: ✓ Found 1 trade file(s) with data (time window will be validated during catalog query)
Status: Creating and registering instrument in catalog...
Status: ✓ Instrument registered successfully
Status: Building data configuration and converting data to catalog...
Status: Converting and registering trades from BINANCE-FUTURES:PERPETUAL:BTC-USDT.parquet...
Status: ✓ Registered X trades from BINANCE-FUTURES:PERPETUAL:BTC-USDT.parquet to catalog
Status: ✓ Created 1 data configuration(s)
Status: Starting backtest execution...
Status: Executing backtest engine (processing ticks, this may take a while)...
Status: ✓ Backtest execution complete
Status: Extracting and analyzing results...
Status: Calculating performance metrics...
Status: Performance evaluation complete

Run ID: BNF_BTC_20230523_020000_018dd7_xxxxxx
Instrument: BTCUSDT
Dataset: day-2023-05-23
Time window: 2023-05-23 02:00:00+00:00 to 2023-05-23 02:05:00+00:00

Summary:
  orders: X
  fills: X
  pnl: X.XX
  ...

Report mode result saved to: backend/backtest_results/report/<run_id>/summary.json
```

## Troubleshooting

### If backtest fails:

1. **Check data files exist**:
   ```bash
   ls -la data_downloads/raw_tick_data/by_date/day-2023-05-23/data_type-trades/BINANCE-FUTURES:PERPETUAL:BTC-USDT.parquet
   ```

2. **Check config file exists**:
   ```bash
   ls -la external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json
   ```

3. **Check Docker is running**:
   ```bash
   docker ps
   ```

4. **Check backend logs**:
   ```bash
   docker logs <backend-container-name>
   ```

## Notes

- The config file has been updated to use `oms_type: "NETTING"` (was "FUTURES")
- UI form defaults have been updated to use 02:00-02:05 UTC window
- Report mode is enabled by default for detailed results
- Data conversion happens automatically on first run (may take time)
- Subsequent runs use cached catalog data (faster)

