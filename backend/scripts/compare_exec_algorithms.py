#!/usr/bin/env python3
"""
Compare execution algorithms by running backtests with different algorithms.

Runs 4 backtests:
1. NORMAL - Market orders
2. TWAP - Time-weighted average price
3. VWAP - Volume-weighted average price
4. ICEBERG - Iceberg orders

Then compares the results.
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


def run_backtest(
    config_path: str,
    instrument: str,
    start: str,
    end: str,
    exec_algorithm: str,
    exec_params: Dict[str, Any] = None,
    fast_mode: bool = True
) -> Dict[str, Any]:
    """
    Run a single backtest with specified execution algorithm.
    
    Args:
        config_path: Path to config file
        instrument: Instrument identifier
        start: Start time (ISO8601)
        end: End time (ISO8601)
        exec_algorithm: Execution algorithm name
        exec_params: Execution algorithm parameters
        fast_mode: Use fast mode for quicker results
    
    Returns:
        Result dictionary with summary metrics
    """
    cmd = [
        "python3",
        "backend/run_backtest.py",
        "--instrument", instrument,
        "--config", config_path,
        "--start", start,
        "--end", end,
        "--exec_algorithm", exec_algorithm,
        "--fast" if fast_mode else "--report"
    ]
    
    if exec_params:
        params_json = json.dumps(exec_params)
        cmd.extend(["--exec_algorithm_params", params_json])
    
    print(f"\n{'='*80}")
    print(f"Running backtest with {exec_algorithm} execution algorithm...")
    print(f"{'='*80}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse output to extract summary
        output = result.stdout
        print(output)
        
        # Try to extract summary from output
        summary = {}
        for line in output.split('\n'):
            if 'Summary:' in line or 'PnL:' in line or 'Orders:' in line or 'Fills:' in line:
                # Extract key metrics
                pass
        
        # Also try to read from result file
        # Results are saved to backend/backtest_results/fast/ or backend/backtest_results/report/
        result_dir = Path(__file__).parent.parent.parent / "backend" / "backtest_results"
        if fast_mode:
            result_dir = result_dir / "fast"
        else:
            result_dir = result_dir / "report"
        
        # Find most recent result file
        result_files = sorted(result_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if result_files:
            with open(result_files[0]) as f:
                result_data = json.load(f)
                summary = result_data.get('summary', {})
                summary['run_id'] = result_data.get('run_id', '')
                summary['exec_algorithm'] = exec_algorithm
        
        return {
            'exec_algorithm': exec_algorithm,
            'success': True,
            'summary': summary,
            'output': output
        }
        
    except subprocess.CalledProcessError as e:
        print(f"Error running backtest: {e}")
        print(f"STDERR: {e.stderr}")
        return {
            'exec_algorithm': exec_algorithm,
            'success': False,
            'error': str(e),
            'stderr': e.stderr
        }


def compare_results(results: List[Dict[str, Any]]) -> None:
    """
    Compare results from multiple backtests.
    
    Args:
        results: List of result dictionaries
    """
    print(f"\n{'='*80}")
    print("COMPARISON RESULTS")
    print(f"{'='*80}\n")
    
    # Create comparison table
    print(f"{'Algorithm':<15} {'PnL':<15} {'Orders':<15} {'Fills':<15} {'Status':<15}")
    print("-" * 80)
    
    for result in results:
        if not result.get('success'):
            print(f"{result['exec_algorithm']:<15} {'ERROR':<15} {'-':<15} {'-':<15} {'Failed':<15}")
            continue
        
        summary = result.get('summary', {})
        pnl = summary.get('pnl', summary.get('PnL', 'N/A'))
        orders = summary.get('orders', summary.get('Orders', 'N/A'))
        fills = summary.get('fills', summary.get('Fills', 'N/A'))
        
        print(f"{result['exec_algorithm']:<15} {str(pnl):<15} {str(orders):<15} {str(fills):<15} {'Success':<15}")
    
    print("\n" + "="*80)
    print("DETAILED COMPARISON")
    print("="*80 + "\n")
    
    for result in results:
        if not result.get('success'):
            print(f"\n{result['exec_algorithm']}: FAILED")
            print(f"Error: {result.get('error', 'Unknown error')}")
            continue
        
        print(f"\n{result['exec_algorithm']}:")
        print("-" * 40)
        summary = result.get('summary', {})
        for key, value in summary.items():
            if key != 'exec_algorithm':
                print(f"  {key}: {value}")


def main():
    """Main entry point."""
    if len(sys.argv) < 5:
        print("Usage: compare_exec_algorithms.py <config_path> <instrument> <start> <end>")
        print("Example: compare_exec_algorithms.py temp_may24_config.json BTCUSDT 2023-05-24T05:00:00Z 2023-05-24T05:05:00Z")
        sys.exit(1)
    
    config_path = sys.argv[1]
    instrument = sys.argv[2]
    start = sys.argv[3]
    end = sys.argv[4]
    
    # Define execution algorithms and their parameters
    algorithms = [
        {
            'name': 'NORMAL',
            'params': None
        },
        {
            'name': 'TWAP',
            'params': {
                'horizon_secs': 60,  # 1 minute horizon for 5-minute window
                'interval_secs': 10   # 10 second intervals
            }
        },
        {
            'name': 'VWAP',
            'params': {
                'horizon_secs': 60,
                'intervals': 6  # 6 intervals over 1 minute
            }
        },
        {
            'name': 'ICEBERG',
            'params': {
                'visible_pct': 0.1  # Show 10% at a time
            }
        }
    ]
    
    # Run all backtests
    results = []
    for algo in algorithms:
        result = run_backtest(
            config_path=config_path,
            instrument=instrument,
            start=start,
            end=end,
            exec_algorithm=algo['name'],
            exec_params=algo['params'],
            fast_mode=True
        )
        results.append(result)
    
    # Compare results
    compare_results(results)
    
    # Save comparison to file
    comparison_file = Path(__file__).parent.parent.parent / "backend" / "backtest_results" / "exec_algorithm_comparison.json"
    comparison_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(comparison_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'config': config_path,
            'instrument': instrument,
            'start': start,
            'end': end,
            'results': results
        }, f, indent=2)
    
    print(f"\nComparison saved to: {comparison_file}")


if __name__ == "__main__":
    main()

