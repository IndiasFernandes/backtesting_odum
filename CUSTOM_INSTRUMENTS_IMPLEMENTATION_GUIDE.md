# Custom Instruments Implementation Guide

## Overview

This guide provides best practices and implementation strategies for extending NautilusTrader's execution engine to support custom instruments (DeFi, Sports, TradFi, etc.) that aren't natively supported by the platform.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Implementation Strategy](#implementation-strategy)
3. [Custom Instrument Classes](#custom-instrument-classes)
4. [Instrument Provider](#instrument-provider)
5. [Data Integration](#data-integration)
6. [Execution Engine Integration](#execution-engine-integration)
7. [Backtesting Integration](#backtesting-integration)
8. [Best Practices](#best-practices)
9. [Code Examples](#code-examples)

---

## Architecture Overview

### NautilusTrader Extension Points

To add custom instruments, you need to extend these components:

```
┌─────────────────────────────────────────────────────────┐
│              Custom Instrument System                     │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  1. Custom Instrument Class                               │
│     └─ Extends: Instrument (base class)                  │
│                                                           │
│  2. Instrument Provider                                   │
│     └─ Manages: Discovery, Registration, Lookup          │
│                                                           │
│  3. Custom Data Types                                     │
│     └─ Extends: Data (base class)                        │
│                                                           │
│  4. Data Client (for live trading)                       │
│     └─ Handles: Market data subscriptions                │
│                                                           │
│  5. Execution Client (for live trading)                  │
│     └─ Handles: Order execution                          │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Inheritance**: Custom instruments must inherit from `Instrument` base class
2. **Provider Pattern**: Use `InstrumentProvider` for instrument discovery and management
3. **Data Separation**: Custom data types (DeFiSwap, SportsEvent) are separate from instruments
4. **Catalog Integration**: All data must integrate with `ParquetDataCatalog` for backtesting
5. **Execution Alignment**: Custom instruments must work with NautilusTrader's execution engine

---

## Implementation Strategy

### Recommended Approach: Layered Architecture

```
Layer 1: Instrument Definition
  ├─ Custom Instrument Classes (DeFiPool, SportsMarket, etc.)
  └─ Instrument Metadata (precision, fees, constraints)

Layer 2: Instrument Management
  ├─ Custom InstrumentProvider
  └─ Instrument Registry

Layer 3: Data Integration
  ├─ Custom Data Types (already implemented)
  ├─ Data Converters
  └─ Catalog Integration

Layer 4: Execution Integration
  ├─ Backtest Engine Extensions
  ├─ Strategy Adaptations
  └─ Order Management
```

### Implementation Phases

**Phase 1: Instrument Definition** ✅ (Foundation)
- Create custom instrument classes
- Define instrument metadata
- Register with catalog

**Phase 2: Provider Implementation** (Discovery)
- Implement custom InstrumentProvider
- Add instrument discovery logic
- Integrate with config system

**Phase 3: Backtesting Integration** (Validation)
- Extend backtest engine
- Add custom instrument support to config loader
- Test with historical data

**Phase 4: Live Trading** (Production)
- Implement DataClient for market data
- Implement ExecutionClient for orders
- Add risk management

---

## Custom Instrument Classes

### Base Instrument Requirements

All custom instruments must:

1. Inherit from `Instrument` base class
2. Implement required properties (`id`, `price_precision`, `size_precision`, etc.)
3. Define `ts_event` and `ts_init` timestamps
4. Support serialization for catalog storage

### Example: DeFi Pool Instrument

```python
from decimal import Decimal
from nautilus_trader.model.instruments.base import Instrument
from nautilus_trader.model.identifiers import InstrumentId, Symbol
from nautilus_trader.model.currencies import Currency
from nautilus_trader.model.objects import Price, Quantity
from typing import Optional


class DeFiPoolInstrument(Instrument):
    """
    Custom instrument representing a DeFi liquidity pool.
    
    Example: Uniswap V3 USDC/ETH pool
    """
    
    def __init__(
        self,
        instrument_id: InstrumentId,
        pool_address: str,
        token0: str,
        token1: str,
        fee_tier: Decimal,  # e.g., 0.003 for 0.3%
        price_precision: int = 8,
        size_precision: int = 8,
        ts_event: int = 0,
        ts_init: int = 0,
    ):
        # Required Instrument properties
        self._id = instrument_id
        self._raw_symbol = Symbol(f"{token0}/{token1}")
        
        # DeFi-specific properties
        self.pool_address = pool_address
        self.token0 = token0
        self.token1 = token1
        self.fee_tier = fee_tier
        
        # Precision
        self._price_precision = price_precision
        self._size_precision = size_precision
        
        # Timestamps (nanoseconds)
        self._ts_event = ts_event
        self._ts_init = ts_init
        
        # Price/Size increments (derived from precision)
        price_inc = Decimal("0.1") ** price_precision
        size_inc = Decimal("0.1") ** size_precision
        
        self._price_increment = Price.from_str(str(price_inc))
        self._size_increment = Quantity.from_str(str(size_inc))
        
        # Limits (can be customized)
        self._max_quantity = Quantity.from_str("1000000")
        self._min_quantity = Quantity.from_str("0.00000001")
        self._max_price = Price.from_str("1000000000")
        self._min_price = Price.from_str("0.00000001")
    
    @property
    def id(self) -> InstrumentId:
        return self._id
    
    @property
    def raw_symbol(self) -> Symbol:
        return self._raw_symbol
    
    @property
    def price_precision(self) -> int:
        return self._price_precision
    
    @property
    def size_precision(self) -> int:
        return self._size_precision
    
    @property
    def price_increment(self) -> Price:
        return self._price_increment
    
    @property
    def size_increment(self) -> Quantity:
        return self._size_increment
    
    @property
    def max_quantity(self) -> Optional[Quantity]:
        return self._max_quantity
    
    @property
    def min_quantity(self) -> Optional[Quantity]:
        return self._min_quantity
    
    @property
    def max_price(self) -> Optional[Price]:
        return self._max_price
    
    @property
    def min_price(self) -> Optional[Price]:
        return self._min_price
    
    @property
    def ts_event(self) -> int:
        return self._ts_event
    
    @property
    def ts_init(self) -> int:
        return self._ts_init
    
    def __eq__(self, other):
        if not isinstance(other, DeFiPoolInstrument):
            return False
        return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)
    
    def __repr__(self):
        return f"DeFiPoolInstrument(id={self.id}, pool={self.pool_address}, fee={self.fee_tier})"
```

### Example: Sports Market Instrument

```python
class SportsMarketInstrument(Instrument):
    """
    Custom instrument representing a sports betting market.
    
    Example: NFL Game Moneyline, NBA Point Spread
    """
    
    def __init__(
        self,
        instrument_id: InstrumentId,
        sport: str,  # "football", "basketball", etc.
        league: str,  # "NFL", "NBA", etc.
        market_type: str,  # "moneyline", "spread", "total"
        event_id: str,
        home_team: str,
        away_team: str,
        price_precision: int = 4,  # Odds precision
        size_precision: int = 2,   # Bet size precision
        ts_event: int = 0,
        ts_init: int = 0,
    ):
        self._id = instrument_id
        self._raw_symbol = Symbol(f"{sport}:{market_type}")
        
        # Sports-specific properties
        self.sport = sport
        self.league = league
        self.market_type = market_type
        self.event_id = event_id
        self.home_team = home_team
        self.away_team = away_team
        
        # Precision
        self._price_precision = price_precision
        self._size_precision = size_precision
        
        # Timestamps
        self._ts_event = ts_event
        self._ts_init = ts_init
        
        # Price/Size increments
        price_inc = Decimal("0.01")  # Odds typically in 0.01 increments
        size_inc = Decimal("0.01")   # Bet sizes
        
        self._price_increment = Price.from_str(str(price_inc))
        self._size_increment = Quantity.from_str(str(size_inc))
        
        # Limits
        self._max_quantity = Quantity.from_str("100000")  # Max bet
        self._min_quantity = Quantity.from_str("1")     # Min bet
        self._max_price = Price.from_str("1000")         # Max odds
        self._min_price = Price.from_str("1.01")         # Min odds
    
    # ... (same property implementations as DeFiPoolInstrument)
```

---

## Instrument Provider

### Custom InstrumentProvider Implementation

```python
from typing import Dict, Optional, List
from nautilus_trader.model.instruments.base import Instrument
from nautilus_trader.model.instruments.provider import InstrumentProvider
from nautilus_trader.model.identifiers import InstrumentId


class CustomInstrumentProvider(InstrumentProvider):
    """
    Custom instrument provider for DeFi, Sports, and other non-standard instruments.
    """
    
    def __init__(self):
        super().__init__()
        self._instruments: Dict[InstrumentId, Instrument] = {}
        self._loaded = False
    
    def load_all(self, filters: Optional[Dict] = None) -> None:
        """
        Load all instruments from catalog or config.
        
        Args:
            filters: Optional filters (e.g., {"type": "defi", "dex": "uniswap"})
        """
        # Load from catalog or config files
        # This is where you'd read from ParquetDataCatalog or JSON configs
        pass
    
    def load(self, instrument_id: InstrumentId) -> None:
        """
        Load a specific instrument.
        
        Args:
            instrument_id: Instrument ID to load
        """
        # Load from catalog or config
        pass
    
    def find(self, instrument_id: InstrumentId) -> Optional[Instrument]:
        """
        Find an instrument by ID.
        
        Args:
            instrument_id: Instrument ID to find
            
        Returns:
            Instrument if found, None otherwise
        """
        return self._instruments.get(instrument_id)
    
    def get_all(self) -> Dict[InstrumentId, Instrument]:
        """
        Get all loaded instruments.
        
        Returns:
            Dictionary of instrument_id -> Instrument
        """
        return self._instruments.copy()
    
    def add_instrument(self, instrument: Instrument) -> None:
        """
        Add an instrument to the provider.
        
        Args:
            instrument: Instrument to add
        """
        self._instruments[instrument.id] = instrument
    
    def remove_instrument(self, instrument_id: InstrumentId) -> None:
        """
        Remove an instrument from the provider.
        
        Args:
            instrument_id: Instrument ID to remove
        """
        self._instruments.pop(instrument_id, None)
```

### Integration with Config System

```python
from backend.config_loader import ConfigLoader
from backend.catalog_manager import CatalogManager


class ConfigBasedInstrumentProvider(CustomInstrumentProvider):
    """
    Instrument provider that loads instruments from JSON configs.
    """
    
    def __init__(self, catalog_manager: CatalogManager):
        super().__init__()
        self.catalog_manager = catalog_manager
        self.configs_dir = Path("external/data_downloads/configs")
    
    def load_from_config(self, config_path: Path) -> Instrument:
        """
        Load instrument from JSON config file.
        
        Args:
            config_path: Path to config JSON file
            
        Returns:
            Instrument instance
        """
        loader = ConfigLoader(str(config_path))
        config = loader.load()
        
        instrument_config = config["instrument"]
        instrument_type = instrument_config.get("type", "crypto_perpetual")
        
        if instrument_type == "defi_pool":
            return self._create_defi_pool_instrument(config)
        elif instrument_type == "sports_market":
            return self._create_sports_market_instrument(config)
        elif instrument_type == "crypto_perpetual":
            # Use existing CryptoPerpetual creation logic
            return self._create_crypto_perpetual_instrument(config)
        else:
            raise ValueError(f"Unknown instrument type: {instrument_type}")
    
    def _create_defi_pool_instrument(self, config: Dict) -> DeFiPoolInstrument:
        """Create DeFi pool instrument from config."""
        instrument_config = config["instrument"]
        instrument_id = InstrumentId.from_str(instrument_config["id"])
        
        return DeFiPoolInstrument(
            instrument_id=instrument_id,
            pool_address=instrument_config["pool_address"],
            token0=instrument_config["token0"],
            token1=instrument_config["token1"],
            fee_tier=Decimal(str(instrument_config["fee_tier"])),
            price_precision=instrument_config.get("price_precision", 8),
            size_precision=instrument_config.get("size_precision", 8),
        )
    
    def _create_sports_market_instrument(self, config: Dict) -> SportsMarketInstrument:
        """Create sports market instrument from config."""
        instrument_config = config["instrument"]
        instrument_id = InstrumentId.from_str(instrument_config["id"])
        
        return SportsMarketInstrument(
            instrument_id=instrument_id,
            sport=instrument_config["sport"],
            league=instrument_config["league"],
            market_type=instrument_config["market_type"],
            event_id=instrument_config["event_id"],
            home_team=instrument_config["home_team"],
            away_team=instrument_config["away_team"],
            price_precision=instrument_config.get("price_precision", 4),
            size_precision=instrument_config.get("size_precision", 2),
        )
```

---

## Data Integration

### Custom Data Types (Already Implemented)

Your existing `DeFiSwap` and `LiquidityPool` data types are correctly implemented:

```python
# ✅ Already implemented in examples/defi/defi_data_types.py
@dataclass
class DeFiSwap(Data):
    ts_event: int
    ts_init: int
    # ... custom fields
    # ✅ Registered with register_arrow()
```

### Instrument-Data Mapping

```python
from typing import Dict, Type
from nautilus_trader.model.data import Data


class InstrumentDataMapper:
    """
    Maps instruments to their associated data types.
    """
    
    # Mapping: Instrument Type -> Data Type
    INSTRUMENT_DATA_MAP: Dict[Type[Instrument], Type[Data]] = {
        DeFiPoolInstrument: DeFiSwap,  # DeFi pools use swap data
        SportsMarketInstrument: BettingOdds,  # Sports markets use odds data
        CryptoPerpetual: TradeTick,  # Crypto uses trade ticks
    }
    
    @classmethod
    def get_data_type(cls, instrument: Instrument) -> Type[Data]:
        """
        Get the data type associated with an instrument.
        
        Args:
            instrument: Instrument instance
            
        Returns:
            Data type class
        """
        instrument_type = type(instrument)
        return cls.INSTRUMENT_DATA_MAP.get(instrument_type, TradeTick)  # Default to TradeTick
```

---

## Execution Engine Integration

### Extending BacktestEngine

```python
# backend/backtest_engine.py - Add custom instrument support

class BacktestEngine:
    """Extended backtest engine with custom instrument support."""
    
    def _create_instrument_from_config(
        self,
        config: Dict[str, Any]
    ) -> Instrument:
        """
        Create instrument from config, supporting custom types.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Instrument instance
        """
        instrument_config = config["instrument"]
        instrument_type = instrument_config.get("type", "crypto_perpetual")
        
        if instrument_type == "defi_pool":
            return self._create_defi_pool_instrument(config)
        elif instrument_type == "sports_market":
            return self._create_sports_market_instrument(config)
        elif instrument_type == "crypto_perpetual":
            return self._create_crypto_perpetual_instrument(config)
        else:
            raise ValueError(f"Unknown instrument type: {instrument_type}")
    
    def _create_defi_pool_instrument(self, config: Dict) -> DeFiPoolInstrument:
        """Create DeFi pool instrument."""
        instrument_config = config["instrument"]
        instrument_id = InstrumentId.from_str(instrument_config["id"])
        
        # Get timestamps
        import time
        now_ns = int(time.time() * 1_000_000_000)
        
        instrument = DeFiPoolInstrument(
            instrument_id=instrument_id,
            pool_address=instrument_config["pool_address"],
            token0=instrument_config["token0"],
            token1=instrument_config["token1"],
            fee_tier=Decimal(str(instrument_config["fee_tier"])),
            price_precision=instrument_config.get("price_precision", 8),
            size_precision=instrument_config.get("size_precision", 8),
            ts_event=now_ns,
            ts_init=now_ns,
        )
        
        # Write to catalog
        self.catalog.write_data([instrument])
        
        return instrument
```

### Config Schema Extension

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
    "swaps_path": "raw_tick_data/by_date/day-*/data_type-defi_swaps/UNISWAP-V3:POOL:USDC-ETH-0.3.parquet",
    "liquidity_pools_path": "raw_tick_data/by_date/day-*/data_type-liquidity_pools/UNISWAP-V3:POOL:USDC-ETH-0.3.parquet"
  }
}
```

---

## Backtesting Integration

### Custom Data Config Builder

```python
def _build_custom_data_config(
    self,
    config: Dict[str, Any],
    instrument: Instrument,
    start: datetime,
    end: datetime,
) -> List[BacktestDataConfig]:
    """
    Build BacktestDataConfig for custom instruments.
    
    Args:
        config: Configuration dictionary
        instrument: Instrument instance
        start: Start time
        end: End time
        
    Returns:
        List of BacktestDataConfig instances
    """
    data_configs = []
    
    # Get data type for this instrument
    data_type = InstrumentDataMapper.get_data_type(instrument)
    
    # Get data paths from config
    data_catalog_config = config.get("data_catalog", {})
    
    if isinstance(instrument, DeFiPoolInstrument):
        # DeFi pools use swap data
        swaps_path = data_catalog_config.get("swaps_path")
        if swaps_path:
            data_configs.append(
                BacktestDataConfig(
                    catalog_path=str(self.catalog.path),
                    data_cls=DeFiSwap,
                    instrument_id=instrument.id,
                    start_time=start,
                    end_time=end,
                )
            )
    
    elif isinstance(instrument, SportsMarketInstrument):
        # Sports markets use odds data
        odds_path = data_catalog_config.get("odds_path")
        if odds_path:
            data_configs.append(
                BacktestDataConfig(
                    catalog_path=str(self.catalog.path),
                    data_cls=BettingOdds,
                    instrument_id=instrument.id,
                    start_time=start,
                    end_time=end,
                )
            )
    
    return data_configs
```

---

## Best Practices

### 1. Instrument Design

✅ **Do:**
- Inherit from `Instrument` base class
- Implement all required properties
- Use proper precision (match your data)
- Set reasonable min/max limits
- Include timestamps (`ts_event`, `ts_init`)

❌ **Don't:**
- Skip required properties
- Use arbitrary precision values
- Forget to register with catalog
- Mix instrument logic with data logic

### 2. Provider Implementation

✅ **Do:**
- Cache loaded instruments
- Support filtering
- Integrate with config system
- Handle missing instruments gracefully

❌ **Don't:**
- Reload instruments on every lookup
- Hardcode instrument definitions
- Ignore config files
- Fail silently on errors

### 3. Data Integration

✅ **Do:**
- Use `register_arrow()` for custom data types
- Maintain consistent timestamps (nanoseconds)
- Sort data by `ts_init` before writing
- Use proper Parquet compression

❌ **Don't:**
- Mix timestamp formats
- Write unsorted data
- Skip schema registration
- Use inefficient compression

### 4. Testing

✅ **Do:**
- Test instrument creation
- Test catalog integration
- Test backtest execution
- Test with sample data first

❌ **Don't:**
- Skip unit tests
- Test only with production data
- Ignore edge cases
- Forget to test precision handling

---

## Code Examples

### Complete Example: DeFi Pool Backtest

```python
# 1. Create custom instrument
from backend.backtest_engine import BacktestEngine
from backend.config_loader import ConfigLoader

# Load config
loader = ConfigLoader("external/data_downloads/configs/uniswap_usdc_eth_config.json")
config = loader.load()

# Initialize engine
engine = BacktestEngine()
engine.initialize()

# Create instrument (handles custom types automatically)
instrument_id = engine.register_instrument(config)

# Run backtest
results = engine.run_backtest(
    instrument_id=str(instrument_id),
    start=datetime(2023, 1, 1),
    end=datetime(2023, 1, 31),
    config=config,
    fast=True,
)

print(f"Backtest completed: {results['summary']}")
```

### Example Config File

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
    "swaps_path": "raw_tick_data/by_date/day-*/data_type-defi_swaps/UNISWAP-V3:POOL:USDC-ETH-0.3.parquet",
    "auto_discover": true
  },
  "time_window": {
    "start": "2023-01-01T00:00:00Z",
    "end": "2023-01-31T23:59:59Z"
  },
  "strategy": {
    "name": "DeFiArbitrageStrategy",
    "submission_mode": "per_swap"
  }
}
```

---

## Implementation Checklist

### Phase 1: Foundation ✅
- [x] Custom data types (DeFiSwap, LiquidityPool)
- [x] Data type registration with `register_arrow()`
- [x] Catalog integration

### Phase 2: Instruments
- [ ] Create custom instrument classes
  - [ ] DeFiPoolInstrument
  - [ ] SportsMarketInstrument
  - [ ] Other custom types
- [ ] Implement InstrumentProvider
- [ ] Add instrument registration to catalog

### Phase 3: Backtesting
- [ ] Extend BacktestEngine for custom instruments
- [ ] Update ConfigLoader to support custom types
- [ ] Add custom data config builders
- [ ] Test with sample data

### Phase 4: Production
- [ ] Implement DataClient (for live data)
- [ ] Implement ExecutionClient (for live orders)
- [ ] Add risk management
- [ ] Performance optimization

---

## References

- [NautilusTrader Instrument Documentation](https://nautilustrader.io/docs/latest/concepts/instruments/)
- [NautilusTrader Adapters Guide](https://nautilustrader.io/docs/latest/concepts/adapters/)
- [NautilusTrader Data Concepts](https://nautilustrader.io/docs/latest/concepts/data/)
- [Polymarket Adapter Example](https://nautilustrader.io/docs/nightly/api_reference/adapters/polymarket/) - Good reference for custom instruments

---

## Summary

To extend NautilusTrader with custom instruments:

1. ✅ **Create custom instrument classes** inheriting from `Instrument`
2. ✅ **Implement InstrumentProvider** for discovery and management
3. ✅ **Extend BacktestEngine** to support custom instrument creation
4. ✅ **Update config system** to handle custom instrument types
5. ✅ **Integrate with catalog** for data storage
6. ✅ **Test thoroughly** with sample data before production

Your existing custom data types (DeFiSwap, LiquidityPool) are correctly implemented. The next step is to create corresponding custom instrument classes and integrate them with your backtest engine.

