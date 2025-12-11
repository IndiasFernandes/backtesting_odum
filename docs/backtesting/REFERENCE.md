# Technical Reference - NautilusTrader Backtest System

This document consolidates essential technical references for understanding and working with the backtesting system.

## Data Conversion & Parquet Schema

### Automatic Conversion Process

**The system automatically converts raw Parquet files to catalog format on first backtest run.**

1. **Raw Data Location**: `data_downloads/raw_tick_data/by_date/day-YYYY-MM-DD/data_type-trades/` and `data_type-book_snapshot_5/`
2. **Conversion Check**: System checks if data exists in catalog before converting
3. **Schema Support**: Handles multiple Parquet schemas:
   - NautilusTrader format (direct): `ts_event`, `ts_init`, `price`, `size`, `aggressor_side`, `trade_id`
   - Common exchange format: `timestamp`, `local_timestamp`, `price`, `amount`, `side`, `id`
4. **Catalog Storage**: Converted data stored in `backend/data/parquet/data/trade_tick/<instrument_id>/`
5. **Caching**: Subsequent runs use cached catalog data (faster)

### Required Parquet Schema (for direct catalog use)

**TradeTick:**
- `ts_event`: int64 (nanoseconds)
- `ts_init`: int64 (nanoseconds)
- `instrument_id`: string (`SYMBOL.VENUE` format)
- `price`: float64
- `size`: float64
- `aggressor_side`: string (`"BUY"`, `"SELL"`, `"AGGRESSOR_BUY"`, `"AGGRESSOR_SELL"`)
- `trade_id`: string

**OrderBookDeltas:**
- Complex nested structure (typically requires conversion via NautilusTrader API)
- See `backend/data_converter.py` for conversion implementation

### Conversion Implementation

The `DataConverter` class (`backend/data_converter.py`) handles:
- Timestamp conversion (microseconds/milliseconds → nanoseconds)
- Column mapping (e.g., `timestamp` → `ts_event`, `side` → `aggressor_side`)
- Batch processing (10,000 rows at a time)
- Skip-if-exists optimization (checks catalog before converting)

## PnL Calculation (NETTING OMS)

### Primary Method: Position Snapshots

**CRITICAL for NETTING OMS** - Positions can flip direction without fully closing.

```python
# Step 1: Aggregate realized PnL from CURRENT positions
current_positions = cache.positions(instrument_id=instrument_id)
for position in current_positions:
    if position.realized_pnl:
        realized_pnl += float(position.realized_pnl.as_decimal())

# Step 2: Aggregate realized PnL from HISTORICAL SNAPSHOTS
# This captures PnL from closed cycles when positions flip direction
all_positions = cache.positions(instrument_id=instrument_id)
position_ids = [pos.id for pos in all_positions]
for position_id in position_ids:
    snapshots = cache.position_snapshots(position_id=position_id)
    for snapshot in snapshots:
        if snapshot.realized_pnl:
            realized_pnl += float(snapshot.realized_pnl.as_double())
```

**Why This Matters:**
- NETTING OMS positions flip direction (LONG → SHORT) without fully closing
- Each flip creates a new cycle with its own realized PnL
- Snapshots preserve realized PnL from all closed cycles
- Without snapshots, you miss realized PnL from intermediate cycles

### Commission Calculation

**Primary Method**: `position.commissions()`
```python
for position in cache.positions(instrument_id=instrument_id):
    position_commissions = position.commissions()  # Returns list[Money]
    for comm_money in position_commissions:
        if comm_money.currency == base_currency_obj:
            commissions += float(comm_money.as_decimal())
```

**Fallback Methods**:
1. Parse `commissions` column from `generate_order_fills_report()` DataFrame
2. Calculate from balance difference: `commissions = (realized + unrealized) - total_pnl`

**Important**: Commissions are always positive (costs), included in account balance change.

### Unrealized PnL

```python
current_price = cache.price(instrument_id, PriceType.LAST)
unrealized_pnl = position.unrealized_pnl(current_price)  # Money object
```

### Position Closing

When `close_positions=True` (default):
- Unrealized PnL is realized at end of backtest
- `unrealized_before_closing` stored for transparency
- Final PnL reflects closed positions only

## Implementation Verification

### Verified Against NautilusTrader Documentation

✅ **PnL Calculation**: Position Snapshots (PRIMARY) matches NETTING OMS best practices  
✅ **Commission Calculation**: `position.commissions()` (PRIMARY) - recommended by docs  
✅ **Position Closing**: Mathematically correct approach  
✅ **Unrealized PnL**: Using `position.unrealized_pnl(current_price)` - official method  

### Current Implementation Status

**Working Features**:
- ✅ Automatic data conversion and catalog registration
- ✅ Fast mode (minimal JSON summary)
- ✅ Report mode (full timeline, orders, metadata)
- ✅ Status updates during execution
- ✅ Data validation before execution
- ✅ Run ID generation (short, readable format)
- ✅ Frontend UI (3 pages: Run, Compare, Definitions)
- ✅ REST API endpoints
- ✅ Position closing at end of backtest
- ✅ Comprehensive PnL breakdown
- ✅ Trade statistics (including position cycles)

**Pending Features**:
- Charts in frontend (tick graph, timeline chart)
- Performance optimizations (virtualization, Web Workers)
- Export ticks functionality (code exists, needs testing)

## Testing Quick Reference

### Verify Services

```bash
docker-compose ps
curl http://localhost:8000/api/health
curl http://localhost:8000/api/datasets
curl http://localhost:8000/api/configs
```

### Run Backtest

**Via UI**: http://localhost:5173/run (form pre-filled with example)

**Via API**:
```bash
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "instrument": "BTCUSDT",
    "dataset": "day-2023-05-23",
    "config": "binance_futures_btcusdt_l2_trades_config.json",
    "start": "2023-05-23T19:23:00Z",
    "end": "2023-05-23T19:28:00Z",
    "fast": true,
    "snapshot_mode": "both"
  }'
```

### Check Results

- **UI**: http://localhost:5173/compare
- **Files**: `backend/backtest_results/fast/` and `backend/backtest_results/report/`
- **API**: `curl http://localhost:8000/api/backtest/results`

### Watch Logs

```bash
docker-compose logs -f backend
```

Expected status messages:
- `Status: Validating data availability...`
- `Status: ✓ Registered XXXX trades to catalog`
- `Status: Executing backtest engine...`
- `Status: ✓ Performance evaluation complete`

## Troubleshooting

### No Data Found

1. Verify files exist: `ls data_downloads/raw_tick_data/by_date/`
2. Check config paths match actual file locations
3. Verify time window matches data availability
4. Check backend logs for validation errors

### Catalog Issues

```bash
# Clear catalog and reconvert
rm -rf backend/data/parquet/*
# Next backtest run will reconvert data
```

### Services Not Starting

```bash
docker-compose up -d --build
docker-compose logs backend
docker-compose logs frontend
```

## References

- [NautilusTrader Backtesting Documentation](https://nautilustrader.io/docs/latest/concepts/backtesting/)
- [NautilusTrader Positions Documentation](https://nautilustrader.io/docs/latest/concepts/positions/)
- [NautilusTrader Portfolio Documentation](https://nautilustrader.io/docs/latest/concepts/portfolio/)
- [NautilusTrader Reports Documentation](https://nautilustrader.io/docs/latest/concepts/reports/)

