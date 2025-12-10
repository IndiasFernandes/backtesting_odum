"""
Shared Instrument Enums

Shared Venue and InstrumentType enums for use across all services.
These enums define the canonical venue and instrument type values used throughout the system.

Note: InstrumentKey dataclass and parsing logic are domain-specific and belong in instruments-service.
"""

from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Venue(str, Enum):
    """Supported venues for instruments"""

    # Crypto exchanges (Tardis)
    BINANCE_SPOT = "BINANCE-SPOT"
    BINANCE_FUTURES = "BINANCE-FUTURES"
    BYBIT = "BYBIT"
    OKX = "OKX"
    DERIBIT = "DERIBIT"
    UPBIT = "UPBIT"  # Korean exchange (spot only) - for kimchi premium
    COINBASE = "COINBASE"  # Coinbase (spot only) - for coinbase premium

    # TradFi exchanges (Databento)
    CME = "CME"
    NASDAQ = "NASDAQ"
    NYSE = "NYSE"
    ICE = "ICE"
    CBOE = "CBOE"  # CBOE Options Exchange (SPY, SPX options)

    # DeFi protocols
    AAVE_V3 = "AAVE_V3"
    AAVE_V3_ETH = "AAVE_V3_ETH"  # Chain-specific
    ETHERFI = "ETHERFI"
    LIDO = "LIDO"
    ETHENA = "ETHENA"  # Ethena sUSDe yield-bearing protocol
    WALLET = "WALLET"

    # DeFi DEX (The Graph)
    UNISWAPV3_ETH = "UNISWAPV3-ETH"
    CURVE_ETH = "CURVE-ETH"
    AERODROME_BASE = "AERODROME-BASE"
    BALANCER_ETH = "BALANCER-ETH"

    # Perpetual futures DEX (CEFI-like data types)
    HYPERLIQUID = "HYPERLIQUID"
    ASTER = "ASTER"

    # Lending protocols
    MORPHO_ETHEREUM = "MORPHO-ETHEREUM"
    EULER_PLASMA = "EULER-PLASMA"
    FLUID_PLASMA = "FLUID-PLASMA"
    AAVE_PLASMA = "AAVE-PLASMA"


class InstrumentType(str, Enum):
    """Supported instrument types"""

    # Spot instruments
    SPOT_ASSET = "SPOT_ASSET"
    SPOT_PAIR = "SPOT_PAIR"

    # Derivatives (crypto)
    PERPETUAL = "PERPETUAL"
    PERP = "PERP"  # Alias for PERPETUAL
    FUTURE = "FUTURE"
    OPTION = "OPTION"

    # TradFi instruments
    EQUITY = "EQUITY"
    INDEX = "INDEX"
    COMMODITY = "COMMODITY"
    CURRENCY = "CURRENCY"

    # TradFi additional
    ETF = "ETF"  # Exchange-traded funds (Bitcoin ETFs, etc.)

    # DeFi instruments
    LST = "LST"  # Liquid Staking Tokens (stETH, wstETH, weETH)
    YIELD_BEARING = "YIELD_BEARING"  # Yield-bearing tokens (sUSDe, etc.)
    A_TOKEN = "A_TOKEN"
    DEBT_TOKEN = "DEBT_TOKEN"
    POOL = "POOL"  # DEX liquidity pools
