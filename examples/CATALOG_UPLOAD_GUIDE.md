# Catalog Upload Guide - All Parquet Files

## ✅ Complete File Inventory

All Parquet files are now created and optimized for Nautilus Trader catalog upload.

### TradeTick Files (Direct Trading Data)

These files contain actual trade/transaction data in Nautilus Trader's native TradeTick format:

1. **tradfi_trade_ticks.parquet**
   - **Records**: 8,640 trades
   - **Instrument**: AAPL.NASDAQ
   - **Time Range**: Last 24 hours (10-second intervals)
   - **Format**: Native TradeTick format
   - **Use**: Direct backtesting with trade-driven strategies

2. **sports_trade_ticks.parquet**
   - **Records**: 1,440 betting trades
   - **Instrument**: Sports betting markets
   - **Time Range**: Last 24 hours (1-minute intervals)
   - **Format**: Native TradeTick format
   - **Use**: Backtesting sports betting strategies

3. **defi_trade_ticks.parquet**
   - **Records**: 2,880 swap transactions
   - **Instrument**: DeFi pools (USDC/WETH, USDC/USDT, USDC/WBTC)
   - **Time Range**: Last 24 hours (30-second intervals)
   - **Format**: Native TradeTick format
   - **Use**: Backtesting DeFi arbitrage/swapping strategies

### Custom Data Type Files

#### TradFi (Traditional Finance)

1. **tradfi_sample.parquet** (TradFiOHLCV)
   - **Records**: 720 hourly bars
   - **Use**: OHLCV analysis, bar-based strategies

2. **tradfi_corporate_actions_sample.parquet** (TradFiCorporateAction)
   - **Records**: 5 corporate actions
   - **Use**: Dividend/split event handling

#### Sports

1. **sports_sample.parquet** (SportsEvent)
   - **Records**: 10 sports events
   - **Use**: Event-based strategies, game outcome analysis

2. **sports_betting_odds_sample.parquet** (BettingOdds)
   - **Records**: 150 odds records
   - **Use**: Odds movement analysis, arbitrage detection

#### DeFi

1. **defi_sample.parquet** (DeFiSwap)
   - **Records**: 2,016 swap transactions
   - **Use**: Swap analysis, price impact studies

2. **defi_liquidity_pools_sample.parquet** (LiquidityPool)
   - **Records**: 504 pool snapshots
   - **Use**: Liquidity analysis, TVL tracking

## 📊 Total Statistics

- **Total Files**: 9 Parquet files
- **Total TradeTick Records**: 12,960 trades
- **Total Custom Data Records**: 3,405 records
- **Grand Total**: 16,365 records

## 🚀 Upload Methods

### Method 1: Automated Upload Script (Recommended)

Use the provided upload script to upload all files at once:

```bash
python3 examples/upload_to_catalog.py
```

This script:
- ✅ Automatically detects all Parquet files
- ✅ Handles TradeTick conversion properly
- ✅ Uploads custom data types correctly
- ✅ Uses batch writes for performance
- ✅ Provides progress feedback

### Method 2: Manual Upload (TradeTick Files)

For TradeTick files, use the DataConverter:

```python
from pathlib import Path
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.model.identifiers import InstrumentId
from backend.data_converter import DataConverter

# Initialize catalog
catalog = ParquetDataCatalog("./data/parquet")

# Upload TradFi trades
instrument_id = InstrumentId.from_str("AAPL.NASDAQ")
DataConverter.convert_trades_parquet_to_catalog(
    parquet_path=Path("examples/tradfi/tradfi_trade_ticks.parquet"),
    instrument_id=instrument_id,
    catalog=catalog,
    price_precision=2,
    size_precision=3,
)

# Upload Sports trades
instrument_id = InstrumentId.from_str("SPORTS.BETTING")
DataConverter.convert_trades_parquet_to_catalog(
    parquet_path=Path("examples/sports/sports_trade_ticks.parquet"),
    instrument_id=instrument_id,
    catalog=catalog,
)

# Upload DeFi trades
instrument_id = InstrumentId.from_str("USDC.WETH.UNISWAP")
DataConverter.convert_trades_parquet_to_catalog(
    parquet_path=Path("examples/defi/defi_trade_ticks.parquet"),
    instrument_id=instrument_id,
    catalog=catalog,
    price_precision=6,  # Higher precision for DeFi
    size_precision=3,
)
```

### Method 3: Manual Upload (Custom Data Types)

For custom data types, load directly:

