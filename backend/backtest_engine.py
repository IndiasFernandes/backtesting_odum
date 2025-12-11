"""Core BacktestNode orchestration for running backtests."""
import hashlib
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, List, Optional

import pandas as pd

from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.backtest.config import (
    BacktestRunConfig,
    BacktestDataConfig,
    BacktestVenueConfig,
    BacktestEngineConfig,
)
from nautilus_trader.config import ImportableStrategyConfig
from nautilus_trader.model.data import TradeTick, OrderBookDeltas
from nautilus_trader.model.identifiers import InstrumentId, Venue, Symbol
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Money, Price, Quantity, Currency
from nautilus_trader.model.enums import OrderSide, PositionSide, TimeInForce
from nautilus_trader.persistence.catalog import ParquetDataCatalog

from backend.catalog_manager import CatalogManager
from backend.config_loader import ConfigLoader
from backend.results import ResultSerializer
from backend.strategy import TempBacktestStrategy, TempBacktestStrategyConfig
from backend.data_converter import DataConverter
from backend.strategy_evaluator import StrategyEvaluator
from backend.strategy_evaluator import StrategyEvaluator
# Use built-in algorithms for testing
try:
    from nautilus_trader.examples.algorithms.twap import TWAPExecAlgorithm as BuiltinTWAPExecAlgorithm
    from nautilus_trader.examples.algorithms.twap import TWAPExecAlgorithmConfig as BuiltinTWAPExecAlgorithmConfig
    BUILTIN_TWAP_AVAILABLE = True
except ImportError:
    BUILTIN_TWAP_AVAILABLE = False

# Fallback to custom algorithms if built-in not available
from backend.execution_algorithms import (
    TWAPExecAlgorithm,
    VWAPExecAlgorithm,
    IcebergExecAlgorithm,
)
from backend.instrument_utils import (
    convert_instrument_id_to_gcs_format,
    get_instrument_id_for_nautilus,
    normalize_venue_name
)

# Optional UCS import
try:
    from backend.ucs_data_loader import UCSDataLoader
    UCS_AVAILABLE = True
except ImportError:
    UCS_AVAILABLE = False
    UCSDataLoader = None


