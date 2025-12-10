# Custom Instruments Implementation Summary

## What Was Created

Based on online research and best practices for extending NautilusTrader, I've created a comprehensive implementation for custom instruments:

### 1. **Implementation Guide** (`CUSTOM_INSTRUMENTS_IMPLEMENTATION_GUIDE.md`)
   - Complete architecture overview
   - Step-by-step implementation strategy
   - Best practices and code examples
   - Integration patterns

### 2. **Custom Instrument Classes** (`backend/instruments/custom_instruments.py`)
   - `DeFiPoolInstrument` - For DeFi liquidity pools (Uniswap, etc.)
   - `SportsMarketInstrument` - For sports betting markets
   - `TradFiInstrument` - For traditional finance assets (stocks, bonds, ETFs)

### 3. **Instrument Provider** (`backend/instruments/instrument_provider.py`)
   - `CustomInstrumentProvider` - Manages custom instrument discovery and registration
   - Loads instruments from JSON configs
   - Integrates with catalog system
   - Supports filtering and lookup

---

## Key Findings from Research

### Best Practices Identified

1. **Inheritance Pattern**: Custom instruments must inherit from `Instrument` base class
2. **Provider Pattern**: Use `InstrumentProvider` for instrument management (discovery, registration, lookup)
3. **Data Separation**: Custom data types (DeFiSwap, etc.) are separate from instruments
4. **Catalog Integration**: All instruments must be registered with `ParquetDataCatalog`
5. **Config-Driven**: Instruments should be defined in JSON configs (aligns with your existing system)

### NautilusTrader Extension Points

- **Instrument Class**: Base class for all instruments
- **InstrumentProvider**: Manages instrument lifecycle
- **DataClient**: For live market data (future)
- **ExecutionClient**: For live order execution (future)

---

## Implementation Status

### ✅ Completed

- [x] Custom instrument class definitions
- [x] Instrument provider implementation
- [x] Config-based loading
- [x] Catalog integration
- [x] Documentation and examples

### 🔄 Next Steps (To Integrate)

1. **Extend BacktestEngine** (`backend/backtest_engine.py`)
   - Add support for custom instrument creation in `register_instrument()`
   - Handle custom instrument types in config loader

2. **Update ConfigLoader** (`backend/config_loader.py`)
   - Add validation for custom instrument types
   - Support new config schema fields

3. **Create Example Configs**
   - DeFi pool config example
   - Sports market config example
   - TradFi config example

4. **Test Integration**
   - Test instrument creation
   - Test catalog registration
   - Test backtest execution with custom instruments

---

## How to Use

### Step 1: Create Custom Instrument Config

```json
{
  "instrument": {
    "type": "defi_pool",
    "id": "UNISWAP-V3:POOL:USDC-ETH-0.3",
    "pool_address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
    "token0": "USDC",
    "token1": "WETH",
    "fee_tier": 0.003,
    "price_precision": 8,
    "size_precision": 8
  },
  "venue": {
    "name": "UNISWAP-V3",
    "oms_type": "NETTING",
    "account_type": "CASH",
    "base_currency": "USDC",
    "starting_balance": 100000,
    "maker_fee": 0.003,
    "taker_fee": 0.003
  },
  "data_catalog": {
    "swaps_path": "raw_tick_data/by_date/day-*/data_type-defi_swaps/UNISWAP-V3:POOL:USDC-ETH-0.3.parquet"
  },
  "time_window": {
    "start": "2023-01-01T00:00:00Z",
    "end": "2023-01-31T23:59:59Z"
  }
}
```

### Step 2: Initialize Provider

```python
from backend.instruments.instrument_provider import CustomInstrumentProvider
from backend.catalog_manager import CatalogManager

# Initialize catalog manager
catalog_manager = CatalogManager()
catalog_manager.initialize()

# Create provider
provider = CustomInstrumentProvider(catalog_manager)

# Load all instruments from configs
provider.load_all()

# Or load specific instrument
instrument_id = InstrumentId.from_str("UNISWAP-V3:POOL:USDC-ETH-0.3")
provider.load(instrument_id)
instrument = provider.find(instrument_id)
```

### Step 3: Integrate with BacktestEngine

```python
# In backend/backtest_engine.py, extend register_instrument():

def register_instrument(self, config: Dict[str, Any]) -> InstrumentId:
    """Register instrument, supporting custom types."""
    instrument_config = config["instrument"]
    instrument_type = instrument_config.get("type", "crypto_perpetual")
    
    if instrument_type == "defi_pool":
        from backend.instruments.custom_instruments import DeFiPoolInstrument
        # Create DeFi pool instrument
        instrument = self._create_defi_pool_instrument(config)
    elif instrument_type == "sports_market":
        from backend.instruments.custom_instruments import SportsMarketInstrument
        instrument = self._create_sports_market_instrument(config)
    elif instrument_type == "tradfi":
        from backend.instruments.custom_instruments import TradFiInstrument
        instrument = self._create_tradfi_instrument(config)
    else:
        # Default to CryptoPerpetual (existing logic)
        instrument = self._create_crypto_perpetual_instrument(config)
    
    # Register with catalog
    self.catalog.write_data([instrument])
    
    return instrument.id
```

---

## Architecture Alignment

### ✅ Aligned with Existing System

1. **Config-Driven**: Uses JSON configs (matches your existing pattern)
2. **Catalog Integration**: Registers with `ParquetDataCatalog` (same as crypto instruments)
3. **Data Types**: Works with your existing custom data types (DeFiSwap, etc.)
4. **Backtest Engine**: Extends existing `BacktestEngine` class

### 🔄 Integration Points

1. **BacktestEngine**: Add custom instrument creation logic
2. **ConfigLoader**: Add validation for custom types
3. **Data Converter**: Ensure custom data types work with custom instruments
4. **Strategy**: Strategies can use custom instruments same as crypto

---

## Benefits

1. **Extensibility**: Easy to add new instrument types
2. **Consistency**: Same patterns as existing crypto instruments
3. **Flexibility**: Supports DeFi, Sports, TradFi, and more
4. **Production-Ready**: Follows NautilusTrader best practices
5. **Backward Compatible**: Doesn't break existing crypto backtests

---

## References

- [NautilusTrader Instrument Docs](https://nautilustrader.io/docs/latest/concepts/instruments/)
- [NautilusTrader Adapters Guide](https://nautilustrader.io/docs/latest/concepts/adapters/)
- [Polymarket Adapter Example](https://nautilustrader.io/docs/nightly/api_reference/adapters/polymarket/) - Reference implementation

---

## Next Steps

1. Review the implementation guide
2. Test custom instrument creation
3. Integrate with BacktestEngine
4. Create example configs
5. Test end-to-end backtest flow

The foundation is ready - now integrate it with your existing backtest engine!

