# Nautilus Trader: TradFi, Sports, and DeFi Data Integration Guide

## Overview

This guide explains everything needed to integrate Traditional Finance (TradFi), Sports, and Decentralized Finance (DeFi) data into Nautilus Trader for backtesting.

## Table of Contents

1. [Requirements](#requirements)
2. [Data Format Requirements](#data-format-requirements)
3. [Custom Data Types](#custom-data-types)
4. [TradFi Integration](#tradfi-integration)
5. [Sports Integration](#sports-integration)
6. [DeFi Integration](#defi-integration)
7. [Backtesting Configuration](#backtesting-configuration)
8. [Example Files](#example-files)

---

## Requirements

### Core Requirements

1. **Nautilus Trader Installation**
   - Python 3.10+ with Nautilus Trader installed
   - PyArrow for Parquet file handling
   - pandas for data manipulation

2. **Data Format**
   - All data must be in **Parquet format** for efficient storage and retrieval
   - Data must include `ts_event` and `ts_init` timestamps (nanoseconds since epoch)
   - Data must be sorted chronologically by `ts_init`

3. **Custom Data Types**
   - Must inherit from Nautilus Trader's `Data` base class
   - Must implement `ts_event` and `ts_init` properties
   - Must register with Arrow schema using `register_arrow`

### Installation

```bash
pip install nautilus-trader pyarrow pandas
```

---

## Data Format Requirements

### Standard Nautilus Trader Data Structure

All custom data types must follow this structure:

```python
from nautilus_trader.model.data import Data
from dataclasses import dataclass
from typing import Optional

@dataclass
class CustomData(Data):
    """Base structure for custom data types."""
    ts_event: int  # Event timestamp in nanoseconds
    ts_init: int   # Initialization timestamp in nanoseconds
    
    # Additional fields specific to your data type
    # ...
```

### Timestamp Requirements

- **ts_event**: UNIX timestamp in nanoseconds when the event occurred
- **ts_init**: UNIX timestamp in nanoseconds when the data object was created
- Both timestamps must be `int64` type
- Data must be sorted by `ts_init` before writing to catalog

### Parquet Schema Requirements

- Columnar format optimized for analytical queries
- Compression: ZSTD (recommended) or SNAPPY
- Row groups: 10,000-100,000 rows per group (for optimal performance)

---

## Custom Data Types

### Creating Custom Data Types

Each data type (TradFi, Sports, DeFi) requires:

1. **Data Class Definition**: Inherit from `Data` base class
2. **Arrow Schema Registration**: Register with `register_arrow` for catalog integration
3. **Serialization Methods**: Implement `to_catalog` and `from_catalog` methods

### Example: Custom Data Type Template

```python
from nautilus_trader.model.data import Data
from nautilus_trader.persistence.catalog import register_arrow
from dataclasses import dataclass
from typing import Optional
import pyarrow as pa

@dataclass
class MyCustomData(Data):
    """Example custom data type."""
    ts_event: int
    ts_init: int
    # Add your custom fields here
    field1: str
    field2: float
    
    @staticmethod
    def schema() -> pa.Schema:
        """Define Arrow schema for Parquet storage."""
        return pa.schema([
            pa.field("ts_event", pa.int64()),
            pa.field("ts_init", pa.int64()),
            pa.field("field1", pa.string()),
            pa.field("field2", pa.float64()),
        ])
    
    @staticmethod
    def to_catalog(data: list["MyCustomData"]) -> pa.Table:
        """Convert data objects to Arrow table."""
        return pa.Table.from_pylist([
            {
                "ts_event": d.ts_event,
                "ts_init": d.ts_init,
                "field1": d.field1,
                "field2": d.field2,
            }
            for d in data
        ], schema=MyCustomData.schema())
    
    @staticmethod
    def from_catalog(table: pa.Table) -> list["MyCustomData"]:
        """Convert Arrow table to data objects."""
        return [
            MyCustomData(
                ts_event=row["ts_event"].as_py(),
                ts_init=row["ts_init"].as_py(),
                field1=row["field1"].as_py(),
                field2=row["field2"].as_py(),
            )
            for row in table.to_pylist()
        ]

# Register with catalog
register_arrow(MyCustomData, MyCustomData.schema(), MyCustomData.to_catalog, MyCustomData.from_catalog)
```

---

## TradFi Integration

### TradFi Data Types

Traditional Finance data typically includes:

1. **Stock Market Data**
   - OHLCV bars (Open, High, Low, Close, Volume)
   - Trade ticks
   - Order book snapshots
   - Corporate actions (dividends, splits)

2. **Forex Data**
   - Currency pair quotes
   - Central bank rates
   - Economic indicators

3. **Bond Data**
   - Yield curves
   - Credit spreads
   - Rating changes

### TradFi Data Structure

```python
@dataclass
class TradFiOHLCV(Data):
    """Traditional Finance OHLCV bar data."""
    ts_event: int
    ts_init: int
    instrument_id: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    bar_type: str  # "1min", "5min", "1hour", "1day"
    exchange: str  # "NYSE", "NASDAQ", "LSE", etc.
```

### TradFi Data Sources

- **Stock Data**: Yahoo Finance, Alpha Vantage, Polygon.io, IEX Cloud
- **Forex Data**: OANDA, FXCM, Dukascopy
- **Bond Data**: FRED, Bloomberg, Quandl

### TradFi Integration Steps

1. **Collect Data**: Download historical TradFi data from your source
2. **Convert Format**: Transform to Nautilus Trader format with proper timestamps
3. **Create Custom Type**: Define `TradFiOHLCV` or similar data class
4. **Register Schema**: Register with Arrow schema
5. **Write to Catalog**: Use `ParquetDataCatalog.write_data()`

---

## Sports Integration

### Sports Data Types

Sports data for trading/backtesting includes:

1. **Event Data**
   - Game schedules and results
   - Team/player statistics
   - Real-time scores and events

2. **Betting Data**
   - Odds movements
   - Betting volumes
   - Market sentiment

3. **Performance Metrics**
   - Player performance stats
   - Team rankings
   - Historical matchups

### Sports Data Structure

```python
@dataclass
class SportsEvent(Data):
    """Sports event data."""
    ts_event: int
    ts_init: int
    event_id: str
    sport: str  # "football", "basketball", "soccer", etc.
    league: str
    home_team: str
    away_team: str
    home_score: Optional[int]
    away_score: Optional[int]
    status: str  # "scheduled", "live", "finished"
    venue: str
```

```python
@dataclass
class BettingOdds(Data):
    """Betting odds data."""
    ts_event: int
    ts_init: int
    event_id: str
    market_type: str  # "moneyline", "spread", "total"
    bookmaker: str
    home_odds: float
    away_odds: float
    draw_odds: Optional[float]
    implied_probability_home: float
    implied_probability_away: float
```

### Sports Data Sources

- **Event Data**: ESPN API, TheSportsDB, Sportradar
- **Betting Odds**: The Odds API, Betfair API, OddsChecker
- **Statistics**: StatsBomb, Opta, Sports Reference

### Sports Integration Steps

1. **Collect Data**: Download historical sports events and betting odds
2. **Convert Format**: Transform to Nautilus Trader format
3. **Create Custom Types**: Define `SportsEvent`, `BettingOdds`, etc.
4. **Register Schemas**: Register each custom type with Arrow
5. **Write to Catalog**: Store in ParquetDataCatalog

---

## DeFi Integration

### DeFi Data Types

Decentralized Finance data includes:

1. **DEX Data**
   - Swap transactions
   - Liquidity pool changes
   - Token prices

2. **Lending/Borrowing**
   - Interest rates
   - Collateral ratios
   - Liquidation events

3. **Yield Farming**
   - APY/APR rates
   - Staking rewards
   - Pool compositions

### DeFi Data Structure

```python
@dataclass
class DeFiSwap(Data):
    """DeFi DEX swap transaction."""
    ts_event: int
    ts_init: int
    transaction_hash: str
    block_number: int
    dex: str  # "uniswap", "sushiswap", "pancakeswap"
    pool_address: str
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    price_impact: float
    fee: float
    trader: str
```

```python
@dataclass
class LiquidityPool(Data):
    """Liquidity pool state snapshot."""
    ts_event: int
    ts_init: int
    pool_address: str
    dex: str
    token0: str
    token1: str
    reserve0: float
    reserve1: float
    total_liquidity: float
    price: float  # token1/token0
    fee_tier: float  # e.g., 0.003 for 0.3%
```

### DeFi Data Sources

- **On-Chain Data**: The Graph, Dune Analytics, Etherscan API
- **DEX Aggregators**: 1inch, 0x Protocol, Paraswap
- **DeFi Analytics**: DeFiLlama, DeFiPulse, CoinGecko

### DeFi Integration Steps

1. **Collect Data**: Query blockchain data or use DeFi APIs
2. **Convert Format**: Transform to Nautilus Trader format with nanosecond timestamps
3. **Create Custom Types**: Define `DeFiSwap`, `LiquidityPool`, etc.
4. **Register Schemas**: Register with Arrow schema
5. **Write to Catalog**: Store in ParquetDataCatalog

---

## Backtesting Configuration

### Configuring Custom Data for Backtests

Use `BacktestDataConfig` to specify custom data:

```python
from nautilus_trader.config import BacktestDataConfig
from nautilus_trader.persistence.catalog import ParquetDataCatalog

# Initialize catalog
catalog = ParquetDataCatalog("./data/parquet")

# Configure TradFi data
tradfi_config = BacktestDataConfig(
    catalog_path=str(catalog.path),
    data_cls=TradFiOHLCV,
    metadata={"exchange": "NYSE"},
)

# Configure Sports data
sports_config = BacktestDataConfig(
    catalog_path=str(catalog.path),
    data_cls=SportsEvent,
    metadata={"sport": "football"},
)

# Configure DeFi data
defi_config = BacktestDataConfig(
    catalog_path=str(catalog.path),
    data_cls=DeFiSwap,
    metadata={"dex": "uniswap"},
)
```

### Subscribing to Custom Data in Strategies

```python
from nautilus_trader.model.data import DataType
from nautilus_trader.trading.strategy import Strategy

class MyStrategy(Strategy):
    def on_start(self):
        # Subscribe to TradFi data
        self.subscribe_data(
            DataType(TradFiOHLCV, metadata={"exchange": "NYSE"}),
        )
        
        # Subscribe to Sports data
        self.subscribe_data(
            DataType(SportsEvent, metadata={"sport": "football"}),
        )
        
        # Subscribe to DeFi data
        self.subscribe_data(
            DataType(DeFiSwap, metadata={"dex": "uniswap"}),
        )
    
    def on_data(self, data):
        """Handle custom data updates."""
        if isinstance(data, TradFiOHLCV):
            # Process TradFi data
            pass
        elif isinstance(data, SportsEvent):
            # Process Sports data
            pass
        elif isinstance(data, DeFiSwap):
            # Process DeFi data
            pass
```

---

## Example Files

See the `examples/` directory for:

1. **TradFi Examples**
   - `tradfi_data_generator.py`: Script to generate sample TradFi data
   - `tradfi_sample.parquet`: Sample Parquet file
   - `tradfi_integration_example.py`: Integration example

2. **Sports Examples**
   - `sports_data_generator.py`: Script to generate sample Sports data
   - `sports_sample.parquet`: Sample Parquet file
   - `sports_integration_example.py`: Integration example

3. **DeFi Examples**
   - `defi_data_generator.py`: Script to generate sample DeFi data
   - `defi_sample.parquet`: Sample Parquet file
   - `defi_integration_example.py`: Integration example

### Running Examples

```bash
# Generate sample data files
python examples/tradfi_data_generator.py
python examples/sports_data_generator.py
python examples/defi_data_generator.py

# Run integration examples
python examples/tradfi_integration_example.py
python examples/sports_integration_example.py
python examples/defi_integration_example.py
```

---

## Best Practices

1. **Data Validation**
   - Validate timestamps are in nanoseconds
   - Ensure data is sorted by `ts_init`
   - Check for missing or invalid values

2. **Performance Optimization**
   - Use vectorized operations when converting data
   - Write data in batches (10,000-100,000 rows)
   - Use appropriate Parquet compression

3. **Error Handling**
   - Handle missing data gracefully
   - Log conversion errors
   - Validate schema before writing

4. **Testing**
   - Create small sample datasets first
   - Test with single instrument before scaling
   - Verify data integrity after conversion

---

## Troubleshooting

### Common Issues

1. **Timestamp Errors**
   - Ensure timestamps are in nanoseconds (not microseconds or milliseconds)
   - Convert: `nanoseconds = microseconds * 1000` or `nanoseconds = milliseconds * 1_000_000`

2. **Schema Mismatches**
   - Verify Arrow schema matches data structure
   - Check field types match (int64, float64, string, etc.)

3. **Data Not Loading**
   - Ensure data is sorted by `ts_init`
   - Check catalog path is correct
   - Verify data class is registered with `register_arrow`

4. **Performance Issues**
   - Use batch writes instead of row-by-row
   - Enable Parquet compression
   - Consider partitioning large datasets

---

## References

- [Nautilus Trader Documentation](https://nautilustrader.io/docs/latest/)
- [Nautilus Trader Data Concepts](https://nautilustrader.io/docs/latest/concepts/data)
- [Nautilus Trader Backtesting Guide](https://nautilustrader.io/docs/latest/concepts/backtesting)
- [PyArrow Documentation](https://arrow.apache.org/docs/python/)

---

## Summary

To integrate TradFi, Sports, and DeFi data into Nautilus Trader:

1. ✅ Create custom data classes inheriting from `Data`
2. ✅ Implement `ts_event` and `ts_init` timestamps (nanoseconds)
3. ✅ Register Arrow schemas with `register_arrow`
4. ✅ Convert data to Parquet format
5. ✅ Write to `ParquetDataCatalog`
6. ✅ Configure `BacktestDataConfig` for each data type
7. ✅ Subscribe to custom data in strategies using `subscribe_data`

See the `examples/` directory for complete working examples.

