"""
Instrument Registry - Comprehensive mapping of venues, instrument types, and symbols.

Provides automatic conversion between different formats:
- Frontend format: Simple selection (venue, type, symbol)
- GCS format: VENUE:PRODUCT_TYPE:SYMBOL@SETTLEMENT
- NautilusTrader format: SYMBOL.VENUE
"""
from typing import Dict, List, Optional, Tuple
from enum import Enum


class VenueType(Enum):
    """Venue categories."""
    CEFI = "cefi"
    TRADFI = "tradfi"


class ProductType(Enum):
    """Product types for CeFi venues."""
    SPOT = "SPOT"
    PERPETUAL = "PERPETUAL"
    FUTURE = "FUTURE"
    OPTION = "OPTION"


# Supported venues configuration
VENUES_CONFIG = {
    "cefi": {
        "BINANCE": {
            "name": "Binance",
            "gcs_code": "BINANCE",
            "nautilus_code": "BINANCE",
            "types": ["SPOT", "PERPETUAL"],
            "gcs_prefix": "BINANCE",
            "spot_gcs_prefix": "BINANCE",
            "futures_gcs_prefix": "BINANCE-FUTURES",
        },
        "BYBIT": {
            "name": "Bybit",
            "gcs_code": "BYBIT",
            "nautilus_code": "BYBIT",
            "types": ["SPOT", "PERPETUAL"],
            "gcs_prefix": "BYBIT",
        },
        "OKX": {
            "name": "OKX",
            "gcs_code": "OKX",
            "nautilus_code": "OKX",
            "types": ["SPOT", "PERPETUAL", "FUTURE"],
            "gcs_prefix": "OKX",
        },
        "DERIBIT": {
            "name": "Deribit",
            "gcs_code": "DERIBIT",
            "nautilus_code": "DERIBIT",
            "types": ["PERPETUAL", "FUTURE", "OPTION"],
            "gcs_prefix": "DERIBIT",
        },
    },
    "tradfi": {
        "CME": {
            "name": "CME",
            "gcs_code": "CME",
            "nautilus_code": "CME",
            "types": ["FUTURE", "OPTION"],
            "gcs_prefix": "CME",
        },
        "CBOE": {
            "name": "CBOE",
            "gcs_code": "CBOE",
            "nautilus_code": "CBOE",
            "types": ["INDEX"],
            "gcs_prefix": "CBOE",
        },
        "NASDAQ": {
            "name": "NASDAQ",
            "gcs_code": "NASDAQ",
            "nautilus_code": "NASDAQ",
            "types": ["EQUITY"],
            "gcs_prefix": "NASDAQ",
        },
        "NYSE": {
            "name": "NYSE",
            "gcs_code": "NYSE",
            "nautilus_code": "NYSE",
            "types": ["EQUITY"],
            "gcs_prefix": "NYSE",
        },
    }
}

# Common instruments per venue (can be expanded)
COMMON_INSTRUMENTS = {
    "BINANCE": {
        "SPOT": ["BTC-USDT", "ETH-USDT", "BNB-USDT", "SOL-USDT", "XRP-USDT"],
        "PERPETUAL": ["BTC-USDT", "ETH-USDT", "BNB-USDT", "SOL-USDT", "XRP-USDT"],
    },
    "BYBIT": {
        "SPOT": ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT"],
        "PERPETUAL": ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT"],
    },
    "OKX": {
        "SPOT": ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT"],
        "PERPETUAL": ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT"],
        "FUTURE": ["BTC-USDT", "ETH-USDT"],
    },
    "DERIBIT": {
        "PERPETUAL": ["BTC-USD", "ETH-USD"],
        "FUTURE": ["BTC-USD", "ETH-USD"],
        "OPTION": ["BTC-USD", "ETH-USD"],
    },
}


def get_venues_by_category(category: str) -> List[Dict[str, str]]:
    """
    Get list of venues for a category.
    
    Args:
        category: "cefi" or "tradfi"
        
    Returns:
        List of venue info dicts
    """
    venues = VENUES_CONFIG.get(category, {})
    return [
        {
            "code": code,
            "name": info["name"],
            "types": info["types"],
        }
        for code, info in venues.items()
    ]


def get_instrument_types_for_venue(venue_code: str) -> List[str]:
    """
    Get available instrument types for a venue.
    
    Args:
        venue_code: Venue code (e.g., "BINANCE", "BYBIT")
        
    Returns:
        List of product types
    """
    for category in VENUES_CONFIG.values():
        if venue_code in category:
            return category[venue_code]["types"]
    return []