```python
from pathlib import Path
from nautilus_trader.persistence.catalog import ParquetDataCatalog
import pyarrow.parquet as pq

# Import custom data types
from tradfi.tradfi_data_types import TradFiOHLCV, TradFiCorporateAction
from sports.sports_data_types import SportsEvent, BettingOdds
from defi.defi_data_types import DeFiSwap, LiquidityPool

# Initialize catalog
catalog = ParquetDataCatalog("./data/parquet")

# Upload TradFi OHLCV
table = pq.read_table("examples/tradfi/tradfi_sample.parquet")
data_objects = TradFiOHLCV.from_catalog(table)
catalog.write_data(data_objects)

# Upload Sports Events
table = pq.read_table("examples/sports/sports_sample.parquet")
data_objects = SportsEvent.from_catalog(table)
catalog.write_data(data_objects)

# Upload DeFi Swaps
table = pq.read_table("examples/defi/defi_sample.parquet")
data_objects = DeFiSwap.from_catalog(table)
catalog.write_data(data_objects)

# ... repeat for other files
```

## 📁 File Structure

```
examples/
├── tradfi/
│   ├── tradfi_trade_ticks.parquet          ✅ TradeTick format
│   ├── tradfi_sample.parquet                ✅ TradFiOHLCV
│   └── tradfi_corporate_actions_sample.parquet ✅ TradFiCorporateAction
├── sports/
│   ├── sports_trade_ticks.parquet           ✅ TradeTick format
│   ├── sports_sample.parquet                ✅ SportsEvent
│   └── sports_betting_odds_sample.parquet   ✅ BettingOdds
└── defi/
    ├── defi_trade_ticks.parquet             ✅ TradeTick format
    ├── defi_sample.parquet                  ✅ DeFiSwap
    └── defi_liquidity_pools_sample.parquet  ✅ LiquidityPool
```

## ✅ Best Practices for Catalog Upload

### 1. TradeTick Files

- ✅ **Format**: Must have `ts_event`, `ts_init`, `instrument_id`, `price`, `size`, `aggressor_side`, `trade_id`
- ✅ **Timestamps**: Nanoseconds (int64)
- ✅ **Sorting**: Data must be sorted by `ts_event` before upload
- ✅ **Precision**: Set appropriate `price_precision` and `size_precision` for each instrument
- ✅ **Batching**: Upload in batches of 10,000 for performance

### 2. Custom Data Types

- ✅ **Registration**: Data types must be registered with `register_arrow` before upload
- ✅ **Schema**: Arrow schema must match exactly
- ✅ **Methods**: Use `from_catalog()` to convert Parquet to objects
- ✅ **Batch Writing**: Use `catalog.write_data()` for efficient writes

### 3. Performance Optimization

- ✅ **Batch Size**: Write in batches of 10,000-50,000 records
- ✅ **Compression**: Files use ZSTD compression (already optimized)
- ✅ **Sorting**: Ensure data is sorted before upload
- ✅ **Caching**: Catalog caches data - subsequent queries are fast

## 🔍 Verification

After upload, verify data is in catalog:

```python
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.identifiers import InstrumentId

catalog = ParquetDataCatalog("./data/parquet")

# Query TradeTick data
instrument_id = InstrumentId.from_str("AAPL.NASDAQ")
trades = catalog.query(
    data_cls=TradeTick,
    instrument_ids=[instrument_id],
    start="2024-01-01",
    end="2024-12-31",
)

print(f"Found {len(trades)} trades for {instrument_id}")

# Query custom data
from tradfi.tradfi_data_types import TradFiOHLCV
ohlcv_data = catalog.query(
    data_cls=TradFiOHLCV,
    start="2024-01-01",
    end="2024-12-31",
)
print(f"Found {len(ohlcv_data)} OHLCV bars")
```

## 🎯 Usage in Backtests

Once uploaded, use in backtest configuration:

```python
from nautilus_trader.config import BacktestDataConfig

# Configure TradeTick data
trade_config = BacktestDataConfig(
    catalog_path=str(catalog.path),
    data_cls=TradeTick,
    instrument_ids=[InstrumentId.from_str("AAPL.NASDAQ")],
)

# Configure custom data
tradfi_config = BacktestDataConfig(
    catalog_path=str(catalog.path),
    data_cls=TradFiOHLCV,
    metadata={"exchange": "NASDAQ"},
)
```

## 📝 Summary

All files are:
- ✅ **Created**: 9 Parquet files ready for upload
- ✅ **Optimized**: Proper schemas, compression, sorting
- ✅ **Compatible**: Native Nautilus Trader format
- ✅ **Tested**: Verified schemas and row counts
- ✅ **Documented**: Complete usage examples provided

**Next Steps:**
1. Run `python3 examples/upload_to_catalog.py` to upload all files
2. Verify data in catalog using query examples
3. Configure backtests with uploaded data
4. Build strategies using TradFi, Sports, and DeFi data

