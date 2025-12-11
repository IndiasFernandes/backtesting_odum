"""
Custom instrument provider for managing custom instruments.
"""
from typing import Dict, Optional, List
from pathlib import Path
from decimal import Decimal
import time

from nautilus_trader.model.instruments.base import Instrument
from nautilus_trader.model.instruments.provider import InstrumentProvider
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Price, Quantity

from backend.instruments.custom_instruments import (
    DeFiPoolInstrument,
    SportsMarketInstrument,
    TradFiInstrument,
)
from backend.config.loader import ConfigLoader
from backend.data.catalog import CatalogManager


class CustomInstrumentProvider(InstrumentProvider):
    """
    Custom instrument provider for DeFi, Sports, and other non-standard instruments.
    
    This provider loads instruments from JSON configs and manages them
    for use in backtesting and live trading.
    """
    
    def __init__(self, catalog_manager: Optional[CatalogManager] = None):
        super().__init__()
        self._instruments: Dict[InstrumentId, Instrument] = {}
        self._loaded = False
        self.catalog_manager = catalog_manager
        self.configs_dir = Path("external/data_downloads/configs")
    
    def load_all(self, filters: Optional[Dict] = None) -> None:
        """
        Load all instruments from config files.
        
        Args:
            filters: Optional filters (e.g., {"type": "defi_pool"})
        """
        if self._loaded:
            return
        
        # Load all config files
        if not self.configs_dir.exists():
            return
        
        for config_file in self.configs_dir.glob("*.json"):
            try:
                instrument = self.load_from_config(config_file)
                if instrument:
                    # Apply filters if provided
                    if filters:
                        instrument_type = self._get_instrument_type(instrument)
                        if filters.get("type") and instrument_type != filters["type"]:
                            continue
                    
                    self.add_instrument(instrument)
            except Exception as e:
                print(f"Warning: Failed to load instrument from {config_file}: {e}")
        
        self._loaded = True
    
    def load(self, instrument_id: InstrumentId) -> None:
        """
        Load a specific instrument from config.
        
        Args:
            instrument_id: Instrument ID to load
        """
        # Try to find config file matching instrument ID
        for config_file in self.configs_dir.glob("*.json"):
            try:
                loader = ConfigLoader(str(config_file))
                config = loader.load()
                
                config_instrument_id = InstrumentId.from_str(config["instrument"]["id"])
                if config_instrument_id == instrument_id:
                    instrument = self.load_from_config(config_file)
                    if instrument:
                        self.add_instrument(instrument)
                        return
            except Exception:
                continue
    
    def load_from_config(self, config_path: Path) -> Optional[Instrument]:
        """
        Load instrument from JSON config file.
        
        Args:
            config_path: Path to config JSON file
            
        Returns:
            Instrument instance or None if failed
        """
        try:
            loader = ConfigLoader(str(config_path))
            config = loader.load()
            
            instrument_config = config["instrument"]
            instrument_type = instrument_config.get("type", "crypto_perpetual")
            
            if instrument_type == "defi_pool":
                return self._create_defi_pool_instrument(config)
            elif instrument_type == "sports_market":
                return self._create_sports_market_instrument(config)
            elif instrument_type == "tradfi":
                return self._create_tradfi_instrument(config)
            else:
                # Unknown type - skip (might be crypto_perpetual handled elsewhere)
                return None
        except Exception as e:
            print(f"Error loading instrument from {config_path}: {e}")
            return None
    
    def _create_defi_pool_instrument(self, config: Dict) -> DeFiPoolInstrument:
        """Create DeFi pool instrument from config."""
        instrument_config = config["instrument"]
        instrument_id = InstrumentId.from_str(instrument_config["id"])
        
        # Get timestamps
        now_ns = int(time.time() * 1_000_000_000)
        
        return DeFiPoolInstrument(
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
    
    def _create_sports_market_instrument(self, config: Dict) -> SportsMarketInstrument:
        """Create sports market instrument from config."""
        instrument_config = config["instrument"]
        instrument_id = InstrumentId.from_str(instrument_config["id"])
        
        # Get timestamps
        now_ns = int(time.time() * 1_000_000_000)
        
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
            ts_event=now_ns,
            ts_init=now_ns,
        )
    
    def _create_tradfi_instrument(self, config: Dict) -> TradFiInstrument:
        """Create TradFi instrument from config."""
        instrument_config = config["instrument"]
        instrument_id = InstrumentId.from_str(instrument_config["id"])
        
        # Get timestamps
        now_ns = int(time.time() * 1_000_000_000)
        
        return TradFiInstrument(
            instrument_id=instrument_id,
            asset_type=instrument_config["asset_type"],
            exchange=instrument_config["exchange"],
            symbol=instrument_config["symbol"],
            currency=instrument_config["currency"],
            price_precision=instrument_config.get("price_precision", 2),
            size_precision=instrument_config.get("size_precision", 0),
            ts_event=now_ns,
            ts_init=now_ns,
        )
    
    def _get_instrument_type(self, instrument: Instrument) -> str:
        """Get instrument type string."""
        if isinstance(instrument, DeFiPoolInstrument):
            return "defi_pool"
        elif isinstance(instrument, SportsMarketInstrument):
            return "sports_market"
        elif isinstance(instrument, TradFiInstrument):
            return "tradfi"
        else:
            return "crypto_perpetual"
    
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
        
        # Write to catalog if catalog manager is available
        if self.catalog_manager:
            catalog = self.catalog_manager.get_catalog()
            catalog.write_data([instrument])
    
    def remove_instrument(self, instrument_id: InstrumentId) -> None:
        """
        Remove an instrument from the provider.
        
        Args:
            instrument_id: Instrument ID to remove
        """
        self._instruments.pop(instrument_id, None)

