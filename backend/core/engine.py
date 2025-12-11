"""Main backtest engine orchestrator."""
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.persistence.catalog import ParquetDataCatalog

from backend.config.loader import ConfigLoader
from backend.data.catalog import CatalogManager
from backend.data.config_builder import DataConfigBuilder
from backend.data.validator import DataValidator
from backend.data.loader import UCSDataLoader
from backend.instruments.factory import InstrumentFactory
from backend.core.node_builder import NodeBuilder
from backend.results.serializer import ResultSerializer
from backend.results.extractor import ResultExtractor
from backend.results.timeline import TimelineBuilder
from backend.results.position_manager import PositionManager


class BacktestEngine:
    """
    Main orchestrator for running backtests.
    
    Coordinates all components: validation, data loading, instrument creation,
    node configuration, execution, and result extraction.
    """
    
    def __init__(
        self,
        config_loader: ConfigLoader,
        catalog_manager: Optional[CatalogManager] = None
    ):
        """
        Initialize backtest engine.
        
        Args:
            config_loader: ConfigLoader instance
            catalog_manager: Optional CatalogManager instance
        """
        self.config_loader = config_loader
        self.catalog_manager = catalog_manager or CatalogManager()
        
        # Initialize catalog
        catalog_path_str = os.getenv("DATA_CATALOG_PATH") or \
            self.config_loader.config.get("environment", {}).get("DATA_CATALOG_PATH", "/app/backend/data/parquet")
        catalog_path = Path(catalog_path_str).resolve()
        catalog_path.mkdir(parents=True, exist_ok=True)
        self.catalog = ParquetDataCatalog(str(catalog_path))
        
        # Initialize UCS loader (lazy)
        self.ucs_loader = None
        
        # Initialize component modules
        self.instrument_factory = InstrumentFactory()
        self.data_builder = DataConfigBuilder(catalog=self.catalog, ucs_loader=None)
        self.data_validator = DataValidator()
        self.node_builder = NodeBuilder()
        self.result_extractor = ResultExtractor()
        self.timeline_builder = TimelineBuilder()
        self.position_manager = PositionManager()
    
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
        data_source: str = "gcs",
        exec_algorithm_type: Optional[str] = None,
        exec_algorithm_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run backtest.
        
        Args:
            instrument: Instrument identifier (for display/logging)
            start: Start timestamp
            end: End timestamp
            dataset: Dataset name (optional - auto-detected from time window if not provided)
            snapshot_mode: Snapshot mode (trades|book|both)
            fast_mode: If True, return minimal summary only
            export_ticks: If True, export tick data (only in report mode)
            close_positions: If True, close all open positions at end of backtest (default: True)
            data_source: Data source ('local' or 'gcs') - defaults to 'gcs'
            exec_algorithm_type: Optional execution algorithm type from CLI
            exec_algorithm_params: Optional execution algorithm parameters from CLI
        
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
            config["data_source"] = "gcs"  # Default to GCS
        
        # Get instrument ID from config and convert to NautilusTrader format
        instrument_config = config["instrument"]
        venue_config = config["venue"]
        config_instrument_id = instrument_config["id"]
        venue_name = venue_config["name"]
        
        # Convert config format (e.g., "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN") to Nautilus format (e.g., "BTC-USDT.BINANCE")
        from backend.instruments.utils import get_instrument_id_for_nautilus
        instrument_id_str = get_instrument_id_for_nautilus(config_instrument_id, venue_name)
        instrument_id = InstrumentId.from_str(instrument_id_str)
        
        # Auto-detect dataset from time window if not provided
        start_date = start.date() if hasattr(start, 'date') else start.date()
        if not dataset:
            dataset = f"day-{start_date.strftime('%Y-%m-%d')}"
            print(f"Status: Auto-detected dataset '{dataset}' from time window")
        
        # Determine actual data source
        actual_data_source = config.get("data_source", "gcs").lower()
        if actual_data_source not in ("local", "gcs"):
            actual_data_source = "gcs"
            config["data_source"] = "gcs"
        
        # Initialize UCS loader if needed for GCS
        if actual_data_source == "gcs":
            try:
                from backend.data.loader import UCSDataLoader
                self.ucs_loader = UCSDataLoader()
                self.data_builder.ucs_loader = self.ucs_loader
                print(f"✅ UCS Data Loader initialized for GCS data source")
            except Exception as e:
                print(f"⚠️  Failed to initialize UCS loader: {e}")
                raise RuntimeError(f"Cannot use GCS data source: {e}")
        
        # Step 1: Validate data availability
        print("Status: Validating data availability...")
        catalog_has_trades, catalog_has_book = self.data_validator.validate_catalog_data(
            self.catalog, instrument_id, start, end, snapshot_mode
        )
        
        validation_errors = []
        validation_warnings = []
        
        # If catalog doesn't have all required data, validate source files
        if not (catalog_has_trades and (snapshot_mode == "trades" or (snapshot_mode in ("book", "both") and catalog_has_book))):
            print("Status: Validating data availability (data not in catalog)...")
            
            # Validate dataset date
            dataset_date, date_errors, date_warnings = self.data_validator.validate_dataset_date(dataset, start_date)
            validation_errors.extend(date_errors)
            validation_warnings.extend(date_warnings)
            
            # Fail fast if date mismatch
            if validation_errors:
                error_msg = "VALIDATION FAILED:\n" + "\n".join(validation_errors)
                raise RuntimeError(error_msg)
            
            # Validate data source files
            if actual_data_source == "gcs":
                gcs_errors, gcs_warnings = self.data_validator.validate_gcs_data_availability(
                    config, start_date, snapshot_mode
                )
                validation_errors.extend(gcs_errors)
                validation_warnings.extend(gcs_warnings)
            else:
                # Local file validation - discover files first
                from backend.utils.paths import discover_data_files
                base_path_str = os.getenv("UNIFIED_CLOUD_LOCAL_PATH") or \
                    config["environment"].get("UNIFIED_CLOUD_LOCAL_PATH", "/app/data_downloads")
                base_path = Path(base_path_str).resolve()
                data_catalog_config = config.get("data_catalog", {})
                trades_path_pattern = data_catalog_config.get("trades_path")
                book_path_pattern = data_catalog_config.get("book_snapshot_5_path")
                
                raw_trades_paths = []
                raw_book_paths = []
                
                if trades_path_pattern:
                    if "*" in trades_path_pattern:
                        raw_trades_paths = discover_data_files(base_path, trades_path_pattern, instrument_id_str)
                    else:
                        path_str = str(trades_path_pattern)
                        if path_str.startswith("data_downloads/"):
                            path_str = path_str[len("data_downloads/"):]
                        resolved = (base_path / path_str).resolve()
                        if resolved.exists():
                            raw_trades_paths = [resolved]
                
                if book_path_pattern:
                    if "*" in book_path_pattern:
                        raw_book_paths = discover_data_files(base_path, book_path_pattern, instrument_id_str)
                    else:
                        path_str = str(book_path_pattern)
                        if path_str.startswith("data_downloads/"):
                            path_str = path_str[len("data_downloads/"):]
                        resolved = (base_path / path_str).resolve()
                        if resolved.exists():
                            raw_book_paths = [resolved]
                
                local_errors, local_warnings = self.data_validator.validate_local_files(
                    config, dataset, instrument_id_str, snapshot_mode,
                    raw_trades_paths, raw_book_paths
                )
                validation_errors.extend(local_errors)
                validation_warnings.extend(local_warnings)
                
                # Validate time window in files
                if raw_trades_paths and not catalog_has_trades:
                    files_with_data, files_without_data = self.data_validator.validate_time_window_in_files(
                        raw_trades_paths, start, end
                    )
                    if not files_with_data:
                        error_msg = (
                            f"ERROR: No trade data files contain data for the requested time window\n"
                            f"  Requested time window: {start} to {end}\n"
                            f"  Files checked: {len(raw_trades_paths)}\n"
                        )
                        for path, reason in files_without_data:
                            error_msg += f"    - {path.name}: {reason}\n"
                        validation_errors.append(error_msg)
            
            # Fail if validation errors exist
            if validation_errors:
                error_msg = "VALIDATION FAILED:\n" + "\n".join(validation_errors)
                if validation_warnings:
                    error_msg += "\n\nWARNINGS:\n" + "\n".join(validation_warnings)
                raise RuntimeError(error_msg)
        
        if validation_warnings:
            print("VALIDATION WARNINGS:")
            for warning in validation_warnings:
                print(f"  {warning}")
        
        # Step 2: Create and register instrument
        print("Status: Creating and registering instrument in catalog...")
        catalog_path_str = os.getenv("DATA_CATALOG_PATH") or \
            config["environment"].get("DATA_CATALOG_PATH", "/app/backend/data/parquet")
        catalog_path = Path(catalog_path_str).resolve()
        catalog_path.mkdir(parents=True, exist_ok=True)
        
        instrument_id_created = self.instrument_factory.create_and_register(config, self.catalog)
        print("Status: ✓ Instrument registered successfully")
        
        # Step 3: Build data configurations
        print("Status: Building data configuration and converting data to catalog...")
        print(f"Status: Catalog location: {catalog_path}")
        data_configs, has_book_data = self.data_builder.build_with_book_check(
            config, instrument_id_str, start, end, snapshot_mode,
            catalog=self.catalog, ucs_loader=self.ucs_loader
        )
        
        if not data_configs:
            raise RuntimeError("ERROR: No data configurations created. Check that trade data files exist and are accessible.")
        
        print(f"Status: ✓ Created {len(data_configs)} data configuration(s)")
        for i, dc in enumerate(data_configs, 1):
            print(f"Status:   Config {i}: {dc.data_cls.__name__} for {dc.instrument_id} ({dc.start_time} to {dc.end_time})")
        
        # Step 4: Build venue and strategy configurations
        print("Status: Configuring venue and strategy...")
        venue_config = self.node_builder.build_venue_config(config, has_book_data=has_book_data)
        
        # Build execution algorithms
        exec_algorithms = self.node_builder.build_exec_algorithms(
            config,
            exec_algorithm_type=exec_algorithm_type,
            exec_algorithm_params=exec_algorithm_params
        )
        
        # Ensure strategy config knows about execution algorithm from CLI
        if exec_algorithm_type:
            if "strategy" not in config:
                config["strategy"] = {}
            config["strategy"]["exec_algorithm"] = {
                "type": exec_algorithm_type.upper(),
                "params": exec_algorithm_params or {}
            }
        
        strategy_config = self.node_builder.build_strategy_config(config)
        
        # Step 5: Build run config
        print("Status: Starting backtest execution...")
        run_config = self.node_builder.build_run_config(
            venue_config, strategy_config, data_configs, start, end, exec_algorithms
        )
        
        # Step 6: Execute backtest
        print(f"Status:   Time window: {start} to {end}")
        print(f"Status:   Instrument: {instrument_id_str}")
        print(f"Status:   Data configs: {len(data_configs)}")
        print(f"Status:   Snapshot mode: {snapshot_mode}")
        if exec_algorithms:
            algo_names = [algo.__class__.__name__ for algo in exec_algorithms]
            print(f"Status:   Execution algorithms: {algo_names}")
        print("Status: Executing backtest engine (processing ticks, this may take a while)...")
        
        # Create and build node
        node = BacktestNode(configs=[run_config])
        node.build()
        
        # Add execution algorithms to engines
        if exec_algorithms:
            try:
                engine = node.get_engine(run_config.id)
                if engine:
                    for exec_algo in exec_algorithms:
                        engine.add_exec_algorithm(exec_algo)
                        print(f"Status: ✓ Added execution algorithm: {exec_algo.__class__.__name__} (ID: {exec_algo.id}) to engine")
            except Exception as e:
                print(f"Warning: Could not add execution algorithms: {e}")
        
        results = node.run()
        
        if not results:
            raise RuntimeError("ERROR: Backtest returned no results. Check that:\n"
                             "  1. Data exists in catalog for the time window\n"
                             "  2. Instrument is correctly registered\n"
                             "  3. Strategy is properly configured\n"
                             "  4. No errors occurred during execution")
        
        print("Status: ✓ Backtest execution complete")
        print("Status: Extracting and analyzing results...")
        backtest_result = results[0]
        
        # Step 7: Generate run ID
        config_hash = hashlib.md5(
            str(self.config_loader.config_path).encode()
        ).hexdigest()
        venue_name = config["venue"]["name"]
        run_id = ResultSerializer.generate_run_id(
            venue_name, instrument, dataset, start, end, config_hash
        )
        
        # Step 8: Extract results
        print("Status: Analyzing backtest performance metrics...")
        engine = node.get_engine(run_config.id)
        
        # Close positions if requested
        positions_closed_count = 0
        if close_positions and engine:
            print("Status: Closing open positions...")
            positions_closed_count = self.position_manager.close_all_positions(engine, instrument_id, config)
        
        # Extract summary
        summary = self.result_extractor.extract_summary(
            engine, backtest_result, config, venue_config.name, close_positions
        )
        
        # Step 9: Build timeline (if not fast mode)
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
        print("Status: Building timeline...")
        timeline = []
        orders_list_for_report = []
        
        if engine:
            timeline = self.timeline_builder.build_timeline(engine)
            
            # Get orders list for report
            all_orders = engine.cache.orders() if hasattr(engine, 'cache') else []
            for order in all_orders:
                try:
                    order_dict = {
                        "id": str(order.client_order_id),
                        "side": order.side.name.lower() if hasattr(order.side, 'name') else str(order.side),
                        "price": float(order.price) if hasattr(order, 'price') and order.price else 0.0,
                        "amount": float(order.quantity) if hasattr(order, 'quantity') and order.quantity else 0.0,
                        "status": order.status.name.lower() if hasattr(order.status, 'name') else str(order.status),
                    }
                    orders_list_for_report.append(order_dict)
                except Exception:
                    continue
        
        # Step 10: Serialize and return results
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
            catalog_root=str(catalog_path)
        )
        
        # Export ticks if requested OR if report mode (for charting)
        # Always export ticks in report mode so charts can display data
        # Report mode is when fast_mode=False (full report mode)
        is_report_mode = not fast_mode
        if export_ticks or is_report_mode:
            ticks = []
            try:
                if self.catalog:
                    start_ns = int(start.timestamp() * 1_000_000_000)
                    end_ns = int(end.timestamp() * 1_000_000_000)
                    
                    trade_ticks = self.catalog.trade_ticks(
                        instrument_ids=[instrument_id],
                        start=start_ns,
                        end=end_ns,
                    )
                    
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
                    print(f"Exported {len(ticks)} ticks for charts")
            except Exception as e:
                print(f"Warning: Could not export ticks: {e}")
            
            if ticks:
                ticks_dir = Path("frontend/public/tickdata")
                ResultSerializer.save_ticks(ticks, ticks_dir, run_id)
        
        return result

