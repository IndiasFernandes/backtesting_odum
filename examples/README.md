# Nautilus Trader: TradFi, Sports, and DeFi Example Files

This directory contains example implementations for integrating Traditional Finance (TradFi), Sports, and Decentralized Finance (DeFi) data into Nautilus Trader for backtesting.

## Directory Structure

```
examples/
├── tradfi/
│   ├── tradfi_data_types.py          # TradFi custom data type definitions
│   ├── tradfi_data_generator.py      # Script to generate sample TradFi data
│   ├── tradfi_integration_example.py # Example integration code
│   └── tradfi_sample.parquet         # Generated sample Parquet file
├── sports/
│   ├── sports_data_types.py          # Sports custom data type definitions
│   ├── sports_data_generator.py      # Script to generate sample Sports data
│   ├── sports_integration_example.py # Example integration code
│   └── sports_sample.parquet         # Generated sample Parquet file
└── defi/
    ├── defi_data_types.py            # DeFi custom data type definitions
    ├── defi_data_generator.py        # Script to generate sample DeFi data
    ├── defi_integration_example.py   # Example integration code
    └── defi_sample.parquet           # Generated sample Parquet file
```

## Quick Start

### 1. Generate Sample Data

Generate sample Parquet files for each data type:

```bash
# TradFi data
cd tradfi
python tradfi_data_generator.py

# Sports data
cd ../sports
python sports_data_generator.py

# DeFi data
cd ../defi
python defi_data_generator.py
```

### 2. Test Integration

Run the integration examples to verify data loading and querying:

```bash
# TradFi integration
cd tradfi
python tradfi_integration_example.py

# Sports integration
cd ../sports
python sports_integration_example.py

# DeFi integration
cd ../defi
python defi_integration_example.py
```

## Data Types

### TradFi Data Types

- **TradFiOHLCV**: OHLCV bar data for stocks, forex, etc.
- **TradFiCorporateAction**: Corporate actions (dividends, splits, etc.)

### Sports Data Types

- **SportsEvent**: Sports event data (games, scores, etc.)
- **BettingOdds**: Betting odds and implied probabilities

### DeFi Data Types

- **DeFiSwap**: DEX swap transactions
- **LiquidityPool**: Liquidity pool state snapshots

## Usage in Backtests

### Step 1: Import Data Types

```python
from tradfi.tradfi_data_types import TradFiOHLCV
from sports.sports_data_types import SportsEvent
from defi.defi_data_types import DeFiSwap
```

### Step 2: Register with Catalog

Data types are automatically registered when imported (via `register_arrow`).

### Step 3: Load Data into Catalog

```python
from nautilus_trader.persistence.catalog import ParquetDataCatalog
import pyarrow.parquet as pq

catalog = ParquetDataCatalog("./data/parquet")

# Load TradFi data
table = pq.read_table("tradfi/tradfi_sample.parquet")
data_objects = TradFiOHLCV.from_catalog(table)
catalog.write_data(data_objects)
```

### Step 4: Configure Backtest

```python
from nautilus_trader.config import BacktestDataConfig

tradfi_config = BacktestDataConfig(
    catalog_path=str(catalog.path),
    data_cls=TradFiOHLCV,
    metadata={"exchange": "NASDAQ"},
)
```

### Step 5: Subscribe in Strategy

```python
from nautilus_trader.model.data import DataType
from nautilus_trader.trading.strategy import Strategy

class MyStrategy(Strategy):
    def on_start(self):
        self.subscribe_data(
            DataType(TradFiOHLCV, metadata={"exchange": "NASDAQ"}),
        )
    
    def on_data(self, data):
        if isinstance(data, TradFiOHLCV):
            # Process TradFi data
            pass
```

## Requirements

- Python 3.10+
- nautilus-trader
- pyarrow
- pandas
- numpy

Install dependencies:

```bash
pip install nautilus-trader pyarrow pandas numpy
```

## File Formats

All sample data files are in Parquet format with:
- Compression: ZSTD
- Timestamps: Nanoseconds since epoch (int64)
- Schema: Defined by Arrow schemas in data type classes

## Notes

- Sample data is generated with realistic but synthetic values
- Timestamps are in nanoseconds (required by Nautilus Trader)
- Data must be sorted by `ts_init` before writing to catalog
- Custom data types must inherit from `Data` base class
- Arrow schemas must match data structure exactly

## See Also

- [Main Integration Guide](../NAUTILUS_TRADFI_SPORTS_DEFI_INTEGRATION.md)
- [Nautilus Trader Documentation](https://nautilustrader.io/docs/latest/)