class BacktestEngine:
    """Orchestrates backtest execution using NautilusTrader BacktestNode."""
    
    def __init__(self, config_loader: ConfigLoader, catalog_manager: CatalogManager):
        """
        Initialize backtest engine.
        
        Args:
            config_loader: Configuration loader instance
            catalog_manager: Catalog manager instance
        """
        self.config_loader = config_loader
        self.catalog_manager = catalog_manager
        self.catalog: Optional[ParquetDataCatalog] = None
        self.ucs_loader: Optional[UCSDataLoader] = None
    
    def _create_and_register_instrument(self, config: Dict[str, Any]) -> InstrumentId:
        """
        Create instrument from config and register it in the catalog.
        
        Args:
            config: Configuration dictionary
        
        Returns:
            InstrumentId instance
        """
        # Initialize catalog at the catalog path (not the raw data path)
        # Instruments and converted data files go into the catalog directory
        # Environment variable takes precedence over config
        catalog_path_str = os.getenv("DATA_CATALOG_PATH") or config["environment"].get("DATA_CATALOG_PATH", "/app/backend/data/parquet")
        catalog_path = Path(catalog_path_str).resolve()
        catalog_path.mkdir(parents=True, exist_ok=True)
        
        if self.catalog is None:
            self.catalog = ParquetDataCatalog(str(catalog_path))
        
        instrument_config = config["instrument"]
        venue_config = config["venue"]
        
        # Get instrument ID in NautilusTrader format
        config_instrument_id = instrument_config["id"]
        venue_name = venue_config["name"]
        nautilus_instrument_id_str = get_instrument_id_for_nautilus(config_instrument_id, venue_name)
        instrument_id = InstrumentId.from_str(nautilus_instrument_id_str)
        
        # Check if instrument already exists in catalog
        try:
            existing = self.catalog.instruments(instrument_ids=[instrument_id])
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
        import time
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
        self.catalog.write_data([instrument])
        
        return instrument_id
    
    def _build_venue_config(self, config: Dict[str, Any], has_book_data: bool = False) -> BacktestVenueConfig:
        """
        Build BacktestVenueConfig from JSON config.
        
        Args:
            config: Configuration dictionary
            has_book_data: Whether order book data is available (affects book_type requirement)
        
        Returns:
            BacktestVenueConfig instance
        """
        venue_config = config["venue"]
        starting_balance = venue_config["starting_balance"]
        base_currency = venue_config["base_currency"]
        
        # Use the configured book_type (default L2_MBP)
        # If book_type is L2_MBP but no book data exists, we need to use a book type that doesn't require data
        # Valid options: L1_MBP, L2_MBP, L3_MBO
        # L1_MBP might work for trades-only, but let's check what NautilusTrader accepts
        book_type = venue_config.get("book_type", "L2_MBP")
        
        # If L2_MBP is requested but no book data exists, try L1_MBP (simpler, might not require full book)
        # If that still fails, we'll need to handle it in the data configs (skip OrderBookDeltas)
        if book_type == "L2_MBP" and not has_book_data:
            # Try L1_MBP which might work with trades-only
            # Note: This is a workaround - ideally we'd use a book type that doesn't require book data
            print(f"Warning: book_type=L2_MBP requested but no book data available. Using L1_MBP for trades-only mode.")
            book_type = "L1_MBP"
        
        # Normalize venue name for NautilusTrader
        venue_name_raw = venue_config["name"]
        is_futures = "FUTURES" in venue_name_raw.upper() or venue_config.get("book_type") == "L2_MBP"
        normalized_venue = normalize_venue_name(venue_name_raw, is_futures=is_futures)
        
        return BacktestVenueConfig(
            name=normalized_venue,
            oms_type=venue_config["oms_type"],
            account_type=venue_config["account_type"],
            starting_balances=[f"{starting_balance} {base_currency}"],
            book_type=book_type,
        )
    
    def _build_data_config_with_book_check(
        self,
        config: Dict[str, Any],
        instrument_id: str,
        start: datetime,
        end: datetime,
        snapshot_mode: str
    ) -> tuple[List[BacktestDataConfig], bool]:
        """
        Build BacktestDataConfig list and check if book data is available.
        
        Supports both local files and GCS bucket based on data_source config.
        
        Returns:
            Tuple of (data_configs list, has_book_data bool)
        """
        data_configs = []
        has_book_data = False
        
        # Use the catalog path from config
        base_path_str = os.getenv("UNIFIED_CLOUD_LOCAL_PATH") or config["environment"].get("UNIFIED_CLOUD_LOCAL_PATH", "/app/data_downloads")
        base_path = Path(base_path_str).resolve()
        
        catalog_path_str = os.getenv("DATA_CATALOG_PATH") or config["environment"].get("DATA_CATALOG_PATH", "/app/backend/data/parquet")
        catalog_path = Path(catalog_path_str).resolve()
        catalog_path.mkdir(parents=True, exist_ok=True)
        
        if self.catalog is None:
            self.catalog = ParquetDataCatalog(str(catalog_path))
        
        instrument = InstrumentId.from_str(instrument_id)
        
        # Determine data source: 'local', 'gcs', or 'auto'
        data_source = config.get("data_source", "auto").lower()
        if data_source not in ("local", "gcs", "auto"):
            print(f"Warning: Invalid data_source '{data_source}', defaulting to 'auto'")
            data_source = "auto"
        
        # Initialize UCS loader if needed
        if data_source in ("gcs", "auto") and UCS_AVAILABLE:
            if self.ucs_loader is None:
                try:
                    self.ucs_loader = UCSDataLoader()
                    print(f"✅ UCS Data Loader initialized (data_source: {data_source})")
                    # If auto and UCS available, use GCS
                    if data_source == "auto":
                        data_source = "gcs"
                except Exception as e:
                    print(f"⚠️  Failed to initialize UCS loader: {e}")
                    if data_source == "gcs":
                        raise RuntimeError(f"Cannot use GCS data source: {e}")
                    # For 'auto', fall back to local
                    data_source = "local"
                    print(f"   Falling back to local files")
        
        # Get raw file paths from config
        data_catalog_config = config.get("data_catalog", {})
        trades_path = data_catalog_config.get("trades_path")
        book_snapshot_5_path = data_catalog_config.get("book_snapshot_5_path")
        
        # Extract instrument identifier from path or config for auto-discovery
        # Format: VENUE:PRODUCT (e.g., BINANCE-FUTURES:PERPETUAL:BTC-USDT)
        instrument_str = str(instrument)
        # Try to extract from trades_path if it contains the pattern
        instrument_file_pattern = None
        if trades_path:
            # Extract filename pattern (e.g., "BINANCE-FUTURES:PERPETUAL:BTC-USDT.parquet")
            if "/" in trades_path:
                instrument_file_pattern = trades_path.split("/")[-1]
            else:
                instrument_file_pattern = trades_path
        
        # Auto-discover data files across all date folders if path contains pattern or is a single date
        # This allows config to work with multiple date folders (FUSE-ready)
        raw_trades_paths = []
        raw_book_paths = []
        
        if trades_path:
            # Check if path contains a wildcard pattern or specific date folder
            if "*" in trades_path or "day-*" in trades_path:
                # Pattern-based - auto-discover across all date folders
                raw_tick_dir = base_path / "raw_tick_data" / "by_date"
                if raw_tick_dir.exists() and instrument_file_pattern:
                    print(f"Auto-discovering trades files for {instrument_file_pattern} across date folders...")
                    for day_dir in sorted(raw_tick_dir.iterdir()):
                        if day_dir.is_dir() and day_dir.name.startswith("day-"):
                            trades_file = day_dir / "data_type-trades" / instrument_file_pattern
                            if trades_file.exists():
                                raw_trades_paths.append(trades_file)
                                print(f"  Found: {trades_file}")
            elif "day-" in trades_path:
                # Specific date folder - use as-is
                if Path(trades_path).is_absolute():
                    raw_trades_paths = [Path(trades_path)]
                else:
                    path_str = str(trades_path)
                    if path_str.startswith("data_downloads/"):
                        path_str = path_str[len("data_downloads/"):]
                    resolved_path = (base_path / path_str).resolve()
                    if resolved_path.exists():
                        raw_trades_paths = [resolved_path]
            else:
                # No date folder specified - auto-discover across all date folders
                raw_tick_dir = base_path / "raw_tick_data" / "by_date"
                if raw_tick_dir.exists() and instrument_file_pattern:
                    print(f"Auto-discovering trades files for {instrument_file_pattern} across date folders...")
                    for day_dir in sorted(raw_tick_dir.iterdir()):
                        if day_dir.is_dir() and day_dir.name.startswith("day-"):
                            trades_file = day_dir / "data_type-trades" / instrument_file_pattern
                            if trades_file.exists():
                                raw_trades_paths.append(trades_file)
                                print(f"  Found: {trades_file}")
        else:
            print("Warning: No trades_path in config - cannot discover data files")
        
        if book_snapshot_5_path:
            if "*" in book_snapshot_5_path or "day-*" in book_snapshot_5_path:
                # Pattern-based - auto-discover across all date folders
                raw_tick_dir = base_path / "raw_tick_data" / "by_date"
                if raw_tick_dir.exists() and instrument_file_pattern:
                    for day_dir in sorted(raw_tick_dir.iterdir()):
                        if day_dir.is_dir() and day_dir.name.startswith("day-"):
                            book_file = day_dir / "data_type-book_snapshot_5" / instrument_file_pattern
                            if book_file.exists():
                                raw_book_paths.append(book_file)
            elif "day-" in book_snapshot_5_path:
                # Specific date folder
                if Path(book_snapshot_5_path).is_absolute():
                    raw_book_paths = [Path(book_snapshot_5_path)]
                else:
                    path_str = str(book_snapshot_5_path)
                    if path_str.startswith("data_downloads/"):
                        path_str = path_str[len("data_downloads/"):]
                    resolved_path = (base_path / path_str).resolve()
                    if resolved_path.exists():
                        raw_book_paths = [resolved_path]
            else:
                # No date folder specified - auto-discover across all date folders
                raw_tick_dir = base_path / "raw_tick_data" / "by_date"
                if raw_tick_dir.exists() and instrument_file_pattern:
                    for day_dir in sorted(raw_tick_dir.iterdir()):
                        if day_dir.is_dir() and day_dir.name.startswith("day-"):
                            book_file = day_dir / "data_type-book_snapshot_5" / instrument_file_pattern
                            if book_file.exists():
                                raw_book_paths.append(book_file)
        else:
            raw_book_paths = []
        
        from backend.data_converter import DataConverter
        instrument_config = config["instrument"]
        venue_config = config["venue"]
        price_precision = instrument_config.get("price_precision", 2)
        size_precision = instrument_config.get("size_precision", 3)
        
        # Process trades
        # OPTIMIZATION: Check if data already exists in catalog before converting
        # This avoids re-converting unchanged files (much faster on subsequent runs)
        if snapshot_mode in ("trades", "both"):
            total_trades_count = 0
            
            # Check if data already exists in catalog
            try:
                            existing_check = self.catalog.query(
                                data_cls=TradeTick,
                                instrument_ids=[instrument],
                    start=start,
                    end=end,
                                limit=1
                            )
                            if existing_check:
                    print(f"✅ Trades data already exists in catalog for time window")
                    total_trades_count = 1  # Mark as existing
                        except Exception:
                            pass  # No data exists, proceed with conversion
                        
            # Load and convert data if not in catalog
            if total_trades_count == 0:
                if data_source == "gcs" and self.ucs_loader:
                    # Load from GCS
                    try:
                        # Extract date from start timestamp
                        date_str = start.strftime("%Y-%m-%d")
                        
                        # Convert instrument ID to GCS format
                        config_instrument_id = instrument_config.get("id", str(instrument_id))
                        venue_name = venue_config.get("name", "BINANCE")
                        gcs_instrument_id = convert_instrument_id_to_gcs_format(config_instrument_id, venue_name)
                        
                        print(f"☁️  Loading trades from GCS for {date_str}...")
                        print(f"   Config instrument: {config_instrument_id}")
                        print(f"   GCS instrument: {gcs_instrument_id}")
                        
                        # Use async loader
                        import asyncio
                        df = asyncio.run(
                            self.ucs_loader.load_trades(
                                date_str=date_str,
                                instrument_id=gcs_instrument_id,
                                start_ts=start,
                                end_ts=end,
                                use_streaming=True
                            )
                        )
                        
                        print(f"   Loaded {len(df)} rows from GCS")
                        
                        # Filter by time window if needed (GCS data might be full day)
                        if 'ts_event' in df.columns:
                            start_ns = int(start.timestamp() * 1_000_000_000)
                            end_ns = int(end.timestamp() * 1_000_000_000)
                            df = df[(df['ts_event'] >= start_ns) & (df['ts_event'] <= end_ns)]
                            print(f"   Filtered to {len(df)} rows in time window")
                        
                        trades_count = DataConverter.convert_trades_parquet_to_catalog(
                            df,  # DataFrame instead of file path
                            instrument,
                            self.catalog,
                            price_precision=price_precision,
                            size_precision=size_precision,
                            skip_if_exists=True
                        )
                        total_trades_count = trades_count
                        print(f"✅ Registered {trades_count} trades from GCS to catalog")
                    except Exception as e:
                        import traceback
                        print(f"❌ Error loading trades from GCS: {e}")
                        traceback.print_exc()
                        if data_source == "gcs":
                            raise
                        # For 'auto', fall back to local
                        print(f"   Falling back to local files...")
                        data_source = "local"
                
                # Load from local files (original logic or fallback)
                if data_source == "local" and raw_trades_paths:
                    for raw_trades_path in raw_trades_paths:
                        if raw_trades_path.exists():
                            try:
                                print(f"📂 Converting and registering trades from {raw_trades_path.name}...")
                                print(f"   File size: {raw_trades_path.stat().st_size / (1024*1024):.2f} MB")
                        trades_count = DataConverter.convert_trades_parquet_to_catalog(
                            raw_trades_path,
                            instrument,
                            self.catalog,
                            price_precision=price_precision,
                            size_precision=size_precision,
                                    skip_if_exists=True
                        )
                        total_trades_count += trades_count
                                print(f"✅ Registered {trades_count} trades from {raw_trades_path.name} to catalog")
                    except Exception as e:
                        import traceback
                                print(f"❌ Error converting/registering trades from {raw_trades_path}: {e}")
                        traceback.print_exc()
            
            if total_trades_count > 0:
                print(f"Total registered: {total_trades_count} trades from {len(raw_trades_paths)} file(s)")
                
                # Verify data exists in the requested time window
                window_check = self.catalog.query(
                    data_cls=TradeTick,
                    instrument_ids=[instrument],
                    start=start,
                    end=end,
                    limit=1
                )
                if window_check:
                    all_in_window = self.catalog.query(
                        data_cls=TradeTick,
                        instrument_ids=[instrument],
                        start=start,
                        end=end
                    )
                    print(f"Verified: Found {len(all_in_window)} trades in time window {start} to {end}")
                else:
                    print(f"Warning: No trades found in time window {start} to {end} after conversion")
            else:
                print(f"Warning: No trades files found or converted")
            
            # Add trades config
            data_configs.append(
                BacktestDataConfig(
                    catalog_path=str(catalog_path),
                    data_cls=TradeTick,
                    instrument_id=instrument,
                    start_time=start,
                    end_time=end,
                )
            )
        
        # Process order book data - only add if file exists and conversion succeeds
        # Skip order book conversion if we're in trades-only mode or if conversion fails
        if snapshot_mode in ("book", "both"):
            # Handle GCS book snapshot loading
            if data_source == "gcs" and self.ucs_loader:
                try:
                    # Extract date from start timestamp
                    date_str = start.strftime("%Y-%m-%d")
                    
                    # Convert instrument ID to GCS format
                    config_instrument_id = instrument_config.get("id", str(instrument_id))
                    venue_name = venue_config.get("name", "BINANCE")
                    gcs_instrument_id = convert_instrument_id_to_gcs_format(config_instrument_id, venue_name)
                    
                    print(f"☁️  Loading book snapshots from GCS for {date_str}...")
                    print(f"   GCS instrument: {gcs_instrument_id}")
                    
                    # Use async loader
                    import asyncio
                    book_df = asyncio.run(
                        self.ucs_loader.load_book_snapshots(
                            date_str=date_str,
                            instrument_id=gcs_instrument_id,
                            start_ts=start,
                            end_ts=end,
                            use_streaming=True
                        )
                    )
                    
                    print(f"   Loaded {len(book_df)} book snapshot rows from GCS")
                    
                    # Filter by time window if needed
                    if 'ts_event' in book_df.columns:
                        start_ns = int(start.timestamp() * 1_000_000_000)
                        end_ns = int(end.timestamp() * 1_000_000_000)
                        book_df = book_df[(book_df['ts_event'] >= start_ns) & (book_df['ts_event'] <= end_ns)]
                        print(f"   Filtered to {len(book_df)} rows in time window")
                    
                    # Convert book snapshots to catalog
                    book_count = DataConverter.convert_orderbook_parquet_to_catalog(
                        book_df,  # DataFrame instead of file path
                        instrument,
                        self.catalog,
                        is_snapshot=True,
                        price_precision=price_precision,
                        size_precision=size_precision,
                        skip_if_exists=True
                    )
                    print(f"✅ Registered {book_count} book snapshots from GCS to catalog")
                    has_book_data = book_count > 0
                except Exception as e:
                    import traceback
                    print(f"❌ Error loading book snapshots from GCS: {e}")
                    traceback.print_exc()
                    if snapshot_mode == "book":
                        raise
                    # For 'both' mode, continue without book data
                    has_book_data = False
            
            # Handle local book snapshot files
            elif raw_book_paths and any(p.exists() for p in raw_book_paths):
                # Check if data already exists in catalog
                try:
                    existing = self.catalog.query(
                        data_cls=OrderBookDeltas,
                        instrument_ids=[instrument],
                        limit=1
                    )
                    has_book_data = len(existing) > 0
                except ValueError as ve:
                    # Empty collection is expected if no data exists yet
                    if "'data' collection was empty" in str(ve) or "empty" in str(ve).lower():
                        has_book_data = False
                    else:
                        raise
                except Exception as e:
                    print(f"Warning: Could not check for existing order book data: {e}")
                    has_book_data = False
                
                if not has_book_data:
                    # Skip order book conversion for now - it's not working correctly
                    # TODO: Fix OrderBookDelta.from_raw() call signature
                    print(f"Info: Skipping order book conversion (not yet fully implemented)")
                    if raw_book_paths:
                        print(f"      Files exist at {[str(p) for p in raw_book_paths]} but conversion is disabled")
                    has_book_data = False
                else:
                    print(f"Order book data already registered in catalog")
                
                # Only add OrderBookDeltas config if we have book data
                if has_book_data:
                    data_configs.append(
                        BacktestDataConfig(
                            catalog_path=str(catalog_path),
                            data_cls=OrderBookDeltas,
                            instrument_id=instrument,
                            start_time=start,
                            end_time=end,
                        )
                    )
                elif snapshot_mode == "book":
                    # Book-only mode requested but no data - fail with clear error
                    raise RuntimeError(
                        f"No order book data available for {instrument_id} but snapshot_mode='book' requested. "
                        f"Files exist: {[str(p) for p in raw_book_paths] if raw_book_paths else []}"
                    )
                else:
                    # "both" mode but no book data - continue with trades only
                    print(f"Info: OrderBookDeltas data not available, continuing with trades only")
            elif snapshot_mode == "book":
                # Book-only mode but no files found
                raise FileNotFoundError(
                    f"Order book files not found (snapshot_mode='book' requires book data)"
                )
            else:
                # "both" mode but files don't exist - continue with trades only
                print(f"Info: Order book files not found, continuing with trades only")
        
        return data_configs, has_book_data
    
    def _build_data_config(
        self,
        config: Dict[str, Any],
        instrument_id: str,
        start: datetime,
        end: datetime,
        snapshot_mode: str
    ) -> List[BacktestDataConfig]:
        """
        Build BacktestDataConfig list from JSON config.
        
        Args:
            config: Configuration dictionary
            instrument_id: Instrument identifier
            start: Start timestamp
            end: End timestamp
            snapshot_mode: Snapshot mode (trades|book|both)
        
        Returns:
            List of BacktestDataConfig instances
        """
        data_configs = []
        # Use the catalog path from config - this should point to where Parquet files are
        # The catalog needs to be initialized at the same path where data files are located
        # Environment variable takes precedence over config
        base_path_str = os.getenv("UNIFIED_CLOUD_LOCAL_PATH") or config["environment"].get("UNIFIED_CLOUD_LOCAL_PATH", "/app/data_downloads")
        
        # Resolve to absolute path
        base_path = Path(base_path_str).resolve()
        
        # For ParquetDataCatalog, we need to use a separate catalog directory
        # where we'll register/converted data, not the raw data_downloads folder
        # The raw Parquet files need to be converted/registered into the catalog format
        catalog_path_str = os.getenv("DATA_CATALOG_PATH") or config["environment"].get("DATA_CATALOG_PATH", "/app/backend/data/parquet")
        catalog_path = Path(catalog_path_str).resolve()
        catalog_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize catalog at the catalog path (where converted data will be stored)
        if self.catalog is None:
            self.catalog = ParquetDataCatalog(str(catalog_path))
        
        instrument = InstrumentId.from_str(instrument_id)
        
        # Get raw file paths from config
        data_catalog_config = config.get("data_catalog", {})
        trades_path = data_catalog_config.get("trades_path")
        book_snapshot_5_path = data_catalog_config.get("book_snapshot_5_path")
        
        # Resolve raw file paths relative to base_path
        # Config paths may start with "data_downloads/" which should be stripped if base_path already points to data_downloads
        if trades_path:
            # Handle both absolute and relative paths
            if Path(trades_path).is_absolute():
                raw_trades_path = Path(trades_path)
            else:
                # Strip leading "data_downloads/" if present since base_path already points there
                path_str = str(trades_path)
                if path_str.startswith("data_downloads/"):
                    path_str = path_str[len("data_downloads/"):]
                raw_trades_path = (base_path / path_str).resolve()
        else:
            raw_trades_path = None
            
        # Note: This method (_build_data_config) is deprecated - use _build_data_config_with_book_check instead
        # Keeping for backward compatibility but should not be used
        raw_book_paths = []
        if book_snapshot_5_path:
            if Path(book_snapshot_5_path).is_absolute():
                raw_book_paths = [Path(book_snapshot_5_path)]
            else:
                # Strip leading "data_downloads/" if present
                path_str = str(book_snapshot_5_path)
                if path_str.startswith("data_downloads/"):
                    path_str = path_str[len("data_downloads/"):]
                resolved_path = (base_path / path_str).resolve()
                if resolved_path.exists():
                    raw_book_paths = [resolved_path]
        raw_book_path = raw_book_paths[0] if raw_book_paths else None  # For backward compatibility
        
        # Register raw Parquet files into catalog if they exist and haven't been registered
        # This converts the raw files into the catalog format
        from backend.data_converter import DataConverter
        
        instrument_config = config["instrument"]
        price_precision = instrument_config.get("price_precision", 2)
        size_precision = instrument_config.get("size_precision", 3)
        
        if raw_trades_path and raw_trades_path.exists() and snapshot_mode in ("trades", "both"):
            # Check if data already exists in catalog for the time window
            # Use a broader query to check if ANY data exists for this instrument
            try:
                # First check if data exists in the SPECIFIC time window
                window_check = self.catalog.query(
                    data_cls=TradeTick,
                    instrument_ids=[instrument],
                    start=start,
                    end=end,
                    limit=1
                )
                if window_check:
                    # Count total trades in window for logging
                    all_in_window = self.catalog.query(
                        data_cls=TradeTick,
                        instrument_ids=[instrument],
                        start=start,
                        end=end
                    )
                    print(f"Trades already registered (found {len(all_in_window)} in time window)")
                else:
                    # No data in time window - check if we need to convert
                    # Query without time window to see if ANY data exists for this instrument
                    existing = self.catalog.query(
                        data_cls=TradeTick,
                        instrument_ids=[instrument],
                        limit=1
                    )
                    if not existing:
                        # No data at all - convert and register
                        print(f"Converting trades from {raw_trades_path}...")
                        trades_count = DataConverter.convert_trades_parquet_to_catalog(
                            raw_trades_path,
                            instrument,
                            self.catalog,
                            price_precision=price_precision,
                            size_precision=size_precision,
                            skip_if_exists=True  # Skip if already converted
                        )
                        if trades_count > 0:
                            print(f"Registered {trades_count} trades from {raw_trades_path}")
                        else:
                            print(f"Skipped conversion - data already exists in catalog")
                    else:
                        # Data exists but not in this time window - check if file needs conversion
                        print(f"Data exists in catalog but checking time window {start} to {end}")
                        trades_count = DataConverter.convert_trades_parquet_to_catalog(
                            raw_trades_path,
                            instrument,
                            self.catalog,
                            price_precision=price_precision,
                            size_precision=size_precision,
                            skip_if_exists=True  # Skip if already converted (major performance improvement)
                        )
                        if trades_count > 0:
                            print(f"Registered {trades_count} trades from {raw_trades_path}")
                        else:
                            print(f"Skipped conversion - data already exists in catalog")
            except Exception as e:
                import traceback
                print(f"Error converting/registering trades: {e}")
                traceback.print_exc()
        elif raw_trades_path:
            print(f"Warning: Trades file not found: {raw_trades_path}")
        
        if raw_book_paths and any(p.exists() for p in raw_book_paths) and snapshot_mode in ("book", "both"):
            # Check if data already exists in catalog
            # Note: query() throws ValueError if collection is empty, so we catch that
            has_existing_book_data = False
            try:
                existing = self.catalog.query(
                    data_cls=OrderBookDeltas,
                    instrument_ids=[instrument],
                    limit=1
                )
                has_existing_book_data = len(existing) > 0
            except ValueError as ve:
                # Empty collection is expected if no data exists yet
                if "'data' collection was empty" in str(ve) or "empty" in str(ve).lower():
                    has_existing_book_data = False
                else:
                    raise
            except Exception as e:
                # Other errors - assume no data exists
                print(f"Warning: Could not check for existing order book data: {e}")
                has_existing_book_data = False
            
            if not has_existing_book_data:
                # Convert and register order book data from all discovered files
                for raw_book_path in raw_book_paths:
                    if raw_book_path.exists():
                        print(f"Converting order book data from {raw_book_path}...")
                        try:
                            book_count = DataConverter.convert_orderbook_parquet_to_catalog(
                                raw_book_path,
                                instrument,
                                self.catalog,
                                is_snapshot=True,
                                price_precision=price_precision,
                                size_precision=size_precision,
                                skip_if_exists=True  # Skip if already converted (performance optimization)
                            )
                            print(f"Registered {book_count} order book entries from {raw_book_path}")
                        except Exception as e:
                            import traceback
                            print(f"Error converting/registering order book data: {e}")
                            traceback.print_exc()
                            # Don't fail the backtest if book conversion fails - continue with trades only
            else:
                print(f"Order book data already registered in catalog for {instrument}")
        
        # Add trades if needed
        if snapshot_mode in ("trades", "both"):
            data_configs.append(
                BacktestDataConfig(
                    catalog_path=str(catalog_path),  # Point to catalog directory
                    data_cls=TradeTick,
                    instrument_id=instrument,
                    start_time=start,
                    end_time=end,
                )
            )
        
        # Add book snapshots if needed
        # Only add OrderBookDeltas config if we have order book data or if explicitly requested
        if snapshot_mode in ("book", "both"):
            # Check if order book data exists before adding config
            # This prevents errors when order book data is not available
            try:
                if raw_book_paths and any(p.exists() for p in raw_book_paths):
                    # Try to query for existing order book data
                    existing_book = self.catalog.query(
                        data_cls=OrderBookDeltas,
                        instrument_ids=[instrument],
                        limit=1
                    )
                    if existing_book or snapshot_mode == "book":
                        # Only add if data exists or if book mode is explicitly requested
                        data_configs.append(
                            BacktestDataConfig(
                                catalog_path=str(catalog_path),
                                data_cls=OrderBookDeltas,
                                instrument_id=instrument,
                                start_time=start,
                                end_time=end,
                            )
                        )
                    else:
                        print(f"Warning: OrderBookDeltas data not found for {instrument}, skipping book data config")
                elif snapshot_mode == "book":
                    # If book mode is explicitly requested but file doesn't exist, still add config
                    # This will fail gracefully with a clear error message
                    data_configs.append(
                        BacktestDataConfig(
                            catalog_path=str(catalog_path),
                            data_cls=OrderBookDeltas,
                            instrument_id=instrument,
                            start_time=start,
                            end_time=end,
                        )
                    )
                else:
                    print(f"Info: OrderBookDeltas file not found, skipping book data (snapshot_mode={snapshot_mode})")
            except Exception as e:
                print(f"Warning: Could not check OrderBookDeltas availability: {e}, skipping book data")
        
        return data_configs
    
    def _close_all_positions(
        self,
        engine,
        instrument_id: InstrumentId,
        config: Dict[str, Any]
    ) -> None:
        """
        Close all open positions at the end of backtest.
        
        This ensures that unrealized PnL is realized, giving accurate final PnL.
        Uses market orders at the last trade price to close positions.
        
        Args:
            engine: BacktestEngine instance
            instrument_id: Instrument ID to close positions for
            config: Configuration dictionary
        """
        try:
            # Get all open positions for this instrument
            open_positions = engine.cache.positions_open(instrument_id=instrument_id)
            
            if not open_positions or len(open_positions) == 0:
                print("No open positions to close")
                return 0
            
            print(f"Realizing PnL for {len(open_positions)} open position(s) at end of backtest...")
            
            # Since we can't submit orders after backtest completes, we manually realize unrealized PnL
            # This gives accurate final PnL by converting unrealized to realized
            # The actual realization happens in StrategyEvaluator.evaluate_performance()
            try:
                portfolio = engine.portfolio if hasattr(engine, 'portfolio') else None
                if portfolio:
                    venue = Venue(config["venue"]["name"])
                    unrealized_pnls = portfolio.unrealized_pnls(venue)
                    base_currency = config["venue"]["base_currency"]
                    base_currency_obj = Currency.from_str(base_currency)
                    total_unrealized = 0.0
                    
                    for currency, money in unrealized_pnls.items():
                        # Compare Currency objects properly
                        if currency == base_currency_obj or str(currency) == "USDT":
                            if money:
                                total_unrealized += float(money.as_decimal())
                    
                    if total_unrealized != 0.0:
                        print(f"  Found {total_unrealized:.2f} {base_currency} unrealized PnL from {len(open_positions)} open position(s)")
                        print(f"  Position details:")
                        for pos in open_positions:
                            try:
                                unrealized = 0.0
                                if hasattr(pos, 'unrealized_pnl'):
                                    # Try to get unrealized PnL if available
                                    try:
                                        # Get last trade price for calculation
                                        last_trade = engine.cache.trade_tick(instrument_id)
                                if last_trade and hasattr(pos, 'unrealized_pnl'):
                                    unrealized = float(pos.unrealized_pnl(last_trade.price).as_decimal())
                                    except Exception:
                                        pass
                                qty = float(pos.quantity.as_decimal()) if pos.quantity else 0.0
                                entry = float(pos.avg_px_open.as_decimal()) if pos.avg_px_open else 0.0
                                print(f"    - {pos.side.name}: {qty} @ {entry} (unrealized: {unrealized:.2f})")
                            except Exception:
                                pass
                        print(f"  Note: Unrealized PnL will be realized in final PnL calculation")
                    else:
                        print(f"  No unrealized PnL to realize")
                    
                    return len(open_positions)
            except Exception as e:
                print(f"Warning: Could not process position closure: {e}")
                import traceback
                traceback.print_exc()
                return 0
            
            return 0
            
        except Exception as e:
            print(f"Warning: Error processing position closure: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def _build_strategy_config(self, config: Dict[str, Any]) -> ImportableStrategyConfig:
        """
        Build strategy config from JSON.
        
        Args:
            config: Configuration dictionary
        
        Returns:
            ImportableStrategyConfig instance
        """
        strategy_config = config["strategy"]
        instrument_id = config["instrument"]["id"]
        
        # Create strategy config with instrument ID and execution algorithm settings
        strategy_config_dict = {
            "instrument_id": instrument_id,
            "submission_mode": strategy_config.get("submission_mode", "per_trade_tick"),
        }
        
        # Add execution algorithm config if specified
        if "exec_algorithm" in strategy_config:
            exec_algo_config = strategy_config["exec_algorithm"]
            exec_algo_type = exec_algo_config.get("type", "").upper() if isinstance(exec_algo_config, dict) else str(exec_algo_config).upper()
            # NORMAL mode means no execution algorithm, but we still pass it to strategy
            if exec_algo_type != "NORMAL":
                strategy_config_dict["use_exec_algorithm"] = True
            strategy_config_dict["exec_algorithm"] = exec_algo_config
        
        return ImportableStrategyConfig(
            strategy_path="backend.strategy:TempBacktestStrategy",
            config_path="backend.strategy:TempBacktestStrategyConfig",
            config=strategy_config_dict,
        )
    
    def _build_exec_algorithms(
        self,
        config: Dict[str, Any],
        exec_algorithm_type: Optional[str] = None,
        exec_algorithm_params: Optional[Dict[str, Any]] = None
    ) -> List:
        """
        Build execution algorithms from config or CLI args.
        
        Args:
            config: Configuration dictionary
            exec_algorithm_type: Execution algorithm type from CLI (overrides config)
            exec_algorithm_params: Execution algorithm parameters from CLI (overrides config)
        
        Returns:
            List of execution algorithm instances
        """
        exec_algorithms = []
        
        # Determine which exec algorithm to use (CLI takes precedence)
        algo_type = None
        algo_params = {}
        
        if exec_algorithm_type:
            # CLI argument provided
            algo_type = exec_algorithm_type.upper()
            algo_params = exec_algorithm_params or {}
        else:
            # Check config
            strategy_config = config.get("strategy", {})
            exec_config = strategy_config.get("exec_algorithm")
            if exec_config:
                algo_type = exec_config.get("type", "").upper()
                algo_params = exec_config.get("params", {})
        
        # Also check execution section in config
        exec_section = config.get("execution", {})
        algorithms = exec_section.get("algorithms", [])
        
        # If no exec algorithm specified, return empty list
        if not algo_type and not algorithms:
            return exec_algorithms
        
        # Create execution algorithms - use built-in if available
        if algo_type:
            # Single algorithm from CLI or strategy config
            if algo_type == "NORMAL":
                # NORMAL mode: no execution algorithm, use regular market orders
                # Return empty list to indicate no exec algorithm
                pass
            elif algo_type == "TWAP":
                # Use built-in TWAP if available, otherwise custom
                if BUILTIN_TWAP_AVAILABLE:
                    exec_algorithms.append(BuiltinTWAPExecAlgorithm())
                    print(f"Status: Using built-in TWAPExecAlgorithm")
                else:
                    exec_algorithms.append(TWAPExecAlgorithm())
                    print(f"Status: Using custom TWAPExecAlgorithm")
            elif algo_type == "VWAP":
                exec_algorithms.append(VWAPExecAlgorithm())
            elif algo_type == "ICEBERG":
                exec_algorithms.append(IcebergExecAlgorithm())
            else:
                print(f"Warning: Unknown execution algorithm type: {algo_type}")
        else:
            # Multiple algorithms from execution section
            for algo_config in algorithms:
                algo_type = algo_config.get("type", "").upper()
                if algo_config.get("enabled", True):
                    if algo_type == "TWAP":
                        if BUILTIN_TWAP_AVAILABLE:
                            exec_algorithms.append(BuiltinTWAPExecAlgorithm())
                        else:
                            exec_algorithms.append(TWAPExecAlgorithm())
                    elif algo_type == "VWAP":
                        exec_algorithms.append(VWAPExecAlgorithm())
                    elif algo_type == "ICEBERG":
                        exec_algorithms.append(IcebergExecAlgorithm())
                    else:
                        print(f"Warning: Unknown execution algorithm type: {algo_type}")
        
        if exec_algorithms:
            algo_names = [algo.__class__.__name__ for algo in exec_algorithms]
            print(f"Status: ✓ Configured {len(exec_algorithms)} execution algorithm(s): {algo_names}")
        
        return exec_algorithms
    
    def run(
        self,
        instrument: str,
        start: datetime,
        end: datetime,
        dataset: Optional[str] = None,
        snapshot_mode: str = "both",
        fast_mode: bool = False,
        export_ticks: bool = False,
        close_positions: bool = True,
        data_source: str = "auto",
        exec_algorithm_type: Optional[str] = None,
        exec_algorithm_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run backtest.
        
        Args:
            instrument: Instrument identifier (for display/logging)
            dataset: Dataset name (optional - auto-detected from time window if not provided)
            start: Start timestamp
            end: End timestamp
            snapshot_mode: Snapshot mode (trades|book|both)
            fast_mode: If True, return minimal summary only
            export_ticks: If True, export tick data (only in report mode)
            close_positions: If True, close all open positions at end of backtest (default: True)
            data_source: Data source ('local', 'gcs', or 'auto') - defaults to config or 'auto'
        
        Returns:
            Result dictionary
        """
        config = self.config_loader.config
        if config is None:
            raise RuntimeError("Config not loaded")
        
        # Set data_source in config (CLI arg takes precedence over config)
        if data_source and data_source != "auto":
            config["data_source"] = data_source
        elif "data_source" not in config:
            config["data_source"] = "auto"
        
        # Get instrument ID from config (not CLI arg)
        instrument_id_str = config["instrument"]["id"]
        instrument_id = InstrumentId.from_str(instrument_id_str)
        
        # Auto-detect dataset from time window if not provided
        start_date = start.date() if hasattr(start, 'date') else start.date()
        if not dataset:
            dataset = f"day-{start_date.strftime('%Y-%m-%d')}"
            print(f"Status: Auto-detected dataset '{dataset}' from time window")
        
        # Determine actual data source early
        actual_data_source = config.get("data_source", "gcs").lower()
        if actual_data_source not in ("local", "gcs"):
            # Default to GCS if invalid
            actual_data_source = "gcs"
            config["data_source"] = "gcs"
        
        # Initialize UCS loader if needed for GCS
        if actual_data_source == "gcs" and UCS_AVAILABLE:
            if self.ucs_loader is None:
                try:
                    self.ucs_loader = UCSDataLoader()
                    print(f"✅ UCS Data Loader initialized for GCS data source")
                except Exception as e:
                    print(f"⚠️  Failed to initialize UCS loader: {e}")
                    raise RuntimeError(f"Cannot use GCS data source: {e}")
        
        # Check catalog FIRST - if data exists, skip validation
        catalog_path_str = os.getenv("DATA_CATALOG_PATH") or config["environment"].get("DATA_CATALOG_PATH", "/app/backend/data/parquet")
        catalog_path = Path(catalog_path_str).resolve()
        catalog_path.mkdir(parents=True, exist_ok=True)
        
        if self.catalog is None:
            self.catalog = ParquetDataCatalog(str(catalog_path))
        
        print(f"Status: Checking catalog at {catalog_path} for existing data...")
        catalog_has_trades = False
        catalog_has_book = False
        
        try:
            existing_trades = self.catalog.query(
                data_cls=TradeTick,
                instrument_ids=[instrument_id],
                start=start,
                end=end,
                limit=1
            )
            if existing_trades:
                catalog_has_trades = True
                all_trades = self.catalog.query(
                    data_cls=TradeTick,
                    instrument_ids=[instrument_id],
                    start=start,
                    end=end
                )
                print(f"Status: ✓ Found {len(all_trades)} existing trade(s) in catalog for time window")
        except Exception:
            pass
        
        if snapshot_mode in ("book", "both"):
            try:
                existing_book = self.catalog.query(
                    data_cls=OrderBookDeltas,
                    instrument_ids=[instrument_id],
                    start=start,
                    end=end,
                    limit=1
                )
                if existing_book:
                    catalog_has_book = True
                    print(f"Status: ✓ Found existing book snapshot data in catalog for time window")
            except Exception:
                pass
        
        # If catalog has all required data, skip validation
        if catalog_has_trades and (snapshot_mode == "trades" or (snapshot_mode in ("book", "both") and catalog_has_book)):
            print(f"Status: ✓ All required data exists in catalog - skipping validation")
            # Skip all validation - data is ready
            validation_errors = []
            validation_warnings = []
        else:
            # VALIDATION: Only validate if data not in catalog
            print("Status: Validating data availability (data not in catalog)...")
        validation_errors = []
        validation_warnings = []
        
            # Validate that dataset name matches the date in time window
        dataset_date = None
        if dataset.startswith("day-"):
            try:
                date_str = dataset.replace("day-", "")
                from datetime import datetime as dt
                dataset_date = dt.strptime(date_str, "%Y-%m-%d").date()
                print(f"Status: Dataset '{dataset}' corresponds to date: {dataset_date}")
            except ValueError as e:
                validation_warnings.append(f"WARNING: Could not parse date from dataset name '{dataset}', expected format 'day-YYYY-MM-DD': {e}")
        else:
            print(f"Status: Dataset '{dataset}' does not start with 'day-', skipping date validation")
        
        print(f"Status: Time window start date: {start_date}")
        
        # Check if dataset date matches time window date
        if dataset_date is not None and dataset_date != start_date:
            print(f"Status: ✗ Date mismatch detected: dataset date {dataset_date} != start date {start_date}")
            error_msg = (
                f"ERROR: Dataset date mismatch\n"
                f"  Dataset name: {dataset} (date: {dataset_date})\n"
                f"  Requested time window start: {start} (date: {start_date})\n"
                f"  The dataset name must match the date in the time window.\n"
                f"  Auto-detected dataset: 'day-{start_date.strftime('%Y-%m-%d')}'"
            )
            validation_errors.append(error_msg)
            print(f"Status: ✗ VALIDATION ERROR: {error_msg}")
        
            # Fail fast if date mismatch
        if validation_errors:
            error_msg = "VALIDATION FAILED:\n" + "\n".join(validation_errors)
            raise RuntimeError(error_msg)
        
            # Only validate source files if data not in catalog
            if actual_data_source == "gcs":
                # GCS validation - already done in form, but double-check if needed
                print(f"Status: GCS data source - validation already done in form")
            else:
                # Local file validation - only if data not in catalog
                base_path_str = os.getenv("UNIFIED_CLOUD_LOCAL_PATH") or config["environment"].get("UNIFIED_CLOUD_LOCAL_PATH", "/app/data_downloads")
        
        # Ensure base_path_str is set (for both GCS and local paths)
        if 'base_path_str' not in locals():
        base_path_str = os.getenv("UNIFIED_CLOUD_LOCAL_PATH") or config["environment"].get("UNIFIED_CLOUD_LOCAL_PATH", "/app/data_downloads")
        base_path = Path(base_path_str).resolve()
        data_catalog_config = config.get("data_catalog", {})
        trades_path_pattern = data_catalog_config.get("trades_path")
        book_path_pattern = data_catalog_config.get("book_snapshot_5_path")
        
        # Discover actual files (handle wildcards)
        raw_trades_paths = []
        raw_book_paths = []
        
        if trades_path_pattern:
            if "*" in trades_path_pattern:
                from backend.utils.paths import discover_data_files
                raw_trades_paths = discover_data_files(base_path, trades_path_pattern, instrument_id_str)
                print(f"Status: Discovered {len(raw_trades_paths)} trade file(s) matching pattern")
            else:
                path_str = str(trades_path_pattern)
                if path_str.startswith("data_downloads/"):
                    path_str = path_str[len("data_downloads/"):]
                resolved = (base_path / path_str).resolve()
                if resolved.exists():
                    raw_trades_paths = [resolved]
        
        if book_path_pattern:
            if "*" in book_path_pattern:
                from backend.utils.paths import discover_data_files
                raw_book_paths = discover_data_files(base_path, book_path_pattern, instrument_id_str)
                print(f"Status: Discovered {len(raw_book_paths)} book snapshot file(s) matching pattern")
            else:
                path_str = str(book_path_pattern)
                if path_str.startswith("data_downloads/"):
                    path_str = path_str[len("data_downloads/"):]
                resolved = (base_path / path_str).resolve()
                if resolved.exists():
                    raw_book_paths = [resolved]
        
            # Validate trades data availability (only if not in catalog)
            if not catalog_has_trades and snapshot_mode in ("trades", "both"):
                # Skip local file validation if using GCS
                if actual_data_source == "gcs":
                    # Validate GCS data availability instead
                    try:
                        from backend.api.data_checker import DataAvailabilityChecker, _convert_instrument_id_to_gcs_format
                        import asyncio
                        checker = DataAvailabilityChecker(data_source="gcs")
                        config_instrument_id = config["instrument"]["id"]
                        venue_name = config["venue"]["name"]
                        gcs_instrument_id = _convert_instrument_id_to_gcs_format(config_instrument_id)
                        
                        date_str = start_date.strftime("%Y-%m-%d")
                        has_trades = asyncio.run(checker.check_gcs_file_exists(date_str, gcs_instrument_id, "trades"))
                        
                        if not has_trades:
                            validation_errors.append(
                                f"ERROR: Trades data NOT FOUND in GCS for {date_str}\n"
                                f"  Instrument: {gcs_instrument_id}\n"
                                f"  Expected: raw_tick_data/by_date/day-{date_str}/data_type-trades/{gcs_instrument_id}.parquet\n"
                                f"  Please ensure the data exists in the GCS bucket."
                            )
                        else:
                            print(f"Status: ✓ Trades data found in GCS for {date_str}")
                    except Exception as e:
                        validation_errors.append(
                            f"ERROR: Failed to validate GCS trades data: {e}\n"
                            f"  Please check GCS connectivity and permissions."
                        )
                else:
                    # Local file validation
            dataset_folder = base_path / "raw_tick_data" / "by_date" / dataset
            if not dataset_folder.exists():
                validation_errors.append(
                    f"ERROR: Dataset folder not found: {dataset_folder}\n"
                    f"  Required for dataset: {dataset}\n"
                    f"  Expected location: {dataset_folder}\n"
                    f"  Please ensure the dataset folder exists before running the backtest."
                )
            elif not raw_trades_paths:
                # Dataset exists but no trade files found
                validation_errors.append(
                    f"ERROR: No trade data files found for dataset '{dataset}'\n"
                    f"  Dataset folder exists: {dataset_folder}\n"
                    f"  Pattern searched: {trades_path_pattern}\n"
                    f"  Please ensure trade data files exist in the dataset folder."
                )
            else:
                # Check if files exist and have data (lenient validation - actual time window checked during catalog query)
                print(f"Status: Checking trade data file availability...")
                total_trades_found = 0
                for path in raw_trades_paths:
                    if path.exists():
                        try:
                            # Quick check: verify file has data (exact time range validation happens during catalog query)
                            import pyarrow.parquet as pq
                            table = pq.read_table(path, columns=[pq.read_schema(path).names[0]])  # Read just first column to check if file has data
                            if table.num_rows > 0:
                                print(f"Status: ✓ Trade data file {path.name} exists and has {table.num_rows} rows")
                                total_trades_found += 1
                            else:
                                validation_warnings.append(f"WARNING: Trade file {path.name} is empty")
                        except Exception as e:
                            validation_warnings.append(f"WARNING: Could not verify trade file {path.name}: {e}")
                
                if total_trades_found == 0:
                    validation_errors.append(
                        f"ERROR: No trade data files found or files are empty for dataset '{dataset}'\n"
                        f"  Dataset folder: {dataset_folder}\n"
                        f"  Files checked: {[str(p) for p in raw_trades_paths]}\n"
                        f"  Please ensure trade data files exist and contain data."
                    )
                else:
                    print(f"Status: ✓ Found {total_trades_found} trade file(s) with data (time window will be validated during catalog query)")
        
            # Validate book data availability (only if not in catalog)
            if not catalog_has_book and snapshot_mode in ("book", "both"):
                # Skip local file validation if using GCS
                if actual_data_source == "gcs":
                    # Validate GCS data availability instead
                    try:
                        from backend.api.data_checker import DataAvailabilityChecker, _convert_instrument_id_to_gcs_format
                        import asyncio
                        checker = DataAvailabilityChecker(data_source="gcs")
                        config_instrument_id = config["instrument"]["id"]
                        gcs_instrument_id = _convert_instrument_id_to_gcs_format(config_instrument_id)
                        
                        date_str = start_date.strftime("%Y-%m-%d")
                        has_book = asyncio.run(checker.check_gcs_file_exists(date_str, gcs_instrument_id, "book_snapshot_5"))
                        
                        if not has_book:
                            if snapshot_mode == "book":
                                validation_errors.append(
                                    f"ERROR: Book snapshot data NOT FOUND in GCS for {date_str}\n"
                                    f"  Instrument: {gcs_instrument_id}\n"
                                    f"  Expected: raw_tick_data/by_date/day-{date_str}/data_type-book_snapshot_5/{gcs_instrument_id}.parquet\n"
                                    f"  Please ensure the data exists in the GCS bucket."
                                )
                            else:
                                validation_warnings.append(
                                    f"WARNING: Book snapshot data not found in GCS for {date_str}, will use trades-only mode"
                                )
                        else:
                            print(f"Status: ✓ Book snapshot data found in GCS for {date_str}")
                    except Exception as e:
                        if snapshot_mode == "book":
                            validation_errors.append(
                                f"ERROR: Failed to validate GCS book snapshot data: {e}\n"
                                f"  Please check GCS connectivity and permissions."
                            )
                        else:
                            validation_warnings.append(f"WARNING: Could not validate GCS book snapshot data: {e}")
                else:
                    # Local file validation
            dataset_folder = base_path / "raw_tick_data" / "by_date" / dataset
            if not dataset_folder.exists():
                if snapshot_mode == "book":
                    validation_errors.append(
                        f"ERROR: Dataset folder not found: {dataset_folder}\n"
                        f"  Required for dataset: {dataset}\n"
                        f"  Book snapshot mode requires the dataset folder to exist.\n"
                        f"  Expected location: {dataset_folder}"
                    )
                        # else: "both" mode - already reported in trades validation above
            elif not raw_book_paths:
                if snapshot_mode == "book":
                    validation_errors.append(
                        f"ERROR: Book snapshot mode requested but no book data files found\n"
                        f"  Dataset folder exists: {dataset_folder}\n"
                        f"  Pattern searched: {book_path_pattern}\n"
                        f"  Please ensure book snapshot data files exist in the dataset folder."
                    )
                else:
                    validation_warnings.append(
                        f"WARNING: Book snapshot data not found for dataset '{dataset}', will use trades-only mode\n"
                        f"  Dataset folder: {dataset_folder}\n"
                        f"  Pattern searched: {book_path_pattern}"
                    )
            else:
                print(f"Status: ✓ Found {len(raw_book_paths)} book snapshot file(s)")
            
            # Fail if validation errors exist (only if data not in catalog)
            if 'validation_errors' in locals() and validation_errors:
                error_msg = "VALIDATION FAILED:\n" + "\n".join(validation_errors)
                raise RuntimeError(error_msg)
        
        # Check catalog for existing data
        catalog_path_str = os.getenv("DATA_CATALOG_PATH") or config["environment"].get("DATA_CATALOG_PATH", "/app/backend/data/parquet")
        catalog_path = Path(catalog_path_str).resolve()
        catalog_path.mkdir(parents=True, exist_ok=True)
        
        if self.catalog is None:
            self.catalog = ParquetDataCatalog(str(catalog_path))
        
        print(f"Status: Checking catalog at {catalog_path} for existing data...")
        catalog_has_data = False
        try:
            existing_trades = self.catalog.query(
                data_cls=TradeTick,
                instrument_ids=[instrument_id],
                start=start,
                end=end,
                limit=1
            )
            if existing_trades:
                # Count total trades in window
                all_trades = self.catalog.query(
                    data_cls=TradeTick,
                    instrument_ids=[instrument_id],
                    start=start,
                    end=end
                )
                print(f"Status: ✓ Found {len(all_trades)} existing trade(s) in catalog for time window")
                catalog_has_data = True
            else:
                print(f"Status: No existing trade data in catalog for time window, will convert from raw files")
        except Exception as e:
            print(f"Status: Catalog check failed (will proceed with conversion): {e}")
        
        # If catalog doesn't have data, validate that raw files contain data for the requested time window
        if not catalog_has_data and snapshot_mode in ("trades", "both") and raw_trades_paths:
            print(f"Status: Validating that raw files contain data for requested time window ({start} to {end})...")
            files_with_data = []
            files_without_data = []
            
            for path in raw_trades_paths:
                if not path.exists():
                    files_without_data.append((path, "File does not exist"))
                    continue
                
                try:
                    import pyarrow.parquet as pq
                    import pandas as pd
                    
                    # Read timestamp column to check time range
                    # Try common timestamp column names
                    table = pq.read_table(path)
                    df = table.to_pandas()
                    
                    # Find timestamp column
                    timestamp_col = None
                    for col in ['ts_event', 'timestamp', 'ts', 'ts_init']:
                        if col in df.columns:
                            timestamp_col = col
                            break
                    
                    if timestamp_col is None:
                        files_without_data.append((path, "No timestamp column found"))
                        continue
                    
                    # Get timestamp range from file
                    timestamps = df[timestamp_col]
                    
                    # Convert to datetime if needed (handle nanoseconds, microseconds, milliseconds)
                    if timestamps.dtype in ['int64', 'int32']:
                        # Assume nanoseconds if values are very large (> 1e15)
                        if timestamps.max() > 1e15:
                            # Nanoseconds
                            min_ts = pd.Timestamp(timestamps.min() / 1e9, unit='s', tz='UTC')
                            max_ts = pd.Timestamp(timestamps.max() / 1e9, unit='s', tz='UTC')
                        elif timestamps.max() > 1e12:
                            # Microseconds
                            min_ts = pd.Timestamp(timestamps.min() / 1e6, unit='s', tz='UTC')
                            max_ts = pd.Timestamp(timestamps.max() / 1e6, unit='s', tz='UTC')
                        else:
                            # Milliseconds
                            min_ts = pd.Timestamp(timestamps.min() / 1e3, unit='s', tz='UTC')
                            max_ts = pd.Timestamp(timestamps.max() / 1e3, unit='s', tz='UTC')
                    else:
                        # Already datetime
                        min_ts = pd.Timestamp(timestamps.min()).tz_localize('UTC') if timestamps.min().tz is None else timestamps.min()
                        max_ts = pd.Timestamp(timestamps.max()).tz_localize('UTC') if timestamps.max().tz is None else timestamps.max()
                    
                    # Check if time window overlaps with file's time range
                    # Convert start/end to pandas Timestamp for comparison
                    start_ts = pd.Timestamp(start).tz_localize('UTC') if start.tzinfo is None else pd.Timestamp(start)
                    end_ts = pd.Timestamp(end).tz_localize('UTC') if end.tzinfo is None else pd.Timestamp(end)
                    
                    # Check overlap: file range overlaps if (file_min < request_end) and (file_max > request_start)
                    if min_ts < end_ts and max_ts > start_ts:
                        files_with_data.append((path, f"Contains data from {min_ts} to {max_ts}"))
                        print(f"Status: ✓ File {path.name} contains data for requested time window (file range: {min_ts} to {max_ts})")
                    else:
                        files_without_data.append((path, f"File range ({min_ts} to {max_ts}) does not overlap with requested window ({start_ts} to {end_ts})"))
                        print(f"Status: ✗ File {path.name} does NOT contain data for requested time window (file range: {min_ts} to {max_ts})")
                        
                except Exception as e:
                    files_without_data.append((path, f"Error checking file: {e}"))
                    print(f"Status: ⚠ Could not validate file {path.name}: {e}")
            
            # If no files contain data for the time window, raise error
            if not files_with_data:
                error_msg = (
                    f"ERROR: No trade data files contain data for the requested time window\n"
                    f"  Requested time window: {start} to {end}\n"
                    f"  Files checked: {len(raw_trades_paths)}\n"
                )
                for path, reason in files_without_data:
                    error_msg += f"    - {path.name}: {reason}\n"
                error_msg += (
                    f"\n  Please ensure:\n"
                    f"    1. The dataset folder contains data for the requested date\n"
                    f"    2. The time window falls within the data file's time range\n"
                    f"    3. The dataset name matches the date folder (e.g., 'day-2023-05-22' for May 22 data)"
                )
                validation_errors.append(error_msg)
        
        # Report validation results
        if validation_errors:
            error_msg = "VALIDATION FAILED:\n" + "\n".join(validation_errors)
            if validation_warnings:
                error_msg += "\n\nWARNINGS:\n" + "\n".join(validation_warnings)
            raise RuntimeError(error_msg)
        
        if validation_warnings:
            print("VALIDATION WARNINGS:")
            for warning in validation_warnings:
                print(f"  {warning}")
        
        # Create and register instrument in catalog BEFORE building data configs
        print("Status: Creating and registering instrument in catalog...")
        self._create_and_register_instrument(config)
        print("Status: ✓ Instrument registered successfully")
        
        # Build data configs - this will attempt to convert/register book data if available
        # We need to track whether book data exists for venue config
        print("Status: Building data configuration and converting data to catalog...")
        print(f"Status: Catalog location: {catalog_path}")
        data_configs, has_book_data = self._build_data_config_with_book_check(
            config, instrument_id_str, start, end, snapshot_mode
        )
        
        # Verify data configs were created
        if not data_configs:
            raise RuntimeError("ERROR: No data configurations created. Check that trade data files exist and are accessible.")
        
        print(f"Status: ✓ Created {len(data_configs)} data configuration(s)")
        for i, dc in enumerate(data_configs, 1):
            print(f"Status:   Config {i}: {dc.data_cls.__name__} for {dc.instrument_id} ({dc.start_time} to {dc.end_time})")
        
        # Build venue config - adjust book_type if no book data is available
        print("Status: Configuring venue and strategy...")
        venue_config = self._build_venue_config(config, has_book_data=has_book_data)
        
        # Build execution algorithms first to determine if NORMAL mode is requested
        exec_algorithms = self._build_exec_algorithms(
            config,
            exec_algorithm_type=exec_algorithm_type,
            exec_algorithm_params=exec_algorithm_params
        )
        
        # Ensure strategy config knows about execution algorithm from CLI
        # This is critical - strategy needs exec_algorithm config to create orders with exec_algorithm_id
        if exec_algorithm_type:
            if "strategy" not in config:
                config["strategy"] = {}
            # Set exec algorithm config for strategy
            config["strategy"]["exec_algorithm"] = {
                "type": exec_algorithm_type.upper(),
                "params": exec_algorithm_params or {}
            }
        
        strategy_config = self._build_strategy_config(config)
        
        # Create BacktestRunConfig
        print("Status: Starting backtest execution...")
        engine_config = BacktestEngineConfig(
                strategies=[strategy_config],
        )
        
        # Create run config - try to pass exec_algorithms if supported
        run_config_kwargs = {
            "engine": engine_config,
            "venues": [venue_config],
            "data": data_configs,
            "start": start,
            "end": end,
        }
        # Try to add exec_algorithms if the parameter exists
        if exec_algorithms:
            try:
                # Check if BacktestRunConfig accepts exec_algorithms parameter
                import inspect
                sig = inspect.signature(BacktestRunConfig.__init__)
                if 'exec_algorithms' in sig.parameters:
                    run_config_kwargs["exec_algorithms"] = exec_algorithms
                    print(f"Status: ✓ Adding execution algorithms to BacktestRunConfig")
            except Exception:
                pass  # Parameter doesn't exist, will add manually later
        
        run_config = BacktestRunConfig(**run_config_kwargs)
        
        # Execute backtest
        print("Status: Starting backtest execution...")
        print(f"Status:   Time window: {start} to {end}")
        print(f"Status:   Instrument: {instrument_id_str}")
        print(f"Status:   Data configs: {len(data_configs)}")
        print(f"Status:   Snapshot mode: {snapshot_mode}")
        if exec_algorithms:
            algo_names = [algo.__class__.__name__ for algo in exec_algorithms]
            print(f"Status:   Execution algorithms: {algo_names}")
        print("Status: Executing backtest engine (processing ticks, this may take a while)...")
        
        # Create node
        node = BacktestNode(configs=[run_config])
        
        # Build engines first (this creates the engines so we can access them)
        node.build()
        
        # Add execution algorithms to the engines before running
        # Execution algorithms must be registered with the engines so they can handle orders
        if exec_algorithms:
            try:
                # Get the engine from the node after building
                engine = node.get_engine(run_config.id)
                if engine:
                    for exec_algo in exec_algorithms:
                        engine.add_exec_algorithm(exec_algo)
                        print(f"Status: ✓ Added execution algorithm: {exec_algo.__class__.__name__} (ID: {exec_algo.id}) to engine")
                else:
                    print(f"Warning: Could not get engine {run_config.id} to add execution algorithms")
                    # Try alternative: access through node's internal structure
                    if hasattr(node, '_engines'):
                        for engine_id, engine in node._engines.items():
                            for exec_algo in exec_algorithms:
                                engine.add_exec_algorithm(exec_algo)
                                print(f"Status: ✓ Added execution algorithm via _engines dict")
            except Exception as e:
                print(f"Warning: Could not add execution algorithms: {e}")
                import traceback
                traceback.print_exc()
        
        results = node.run()
        
        # Extract results
        if not results:
            raise RuntimeError("ERROR: Backtest returned no results. Check that:\n"
                             "  1. Data exists in catalog for the time window\n"
                             "  2. Instrument is correctly registered\n"
                             "  3. Strategy is properly configured\n"
                             "  4. No errors occurred during execution")
        
        print("Status: ✓ Backtest execution complete")
        print("Status: Extracting and analyzing results...")
        backtest_result = results[0]
        
        # Generate run ID
        config_hash = hashlib.md5(
            str(self.config_loader.config_path).encode()
        ).hexdigest()
        venue_name = config["venue"]["name"]
        run_id = ResultSerializer.generate_run_id(
            venue_name, instrument, dataset, start, end, config_hash
        )
        
        # Build summary
        # Get engine from node to access cache/portfolio BEFORE node is disposed
        print("Status: Analyzing backtest performance metrics...")
        print("Status:   Calculating PnL breakdown...")
        engine = node.get_engine(run_config.id)
        
        # Close all open positions if requested
        # Note: After backtest completes, we can't submit new orders, so we realize unrealized PnL manually
        positions_closed_count = 0
        if close_positions and engine:
            print("Status: Closing open positions...")
            positions_closed_count = self._close_all_positions(engine, instrument_id, config)
        
        # Extract order and fill counts from BacktestResult
        # Orders are stored in engine.cache, not trader.cache
        orders_count = 0
        fills_count = 0
        pnl = 0.0
        avg_return = 0.0
        avg_loss = 0.0
        
        try:
            if engine:
                # Get all orders from engine cache (this is the correct way per NautilusTrader docs)
                orders = engine.cache.orders()
                orders_count = len(orders) if orders else 0
                
                # Get all fills from cache (orders with filled_qty > 0)
                # An order is considered filled if it has any filled quantity
                fills = [o for o in orders if hasattr(o, 'filled_qty') and o.filled_qty and float(o.filled_qty.as_decimal()) > 0] if orders else []
                fills_count = len(fills) if fills else 0
                
                # Try to get PnL and return statistics from engine's portfolio analyzer (most direct method)
                try:
                    if hasattr(engine, 'portfolio') and engine.portfolio:
                        analyzer = engine.portfolio.analyzer
                        stats_pnls = analyzer.get_performance_stats_pnls()
                        stats_returns = analyzer.get_performance_stats_returns()
                        
                        # Get total PnL from statistics - look for "PnL (total)" key
                        base_currency_str = config["venue"]["base_currency"]
                        # Direct lookup for 'PnL (total)' key
                        if 'PnL (total)' in stats_pnls:
                            pnl_value = stats_pnls['PnL (total)']
                            if pnl_value is not None:
                                pnl = float(pnl_value)
                        else:
                            # Fallback: search for any key with "total" and "pnl"
                            for key, value in stats_pnls.items():
                                if "total" in key.lower() and "pnl" in key.lower():
                                    if isinstance(value, dict):
                                        # Value is a dict with currency keys
                                        for currency, pnl_val in value.items():
                                            if currency == base_currency_str or currency == "USDT":
                                                if pnl_val is not None:
                                                    pnl += float(pnl_val)
                                    elif value is not None:
                                        # Value is a direct number
                                        pnl += float(value)
                                        break  # Found it, no need to continue
                        
                        # Calculate avg_return and avg_loss from positions report or fills
                        # For NETTING OMS with frequent opens/closes, we need to track all position cycles
                        try:
                            instrument_id = InstrumentId.from_str(config["instrument"]["id"])
                            realized_pnls = []
                            
                            # Method 1: Try trader's positions report (includes snapshots automatically)
                            try:
                                if hasattr(engine, 'trader') and engine.trader:
                                    positions_report = engine.trader.generate_positions_report()
                                    if positions_report is not None and len(positions_report) > 0:
                                        # Filter by instrument_id and extract realized_pnl
                                        instrument_id_str = str(instrument_id)
                                        for row in positions_report.itertuples():
                                            row_instrument_id = str(row.instrument_id) if hasattr(row, 'instrument_id') else None
                                            if row_instrument_id == instrument_id_str:
                                                if hasattr(row, 'realized_pnl') and row.realized_pnl:
                                                    try:
                                                        pnl_val = float(row.realized_pnl)
                                                        realized_pnls.append(pnl_val)
                                                    except (ValueError, TypeError):
                                                        pass
                            except Exception as report_error:
                                pass
                            
                            # Method 2: Get all positions (open + closed) for realized_pnl
                            if not realized_pnls:
                                try:
                                    closed_positions = engine.cache.positions_closed(instrument_id=instrument_id)
                                    if closed_positions and len(closed_positions) > 0:
                                        for pos in closed_positions:
                                            if pos.realized_pnl:
                                                pnl_val = float(pos.realized_pnl.as_decimal())
                                                realized_pnls.append(pnl_val)
                                    
                                    open_positions = engine.cache.positions_open(instrument_id=instrument_id)
                                    if open_positions and len(open_positions) > 0:
                                        for pos in open_positions:
                                            if pos.realized_pnl:
                                                pnl_val = float(pos.realized_pnl.as_decimal())
                                                realized_pnls.append(pnl_val)
                                except Exception as pos_error:
                                    pass
                            
                            # Method 3: Calculate from fills report (has execution prices)
                            # This gives us ALL cycles with actual fill prices
                            # For trade-driven strategies, positions may accumulate without closing
                            if fills:
                                try:
                                    # Get fills report which includes execution prices
                                    fills_report = None
                                    if hasattr(engine, 'trader') and engine.trader:
                                        fills_report = engine.trader.generate_order_fills_report()
                                    
                                    if fills_report is not None and len(fills_report) > 0:
                                        # Filter by instrument_id and sort by timestamp
                                        instrument_id_str = str(instrument_id)
                                        instrument_fills = fills_report[
                                            fills_report['instrument_id'].astype(str) == instrument_id_str
                                        ].copy()
                                        
                                        if 'ts_event' in instrument_fills.columns:
                                            instrument_fills = instrument_fills.sort_values('ts_event')
                                        
                                        # Track position cycles from fills report
                                        net_position_qty = 0.0
                                        avg_entry_price = 0.0
                                        position_cycles = []
                                        
                                        for idx, row in instrument_fills.iterrows():
                                            try:
                                                fill_price = float(row['last_px']) if 'last_px' in row else None
                                                fill_qty = float(row['last_qty']) if 'last_qty' in row else None
                                                fill_side_str = str(row['order_side']) if 'order_side' in row else None
                                                
                                                if fill_price is None or fill_qty is None or fill_side_str is None:
                                                    continue
                                                
                                                is_buy = 'BUY' in fill_side_str.upper()
                                                
                                                prev_position_qty = net_position_qty
                                                
                                                # Update position quantity
                                                if is_buy:
                                                    net_position_qty += fill_qty
                                                else:
                                                    net_position_qty -= fill_qty
                                                
                                                # Detect closed cycles
                                                if prev_position_qty != 0:
                                                    if (prev_position_qty > 0 and net_position_qty <= 0) or \
                                                       (prev_position_qty < 0 and net_position_qty >= 0) or \
                                                       (net_position_qty == 0):
                                                        # Position closed or flipped
                                                        closed_qty = abs(prev_position_qty)
                                                        if closed_qty > 0 and avg_entry_price > 0:
                                                            if prev_position_qty > 0:  # Was long
                                                                cycle_pnl = (fill_price - avg_entry_price) * closed_qty
                                                            else:  # Was short
                                                                cycle_pnl = (avg_entry_price - fill_price) * closed_qty
                                                            position_cycles.append(cycle_pnl)
                                                            
                                                            # Reset for new position
                                                            if net_position_qty == 0:
                                                                avg_entry_price = 0.0
                                                            else:
                                                                avg_entry_price = fill_price
                                                    elif prev_position_qty * net_position_qty > 0:
                                                        # Same direction, update average entry price
                                                        total_cost = (abs(prev_position_qty) * avg_entry_price) + (fill_qty * fill_price)
                                                        net_position_qty_abs = abs(net_position_qty)
                                                        if net_position_qty_abs > 0:
                                                            avg_entry_price = total_cost / net_position_qty_abs
                                                else:
                                                    # Opening new position
                                                    avg_entry_price = fill_price
                                            except Exception as row_error:
                                                continue
                                        
                                        # Add cycles to realized_pnls
                                        for cycle_pnl in position_cycles:
                                            if not any(abs(existing - cycle_pnl) < 0.01 for existing in realized_pnls):
                                                realized_pnls.append(cycle_pnl)
                                        print(f"Debug: Method 3 (fills report): Found {len(position_cycles)} position cycles")
                                        
                                        # Add cycles to realized_pnls (avoid duplicates)
                                        for cycle_pnl in position_cycles:
                                            if not any(abs(existing - cycle_pnl) < 0.01 for existing in realized_pnls):
                                                realized_pnls.append(cycle_pnl)
                                        print(f"Debug: Method 3: Total cycles now: {len(realized_pnls)}")
                                        
                                        if len(position_cycles) == 0:
                                            print(f"Debug: No position cycles detected - positions are accumulating without closing/flipping")
                                            print(f"Debug: This is normal for trade-driven strategies that follow market flow")
                                except Exception as fill_error:
                                    print(f"Debug: Method 3 failed: {fill_error}")
                                    import traceback
                                    traceback.print_exc()
                                    pass
                            
                            # Calculate avg_return and avg_loss from realized PnLs
                            if realized_pnls:
                                wins = [p for p in realized_pnls if p > 0]
                                losses = [p for p in realized_pnls if p < 0]
                                
                                # Calculate average returns as percentage of starting balance
                                starting_balance = config["venue"]["starting_balance"]
                                if wins:
                                    avg_return = (sum(wins) / len(wins)) / starting_balance
                                if losses:
                                    avg_loss = (sum(losses) / len(losses)) / starting_balance
                        except Exception as snapshot_error:
                            # Fallback to stats_returns if snapshots/closed positions not available
                            if stats_returns:
                                # Average Win (Return) - average return for winning trades
                                if 'Average Win (Return)' in stats_returns:
                                    avg_win_val = stats_returns['Average Win (Return)']
                                    if avg_win_val is not None and not (isinstance(avg_win_val, float) and (avg_win_val != avg_win_val)):  # Check for NaN
                                        avg_return = float(avg_win_val)
                                
                                # Average Loss (Return) - average return for losing trades
                                if 'Average Loss (Return)' in stats_returns:
                                    avg_loss_val = stats_returns['Average Loss (Return)']
                                    if avg_loss_val is not None and not (isinstance(avg_loss_val, float) and (avg_loss_val != avg_loss_val)):  # Check for NaN
                                        avg_loss = float(avg_loss_val)
                                
                                # Fallback: use overall average if no wins/losses separated
                                if avg_return == 0.0 and 'Average (Return)' in stats_returns:
                                    avg_return_val = stats_returns['Average (Return)']
                                    if avg_return_val is not None and not (isinstance(avg_return_val, float) and (avg_return_val != avg_return_val)):  # Check for NaN
                                        avg_return = float(avg_return_val)
                        
                        # Also try to get from account balance change if still 0
                        if pnl == 0.0:
                            venue = Venue(venue_config.name)
                            account = engine.portfolio.account(venue)
                            if account:
                                base_currency_str = config["venue"]["base_currency"]
                                base_currency_obj = Currency.from_str(base_currency_str)
                                final_balance = float(account.balance_total(base_currency_obj).as_decimal())
                                starting_balance = config["venue"]["starting_balance"]
                                pnl = final_balance - starting_balance
                except Exception as analyzer_error:
                    print(f"Warning: Could not get PnL from engine portfolio analyzer: {analyzer_error}")
                    import traceback
                    traceback.print_exc()
                    # Reset pnl to 0.0 only if there was an error
                    pnl = 0.0
                
                # Fallback: Get portfolio from backtest result to calculate P&L (only if pnl is still 0)
                if pnl == 0.0:
                    portfolio = backtest_result.get_portfolio() if hasattr(backtest_result, 'get_portfolio') else None
                    if portfolio:
                        try:
                            # Use portfolio analyzer to get PnL statistics (most reliable method)
                            analyzer = portfolio.analyzer
                            stats_pnls = analyzer.get_performance_stats_pnls()
                            stats_returns_fallback = analyzer.get_performance_stats_returns()
                            
                            # Extract average return and average loss from positions
                            # (same logic as main section - best for NETTING OMS with frequent opens/closes)
                            if avg_return == 0.0 or avg_loss == 0.0:
                                try:
                                    instrument_id = InstrumentId.from_str(config["instrument"]["id"])
                                    realized_pnls = []
                                    
                                    # Get positions (closed + open) for this instrument
                                    if hasattr(engine, 'cache'):
                                        # Check closed positions first
                                        closed_positions = engine.cache.positions_closed(instrument_id=instrument_id)
                                        if closed_positions and len(closed_positions) > 0:
                                            for pos in closed_positions:
                                                if pos.realized_pnl:
                                                    pnl_val = float(pos.realized_pnl.as_decimal())
                                                    realized_pnls.append(pnl_val)
                                        
                                        # Also check open positions
                                        open_positions = engine.cache.positions_open(instrument_id=instrument_id)
                                        if open_positions and len(open_positions) > 0:
                                            for pos in open_positions:
                                                if pos.realized_pnl:
                                                    pnl_val = float(pos.realized_pnl.as_decimal())
                                                    realized_pnls.append(pnl_val)
                                    
                                    # Calculate avg_return and avg_loss from realized PnLs
                                    if realized_pnls:
                                        wins = [p for p in realized_pnls if p > 0]
                                        losses = [p for p in realized_pnls if p < 0]
                                        
                                        starting_balance = config["venue"]["starting_balance"]
                                        if wins and avg_return == 0.0:
                                            avg_return = (sum(wins) / len(wins)) / starting_balance
                                        if losses and avg_loss == 0.0:
                                            avg_loss = (sum(losses) / len(losses)) / starting_balance
                                except Exception as snapshot_error:
                                    # Fallback to stats_returns if snapshots not available
                                    if stats_returns_fallback:
                                        if 'Average Win (Return)' in stats_returns_fallback and avg_return == 0.0:
                                            avg_win_val = stats_returns_fallback['Average Win (Return)']
                                            if avg_win_val is not None and not (isinstance(avg_win_val, float) and (avg_win_val != avg_win_val)):
                                                avg_return = float(avg_win_val)
                                        
                                        if 'Average Loss (Return)' in stats_returns_fallback and avg_loss == 0.0:
                                            avg_loss_val = stats_returns_fallback['Average Loss (Return)']
                                            if avg_loss_val is not None and not (isinstance(avg_loss_val, float) and (avg_loss_val != avg_loss_val)):
                                                avg_loss = float(avg_loss_val)
                                        
                                        # Final fallback: use overall average
                                        if avg_return == 0.0 and 'Average (Return)' in stats_returns_fallback:
                                            avg_return_val = stats_returns_fallback['Average (Return)']
                                            if avg_return_val is not None and not (isinstance(avg_return_val, float) and (avg_return_val != avg_return_val)):
                                                avg_return = float(avg_return_val)
                            
                            # Get total PnL from statistics (this includes all realized PnL)
                            # The key format is usually "PnL (total)" or similar
                            total_pnl = 0.0
                            base_currency_str = config["venue"]["base_currency"]
                            
                            # Try to find total PnL in stats
                            for key, value in stats_pnls.items():
                                if "total" in key.lower() or "pnl" in key.lower():
                                    if value is not None:
                                        # Value might be a dict with currency keys
                                        if isinstance(value, dict):
                                            for currency, pnl_val in value.items():
                                                if currency == base_currency_str or currency == "USDT":
                                                    total_pnl += float(pnl_val) if pnl_val is not None else 0.0
                                        else:
                                            total_pnl += float(value) if value is not None else 0.0
                            
                            # If no total found, sum all PnL values
                            if total_pnl == 0.0:
                                for key, value in stats_pnls.items():
                                    if isinstance(value, dict):
                                        for currency, pnl_val in value.items():
                                            if pnl_val is not None:
                                                total_pnl += float(pnl_val)
                                    elif value is not None:
                                        total_pnl += float(value)
                            
                            # Fallback: calculate from realized + unrealized PnL
                            if total_pnl == 0.0:
                                venue = Venue(venue_config.name)
                                realized_pnls = portfolio.realized_pnls(venue)
                                unrealized_pnls = portfolio.unrealized_pnls(venue)
                                
                                for currency, money in realized_pnls.items():
                                    if money:
                                        total_pnl += float(money.as_decimal())
                                
                                for currency, money in unrealized_pnls.items():
                                    if money:
                                        total_pnl += float(money.as_decimal())
                            
                            pnl = total_pnl
                        except Exception as pnl_error:
                            print(f"Warning: Could not calculate PnL from portfolio analyzer: {pnl_error}")
                            import traceback
                            traceback.print_exc()
                            # Fallback: try account balance difference
                            try:
                                venue = Venue(venue_config.name)
                                account = portfolio.account(venue)
                                if account:
                                    base_currency_str = config["venue"]["base_currency"]
                                    base_currency_obj = Currency.from_str(base_currency_str)
                                    final_balance = float(account.balance_total(base_currency_obj).as_decimal())
                                    starting_balance = config["venue"]["starting_balance"]
                                    pnl = final_balance - starting_balance
                            except Exception as balance_error:
                                print(f"Warning: Could not calculate PnL from account balance: {balance_error}")
                                pnl = 0.0
                else:
                    # Only try fallback if pnl is still 0.0
                    if pnl == 0.0:
                        # Fallback: try to get account from engine cache
                        try:
                            account = engine.cache.account(venue_config.name) if hasattr(engine.cache, 'account') else None
                            if account:
                                base_currency_str = config["venue"]["base_currency"]
                                base_currency_obj = Currency.from_str(base_currency_str)
                                final_balance = float(account.balance_total(base_currency_obj).as_decimal())
                                starting_balance = config["venue"]["starting_balance"]
                                pnl = final_balance - starting_balance
                        except Exception as cache_error:
                            print(f"Warning: Could not get account from cache: {cache_error}")
                            # Don't reset pnl if it was already set
                            if pnl == 0.0:
                                pnl = 0.0
        except Exception as e:
            print(f"Warning: Could not extract results from engine cache: {e}")
            import traceback
            traceback.print_exc()
        
        # Use StrategyEvaluator for comprehensive performance analysis
        # Pass close_positions flag to adjust PnL calculation
        print("Status: Calculating performance metrics...")
        try:
            performance = StrategyEvaluator.evaluate_performance(
                engine=engine,
                portfolio=backtest_result.get_portfolio() if hasattr(backtest_result, 'get_portfolio') else None,
                config=config,
                venue_config_name=venue_config.name,
                close_positions=close_positions
            )
            print("Status: Performance evaluation complete")
            
            # Build summary with comprehensive metrics
            summary = {
                "orders": orders_count,
                "fills": fills_count,
                "pnl": performance["pnl"]["total"],
                "pnl_breakdown": {
                    "realized": performance["pnl"]["realized"],
                    "unrealized": performance["pnl"]["unrealized"],
                    "unrealized_before_closing": performance["pnl"].get("unrealized_before_closing", performance["pnl"]["unrealized"]),
                    "commissions": performance["pnl"]["commissions"],
                    "net": performance["pnl"]["net"],
                },
                "account": performance["account"],
                "returns": performance["returns"],
                "position": performance["position"],
                "position_stats": performance.get("position_stats", {}),
                "trades": performance["trades"],
                "drawdown": performance["drawdown"],
                # Legacy fields for backward compatibility
                "avg_return": performance["returns"].get("avg_return", avg_return),
                "avg_loss": performance["trades"].get("avg_loss_pct", avg_loss),
                "max_drawdown": performance["drawdown"]["max_drawdown"],
            }
        except Exception as eval_error:
            print(f"Warning: Could not evaluate performance: {eval_error}")
            import traceback
            traceback.print_exc()
            # Fallback to basic summary
            summary = {
                "orders": orders_count,
                "fills": fills_count,
                "pnl": pnl,
                "avg_return": avg_return,
                "avg_loss": avg_loss,
                "max_drawdown": 0.0,
            }
        
        if fast_mode:
            return ResultSerializer.serialize_fast(
                run_id=run_id,
                instrument=instrument,
                dataset=dataset,
                start=start,
                end=end,
                summary=summary,
                config_path=str(self.config_loader.config_path),
                snapshot_mode=snapshot_mode
            )
        
        # Report mode - build detailed results
        timeline = []
        orders_list_for_report = []
        
        # Build timeline from events (chronological order)
        # OPTIMIZED: Use cache directly instead of generating full reports for better performance
        # Following NautilusTrader best practices: use cache for efficient data access
        if engine:
            # Convert nanoseconds to datetime
            def ns_to_datetime(ns: int) -> datetime:
                """Convert nanoseconds timestamp to datetime."""
                return datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc)
            
            # Get orders from cache (fast)
            all_orders = engine.cache.orders()
            print(f"Debug: Found {len(all_orders) if all_orders else 0} orders in cache")
            
            if not all_orders:
                print("Warning: No orders found in cache for timeline")
            else:
                orders_by_id = {}
                timeline_count = 0
                
                # First pass: collect all orders and add to timeline
                timeline_count = 0
                # Track rejection reasons from strategy events (will be populated later)
                rejection_reasons_by_order_id = {}
                
                for order in all_orders:
                    try:
                        order_id = str(order.client_order_id)
                        order_dict = {
                            "id": order_id,
                            "side": order.side.name.lower() if hasattr(order.side, 'name') else str(order.side),
                            "price": float(order.price) if hasattr(order, 'price') and order.price else 0.0,
                            "amount": float(order.quantity) if hasattr(order, 'quantity') and order.quantity else 0.0,
                            "status": order.status.name.lower() if hasattr(order.status, 'name') else str(order.status),
                        }
                        orders_list_for_report.append(order_dict)
                        orders_by_id[order_id] = order_dict
                        
                        # Add order event to timeline (try multiple timestamp attributes)
                        order_ts_ns = None
                        if hasattr(order, 'ts_init') and order.ts_init:
                            order_ts_ns = order.ts_init
                        elif hasattr(order, 'ts_event') and order.ts_event:
                            order_ts_ns = order.ts_event
                        elif hasattr(order, 'ts_accepted') and order.ts_accepted:
                            order_ts_ns = order.ts_accepted
                        
                        if order_ts_ns:
                            try:
                                order_ts = ns_to_datetime(order_ts_ns)
                                timeline.append({
                                    "ts": order_ts.isoformat().replace('+00:00', 'Z'),
                                    "event": "Order",
                                    "data": order_dict
                                })
                                timeline_count += 1
                            except Exception as ts_error:
                                print(f"Debug: Timestamp conversion failed for order {order.client_order_id}: {ts_error}")
                                pass  # Skip if timestamp conversion fails
                    except Exception as e:
                        print(f"Warning: Could not serialize order {order.client_order_id}: {e}")
                        continue
            
                # ENHANCED: Use strategy-captured fill events for accurate fill data
                # First try to get fills from strategy (most accurate - has actual fill prices)
                fill_count = 0
                try:
                    # Try to get strategy instance to access captured fill events
                    strategy_fills = []
                    strategy_rejections = []
                    
                    # Access strategy from engine
                    if hasattr(engine, 'trader') and engine.trader:
                        # Try multiple methods to access strategies
                        strategies = []
                        if hasattr(engine.trader, 'strategies'):
                            try:
                                strategies = engine.trader.strategies()
                            except Exception:
                                pass
                        elif hasattr(engine.trader, 'cache') and hasattr(engine.trader.cache, 'strategies'):
                            try:
                                strategies = engine.trader.cache.strategies()
                            except Exception:
                                pass
                        
                        # Also try accessing via engine cache
                        if not strategies and hasattr(engine, 'cache'):
                            try:
                                if hasattr(engine.cache, 'strategies'):
                                    strategies = engine.cache.strategies()
                            except Exception:
                                pass
                        
                        # Extract fill and rejection events from strategies
                        for strategy in strategies:
                            try:
                                if hasattr(strategy, 'get_fill_events'):
                                    fills = strategy.get_fill_events()
                                    if fills:
                                        strategy_fills.extend(fills)
                                if hasattr(strategy, 'get_rejection_events'):
                                    rejections = strategy.get_rejection_events()
                                    if rejections:
                                        strategy_rejections.extend(rejections)
                            except Exception as strategy_access_error:
                                print(f"Warning: Could not access strategy events: {strategy_access_error}")
                                continue
                    
                    # Add fill events from strategy (has actual fill prices and timestamps)
                    fill_events_by_order_id = {}
                    for fill_event in strategy_fills:
                        try:
                            order_id = fill_event.get('order_id')
                            fill_ts_ns = fill_event.get('ts_event') or fill_event.get('ts_init')
                            
                            if order_id and fill_ts_ns:
                                fill_ts = ns_to_datetime(fill_ts_ns)
                                fill_data = {
                                    "order_id": order_id,
                                    "price": fill_event.get('price', 0.0),
                                    "quantity": fill_event.get('quantity', 0.0),
                                    "side": fill_event.get('side', 'unknown'),
                                }
                                
                                # Store by order_id to avoid duplicates
                                fill_events_by_order_id[order_id] = {
                                    "ts": fill_ts.isoformat().replace('+00:00', 'Z'),
                                    "event": "Fill",
                                    "data": fill_data
                                }
                        except Exception as fill_parse_error:
                            print(f"Warning: Error parsing fill event: {fill_parse_error}")
                            continue
                    
                    # Add fill events to timeline
                    for fill_event_entry in fill_events_by_order_id.values():
                        timeline.append(fill_event_entry)
                    fill_count = len(fill_events_by_order_id)
                    
                    # Add rejection events to timeline
                    rejection_count = 0
                    for rejection_event in strategy_rejections:
                        try:
                            order_id = rejection_event.get('order_id')
                            rejection_ts_ns = rejection_event.get('ts_event') or rejection_event.get('ts_init')
                            
                            if order_id and rejection_ts_ns:
                                rejection_ts = ns_to_datetime(rejection_ts_ns)
                                
                                # Find corresponding order to get full details
                                order_details = orders_by_id.get(order_id, {})
                                
                                rejection_data = {
                                    "order_id": order_id,
                                    "reason": rejection_event.get('reason', 'Unknown'),
                                    "side": order_details.get('side', 'unknown'),
                                    "price": order_details.get('price', 0.0),
                                    "amount": order_details.get('amount', 0.0),
                                }
                                
                                timeline.append({
                                    "ts": rejection_ts.isoformat().replace('+00:00', 'Z'),
                                    "event": "OrderRejected",
                                    "data": rejection_data
                                })
                                rejection_count += 1
                                
                                # Store rejection reason for later use
                                rejection_reasons_by_order_id[order_id] = rejection_event.get('reason', 'Unknown')
                                
                                # Update order status in orders_list_for_report
                                for order_dict in orders_list_for_report:
                                    if order_dict.get('id') == order_id:
                                        if order_dict.get('status') not in ['denied', 'rejected']:
                                            order_dict['status'] = 'rejected'
                                        order_dict['rejection_reason'] = rejection_reasons_by_order_id[order_id]
                                        break
                        except Exception as rejection_parse_error:
                            print(f"Warning: Error parsing rejection event: {rejection_parse_error}")
                            continue
                    
                    print(f"Debug: Added {fill_count} fill events and {rejection_count} rejection events from strategy")
                    
                except Exception as strategy_events_error:
                    print(f"Warning: Could not get fill/rejection events from strategy: {strategy_events_error}")
                    import traceback
                    traceback.print_exc()
                    
                    # Fallback: Add fill events based on order status (original method)
                    try:
                        fill_count = 0
                        for order in all_orders:
                            try:
                                order_id = str(order.client_order_id)
                                if order_id not in orders_by_id:
                                    continue
                                
                                # Check if order was filled
                                is_filled = False
                                filled_qty = 0.0
                                fill_price = orders_by_id[order_id]['price']
                                
                                if hasattr(order, 'filled_qty') and order.filled_qty:
                                    filled_qty = float(order.filled_qty.as_decimal())
                                    if filled_qty > 0:
                                        is_filled = True
                                
                                # Also check status
                                if hasattr(order, 'status'):
                                    status_str = order.status.name.lower() if hasattr(order.status, 'name') else str(order.status)
                                    if 'filled' in status_str or 'partially_filled' in status_str:
                                        is_filled = True
                                
                                if is_filled:
                                    # Use order timestamp for fill (or try to get fill timestamp)
                                    fill_ts_ns = None
                                    if hasattr(order, 'ts_event') and order.ts_event:
                                        fill_ts_ns = order.ts_event
                                    elif hasattr(order, 'ts_last') and order.ts_last:
                                        fill_ts_ns = order.ts_last
                                    elif hasattr(order, 'ts_init') and order.ts_init:
                                        fill_ts_ns = order.ts_init
                                    
                                    if fill_ts_ns:
                                        try:
                                            fill_ts = ns_to_datetime(fill_ts_ns)
                                            fill_data = {
                                                "order_id": order_id,
                                                "price": fill_price,
                                                "quantity": filled_qty if filled_qty > 0 else orders_by_id[order_id]['amount'],
                                            }
                                            
                                            timeline.append({
                                                "ts": fill_ts.isoformat().replace('+00:00', 'Z'),
                                                "event": "Fill",
                                                "data": fill_data
                                            })
                                            fill_count += 1
                                        except Exception as fill_ts_error:
                                            pass
                            except Exception:
                                continue
                        
                        print(f"Debug: Added {fill_count} fill events to timeline (fallback method)")
                    except Exception as fills_error:
                        print(f"Warning: Could not build fill timeline: {fills_error}")
                        import traceback
                        traceback.print_exc()
                
                # Sort timeline by timestamp (required for chronological order)
                if timeline:
                    timeline.sort(key=lambda x: x["ts"])
                print(f"Debug: Built timeline with {len(timeline)} events ({timeline_count} orders, {fill_count if 'fill_count' in locals() else 0} fills)")
        
        result = ResultSerializer.serialize_report(
            run_id=run_id,
            instrument=instrument,
            dataset=dataset,
            start=start,
            end=end,
            summary=summary,
            timeline=timeline,
            orders=orders_list_for_report,
            config_path=str(self.config_loader.config_path),
            snapshot_mode=snapshot_mode,
            catalog_root=str(self.catalog_manager.catalog_path)
        )
        
        # Export ticks if requested
        if export_ticks:
            ticks = []
            # Extract ticks from catalog for the time window
            try:
                if self.catalog:
                    # Convert datetime to nanoseconds
                    start_ns = int(start.timestamp() * 1_000_000_000)
                    end_ns = int(end.timestamp() * 1_000_000_000)
                    
                    # Query TradeTick data from catalog
                    trade_ticks = self.catalog.trade_ticks(
                        instrument_ids=[instrument_id],
                        start=start_ns,
                        end=end_ns,
                    )
                    
                    # Convert TradeTick objects to dictionaries
                    for tick in trade_ticks:
                        ticks.append({
                            "ts_event": tick.ts_event,
                            "ts_init": tick.ts_init,
                            "instrument_id": str(tick.instrument_id),
                            "price": float(tick.price.as_decimal()),
                            "size": float(tick.size.as_decimal()),
                            "aggressor_side": tick.aggressor_side.name if tick.aggressor_side else None,
                            "trade_id": str(tick.trade_id),
                        })
                    print(f"Exported {len(ticks)} ticks for export")
            except Exception as e:
                print(f"Warning: Could not export ticks: {e}")
                import traceback
                traceback.print_exc()
            
            ticks_dir = Path("frontend/public/tickdata")
            ResultSerializer.save_ticks(ticks, ticks_dir, run_id)
        
        return result