def get_common_instruments(venue_code: str, product_type: str) -> List[str]:
    """
    Get common instruments for a venue and product type.
    
    Args:
        venue_code: Venue code
        product_type: Product type (SPOT, PERPETUAL, etc.)
        
    Returns:
        List of instrument symbols
    """
    return COMMON_INSTRUMENTS.get(venue_code, {}).get(product_type, [])


def convert_to_gcs_format(venue_code: str, product_type: str, symbol: str, settlement: str = "LIN") -> str:
    """
    Convert venue/product/symbol to GCS format.
    
    Format: VENUE:PRODUCT_TYPE:SYMBOL@SETTLEMENT
    
    Args:
        venue_code: Venue code (e.g., "BINANCE")
        product_type: Product type (e.g., "PERPETUAL", "SPOT")
        symbol: Symbol (e.g., "BTC-USDT")
        settlement: Settlement type ("LIN" for linear, "INV" for inverse)
        
    Returns:
        GCS format instrument ID
    """
    # Get GCS prefix for venue
    venue_gcs = None
    for category in VENUES_CONFIG.values():
        if venue_code in category:
            venue_info = category[venue_code]
            if product_type == "SPOT" and "spot_gcs_prefix" in venue_info:
                venue_gcs = venue_info["spot_gcs_prefix"]
            elif product_type in ["PERPETUAL", "FUTURE"] and "futures_gcs_prefix" in venue_info:
                venue_gcs = venue_info["futures_gcs_prefix"]
            else:
                venue_gcs = venue_info.get("gcs_prefix", venue_info["gcs_code"])
            break
    
    if not venue_gcs:
        venue_gcs = venue_code
    
    return f"{venue_gcs}:{product_type}:{symbol}@{settlement}"


def convert_to_nautilus_format(venue_code: str, product_type: str, symbol: str) -> str:
    """
    Convert to NautilusTrader format.
    
    Format: SYMBOL.VENUE
    
    Args:
        venue_code: Venue code
        product_type: Product type (not used in Nautilus format)
        symbol: Symbol
        
    Returns:
        NautilusTrader format instrument ID
    """
    # Get Nautilus venue code
    venue_nautilus = None
    for category in VENUES_CONFIG.values():
        if venue_code in category:
            venue_nautilus = category[venue_code]["nautilus_code"]
            break
    
    if not venue_nautilus:
        venue_nautilus = venue_code
    
    return f"{symbol}.{venue_nautilus}"


def convert_gcs_to_components(gcs_instrument_id: str) -> Tuple[str, str, str, str]:
    """
    Parse GCS format instrument ID into components.
    
    Args:
        gcs_instrument_id: GCS format (e.g., "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN")
        
    Returns:
        Tuple of (venue_code, product_type, symbol, settlement)
    """
    if ":" not in gcs_instrument_id:
        raise ValueError(f"Invalid GCS format: {gcs_instrument_id}")
    
    parts = gcs_instrument_id.split(":")
    venue_gcs = parts[0]
    product_type = parts[1] if len(parts) > 1 else "PERPETUAL"
    symbol_with_settlement = parts[2] if len(parts) > 2 else parts[1]
    
    if "@" in symbol_with_settlement:
        symbol, settlement = symbol_with_settlement.split("@")
    else:
        symbol = symbol_with_settlement
        settlement = "LIN"
    
    # Map GCS venue back to venue code
    venue_code = None
    for category in VENUES_CONFIG.values():
        for code, info in category.items():
            if venue_gcs == info.get("gcs_prefix") or venue_gcs == info.get("gcs_code"):
                venue_code = code
                break
            if venue_gcs == info.get("spot_gcs_prefix") or venue_gcs == info.get("futures_gcs_prefix"):
                venue_code = code
                break
        if venue_code:
            break
    
    if not venue_code:
        # Try to infer from venue_gcs
        if "BINANCE" in venue_gcs:
            venue_code = "BINANCE"
        else:
            venue_code = venue_gcs.split("-")[0] if "-" in venue_gcs else venue_gcs
    
    return (venue_code, product_type, symbol, settlement)


def get_config_instrument_id(venue_code: str, product_type: str, symbol: str) -> str:
    """
    Get config format instrument ID.
    
    For Binance: Uses "SYMBOL.VENUE" format
    For others: Uses "VENUE:PRODUCT_TYPE:SYMBOL" format
    
    Args:
        venue_code: Venue code
        product_type: Product type
        symbol: Symbol
        
    Returns:
        Config format instrument ID
    """
    if venue_code == "BINANCE":
        if product_type == "PERPETUAL":
            return f"{symbol}.BINANCE"  # Binance futures uses .BINANCE
        else:
            return f"{symbol}.BINANCE"
    else:
        return f"{venue_code}:{product_type}:{symbol}"

