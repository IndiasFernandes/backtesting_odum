# Quick Test Commands - Copy & Paste Ready

## UI Test (Recommended First)

1. Open the UI in your browser
2. The form is pre-filled with:
   - Instrument: `BTCUSDT`
   - Dataset: `day-2023-05-23`
   - Config: `binance_futures_btcusdt_l2_trades_config.json`
   - Start: `2023-05-23T02:00`
   - End: `2023-05-23T02:05`
   - Report Mode: ✓ Checked
   - Snapshot Mode: `both`

3. Click "Run Backtest" and watch the logs

---

## CLI Test Commands (Copy & Paste)

### Test 1: Full Report Mode (5 minutes)
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

### Test 2: Fast Mode (Quick Test)
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

### Test 3: With Tick Export
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

---

## Expected Output

You should see output like:
```
Status: Validating data availability...
Status: ✓ Found 1 trade file(s) with data
Status: Creating and registering instrument in catalog...
Status: ✓ Instrument registered successfully
Status: Building data configuration...
Status: Converting and registering trades...
Status: ✓ Registered X trades to catalog
Status: Starting backtest execution...
Status: ✓ Backtest execution complete

Run ID: BNF_BTC_20230523_020000_018dd7_xxxxxx
Instrument: BTCUSDT
Dataset: day-2023-05-23
Time window: 2023-05-23 02:00:00+00:00 to 2023-05-23 02:05:00+00:00

Summary:
  orders: X
  fills: X
  pnl: X.XX
```

---

## What Was Fixed

1. ✅ UI form defaults updated to 02:00-02:05 UTC (5 minutes)
2. ✅ Config file fixed: `oms_type` changed from `FUTURES` to `NETTING`
3. ✅ Report mode enabled by default
4. ✅ Test guide created

---

## Next Steps

1. Test through UI first (easiest)
2. Copy/paste CLI commands above to test via terminal
3. Verify results are saved correctly
4. Check logs for any errors

