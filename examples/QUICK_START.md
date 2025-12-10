# Quick Start: TradFi, Sports, and DeFi Integration

## Overview

This guide provides everything you need to integrate TradFi, Sports, and DeFi data into Nautilus Trader for backtesting.

## What's Included

### 📁 Directory Structure

```
examples/
├── tradfi/          # Traditional Finance examples
├── sports/          # Sports betting examples  
└── defi/            # Decentralized Finance examples
```

Each directory contains:
- `*_data_types.py` - Custom data type definitions
- `*_data_generator.py` - Scripts to generate sample Parquet files
- `*_integration_example.py` - Integration examples
- `*_sample.parquet` - Generated sample data files

## Quick Start (5 Minutes)

### Step 1: Install Dependencies

```bash
pip install nautilus-trader pyarrow pandas numpy
```

### Step 2: Generate Sample Data

```bash
# TradFi
cd examples/tradfi
python tradfi_data_generator.py

# Sports
cd ../sports
python sports_data_generator.py

# DeFi
cd ../defi
python defi_data_generator.py
```

This creates sample Parquet files you can use immediately.

### Step 3: Test Integration

```bash
# Test TradFi
cd examples/tradfi
python tradfi_integration_example.py

# Test Sports
cd ../sports
python sports_integration_example.py

# Test DeFi
cd ../defi
python defi_integration_example.py
```

## Key Requirements

### 1. Data Format
- ✅ Parquet format (columnar, compressed)
- ✅ Nanosecond timestamps (`ts_event`, `ts_init`)
- ✅ Sorted by `ts_init` chronologically

### 2. Custom Data Types
- ✅ Inherit from `Data` base class
- ✅ Implement `ts_event` and `ts_init` properties
- ✅ Register with Arrow schema using `register_arrow`

### 3. Integration Steps
1. Define custom data class
2. Register Arrow schema
3. Convert data to Parquet
4. Write to `ParquetDataCatalog`
5. Configure `BacktestDataConfig`
6. Subscribe in strategy

## Data Types Provided

### TradFi
- **TradFiOHLCV**: OHLCV bars (stocks, forex, etc.)
- **TradFiCorporateAction**: Dividends, splits, etc.

### Sports
- **SportsEvent**: Game schedules, scores, results
- **BettingOdds**: Odds movements, implied probabilities

### DeFi
- **DeFiSwap**: DEX swap transactions
- **LiquidityPool**: Pool state snapshots (reserves, TVL, etc.)

## Example Usage

### In a Strategy

```python
from nautilus_trader.model.data import DataType
from tradfi.tradfi_data_types import TradFiOHLCV

class MyStrategy(Strategy):
    def on_start(self):
        # Subscribe to TradFi data
        self.subscribe_data(
            DataType(TradFiOHLCV, metadata={"exchange": "NASDAQ"}),
        )
    
    def on_data(self, data):
        if isinstance(data, TradFiOHLCV):
            # Process TradFi OHLCV data
            print(f"Price: {data.close}, Volume: {data.volume}")
```

### Loading Data into Catalog

```python
from nautilus_trader.persistence.catalog import ParquetDataCatalog
import pyarrow.parquet as pq
from tradfi.tradfi_data_types import TradFiOHLCV

# Initialize catalog
catalog = ParquetDataCatalog("./data/parquet")

# Load Parquet file
table = pq.read_table("examples/tradfi/tradfi_sample.parquet")
data_objects = TradFiOHLCV.from_catalog(table)

# Write to catalog
catalog.write_data(data_objects)
```

### Querying Data

```python
# Query TradFi data
ohlcv_data = catalog.query(
    data_cls=TradFiOHLCV,
    start="2024-01-01",
    end="2024-12-31",
    where="exchange == 'NASDAQ'",
)
```

## Next Steps

1. **Read the Full Guide**: See `NAUTILUS_TRADFI_SPORTS_DEFI_INTEGRATION.md`
2. **Customize Data Types**: Modify the data type classes for your needs
3. **Generate Real Data**: Replace sample generators with real data sources
4. **Build Strategies**: Create strategies using the custom data types

## Troubleshooting

### Import Errors
- Ensure `nautilus-trader` is installed: `pip install nautilus-trader`
- Check Python version (3.10+ required)

### Timestamp Errors
- Ensure timestamps are in nanoseconds: `nanoseconds = microseconds * 1000`
- Verify data is sorted by `ts_init`

### Schema Errors
- Ensure Arrow schema matches data structure exactly
- Check field types (int64, float64, string, etc.)

## Resources

- [Main Integration Guide](../NAUTILUS_TRADFI_SPORTS_DEFI_INTEGRATION.md)
- [Nautilus Trader Docs](https://nautilustrader.io/docs/latest/)
- [Examples README](README.md)

## Support

For issues or questions:
1. Check the main integration guide
2. Review example code in each directory
3. Consult Nautilus Trader documentation

