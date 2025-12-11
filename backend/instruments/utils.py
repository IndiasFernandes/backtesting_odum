"""
Utility functions for instrument ID and venue name conversion.

Handles conversion between config format and GCS format for various exchanges.
"""
from typing import Dict, Optional
from backend.instruments.registry import (
    convert_to_gcs_format,
    convert_to_nautilus_format,
    get_config_instrument_id,
    convert_gcs_to_components,
)


# Mapping from config venue names to GCS venue names
VENUE_MAP: Dict[str, str] = {
    # Binance
    "BINANCE": "BINANCE-FUTURES",  # Default to futures if not specified
    "BINANCE-FUTURES": "BINANCE-FUTURES",
    "BINANCE-SPOT": "BINANCE",
    
    # Bybit
    "BYBIT": "BYBIT",
    
    # OKX
    "OKX": "OKX",
    
    # Deribit
    "DERIBIT": "DERIBIT",
}


# Mapping from config instrument ID format to GCS format
# Format: {exchange}:{product_type}:{symbol}@{settlement}
# Example: BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN
def convert_instrument_id_to_gcs_format(instrument_id: str, venue_name: Optional[str] = None) -> str:
    """
    Convert instrument ID from config format to GCS format.
    
    Uses the new instrument_registry for comprehensive conversion.
    
    Config formats:
    - "BTC-USDT.BINANCE" → "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN"
    - "BYBIT:PERPETUAL:BTC-USDT" → "BYBIT:PERPETUAL:BTC-USDT@LIN"
    - "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN" → unchanged (already in GCS format)
    
    Args:
        instrument_id: Instrument ID in config format or GCS format
        venue_name: Optional venue name to help determine format
        
    Returns:
        Instrument ID in GCS format: VENUE:PRODUCT_TYPE:SYMBOL@SETTLEMENT
    """
    # If already in GCS format, return as-is
    if ":" in instrument_id and "@" in instrument_id:
        return instrument_id
    
    try:
        # Try to parse using registry
        if ":" in instrument_id:
            # Format: VENUE:PRODUCT_TYPE:SYMBOL
            parts = instrument_id.split(":")
            if len(parts) >= 3:
                venue_code = parts[0]
                product_type = parts[1]
                symbol = parts[2]
                return convert_to_gcs_format(venue_code, product_type, symbol)
        elif "." in instrument_id:
            # Format: SYMBOL.VENUE (e.g., "BTC-USDT.BINANCE")
            parts = instrument_id.split(".")
            if len(parts) == 2:
                symbol = parts[0]
                venue_code = parts[1].upper()
                # Determine product type - default to PERPETUAL for Binance, SPOT otherwise
                product_type = "PERPETUAL" if venue_code == "BINANCE" else "SPOT"
                return convert_to_gcs_format(venue_code, product_type, symbol)
    except Exception:
        pass
    
    # Fallback to old logic for compatibility
    # Handle simple symbol format (e.g., "BTCUSDT")
    symbol = instrument_id
    if "-" not in symbol and len(symbol) > 4:
        if symbol.endswith("USDT"):
            base = symbol[:-4]
            symbol = f"{base}-USDT"
        elif symbol.endswith("USD"):
            base = symbol[:-3]
            symbol = f"{base}-USD"
    
    # Default to Binance Futures if venue not specified
    venue_code = venue_name.upper() if venue_name else "BINANCE"
    product_type = "PERPETUAL"
    
    return convert_to_gcs_format(venue_code, product_type, symbol)


def convert_gcs_instrument_to_config_format(gcs_instrument_id: str) -> str:
    """
    Convert GCS format instrument ID to config format.
    
    Example: "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN" → "BTC-USDT.BINANCE"
    
    Args:
        gcs_instrument_id: Instrument ID in GCS format
        
    Returns:
        Instrument ID in config format: SYMBOL.VENUE
    """
    if ":" not in gcs_instrument_id:
        return gcs_instrument_id  # Already in config format
    
    # Parse GCS format: VENUE:PRODUCT_TYPE:SYMBOL@SETTLEMENT
    parts = gcs_instrument_id.split(":")
    if len(parts) >= 3:
        venue_gcs = parts[0]  # "BINANCE-FUTURES"
        symbol_with_settlement = parts[-1]  # "BTC-USDT@LIN"
        symbol = symbol_with_settlement.split("@")[0]  # "BTC-USDT"
        
        # Map venue back to config format
        # Reverse lookup in VENUE_MAP
        venue_config = None
        for config_venue, gcs_venue in VENUE_MAP.items():
            if gcs_venue == venue_gcs:
                venue_config = config_venue
                break
        
        if not venue_config:
            # Default mapping
            if "FUTURES" in venue_gcs:
                venue_config = "BINANCE"
            else:
                venue_config = venue_gcs
        
        return f"{symbol}.{venue_config}"
    
    return gcs_instrument_id


def normalize_venue_name(venue_name: str, is_futures: bool = True) -> str:
    """
    Normalize venue name for NautilusTrader.
    
    Args:
        venue_name: Venue name from config
        is_futures: Whether this is a futures/derivatives venue
        
    Returns:
        Normalized venue name for NautilusTrader
    """
    venue_upper = venue_name.upper()
    
    # Map to NautilusTrader venue names
    if venue_upper in ("BINANCE", "BINANCE-FUTURES"):
        return "BINANCE"  # NautilusTrader uses "BINANCE" for both spot and futures
    elif venue_upper == "BYBIT":
        return "BYBIT"
    elif venue_upper == "OKX":
        return "OKX"
    elif venue_upper == "DERIBIT":
        return "DERIBIT"
    
    return venue_upper


def get_instrument_id_for_nautilus(config_instrument_id: str, venue_name: str) -> str:
    """
    Get the instrument ID format that NautilusTrader expects.
    
    NautilusTrader uses format: SYMBOL.VENUE
    Example: "BTC-USDT.BINANCE"
    
    Args:
        config_instrument_id: Instrument ID from config
        venue_name: Venue name from config
        
    Returns:
        Instrument ID in NautilusTrader format
    """
    # If already in NautilusTrader format, return as-is
    if "." in config_instrument_id and ":" not in config_instrument_id:
        return config_instrument_id
    
    try:
        # Try to parse and convert using registry
        if ":" in config_instrument_id:
            # GCS format: VENUE:PRODUCT_TYPE:SYMBOL@SETTLEMENT
            venue_code, product_type, symbol, _ = convert_gcs_to_components(config_instrument_id)
            return convert_to_nautilus_format(venue_code, product_type, symbol)
        elif "." in config_instrument_id:
            # Config format: SYMBOL.VENUE
            parts = config_instrument_id.split(".")
            if len(parts) == 2:
                symbol = parts[0]
                venue_code = parts[1].upper()
                product_type = "PERPETUAL" if venue_code == "BINANCE" else "SPOT"
                return convert_to_nautilus_format(venue_code, product_type, symbol)
    except Exception:
        pass
    
    # Fallback: Simple symbol - add venue
    normalized_venue = normalize_venue_name(venue_name)
    return f"{config_instrument_id}.{normalized_venue}"

