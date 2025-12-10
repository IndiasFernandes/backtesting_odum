"""
Custom instruments module for extending NautilusTrader with non-standard instruments.
"""
from backend.instruments.custom_instruments import (
    DeFiPoolInstrument,
    SportsMarketInstrument,
    TradFiInstrument,
)

__all__ = [
    "DeFiPoolInstrument",
    "SportsMarketInstrument",
    "TradFiInstrument",
]

