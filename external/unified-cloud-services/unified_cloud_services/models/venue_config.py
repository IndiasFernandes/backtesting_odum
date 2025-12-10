"""
Centralized Venue and Data Type Configuration

Provides canonical venue mappings, data type configurations, and exchange settings
used across all services in the unified trading system.

This module centralizes business logic that was previously duplicated in:
- instruments-service/instruments_service/config.py
- market-tick-data-handler/market_data_tick_handler/config.py
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


def _get_env_config(key: str, default: str = "") -> str:
    """Get configuration from environment variable."""
    return os.environ.get(key, default)


@dataclass
class VenueMapping:
    """CANONICAL venue to exchange API mappings (centralized business logic)"""

    # ALL possible Tardis exchange endpoints (we'll call each to get complete data)
    all_tardis_exchanges: List[str] = field(
        default_factory=lambda: [
            "binance",
            "binance-futures",  # BINANCE split
            "deribit",  # DERIBIT unified
            "bybit",
            "bybit-spot",  # BYBIT unified
            "okex",
            "okex-futures",
            "okex-swap",  # OKX needs all endpoints for complete data
            "upbit",  # Upbit (Korean exchange) - spot only, for kimchi premium
            "coinbase",  # Coinbase - spot only, for coinbase premium
        ]
    )

    # Canonical TradFi venues (user-friendly names, not data source names)
    all_databento_venues: List[str] = field(
        default_factory=lambda: [
            "CME",  # Chicago Mercantile Exchange (futures, options, treasuries)
            "CBOE",  # Cboe Global Markets (VIX index only - special treatment)
            "NASDAQ",  # NASDAQ Stock Market (equities, ETFs)
            "NYSE",  # New York Stock Exchange (equities, ETFs)
            "ICE",  # Intercontinental Exchange (futures, options)
        ]
    )

    # DeFi venues (multi-chain support: Ethereum, Plasma, Hyperliquid)
    all_defi_venues: List[str] = field(
        default_factory=lambda: [
            # Ethereum DEX protocols
            "UNISWAPV2-ETH",  # Uniswap V2 Ethereum
            "UNISWAPV3-ETH",  # Uniswap V3 Ethereum
            "UNISWAPV4-ETH",  # Uniswap V4 Ethereum (launched January 31, 2025)
            "CURVE-ETH",  # Curve Ethereum
            "BALANCER-ETH",  # Balancer V2 Ethereum
            "AAVE_V3_ETH",  # AAVE V3 Ethereum
            "ETHERFI",  # EtherFi LST (Ethereum)
            "LIDO",  # Lido LST (Ethereum)
            "ETHENA",  # Ethena synthetic dollars (Ethereum)
            "MORPHO-ETHEREUM",  # Morpho lending protocol (Ethereum)
            # Plasma lending protocols
            "EULER-PLASMA",  # Euler lending (Plasma)
            "FLUID-PLASMA",  # Fluid lending (Plasma)
            "AAVE-PLASMA",  # AAVE Plasma market (Plasma)
            # Perpetual futures DEX
            "HYPERLIQUID",  # Hyperliquid perpetual futures (HyperEVM)
            "ASTER",  # Aster perpetual futures exchange
        ]
    )

    # All exchanges (computed from above - no duplication)
    @property
    def all_exchanges(self) -> List[str]:
        """All exchanges (Tardis + Databento + DeFi)"""
        return self.all_tardis_exchanges + self.all_databento_venues + self.all_defi_venues

    # Map canonical venues to Databento dataset identifiers
    venue_to_databento: Dict[str, str] = field(
        default_factory=lambda: {
            "CME": "GLBX.MDP3",  # CME Globex Market Data Platform 3.0
            "CBOE": "BARCHART",  # VIX index only (not via Databento OPRA.PILLAR)
            "NASDAQ": "DBEQ.BASIC",  # NASDAQ equities via Databento DBEQ.BASIC
            "NYSE": "DBEQ.BASIC",  # NYSE equities via Databento DBEQ.BASIC
            "ICE": "IFEU.IMPACT",  # ICE futures via Databento IFEU.IMPACT
        }
    )

    # Canonical venues to CCXT exchange IDs
    venue_to_ccxt: Dict[str, str] = field(
        default_factory=lambda: {
            "BINANCE-SPOT": "binance",
            "BINANCE-FUTURES": "binance",  # Same CCXT class, different market types
            "DERIBIT": "deribit",
            "BYBIT": "bybit",  # Unified
            "OKX": "okx",  # Unified
            "HYPERLIQUID": "hyperliquid",  # CCXT supports Hyperliquid
            "UPBIT": "upbit",  # Korean exchange (spot only)
            "COINBASE": "coinbase",  # Coinbase (spot only)
            # Note: ASTER not in CCXT yet
        }
    )

    # Reverse mapping for imports
    tardis_to_venue: Dict[str, str] = field(
        default_factory=lambda: {
            "binance": "BINANCE-SPOT",  # Fixed: binance spot should be BINANCE-SPOT
            "binance-futures": "BINANCE-FUTURES",
            "deribit": "DERIBIT",
            "bybit": "BYBIT",
            "bybit-spot": "BYBIT",
            "okex": "OKX",
            "okex-futures": "OKX",
            "okex-swap": "OKX",
            "upbit": "UPBIT",  # Korean exchange (spot only)
            "coinbase": "COINBASE",  # Coinbase (spot only)
        }
    )

    # Map venues to their data providers (for non-Tardis venues)
    venue_to_data_provider: Dict[str, str] = field(
        default_factory=lambda: {
            # DeFi venues with direct API integration
            "HYPERLIQUID": "hyperliquid_api",  # Hyperliquid REST/WebSocket API + S3 archive
            "ASTER": "aster_api",  # Aster REST API
            # DeFi venues using The Graph
            "UNISWAPV2-ETH": "the_graph",
            "UNISWAPV3-ETH": "the_graph",
            "UNISWAPV4-ETH": "the_graph",
            "CURVE-ETH": "the_graph",
            "BALANCER-ETH": "the_graph",
            # DeFi venues using protocol SDKs
            "AAVE_V3_ETH": "protocol_sdk",
            "MORPHO-ETHEREUM": "protocol_sdk",
            "EULER-PLASMA": "protocol_sdk",
            "FLUID-PLASMA": "protocol_sdk",
            "AAVE-PLASMA": "protocol_sdk",
            "ETHERFI": "protocol_sdk",
            "LIDO": "protocol_sdk",
            "ETHENA": "protocol_sdk",
        }
    )

    # MVP token list for DeFi pool discovery (configurable)
    defi_mvp_base_currencies: List[str] = field(
        default_factory=lambda: [
            "ETH",  # Native Ethereum
            "WETH",  # Wrapped ETH
            "BTC",  # Bitcoin (WBTC on Ethereum)
            "WBTC",  # Wrapped Bitcoin (explicitly include WBTC)
            "USDT",  # Tether
            "USDC",  # USD Coin
            "DAI",  # Dai stablecoin
            "weETH",  # EtherFi LST (Wrapped eETH) - non-rebasing
            "WSTETH",  # Lido LST (non-rebasing, wrapped version)
            # STETH removed - rebasing token, not supported by AAVE
        ]
    )

    # MVP base assets for Hyperliquid and Aster perpetuals
    # These are the 21 trading assets used for CeFi/TradFi MVP
    hyperliquid_aster_mvp_base_assets: List[str] = field(
        default_factory=lambda: [
            "SOL",  # Solana
            "BTC",  # Bitcoin
            "ETH",  # Ethereum
            "AVAX",  # Avalanche
            "ADA",  # Cardano
            "SUSHI",  # SushiSwap
            "CAKE",  # PancakeSwap
            "XRP",  # Ripple
            "DOGE",  # Dogecoin
            "XLM",  # Stellar
            "LTC",  # Litecoin
            "ALGO",  # Algorand
            "FIL",  # Filecoin
            "TRX",  # Tron
            "BNB",  # Binance Coin
            "LINK",  # Chainlink
            "MATIC",  # Polygon
            "APT",  # Aptos
            "VET",  # VeChain
            "ATOM",  # Cosmos
            "NEAR",  # Near Protocol
        ]
    )

    def is_databento_venue(self, venue: str) -> bool:
        """Check if venue uses Databento (canonical venue name)."""
        return venue in self.all_databento_venues

    def is_tardis_exchange(self, exchange: str) -> bool:
        """Check if exchange uses Tardis (API endpoint name)."""
        return exchange in self.all_tardis_exchanges

    def is_defi_venue(self, venue: str) -> bool:
        """Check if venue is a DeFi protocol."""
        return venue in self.all_defi_venues

    def get_venue_to_tardis_exchanges(self) -> Dict[str, List[str]]:
        """
        Get reverse mapping: canonical venue -> list of Tardis exchange names.
        
        Note: One canonical venue can map to multiple Tardis exchanges.
        E.g., OKX -> ["okex", "okex-futures", "okex-swap"]
        
        Returns:
            Dict mapping canonical venue names to list of Tardis exchange names
        """
        venue_to_exchanges: Dict[str, List[str]] = {}
        for tardis_exchange, canonical_venue in self.tardis_to_venue.items():
            if canonical_venue not in venue_to_exchanges:
                venue_to_exchanges[canonical_venue] = []
            venue_to_exchanges[canonical_venue].append(tardis_exchange)
        return venue_to_exchanges

    def get_tardis_exchange_for_venue(self, canonical_venue: str) -> Optional[str]:
        """
        Get primary Tardis exchange name for a canonical venue.
        
        For venues with multiple Tardis endpoints (e.g., OKX), returns the first/primary one.
        For simple venues like UPBIT, COINBASE, returns the single Tardis exchange name.
        
        Args:
            canonical_venue: Canonical venue name (e.g., "UPBIT", "COINBASE", "OKX")
            
        Returns:
            Tardis exchange name (lowercase) or None if not found
        """
        # Direct lookup in reverse mapping
        for tardis_exchange, venue in self.tardis_to_venue.items():
            if venue == canonical_venue:
                return tardis_exchange
        return None

    def convert_to_tardis_exchange(self, exchange_or_venue: str) -> str:
        """
        Convert exchange name to Tardis API format (lowercase).
        
        Handles both:
        - Canonical venue names: UPBIT -> upbit, COINBASE -> coinbase
        - Already lowercase Tardis names: upbit -> upbit
        
        Args:
            exchange_or_venue: Exchange name (could be canonical venue or Tardis name)
            
        Returns:
            Lowercase Tardis exchange name
        """
        # If it's uppercase, it's likely a canonical venue name
        upper_name = exchange_or_venue.upper()
        lower_name = exchange_or_venue.lower()
        
        # Check if it's a canonical venue name
        tardis_name = self.get_tardis_exchange_for_venue(upper_name)
        if tardis_name:
            return tardis_name
        
        # Check if it's already a valid Tardis exchange name
        if lower_name in self.all_tardis_exchanges:
            return lower_name
        
        # Return lowercase as fallback
        return lower_name

    def get_defi_mvp_tokens(self) -> List[str]:
        """Get MVP token list, checking environment variable first."""
        env_tokens = _get_env_config("DEFI_MVP_TOKENS", "")
        if env_tokens:
            return [t.strip().upper() for t in env_tokens.split(",")]
        return self.defi_mvp_base_currencies

    def get_databento_exchange_id(self, venue: str) -> Optional[str]:
        """Get Databento exchange identifier for canonical venue."""
        return self.venue_to_databento.get(venue)

    # CRITICAL: Map venue+instrument_type → Tardis exchange endpoint
    # Note: HYPERLIQUID and ASTER use direct APIs, not Tardis
    venue_instrument_type_to_tardis: Dict[tuple, str] = field(
        default_factory=lambda: {
            # Binance mappings
            ("BINANCE-SPOT", "SPOT_PAIR"): "binance",
            ("BINANCE-FUTURES", "PERPETUAL"): "binance-futures",
            ("BINANCE-FUTURES", "FUTURE"): "binance-futures",
            # OKX mappings (CRITICAL: instrument_type determines endpoint)
            ("OKX", "SPOT_PAIR"): "okex",
            ("OKX", "PERPETUAL"): "okex-swap",
            ("OKX", "FUTURE"): "okex-futures",
            # Bybit mappings
            ("BYBIT", "SPOT_PAIR"): "bybit-spot",
            ("BYBIT", "PERPETUAL"): "bybit",
            ("BYBIT", "FUTURE"): "bybit",
            # Deribit (unified endpoint)
            ("DERIBIT", "SPOT_PAIR"): "deribit",
            ("DERIBIT", "PERPETUAL"): "deribit",
            ("DERIBIT", "FUTURE"): "deribit",
            ("DERIBIT", "OPTION"): "deribit",
            # Upbit (spot only - Korean exchange for kimchi premium)
            ("UPBIT", "SPOT_PAIR"): "upbit",
            # Coinbase (spot only - for coinbase premium)
            ("COINBASE", "SPOT_PAIR"): "coinbase",
        }
    )

    # Which Tardis exchanges map to which instrument types (for filtering)
    tardis_exchange_instrument_types: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "binance": ["SPOT_PAIR"],
            "binance-futures": ["PERPETUAL", "FUTURE"],
            "okex": ["SPOT_PAIR"],
            "okex-swap": ["PERPETUAL"],
            "okex-futures": ["FUTURE"],
            "bybit": ["PERPETUAL", "FUTURE"],
            "bybit-spot": ["SPOT_PAIR"],
            "deribit": ["SPOT_PAIR", "PERPETUAL", "FUTURE", "OPTION"],
            "upbit": ["SPOT_PAIR"],  # Spot only (Korean exchange)
            "coinbase": ["SPOT_PAIR"],  # Spot only
        }
    )

    # Venues that require MVP base asset filtering (spot only venues for premium calculations)
    # These venues will only include instruments for the 21 MVP base assets
    spot_mvp_filtered_venues: List[str] = field(
        default_factory=lambda: [
            "UPBIT",  # Korean exchange - for kimchi premium
            "COINBASE",  # Coinbase - for coinbase premium
        ]
    )

    def get_data_provider(self, venue: str) -> Optional[str]:
        """Get data provider for a venue (tardis, databento, hyperliquid_api, aster_api, the_graph, protocol_sdk)."""
        # Check if it's a Tardis venue
        if venue in self.tardis_to_venue.values() or any(
            venue == v for v in self.tardis_to_venue.values()
        ):
            return "tardis"
        # Check if it's a Databento venue
        if venue in self.all_databento_venues:
            return "databento"
        # Check venue_to_data_provider mapping
        return self.venue_to_data_provider.get(venue)


@dataclass
class DataTypeConfig:
    """CRITICAL: Data types per instrument type (fixes 66% false positives)"""

    instrument_data_types: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "SPOT_PAIR": ["trades", "book_snapshot_5"],
            "PERPETUAL": [
                "trades",
                "book_snapshot_5",
                "derivative_ticker",
                "liquidations",
            ],
            "FUTURE": [
                "trades",
                "book_snapshot_5",
                "derivative_ticker",
                "liquidations",
            ],
            "OPTION": ["options_chain"],
        }
    )

    default_data_types: List[str] = field(
        default_factory=lambda: [
            "trades",
            "book_snapshot_5",
            "derivative_ticker",
            "liquidations",
            "options_chain",
        ]
    )

    # Instrument type filters (exclude complex types we don't want to process)
    excluded_instrument_types: List[str] = field(
        default_factory=lambda: ["combo"]  # Exclude Deribit combo strategies
    )

    # Complex option strategy filters (Deribit specific - exclude complex strategies)
    excluded_deribit_strategies: List[str] = field(
        default_factory=lambda: [
            "PS-",
            "STRG-",
            "CBUT-",
            "CCOND-",
            "PDIAG-",
            "PBUT-",
            "ICOND-",
            "BOX-",
            "FS-",
            "RR-",
            "CSR12-",
            "PSR12-",
            "CSR13-",
            "PSR13-",
            "CCAL-",
            "CDIAG-",
        ]
    )


@dataclass
class ExchangeInstrumentConfig:
    """Valid instrument types and quote currencies per exchange (CORRECTED canonical venues)"""

    exchange_instrument_types: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "BINANCE-SPOT": ["SPOT_PAIR"],  # Spot only
            "BINANCE-FUTURES": ["PERPETUAL", "FUTURE"],  # Derivatives only
            "DERIBIT": ["PERPETUAL", "FUTURE", "OPTION"],  # Full derivatives exchange
            "BYBIT": ["SPOT_PAIR", "PERPETUAL"],  # Combined
            "OKX": ["SPOT_PAIR", "PERPETUAL", "FUTURE"],  # Combined
            "UPBIT": ["SPOT_PAIR"],  # Spot only (Korean exchange for kimchi premium)
            "COINBASE": ["SPOT_PAIR"],  # Spot only (for coinbase premium)
        }
    )

    valid_quote_currencies: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "BINANCE-SPOT": ["USDT"],  # STRICT: Only USDT
            "BINANCE-FUTURES": ["USDT"],  # STRICT: Only USDT
            "DERIBIT": ["USD", "USDC"],  # Options exchange
            "BYBIT": ["USDT"],  # STRICT: Only USDT
            "OKX": ["USDT"],  # STRICT: Only USDT
            "UPBIT": ["KRW"],  # Korean Won (for kimchi premium calculations)
            "COINBASE": ["USD"],  # US Dollar (for coinbase premium calculations)
        }
    )

    derivative_exchanges: List[str] = field(
        default_factory=lambda: [
            "DERIBIT",
            "BINANCE-FUTURES",
            "OKX",
            "BYBIT",
        ]
    )

    # Excluded base currencies per exchange (e.g., deprecated tokens, leveraged products)
    excluded_base_currencies: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "OKX": ["USTC"],  # USTC (Terra Classic) deprecated
            "BYBIT": [],  # No base currency exclusions
        }
    )

    # Excluded symbol patterns per exchange (e.g., leveraged products)
    excluded_symbol_patterns: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "BYBIT": [
                "3L",  # 3x leveraged LONG products
                "2L",  # 2x leveraged LONG products
                "3S",  # 3x leveraged SHORT products
                "2S",  # 2x leveraged SHORT products
            ],
            "OKX": [],  # No symbol pattern exclusions
        }
    )

    # Symbol format per exchange
    # Most exchanges use BASE-QUOTE (e.g., BTC-USD, SOL-USDT)
    # Some exchanges like Upbit use QUOTE-BASE (e.g., KRW-BTC, KRW-SOL)
    symbol_format: Dict[str, str] = field(
        default_factory=lambda: {
            "UPBIT": "QUOTE-BASE",  # Upbit uses KRW-SOL format (quote first)
            # All other exchanges use BASE-QUOTE by default
        }
    )

    def get_symbol_format(self, venue: str) -> str:
        """Get symbol format for a venue. Returns 'BASE-QUOTE' if not specified."""
        return self.symbol_format.get(venue, "BASE-QUOTE")


