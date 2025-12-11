"""Instrument factory for creating and registering instruments."""
import os
import time
from pathlib import Path
from typing import Dict, Any

from nautilus_trader.model.identifiers import InstrumentId, Venue, Symbol
from nautilus_trader.model.instruments import CryptoPerpetual
from decimal import Decimal
from nautilus_trader.model.objects import Price, Quantity, Currency
from nautilus_trader.persistence.catalog import ParquetDataCatalog

from backend.instruments.utils import get_instrument_id_for_nautilus


class InstrumentFactory:
    """Factory for creating and registering instruments in the catalog."""
    
    @staticmethod
    def create_and_register(
        config: Dict[str, Any],
        catalog: ParquetDataCatalog
    ) -> InstrumentId:
        """
        Create instrument from config and register it in the catalog.
        
        Args:
            config: Configuration dictionary
            catalog: ParquetDataCatalog instance
            
        Returns:
            InstrumentId instance
        """
        instrument_config = config["instrument"]
        venue_config = config["venue"]
        
        # Get instrument ID in NautilusTrader format
        config_instrument_id = instrument_config["id"]
        venue_name = venue_config["name"]
        nautilus_instrument_id_str = get_instrument_id_for_nautilus(config_instrument_id, venue_name)
        instrument_id = InstrumentId.from_str(nautilus_instrument_id_str)
        
        # Check if instrument already exists in catalog
        try:
            existing = catalog.instruments(instrument_ids=[instrument_id])
            if existing:
                return instrument_id
        except Exception:
            pass
        
        # Create instrument definition
        # For crypto perpetuals, we need to create a CryptoPerpetual instrument
        symbol = Symbol(instrument_id.symbol.value)
        venue = Venue(venue_config["name"])
        
        # Create a basic crypto perpetual instrument
        # Note: This is a simplified version - in production you'd load full instrument details
        base_currency_str = venue_config.get("base_currency", "USDT")
        
        # Extract base and quote currencies from instrument symbol (e.g., "BTC-USDT" -> BTC, USDT)
        symbol_parts = instrument_id.symbol.value.split("-")
        if len(symbol_parts) >= 2:
            base_currency_str = symbol_parts[0]  # BTC
            quote_currency_str = symbol_parts[1]  # USDT
        else:
            quote_currency_str = base_currency_str
        
        base_currency = Currency.from_str(base_currency_str)
        quote_currency = Currency.from_str(quote_currency_str)
        settlement_currency = Currency.from_str(base_currency_str)  # Usually same as base for perpetuals
        
        # Calculate price and size increments based on precision
        price_prec = instrument_config["price_precision"]
        size_prec = instrument_config["size_precision"]
        price_inc_str = f"0.{'0' * (price_prec - 1)}1" if price_prec > 0 else "1"
        size_inc_str = f"0.{'0' * (size_prec - 1)}1" if size_prec > 0 else "1"
        
        # Get current timestamp in nanoseconds
        now_ns = int(time.time() * 1_000_000_000)
        
        instrument = CryptoPerpetual(
            instrument_id=instrument_id,
            raw_symbol=Symbol(f"{instrument_id.symbol.value}-PERP"),
            base_currency=base_currency,
            quote_currency=quote_currency,
            settlement_currency=settlement_currency,
            is_inverse=False,  # Standard perpetual (not inverse)
            price_precision=price_prec,
            size_precision=size_prec,
            price_increment=Price.from_str(price_inc_str),
            size_increment=Quantity.from_str(size_inc_str),
            ts_event=now_ns,
            ts_init=now_ns,
            max_quantity=Quantity.from_str("1000000"),
            min_quantity=Quantity.from_str("0.001"),
            max_price=Price.from_str("1000000"),
            min_price=Price.from_str("0.01"),
            margin_init=Decimal("0.01"),  # 1% initial margin
            margin_maint=Decimal("0.005"),  # 0.5% maintenance margin
            maker_fee=Decimal(str(venue_config.get("maker_fee", 0.0002))),  # Maker fee from config (default 0.02%)
            taker_fee=Decimal(str(venue_config.get("taker_fee", 0.0004))),  # Taker fee from config (default 0.04%)
        )
        
        # Write instrument to catalog
        catalog.write_data([instrument])
        
        return instrument_id

