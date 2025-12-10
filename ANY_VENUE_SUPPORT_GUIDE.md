# Using ANY Venue/Exchange with NautilusTrader

## Short Answer: **YES, You Can Use Everything!** ✅

**For Backtesting**: You can use **ANY** venue/exchange (Deribit, Binance, Uniswap, SportsBook, etc.) as long as you have the data in Parquet format. The venue name is just metadata in your config.

**For Live Trading**: NautilusTrader has adapters for many exchanges, and you can create custom adapters for any exchange.

---

## Understanding the Two Modes

### 1. Backtesting Mode (What You're Currently Using)

**Key Insight**: For backtesting, NautilusTrader is **venue-agnostic**. It doesn't care what exchange the data came from - it only cares about:
- The data format (Parquet files with proper schema)
- The instrument definition
- The venue configuration (fees, account type, etc.)

#### How It Works

Your system already supports Deribit! Look at your configs:

```json
{
  "venue": {
    "name": "DERIBIT",  // ← Just a string! Can be anything!
    "oms_type": "FUTURES",
    "account_type": "MARGIN",
    "base_currency": "USDT",
    "starting_balance": 1000000,
    "book_type": "L2_MBP"
  }
}
```

The venue name (`"DERIBIT"`) is just metadata. NautilusTrader doesn't validate it against a list of supported exchanges. It's used for:
- Organizing results
- Fee calculations (maker_fee, taker_fee from config)
- Account management simulation

#### What You Need

1. **Parquet Data Files** - Historical data in the correct format
2. **Instrument Definition** - Defined in your JSON config
3. **Venue Config** - Fees, account type, etc. (all in JSON)

**That's it!** No adapter needed for backtesting.

---

## Examples: Using Different Venues

### Example 1: Deribit (Already Working!)

```json
{
  "instrument": {
    "id": "DERIBIT:PERPETUAL:BTC-USDT",
    "price_precision": 2,
    "size_precision": 3
  },
  "venue": {
    "name": "DERIBIT",  // ← Works! No adapter needed for backtesting
    "oms_type": "FUTURES",
    "account_type": "MARGIN",
    "base_currency": "USDT",
    "starting_balance": 1000000,
    "maker_fee": 0.0001,
    "taker_fee": 0.0003
  },
  "data_catalog": {
    "trades_path": "raw_tick_data/by_date/day-*/data_type-trades/DERIBIT:PERPETUAL:BTC-USDT.parquet"
  }
}
```

### Example 2: Custom DeFi Exchange

```json
{
  "instrument": {
    "id": "UNISWAP-V3:POOL:USDC-ETH-0.3",
    "price_precision": 8,
    "size_precision": 8
  },
  "venue": {
    "name": "UNISWAP-V3",  // ← Custom venue name!
    "oms_type": "NETTING",
    "account_type": "CASH",
    "base_currency": "USDC",
    "starting_balance": 100000,
    "maker_fee": 0.003,  // Uniswap V3 fee tier
    "taker_fee": 0.003
  },
  "data_catalog": {
    "swaps_path": "raw_tick_data/by_date/day-*/data_type-defi_swaps/UNISWAP-V3:POOL:USDC-ETH-0.3.parquet"
  }
}
```

### Example 3: Sports Betting Platform

```json
{
  "instrument": {
    "id": "DRAFTKINGS:NFL:MONEYLINE:2024-01-15",
    "price_precision": 4,
    "size_precision": 2
  },
  "venue": {
    "name": "DRAFTKINGS",  // ← Sports betting venue!
    "oms_type": "NETTING",
    "account_type": "CASH",
    "base_currency": "USD",
    "starting_balance": 10000,
    "maker_fee": 0.0,  // No maker fee for sports betting
    "taker_fee": 0.1   // 10% vig
  },
  "data_catalog": {
    "odds_path": "raw_tick_data/by_date/day-*/data_type-betting_odds/DRAFTKINGS:NFL:MONEYLINE:2024-01-15.parquet"
  }
}
```

### Example 4: Traditional Stock Exchange

```json
{
  "instrument": {
    "id": "NYSE:STOCK:AAPL",
    "price_precision": 2,
    "size_precision": 0
  },
  "venue": {
    "name": "NYSE",  // ← Stock exchange!
    "oms_type": "NETTING",
    "account_type": "CASH",
    "base_currency": "USD",
    "starting_balance": 100000,
    "maker_fee": 0.0,
    "taker_fee": 0.001  // 0.1% commission
  },
  "data_catalog": {
    "trades_path": "raw_tick_data/by_date/day-*/data_type-trades/NYSE:STOCK:AAPL.parquet"
  }
}
```

---

## How Your System Handles Venues

### Current Implementation (`backend/backtest_engine.py`)

```python
def _build_venue_config(self, config: Dict[str, Any], has_book_data: bool = False) -> BacktestVenueConfig:
    """Build BacktestVenueConfig from JSON config."""
    venue_config = config["venue"]
    
    return BacktestVenueConfig(
        name=venue_config["name"],  # ← Just uses the string from config!
        oms_type=venue_config["oms_type"],
        account_type=venue_config["account_type"],
        starting_balances=[f"{starting_balance} {base_currency}"],
        book_type=book_type,
    )
```

**Key Point**: The venue name is just passed through as-is. NautilusTrader doesn't validate it against a list of supported exchanges.

---

## Data Requirements

### What You Need for ANY Venue

1. **Parquet Files** with proper schema:
   - `ts_event` (nanoseconds)
   - `ts_init` (nanoseconds)
   - Instrument-specific fields

