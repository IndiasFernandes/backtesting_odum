"""
Shared Schemas for Unified Cloud Services

This module contains shared dataclasses and schemas used across multiple services:
- instruments-service
- market-tick-data-handler
- market-data-processing-service

These schemas provide consistent data structures for:
- Instrument key parsing
- Validation configuration
- Download orchestration
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from enum import Enum

from unified_cloud_services.models.instrument import Venue, InstrumentType


@dataclass
class InstrumentKey:
    """
    Instrument key following VENUE:INSTRUMENT_TYPE:SYMBOL format.
    
    Used for canonical instrument identification across all services.
    
    Examples:
        - BINANCE-FUTURES:PERPETUAL:BTC-USDT
        - DERIBIT:OPTION:ETH-USDC-251027-3500-CALL
        - CME:FUTURE:ES.FUT
    """
    venue: Venue
    instrument_type: InstrumentType
    symbol: str
    expiry: Optional[str] = None  # For futures/options (YYMMDD format)
    option_type: Optional[str] = None  # C or P for options

    def __str__(self) -> str:
        """Format: venue:type:symbol:expiry:option_type"""
        parts = [self.venue.value, self.instrument_type.value, self.symbol]
        if self.expiry:
            parts.append(self.expiry)
        if self.option_type:
            parts.append(self.option_type)
        return ":".join(parts)

    @classmethod
    def from_string(cls, instrument_key_str: str) -> "InstrumentKey":
        """Parse instrument key from string"""
        parts = instrument_key_str.split(":")
        if len(parts) < 3:
            raise ValueError(f"Invalid instrument key format: {instrument_key_str}")

        venue = Venue(parts[0])
        instrument_type = InstrumentType(parts[1])
        symbol = parts[2]
        expiry = parts[3] if len(parts) > 3 else None
        option_type = parts[4] if len(parts) > 4 else None

        return cls(
            venue=venue,
            instrument_type=instrument_type,
            symbol=symbol,
            expiry=expiry,
            option_type=option_type,
        )

    @classmethod
    def parse_for_tardis(cls, instrument_key_str: str) -> dict:
        """
        Parse instrument key and return venue/symbol for Tardis API and post-validation storage.
        
        Converts VENUE:INSTRUMENT_TYPE:SYMBOL → venue + symbol for streaming architecture compatibility.
        
        Args:
            instrument_key_str: Instrument key in format VENUE:INSTRUMENT_TYPE:SYMBOL
            
        Returns:
            Dict with venue, symbol, exchange (for Tardis), tardis_symbol
        """
        parts = instrument_key_str.split(":")
        if len(parts) < 3:
            raise ValueError(f"Invalid instrument key format: {instrument_key_str}")

        venue = parts[0]  # BINANCE, DERIBIT, etc.
        instrument_type = parts[1]  # SPOT_PAIR, PERPETUAL, etc.
        symbol = ":".join(parts[2:])  # BTC-USDT, BTC-USD-50000-241225-CALL, etc.

        # Map venue to Tardis exchange (corrected mapping based on Tardis API allowed values)
        venue_to_tardis = {
            "BINANCE-SPOT": "binance",
            "BINANCE-FUTURES": "binance-futures",
            "DERIBIT": "deribit",
            "BYBIT": "bybit",
            "OKX": "okex",  # Corrected: okx → okex
            "OKX-FUTURES": "okex-futures",
            "UPBIT": "upbit",  # Korean exchange (spot only)
            "COINBASE": "coinbase",  # Coinbase (spot only)
        }

        tardis_exchange = venue_to_tardis.get(venue, venue.lower())

        # Convert symbol to proper Tardis format based on exchange
        if tardis_exchange in ["binance", "binance-futures"]:
            # Binance format: SOL-USDT → solusdt (lowercase, no dash)
            tardis_symbol_formatted = symbol.replace("-", "").lower()
        elif tardis_exchange == "deribit":
            # Deribit format: keep original but lowercase
            tardis_symbol_formatted = symbol.lower()
        elif tardis_exchange == "upbit":
            # Upbit format: Our canonical key has BASE-QUOTE (VET-KRW) but Tardis expects QUOTE-BASE (KRW-VET) uppercase
            # Reverse the symbol parts and keep uppercase
            symbol_parts = symbol.split("-")
            if len(symbol_parts) == 2:
                tardis_symbol_formatted = f"{symbol_parts[1]}-{symbol_parts[0]}"  # VET-KRW → KRW-VET
            else:
                tardis_symbol_formatted = symbol  # Fallback
        elif tardis_exchange == "coinbase":
            # Coinbase format: Our canonical key has BASE-QUOTE (SOL-USD), Tardis expects same format uppercase
            tardis_symbol_formatted = symbol.upper()  # SOL-USD stays SOL-USD
        else:
            # Default: lowercase
            tardis_symbol_formatted = symbol.lower()

        return {
            "venue": venue,  # For post-validation storage (streaming compatible)
            "symbol": symbol,  # For post-validation storage (canonical format)
            "tardis_exchange": tardis_exchange,  # For Tardis API call
            "tardis_symbol": tardis_symbol_formatted,  # For Tardis API call (exchange-specific formatting)
            "instrument_type": instrument_type,
        }


@dataclass
class ValidationConfig:
    """
    Configuration for validation operations - centralized validation settings.
    
    Used by both instruments-service and market-tick-data-handler for schema validation.
    """
    enable_schema_validation: bool = True
    enable_data_quality_validation: bool = True
    enable_timestamp_validation: bool = True
    strict_mode: bool = False
    max_duplicate_timestamps: int = 10
    max_duplicate_rows: int = 10
    max_invalid_prices: int = 0
    
    timestamp_format_patterns: List[str] = field(default_factory=lambda: [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    ])
    
    # Required columns by data type for raw data (Tardis schema uses exchange/symbol)
    required_columns_by_data_type: Dict[str, List[str]] = field(default_factory=lambda: {
        # Raw data schemas (exchange/symbol from Tardis)
        "trades": ["exchange", "symbol", "timestamp", "local_timestamp", "id", "side", "price", "amount"],
        "trades_validated": ["venue", "symbol", "timestamp", "local_timestamp", "timestamp_out", "id", "side", "price", "amount"],
        "book_snapshot_5": [
            "exchange", "symbol", "timestamp", "local_timestamp",
            "ask_price_0", "ask_volume_0", "bid_price_0", "bid_volume_0",
            "ask_price_1", "ask_volume_1", "bid_price_1", "bid_volume_1",
            "ask_price_2", "ask_volume_2", "bid_price_2", "bid_volume_2",
            "ask_price_3", "ask_volume_3", "bid_price_3", "bid_volume_3",
            "ask_price_4", "ask_volume_4", "bid_price_4", "bid_volume_4",
        ],
        "book_snapshot_5_validated": [
            "venue", "symbol", "timestamp", "local_timestamp", "timestamp_out",
            "ask_price_0", "ask_volume_0", "bid_price_0", "bid_volume_0",
            "ask_price_1", "ask_volume_1", "bid_price_1", "bid_volume_1",
            "ask_price_2", "ask_volume_2", "bid_price_2", "bid_volume_2",
            "ask_price_3", "ask_volume_3", "bid_price_3", "bid_volume_3",
            "ask_price_4", "ask_volume_4", "bid_price_4", "bid_volume_4",
        ],
        "liquidations": ["exchange", "symbol", "timestamp", "local_timestamp", "side", "price", "amount"],
        "liquidations_validated": ["venue", "symbol", "timestamp", "local_timestamp", "timestamp_out", "id", "side", "price", "amount"],
        "derivative_ticker": [
            "exchange", "symbol", "timestamp", "local_timestamp", "funding_timestamp",
            "funding_rate", "open_interest", "last_price", "index_price", "mark_price",
        ],
        "derivative_ticker_validated": [
            "venue", "symbol", "timestamp", "local_timestamp", "timestamp_out", "funding_timestamp",
            "funding_rate", "open_interest", "last_price", "index_price", "mark_price",
        ],
        "options_chain": [
            "exchange", "symbol", "timestamp", "local_timestamp", "timestamp_out", "type", "strike_price",
            "expiration", "open_interest", "last_price", "bid_price", "bid_amount", "bid_iv",
            "ask_price", "ask_amount", "ask_iv", "mark_price", "mark_iv", "underlying_index",
            "underlying_price", "delta", "gamma", "vega", "theta", "rho",
        ],
        "options_chain_validated": [
            "venue", "symbol", "timestamp", "local_timestamp", "timestamp_out", "type", "strike_price",
            "expiration", "open_interest", "last_price", "bid_price", "bid_amount", "bid_iv",
            "ask_price", "ask_amount", "ask_iv", "mark_price", "mark_iv", "underlying_index",
            "underlying_price", "delta", "gamma", "vega", "theta", "rho",
        ],
        # OHLCV schemas (for Hyperliquid, Aster, TradFi)
        "ohlcv_1m": ["timestamp", "open", "high", "low", "close", "volume"],
        "ohlcv_15m": ["timestamp", "open", "high", "low", "close", "volume"],
        "ohlcv_1h": ["timestamp", "open", "high", "low", "close", "volume"],
        
        # ============================================================
        # Optimized schemas for NautilusTrader backtesting
        # NOTE: instrument_key in canonical format (VENUE:TYPE:SYMBOL)
        # Convert to NautilusTrader format on read
        # ============================================================
        "trades_nautilus": ["instrument_key", "price", "size", "aggressor_side", "trade_id", "ts_event", "ts_init"],
        "book_snapshot_5_nautilus": [
            "instrument_key", "ts_event", "ts_init",
            "bid_price_0", "bid_size_0", "ask_price_0", "ask_size_0",
            "bid_price_1", "bid_size_1", "ask_price_1", "ask_size_1",
            "bid_price_2", "bid_size_2", "ask_price_2", "ask_size_2",
            "bid_price_3", "bid_size_3", "ask_price_3", "ask_size_3",
            "bid_price_4", "bid_size_4", "ask_price_4", "ask_size_4",
        ],
        "liquidations_nautilus": ["instrument_key", "price", "size", "aggressor_side", "ts_event", "ts_init"],
        "derivative_ticker_nautilus": ["instrument_key", "ts_event", "ts_init", "funding_rate", "index_price", "mark_price", "open_interest"],
    })


@dataclass
class DownloadTarget:
    """
    Target for download operation - used across all download orchestration.
    
    Defines a single instrument/data_type/date combination to download.
    """
    exchange: str
    instrument_id: str
    data_type: str
    date: datetime
    venue: str = None
    instrument_type: str = None
    expected_size_mb: float = 0.0
    priority: int = 1  # 1=high, 2=normal, 3=low
    shard_index: Optional[int] = None
    total_shards: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestrationResult:
    """
    Result from data orchestration operations - centralized result tracking.
    
    Aggregates results from batch download/upload operations.
    """
    total_targets: int
    successful_downloads: int
    failed_downloads: int
    successful_uploads: int
    failed_uploads: int
    total_data_size_mb: float
    total_duration: float
    memory_peak_usage: float
    batch_count: int
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    error_summary: List[str] = field(default_factory=list)

    @property
    def download_success_rate(self) -> float:
        return self.successful_downloads / self.total_targets if self.total_targets > 0 else 0.0

    @property
    def upload_success_rate(self) -> float:
        total_attempts = self.successful_uploads + self.failed_uploads
        return self.successful_uploads / total_attempts if total_attempts > 0 else 0.0

