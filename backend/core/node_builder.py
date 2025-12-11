"""BacktestNode configuration builder."""
from typing import Dict, Any, List, Optional

from nautilus_trader.backtest.config import (
    BacktestRunConfig,
    BacktestVenueConfig,
    BacktestEngineConfig,
)
from nautilus_trader.config import ImportableStrategyConfig

from backend.instruments.utils import normalize_venue_name
from backend.execution.algorithms import (
    TWAPExecAlgorithm,
    VWAPExecAlgorithm,
    IcebergExecAlgorithm,
)

# Use built-in algorithms for testing
try:
    from nautilus_trader.examples.algorithms.twap import TWAPExecAlgorithm as BuiltinTWAPExecAlgorithm
    BUILTIN_TWAP_AVAILABLE = True
except ImportError:
    BUILTIN_TWAP_AVAILABLE = False


class NodeBuilder:
    """Builds BacktestNode configuration components."""
    
    @staticmethod
    def build_venue_config(config: Dict[str, Any], has_book_data: bool = False) -> BacktestVenueConfig:
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
        book_type = venue_config.get("book_type", "L2_MBP")
        
        # If L2_MBP is requested but no book data exists, try L1_MBP (simpler, might not require full book)
        if book_type == "L2_MBP" and not has_book_data:
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
    
    @staticmethod
    def build_strategy_config(config: Dict[str, Any]) -> ImportableStrategyConfig:
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
            strategy_path="backend.strategies.base:TempBacktestStrategy",
            config_path="backend.strategies.base:TempBacktestStrategyConfig",
            config=strategy_config_dict,
        )
    
    @staticmethod
    def build_exec_algorithms(
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
    
    @staticmethod
    def build_run_config(
        venue_config: BacktestVenueConfig,
        strategy_config: ImportableStrategyConfig,
        data_configs: List,
        start,
        end,
        exec_algorithms: Optional[List] = None
    ) -> BacktestRunConfig:
        """
        Build BacktestRunConfig from components.
        
        Args:
            venue_config: Venue configuration
            strategy_config: Strategy configuration
            data_configs: List of data configurations
            start: Start timestamp
            end: End timestamp
            exec_algorithms: Optional list of execution algorithms
        
        Returns:
            BacktestRunConfig instance
        """
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
        
        return BacktestRunConfig(**run_config_kwargs)

