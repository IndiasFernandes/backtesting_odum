"""Data validation utilities for backtest setup."""
import os
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.data import TradeTick, OrderBookDeltas
from nautilus_trader.persistence.catalog import ParquetDataCatalog


class DataValidator:
    """Validates data availability and configuration for backtests."""
    
    @staticmethod
    def validate_dataset_date(
        dataset: str,
        start_date: date
    ) -> Tuple[Optional[date], List[str], List[str]]:
        """
        Validate that dataset name matches the date in time window.
        
        Args:
            dataset: Dataset name (e.g., "day-2023-05-23")
            start_date: Start date from time window
        
        Returns:
            Tuple of (dataset_date, errors, warnings)
        """
        errors = []
        warnings = []
        dataset_date = None
        
        if dataset.startswith("day-"):
            try:
                date_str = dataset.replace("day-", "")
                dataset_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                print(f"Status: Dataset '{dataset}' corresponds to date: {dataset_date}")
            except ValueError as e:
                warnings.append(
                    f"WARNING: Could not parse date from dataset name '{dataset}', "
                    f"expected format 'day-YYYY-MM-DD': {e}"
                )
        else:
            print(f"Status: Dataset '{dataset}' does not start with 'day-', skipping date validation")
        
        # Check if dataset date matches time window date
        if dataset_date is not None and dataset_date != start_date:
            error_msg = (
                f"ERROR: Dataset date mismatch\n"
                f"  Dataset name: {dataset} (date: {dataset_date})\n"
                f"  Requested time window start: {start_date}\n"
                f"  The dataset name must match the date in the time window.\n"
                f"  Auto-detected dataset: 'day-{start_date.strftime('%Y-%m-%d')}'"
            )
            errors.append(error_msg)
            print(f"Status: ✗ VALIDATION ERROR: {error_msg}")
        
        return dataset_date, errors, warnings
    
    @staticmethod
    def validate_catalog_data(
        catalog: ParquetDataCatalog,
        instrument_id: InstrumentId,
        start: datetime,
        end: datetime,
        snapshot_mode: str
    ) -> Tuple[bool, bool]:
        """
        Check if required data exists in catalog.
        
        Args:
            catalog: ParquetDataCatalog instance
            instrument_id: Instrument ID
            start: Start timestamp
            end: End timestamp
            snapshot_mode: Snapshot mode ('trades', 'book', or 'both')
        
        Returns:
            Tuple of (has_trades, has_book)
        """
        catalog_has_trades = False
        catalog_has_book = False
        
        try:
            existing_trades = catalog.query(
                data_cls=TradeTick,
                instrument_ids=[instrument_id],
                start=start,
                end=end,
                limit=1
            )
            if existing_trades:
                catalog_has_trades = True
                all_trades = catalog.query(
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
                existing_book = catalog.query(
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
        
        return catalog_has_trades, catalog_has_book
    
    @staticmethod
    def validate_gcs_data_availability(
        config: Dict[str, Any],
        start_date: date,
        snapshot_mode: str
    ) -> Tuple[List[str], List[str]]:
        """
        Validate GCS data availability.
        
        Args:
            config: Configuration dictionary
            start_date: Start date
            snapshot_mode: Snapshot mode
        
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        try:
            from backend.api.data_checker import DataAvailabilityChecker, _convert_instrument_id_to_gcs_format
            import asyncio
            
            checker = DataAvailabilityChecker(data_source="gcs")
            config_instrument_id = config["instrument"]["id"]
            gcs_instrument_id = _convert_instrument_id_to_gcs_format(config_instrument_id)
            
            date_str = start_date.strftime("%Y-%m-%d")
            
            # Validate trades
            if snapshot_mode in ("trades", "both"):
                has_trades = asyncio.run(checker.check_gcs_file_exists(date_str, gcs_instrument_id, "trades"))
                
                if not has_trades:
                    errors.append(
                        f"ERROR: Trades data NOT FOUND in GCS for {date_str}\n"
                        f"  Instrument: {gcs_instrument_id}\n"
                        f"  Expected: raw_tick_data/by_date/day-{date_str}/data_type-trades/{gcs_instrument_id}.parquet\n"
                        f"  Please ensure the data exists in the GCS bucket."
                    )
                else:
                    print(f"Status: ✓ Trades data found in GCS for {date_str}")
            
            # Validate book snapshots
            if snapshot_mode in ("book", "both"):
                has_book = asyncio.run(checker.check_gcs_file_exists(date_str, gcs_instrument_id, "book_snapshot_5"))
                
                if not has_book:
                    if snapshot_mode == "book":
                        errors.append(
                            f"ERROR: Book snapshot data NOT FOUND in GCS for {date_str}\n"
                            f"  Instrument: {gcs_instrument_id}\n"
                            f"  Expected: raw_tick_data/by_date/day-{date_str}/data_type-book_snapshot_5/{gcs_instrument_id}.parquet\n"
                            f"  Please ensure the data exists in the GCS bucket."
                        )
                    else:
                        warnings.append(
                            f"WARNING: Book snapshot data not found in GCS for {date_str}, will use trades-only mode"
                        )
                else:
                    print(f"Status: ✓ Book snapshot data found in GCS for {date_str}")
        
        except Exception as e:
            if snapshot_mode == "book":
                errors.append(
                    f"ERROR: Failed to validate GCS book snapshot data: {e}\n"
                    f"  Please check GCS connectivity and permissions."
                )
            else:
                warnings.append(f"WARNING: Could not validate GCS book snapshot data: {e}")
        
        return errors, warnings
    
    @staticmethod
    def validate_local_files(
        config: Dict[str, Any],
        dataset: str,
        instrument_id_str: str,
        snapshot_mode: str,
        raw_trades_paths: List[Path],
        raw_book_paths: List[Path]
    ) -> Tuple[List[str], List[str]]:
        """
        Validate local file availability.
        
        Args:
            config: Configuration dictionary
            dataset: Dataset name
            instrument_id_str: Instrument ID string
            snapshot_mode: Snapshot mode
            raw_trades_paths: List of trade file paths
            raw_book_paths: List of book file paths
        
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        base_path_str = os.getenv("UNIFIED_CLOUD_LOCAL_PATH") or config["environment"].get("UNIFIED_CLOUD_LOCAL_PATH", "/app/data_downloads")
        base_path = Path(base_path_str).resolve()
        data_catalog_config = config.get("data_catalog", {})
        trades_path_pattern = data_catalog_config.get("trades_path")
        book_path_pattern = data_catalog_config.get("book_snapshot_5_path")
        
        dataset_folder = base_path / "raw_tick_data" / "by_date" / dataset
        
        # Validate trades
        if snapshot_mode in ("trades", "both"):
            if not dataset_folder.exists():
                errors.append(
                    f"ERROR: Dataset folder not found: {dataset_folder}\n"
                    f"  Required for dataset: {dataset}\n"
                    f"  Expected location: {dataset_folder}\n"
                    f"  Please ensure the dataset folder exists before running the backtest."
                )
            elif not raw_trades_paths:
                errors.append(
                    f"ERROR: No trade data files found for dataset '{dataset}'\n"
                    f"  Dataset folder exists: {dataset_folder}\n"
                    f"  Pattern searched: {trades_path_pattern}\n"
                    f"  Please ensure trade data files exist in the dataset folder."
                )
            else:
                # Check if files exist and have data
                print(f"Status: Checking trade data file availability...")
                total_trades_found = 0
                for path in raw_trades_paths:
                    if path.exists():
                        try:
                            import pyarrow.parquet as pq
                            table = pq.read_table(path, columns=[pq.read_schema(path).names[0]])
                            if table.num_rows > 0:
                                print(f"Status: ✓ Trade data file {path.name} exists and has {table.num_rows} rows")
                                total_trades_found += 1
                            else:
                                warnings.append(f"WARNING: Trade file {path.name} is empty")
                        except Exception as e:
                            warnings.append(f"WARNING: Could not verify trade file {path.name}: {e}")
                
                if total_trades_found == 0:
                    errors.append(
                        f"ERROR: No trade data files found or files are empty for dataset '{dataset}'\n"
                        f"  Dataset folder: {dataset_folder}\n"
                        f"  Files checked: {[str(p) for p in raw_trades_paths]}\n"
                        f"  Please ensure trade data files exist and contain data."
                    )
                else:
                    print(f"Status: ✓ Found {total_trades_found} trade file(s) with data")
        
        # Validate book snapshots
        if snapshot_mode in ("book", "both"):
            if not dataset_folder.exists():
                if snapshot_mode == "book":
                    errors.append(
                        f"ERROR: Dataset folder not found: {dataset_folder}\n"
                        f"  Required for dataset: {dataset}\n"
                        f"  Book snapshot mode requires the dataset folder to exist.\n"
                        f"  Expected location: {dataset_folder}"
                    )
            elif not raw_book_paths:
                if snapshot_mode == "book":
                    errors.append(
                        f"ERROR: Book snapshot mode requested but no book data files found\n"
                        f"  Dataset folder exists: {dataset_folder}\n"
                        f"  Pattern searched: {book_path_pattern}\n"
                        f"  Please ensure book snapshot data files exist in the dataset folder."
                    )
                else:
                    warnings.append(
                        f"WARNING: Book snapshot data not found for dataset '{dataset}', will use trades-only mode\n"
                        f"  Dataset folder: {dataset_folder}\n"
                        f"  Pattern searched: {book_path_pattern}"
                    )
            else:
                print(f"Status: ✓ Found {len(raw_book_paths)} book snapshot file(s)")
        
        return errors, warnings
    
    @staticmethod
    def validate_time_window_in_files(
        raw_trades_paths: List[Path],
        start: datetime,
        end: datetime
    ) -> Tuple[List[Tuple[Path, str]], List[Tuple[Path, str]]]:
        """
        Validate that raw files contain data for the requested time window.
        
        Args:
            raw_trades_paths: List of trade file paths
            start: Start timestamp
            end: End timestamp
        
        Returns:
            Tuple of (files_with_data, files_without_data)
            Each tuple contains (path, reason) pairs
        """
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
                
                # Convert to datetime if needed
                if timestamps.dtype in ['int64', 'int32']:
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
                start_ts = pd.Timestamp(start).tz_localize('UTC') if start.tzinfo is None else pd.Timestamp(start)
                end_ts = pd.Timestamp(end).tz_localize('UTC') if end.tzinfo is None else pd.Timestamp(end)
                
                # Check overlap: file range overlaps if (file_min < request_end) and (file_max > request_start)
                if min_ts < end_ts and max_ts > start_ts:
                    files_with_data.append((path, f"Contains data from {min_ts} to {max_ts}"))
                    print(f"Status: ✓ File {path.name} contains data for requested time window (file range: {min_ts} to {max_ts})")
                else:
                    files_without_data.append((path, f"File range ({min_ts} to {max_ts}) does not overlap with requested window ({start_ts} to {end_ts})"))
                    print(f"Status: ✗ File {path.name} does NOT contain data for requested time window")
            
            except Exception as e:
                files_without_data.append((path, f"Error checking file: {e}"))
                print(f"Status: ⚠ Could not validate file {path.name}: {e}")
        
        return files_with_data, files_without_data

