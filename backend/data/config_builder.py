"""Data configuration builder for backtest data setup."""
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from nautilus_trader.backtest.config import BacktestDataConfig
from nautilus_trader.model.data import TradeTick, OrderBookDeltas
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.persistence.catalog import ParquetDataCatalog

from backend.data.converter import DataConverter
from backend.data.loader import UCSDataLoader
from backend.instruments.utils import convert_instrument_id_to_gcs_format


class DataConfigBuilder:
    """Builds BacktestDataConfig instances from configuration."""
    
    def __init__(
        self,
        catalog: Optional[ParquetDataCatalog] = None,
        ucs_loader: Optional[UCSDataLoader] = None
    ):
        """
        Initialize data config builder.
        
        Args:
            catalog: ParquetDataCatalog instance (optional, will be created if needed)
            ucs_loader: UCSDataLoader instance for GCS access (optional)
        """
        self.catalog = catalog
        self.ucs_loader = ucs_loader
    
    def build_with_book_check(
        self,
        config: Dict[str, Any],
        instrument_id: str,
        start: datetime,
        end: datetime,
        snapshot_mode: str,
        catalog: Optional[ParquetDataCatalog] = None,
        ucs_loader: Optional[UCSDataLoader] = None
    ) -> Tuple[List[BacktestDataConfig], bool]:
        """
        Build BacktestDataConfig list and check if book data is available.
        
        Supports both local files and GCS bucket based on data_source config.
        
        Args:
            config: Configuration dictionary
            instrument_id: Instrument identifier string
            start: Start timestamp
            end: End timestamp
            snapshot_mode: Snapshot mode ('trades', 'book', or 'both')
            catalog: ParquetDataCatalog instance (uses self.catalog if not provided)
            ucs_loader: UCSDataLoader instance (uses self.ucs_loader if not provided)
        
        Returns:
            Tuple of (data_configs list, has_book_data bool)
        """
        # Use provided catalog or instance catalog
        catalog = catalog or self.catalog
        ucs_loader = ucs_loader or self.ucs_loader
        
        data_configs = []
        has_book_data = False
        
        # Use the catalog path from config
        base_path_str = os.getenv("UNIFIED_CLOUD_LOCAL_PATH") or config["environment"].get("UNIFIED_CLOUD_LOCAL_PATH", "/app/data_downloads")
        base_path = Path(base_path_str).resolve()
        
        catalog_path_str = os.getenv("DATA_CATALOG_PATH") or config["environment"].get("DATA_CATALOG_PATH", "/app/backend/data/parquet")
        catalog_path = Path(catalog_path_str).resolve()
        catalog_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize catalog if needed
        if catalog is None:
            catalog = ParquetDataCatalog(str(catalog_path))
            self.catalog = catalog
        
        instrument = InstrumentId.from_str(instrument_id)
        
        # Determine data source: 'local', 'gcs', or 'auto' (defaults to 'gcs')
        data_source = config.get("data_source", "gcs").lower()
        if data_source not in ("local", "gcs", "auto"):
            print(f"Warning: Invalid data_source '{data_source}', defaulting to 'gcs'")
            data_source = "gcs"
        
        # Handle 'auto' - prefer GCS, fall back to local only if GCS unavailable
        if data_source == "auto":
            data_source = "gcs"  # Default to GCS
        
        # Initialize UCS loader if needed
        if data_source == "gcs" and ucs_loader is None:
            try:
                from backend.data.loader import UCSDataLoader
                ucs_loader = UCSDataLoader()
                self.ucs_loader = ucs_loader
                print(f"✅ UCS Data Loader initialized (data_source: {data_source})")
            except Exception as e:
                print(f"⚠️  Failed to initialize UCS loader: {e}")
                raise RuntimeError(f"Cannot use GCS data source: {e}")
        
        # Get raw file paths from config
        data_catalog_config = config.get("data_catalog", {})
        trades_path = data_catalog_config.get("trades_path")
        book_snapshot_5_path = data_catalog_config.get("book_snapshot_5_path")
        
        # Extract instrument identifier from path or config for auto-discovery
        instrument_str = str(instrument)
        instrument_file_pattern = None
        if trades_path:
            # Extract filename pattern (e.g., "BINANCE-FUTURES:PERPETUAL:BTC-USDT.parquet")
            if "/" in trades_path:
                instrument_file_pattern = trades_path.split("/")[-1]
            else:
                instrument_file_pattern = trades_path
        
        # Auto-discover data files across all date folders
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
        
        instrument_config = config["instrument"]
        venue_config = config["venue"]
        price_precision = instrument_config.get("price_precision", 2)
        size_precision = instrument_config.get("size_precision", 3)
        
        # Process trades
        if snapshot_mode in ("trades", "both"):
            total_trades_count = 0
            
            # Check if data already exists in catalog
            try:
                existing_check = catalog.query(
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
                if data_source == "gcs" and ucs_loader:
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
                            ucs_loader.load_trades(
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
                            catalog,
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
                        # For 'gcs', raise error - don't fall back
                        raise
                
                # Load from local files (only when explicitly selected)
                if data_source == "local" and raw_trades_paths:
                    for raw_trades_path in raw_trades_paths:
                        if raw_trades_path.exists():
                            try:
                                print(f"📂 Converting and registering trades from {raw_trades_path.name}...")
                                print(f"   File size: {raw_trades_path.stat().st_size / (1024*1024):.2f} MB")
                                trades_count = DataConverter.convert_trades_parquet_to_catalog(
                                    raw_trades_path,
                                    instrument,
                                    catalog,
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
                window_check = catalog.query(
                    data_cls=TradeTick,
                    instrument_ids=[instrument],
                    start=start,
                    end=end,
                    limit=1
                )
                if window_check:
                    all_in_window = catalog.query(
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
        
        # Process order book data
        if snapshot_mode in ("book", "both"):
            # Handle GCS book snapshot loading
            if data_source == "gcs" and ucs_loader:
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
                        ucs_loader.load_book_snapshots(
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
                        catalog,
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
                    existing = catalog.query(
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