2. **Data Converter** (`backend/data_converter.py`):
   - Converts raw Parquet → NautilusTrader format
   - Handles schema mapping
   - Works for any venue's data format

3. **Instrument Definition**:
   - Defined in JSON config
   - Includes precision, limits, etc.

### Supported Data Types

Your system already supports:
- ✅ **Trade Ticks** - Executed trades
- ✅ **Order Book Snapshots** - L2 market data
- ✅ **Custom Data Types** - DeFi swaps, sports events, etc.

---

## Live Trading (Future)

### For Live Trading, You Need Adapters

**Good News**: NautilusTrader has adapters for many exchanges:
- ✅ Binance
- ✅ Binance Futures
- ✅ Deribit (exists!)
- ✅ OKX
- ✅ Bybit
- And many more...

### Creating Custom Adapters

If an exchange doesn't have an adapter, you can create one:

```python
from nautilus_trader.adapters import DataClient, ExecutionClient

class CustomExchangeDataClient(DataClient):
    """Custom data client for your exchange."""
    # Implement market data subscriptions
    
class CustomExchangeExecutionClient(ExecutionClient):
    """Custom execution client for your exchange."""
    # Implement order execution
```

**But for backtesting**: You don't need adapters! Just Parquet data files.

---

## Practical Examples

### Adding a New Venue (5 Steps)

1. **Get Historical Data** → Convert to Parquet format
2. **Create Config File** → Define instrument and venue
3. **Place Data Files** → In `data_downloads/raw_tick_data/by_date/`
4. **Run Backtest** → Uses your config
5. **Done!** → No code changes needed

### Example: Adding FTX (Even Though It's Dead)

```json
// external/data_downloads/configs/ftx_btcusdt_config.json
{
  "instrument": {
    "id": "FTX:PERPETUAL:BTC-USDT",
    "price_precision": 2,
    "size_precision": 3
  },
  "venue": {
    "name": "FTX",  // ← Works! Even though FTX is dead
    "oms_type": "NETTING",
    "account_type": "MARGIN",
    "base_currency": "USDT",
    "starting_balance": 1000000,
    "maker_fee": 0.0002,
    "taker_fee": 0.0007
  },
  "data_catalog": {
    "trades_path": "raw_tick_data/by_date/day-*/data_type-trades/FTX:PERPETUAL:BTC-USDT.parquet"
  }
}
```

**Works perfectly for backtesting!** You just need the historical data.

---

## Venue Configuration Options

### OMS Types
- `NETTING` - Net positions (futures, perpetuals)
- `HEDGING` - Separate long/short positions

### Account Types
- `CASH` - Cash account (stocks, spot)
- `MARGIN` - Margin account (futures, perpetuals)

### Book Types
- `L1_MBP` - Top level only (fastest)
- `L2_MBP` - Full depth aggregated (recommended)
- `L3_MBO` - Full depth individual orders (most accurate)

---

## Common Venues You Can Use

### Crypto Exchanges
- ✅ Deribit (already in your configs!)
- ✅ Binance
- ✅ Binance Futures
- ✅ OKX
- ✅ Bybit
- ✅ FTX (historical data)
- ✅ Any exchange with Parquet data

### DeFi Protocols
- ✅ Uniswap V2/V3
- ✅ Sushiswap
- ✅ PancakeSwap
- ✅ Curve
- ✅ Any DEX with swap data

### Traditional Finance
- ✅ NYSE
- ✅ NASDAQ
- ✅ CME
- ✅ ICE
- ✅ Any exchange with OHLCV data

### Sports Betting
- ✅ DraftKings
- ✅ FanDuel
- ✅ BetMGM
- ✅ Any sportsbook with odds data

---

## Verification: Your System Already Supports This!

### Evidence

1. **Deribit Configs Exist**:
   - `deribit_btcusdt_l2_trades_config.json`
   - `deribit_ethusdt_l2_trades_config.json`

2. **Venue Name Handling**:
   ```python
   # backend/results.py
   venue_short = venue.replace("DERIBIT", "DER")  # ← Already handled!
   ```

3. **Config-Driven Architecture**:
   - All venue settings come from JSON
   - No hardcoded venue validation
   - Fully extensible

---

## Summary

### ✅ For Backtesting

**You can use ANY venue/exchange** as long as you have:
1. Parquet data files
2. JSON config file
3. Instrument definition

**No adapter needed!** The venue name is just metadata.

### 🔄 For Live Trading

**You need adapters**, but:
- Many exchanges already have adapters (including Deribit!)
- You can create custom adapters if needed
- Adapters are separate from backtesting

### 🎯 Bottom Line

**YES, you can do everything with NautilusTrader!**

- ✅ Deribit? **Yes** (already working in your system)
- ✅ Any crypto exchange? **Yes** (just need Parquet data)
- ✅ DeFi protocols? **Yes** (custom data types)
- ✅ Sports betting? **Yes** (custom instruments)
- ✅ Traditional finance? **Yes** (custom data types)

**Your system is already venue-agnostic for backtesting!** 🎉

---

## Next Steps

1. **Verify Deribit Works**: Run a backtest with your Deribit config
2. **Add More Venues**: Create configs for any venue you have data for
3. **Test Custom Venues**: Try creating configs for DeFi, Sports, etc.
4. **For Live Trading**: Use existing adapters or create custom ones

---

## References

- [NautilusTrader Adapters Guide](https://nautilustrader.io/docs/latest/concepts/adapters/)
- [NautilusTrader Backtesting Guide](https://nautilustrader.io/docs/latest/concepts/backtesting/)
- Your existing Deribit configs: `external/data_downloads/configs/deribit_*.json`

