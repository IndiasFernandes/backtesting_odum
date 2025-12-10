"""
Custom instrument classes for DeFi, Sports, and other non-standard instruments.

These instruments extend NautilusTrader's Instrument base class to support
instruments not natively supported by the platform.
"""
from decimal import Decimal
from typing import Optional
from nautilus_trader.model.instruments.base import Instrument
from nautilus_trader.model.identifiers import InstrumentId, Symbol
from nautilus_trader.model.currencies import Currency
from nautilus_trader.model.objects import Price, Quantity


class DeFiPoolInstrument(Instrument):
    """
    Custom instrument representing a DeFi liquidity pool.
    
    Example: Uniswap V3 USDC/ETH pool
    
    Attributes:
        instrument_id: Unique instrument identifier
        pool_address: Smart contract address of the pool
        token0: First token in the pair (e.g., "USDC")
        token1: Second token in the pair (e.g., "WETH")
        fee_tier: Pool fee tier as decimal (e.g., 0.003 for 0.3%)
        price_precision: Price precision (default: 8)
        size_precision: Size precision (default: 8)
    """
    
    def __init__(
        self,
        instrument_id: InstrumentId,
        pool_address: str,
        token0: str,
        token1: str,
        fee_tier: Decimal,
        price_precision: int = 8,
        size_precision: int = 8,
        ts_event: int = 0,
        ts_init: int = 0,
        max_quantity: Optional[Quantity] = None,
        min_quantity: Optional[Quantity] = None,
        max_price: Optional[Price] = None,
        min_price: Optional[Price] = None,
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
        self._max_quantity = max_quantity or Quantity.from_str("1000000")
        self._min_quantity = min_quantity or Quantity.from_str("0.00000001")
        self._max_price = max_price or Price.from_str("1000000000")
        self._min_price = min_price or Price.from_str("0.00000001")
    
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
        return (
            f"DeFiPoolInstrument("
            f"id={self.id}, "
            f"pool={self.pool_address}, "
            f"pair={self.token0}/{self.token1}, "
            f"fee={self.fee_tier}"
            f")"
        )


class SportsMarketInstrument(Instrument):
    """
    Custom instrument representing a sports betting market.
    
    Example: NFL Game Moneyline, NBA Point Spread
    
    Attributes:
        instrument_id: Unique instrument identifier
        sport: Sport type (e.g., "football", "basketball")
        league: League name (e.g., "NFL", "NBA")
        market_type: Market type (e.g., "moneyline", "spread", "total")
        event_id: Unique event identifier
        home_team: Home team name
        away_team: Away team name
        price_precision: Odds precision (default: 4)
        size_precision: Bet size precision (default: 2)
    """
    
    def __init__(
        self,
        instrument_id: InstrumentId,
        sport: str,
        league: str,
        market_type: str,
        event_id: str,
        home_team: str,
        away_team: str,
        price_precision: int = 4,
        size_precision: int = 2,
        ts_event: int = 0,
        ts_init: int = 0,
        max_quantity: Optional[Quantity] = None,
        min_quantity: Optional[Quantity] = None,
        max_price: Optional[Price] = None,
        min_price: Optional[Price] = None,
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
        size_inc = Decimal("0.01")    # Bet sizes
        
        self._price_increment = Price.from_str(str(price_inc))
        self._size_increment = Quantity.from_str(str(size_inc))
        
        # Limits
        self._max_quantity = max_quantity or Quantity.from_str("100000")
        self._min_quantity = min_quantity or Quantity.from_str("1")
        self._max_price = max_price or Price.from_str("1000")
        self._min_price = min_price or Price.from_str("1.01")
    
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
        if not isinstance(other, SportsMarketInstrument):
            return False
        return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)
    
    def __repr__(self):
        return (
            f"SportsMarketInstrument("
            f"id={self.id}, "
            f"sport={self.sport}, "
            f"league={self.league}, "
            f"market={self.market_type}, "
            f"event={self.event_id}"
            f")"
        )


class TradFiInstrument(Instrument):
    """
    Custom instrument for Traditional Finance assets.
    
    Example: Stocks, Bonds, ETFs
    
    Attributes:
        instrument_id: Unique instrument identifier
        asset_type: Asset type (e.g., "stock", "bond", "etf")
        exchange: Exchange name (e.g., "NYSE", "NASDAQ")
        symbol: Trading symbol
        currency: Quote currency
    """
    
    def __init__(
        self,
        instrument_id: InstrumentId,
        asset_type: str,
        exchange: str,
        symbol: str,
        currency: str,
        price_precision: int = 2,
        size_precision: int = 0,  # Shares are typically whole numbers
        ts_event: int = 0,
        ts_init: int = 0,
        max_quantity: Optional[Quantity] = None,
        min_quantity: Optional[Quantity] = None,
        max_price: Optional[Price] = None,
        min_price: Optional[Price] = None,
    ):
        self._id = instrument_id
        self._raw_symbol = Symbol(symbol)
        
        # TradFi-specific properties
        self.asset_type = asset_type
        self.exchange = exchange
        self.symbol = symbol
        self.currency = currency
        
        # Precision
        self._price_precision = price_precision
        self._size_precision = size_precision
        
        # Timestamps
        self._ts_event = ts_event
        self._ts_init = ts_init
        
        # Price/Size increments
        price_inc = Decimal("0.01") if price_precision == 2 else Decimal("0.1") ** price_precision
        size_inc = Decimal("1") if size_precision == 0 else Decimal("0.1") ** size_precision
        
        self._price_increment = Price.from_str(str(price_inc))
        self._size_increment = Quantity.from_str(str(size_inc))
        
        # Limits (customize based on asset type)
        self._max_quantity = max_quantity or Quantity.from_str("10000000")
        self._min_quantity = min_quantity or Quantity.from_str("1")
        self._max_price = max_price or Price.from_str("1000000")
        self._min_price = min_price or Price.from_str("0.01")
    
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
        if not isinstance(other, TradFiInstrument):
            return False
        return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)
    
    def __repr__(self):
        return (
            f"TradFiInstrument("
            f"id={self.id}, "
            f"type={self.asset_type}, "
            f"exchange={self.exchange}, "
            f"symbol={self.symbol}"
            f")"
        )

