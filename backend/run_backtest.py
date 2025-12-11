#!/usr/bin/env python3
"""CLI entrypoint for running backtests."""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from backend.backtest_engine import BacktestEngine
from backend.catalog_manager import CatalogManager
from backend.config_loader import ConfigLoader
from backend.results import ResultSerializer
from backend.utils.validation import validate_iso8601


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run NautilusTrader backtest",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--instrument",
        type=str,
        required=True,
        help="Instrument identifier (e.g., BTCUSDT)"
    )
    
    parser.add_argument(
        "--dataset",
        type=str,
        required=False,
        default=None,
        help="Dataset name (optional - auto-detected from time window if not provided)"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to JSON configuration file"
    )
    
    parser.add_argument(
        "--start",
        type=str,
        required=True,
        help="Start time in ISO8601 UTC format (e.g., 2023-05-23T02:00:00Z)"
    )
    
    parser.add_argument(
        "--end",
        type=str,
        required=True,
        help="End time in ISO8601 UTC format (e.g., 2023-05-23T02:30:00Z)"
    )
    
    parser.add_argument(
        "--fast",
        action="store_true",
        default=False,
        help="Run in fast mode (minimal JSON summary only)"
    )
    
    parser.add_argument(
        "--report",
        action="store_true",
        default=False,
        help="Run in report mode (full details: timeline, orders, ticks, metadata)"
    )
    
    parser.add_argument(
        "--export_ticks",
        action="store_true",
        default=False,
        help="Export tick data (only valid with --report)"
    )
    
    parser.add_argument(
        "--snapshot_mode",
        type=str,
        choices=["trades", "book", "both"],
        default="both",
        help="Snapshot mode: trades, book, or both"
    )
    
    parser.add_argument(
        "--data_source",
        type=str,
        choices=["local", "gcs", "auto"],
        default="auto",
        help="Data source: 'local' for local files, 'gcs' for GCS bucket, 'auto' to auto-detect (default: auto)"
    )
    
    parser.add_argument(
        "--no_close_positions",
        action="store_true",
        default=False,
        help="Do not close open positions at end of backtest (default: positions are closed)"
    )
    
    parser.add_argument(
        "--exec_algorithm",
        type=str,
        choices=["NORMAL", "TWAP", "VWAP", "ICEBERG"],
        default=None,
        help="Execution algorithm to use: NORMAL (market orders), TWAP, VWAP, or ICEBERG (optional - can also be specified in config)"
    )
    
    parser.add_argument(
        "--exec_algorithm_params",
        type=str,
        default=None,
        help="Execution algorithm parameters as JSON string (e.g., '{\"horizon_secs\": 20, \"interval_secs\": 2.5}' for TWAP)"
    )
    
    return parser.parse_args()


def main():
    """Main entrypoint."""
    args = parse_args()
    
    # Validate flags
    if args.fast and args.report:
        print("Error: Cannot use both --fast and --report flags", file=sys.stderr)
        sys.exit(1)
    
    if args.export_ticks and not args.report:
        print("Error: --export_ticks requires --report flag", file=sys.stderr)
        sys.exit(1)
    
    # Determine if positions should be closed (default: True, unless --no_close_positions is set)
    close_positions = not args.no_close_positions
    
    # Determine mode
    fast_mode = args.fast
    report_mode = args.report or (not args.fast and not args.report)  # Default to report if neither specified
    
    # Parse timestamps
    try:
        start = validate_iso8601(args.start)
        end = validate_iso8601(args.end)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Load configuration
    try:
        config_loader = ConfigLoader(args.config)
        config_loader.load()
    except (FileNotFoundError, ValueError) as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Initialize catalog manager
    catalog_manager = CatalogManager()
    
    # Parse execution algorithm parameters if provided
    exec_algorithm_params = None
    if args.exec_algorithm_params:
        try:
            exec_algorithm_params = json.loads(args.exec_algorithm_params)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --exec_algorithm_params: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Create backtest engine
    engine = BacktestEngine(config_loader, catalog_manager)
    
    # Run backtest
    try:
        result = engine.run(
            instrument=args.instrument,
            dataset=args.dataset,
            start=start,
            end=end,
            snapshot_mode=args.snapshot_mode,
            fast_mode=fast_mode,
            export_ticks=args.export_ticks,
            close_positions=close_positions,
            data_source=args.data_source,
            exec_algorithm_type=args.exec_algorithm,
            exec_algorithm_params=exec_algorithm_params
        )
    except Exception as e:
        print(f"Error running backtest: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Save results
    try:
        if fast_mode:
            output_dir = Path("backend/backtest_results/fast")
            output_file = ResultSerializer.save_fast(result, output_dir)
            print(f"Fast mode result saved to: {output_file}")
        else:
            output_dir = Path("backend/backtest_results/report")
            output_file = ResultSerializer.save_report(result, output_dir)
            print(f"Report mode result saved to: {output_file}")
        
        # Print summary
        print(f"\nRun ID: {result['run_id']}")
        print(f"Instrument: {result['instrument']}")
        print(f"Dataset: {result['dataset']}")
        print(f"Time window: {result['start']} to {result['end']}")
        print(f"\nSummary:")
        for key, value in result['summary'].items():
            print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"Error saving results: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

