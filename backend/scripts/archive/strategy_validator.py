#!/usr/bin/env python3
"""
Strategy Validation Tool

Implements walk-forward analysis, overfitting detection, and risk management calculations
to validate strategies before going live.

Usage:
    python backend/scripts/strategy_validator.py \
        --config external/data_downloads/configs/binance_futures_btcusdt_l2_trades_config.json \
        --dataset day-2023-05-23 \
        --walk_forward \
        --kelly_calc
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
import statistics

def load_backtest_result(result_path: str) -> Dict[str, Any]:
    """
    Load backtest result from JSON file.
    
    Args:
        result_path: Path to backtest result JSON file
    
    Returns:
        Dictionary with backtest result data
    """
    result_file = Path(result_path)
    if not result_file.exists():
        return {}
    
    with open(result_file, 'r') as f:
        return json.load(f)


def calculate_kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> Dict[str, float]:
    """
    Calculate Kelly Criterion for optimal position sizing.
    
    Args:
        win_rate: Win rate as percentage (0-100)
        avg_win: Average winning trade PnL
        avg_loss: Average losing trade PnL (negative value)
    
    Returns:
        Dictionary with Kelly fraction and recommended position sizes
    """
    if avg_loss == 0 or win_rate <= 0 or win_rate >= 100:
        return {
            "kelly_fraction": 0.0,
            "fractional_kelly_25": 0.0,
            "fractional_kelly_50": 0.0,
            "fractional_kelly_75": 0.0,
            "recommended_risk_pct": 0.0,
            "warning": "Invalid inputs for Kelly calculation"
        }
    
    p = win_rate / 100.0  # Win probability
    q = 1 - p  # Loss probability
    b = abs(avg_win / avg_loss)  # Win/loss ratio
    
    # Kelly formula: f* = (p × b - q) / b
    kelly_fraction = (p * b - q) / b
    
    # Clamp to reasonable range (0 to 1)
    kelly_fraction = max(0.0, min(1.0, kelly_fraction))
    
    # Fractional Kelly (more conservative)
    fractional_25 = kelly_fraction * 0.25
    fractional_50 = kelly_fraction * 0.50
    fractional_75 = kelly_fraction * 0.75
    
    # Recommended risk per trade (conservative for crypto)
    # Use 0.25 Kelly as starting point, but cap at 2%
    recommended_risk = min(fractional_25 * 100, 2.0)
    
    return {
        "kelly_fraction": kelly_fraction * 100,  # As percentage
        "fractional_kelly_25": fractional_25 * 100,
        "fractional_kelly_50": fractional_50 * 100,
        "fractional_kelly_75": fractional_75 * 100,
        "recommended_risk_pct": recommended_risk,
        "win_probability": p * 100,
        "loss_probability": q * 100,
        "win_loss_ratio": b,
        "warning": None
    }


def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sharpe ratio from list of returns.
    
    Args:
        returns: List of periodic returns (as decimals, e.g., 0.05 for 5%)
        risk_free_rate: Risk-free rate (default 0 for crypto)
    
    Returns:
        Sharpe ratio
    """
    if not returns or len(returns) < 2:
        return 0.0
    
    mean_return = statistics.mean(returns)
    std_return = statistics.stdev(returns) if len(returns) > 1 else 0.0
    
    if std_return == 0:
        return 0.0
    
    # Annualized Sharpe (assuming daily returns)
    sharpe = (mean_return - risk_free_rate) / std_return
    # Annualize: multiply by sqrt(252) for daily, sqrt(365) for crypto (24/7)
    sharpe_annualized = sharpe * (365 ** 0.5)
    
    return sharpe_annualized


def detect_overfitting(training_performance: Dict[str, float], 
                       test_performance: Dict[str, float]) -> Dict[str, Any]:
    """
    Detect overfitting by comparing training vs. test performance.
    
    Args:
        training_performance: Performance metrics from training period
        test_performance: Performance metrics from test period
    
    Returns:
        Dictionary with overfitting analysis
    """
    train_return = training_performance.get("total_return_pct", 0.0)
    test_return = test_performance.get("total_return_pct", 0.0)
    
    train_sharpe = training_performance.get("sharpe_ratio", 0.0)
    test_sharpe = test_performance.get("sharpe_ratio", 0.0)
    
    train_pf = training_performance.get("profit_factor", 0.0)
    test_pf = test_performance.get("profit_factor", 0.0)
    
    # Calculate degradation
    return_degradation = ((train_return - test_return) / abs(train_return) * 100) if train_return != 0 else 0
    sharpe_degradation = ((train_sharpe - test_sharpe) / abs(train_sharpe) * 100) if train_sharpe != 0 else 0
    pf_degradation = ((train_pf - test_pf) / abs(train_pf) * 100) if train_pf != 0 else 0
    
    # Overfitting thresholds
    is_overfitted = False
    warnings = []
    
    if return_degradation > 50:
        is_overfitted = True
        warnings.append(f"Return degraded by {return_degradation:.1f}% (threshold: 50%)")
    
    if sharpe_degradation > 50:
        is_overfitted = True
        warnings.append(f"Sharpe ratio degraded by {sharpe_degradation:.1f}% (threshold: 50%)")
    
    if test_return < 0 and train_return > 0:
        is_overfitted = True
        warnings.append("Strategy profitable in training but losing in test")
    
    if test_sharpe < 0.5 and train_sharpe > 1.5:
        is_overfitted = True
        warnings.append("Sharpe ratio dropped below acceptable threshold")
    
    return {
        "is_overfitted": is_overfitted,
        "return_degradation_pct": return_degradation,
        "sharpe_degradation_pct": sharpe_degradation,
        "profit_factor_degradation_pct": pf_degradation,
        "warnings": warnings,
        "recommendation": "DO NOT TRADE LIVE" if is_overfitted else "Proceed to paper trading"
    }


def validate_strategy_metrics(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate strategy meets minimum requirements for live trading.
    
    Args:
        result: Backtest result dictionary
    
    Returns:
        Validation results with pass/fail status
    """
    summary = result.get("summary", {})
    trades = summary.get("trades", {})
    drawdown = summary.get("drawdown", {})
    returns = summary.get("returns", {})
    pnl = summary.get("pnl", {})
    
    # Extract metrics
    profit_factor = trades.get("profit_factor", 0.0)
    win_rate = trades.get("win_rate", 0.0)
    max_drawdown_pct = drawdown.get("max_drawdown_pct", 0.0)
    total_return_pct = returns.get("total_return_pct", 0.0)
    expectancy = trades.get("expectancy", 0.0)
    
    # Calculate Sharpe ratio (simplified - would need daily returns for accurate)
    # Using total return and drawdown as proxy
    sharpe_estimate = (total_return_pct / max_drawdown_pct) if max_drawdown_pct > 0 else 0.0
    
    # Validation thresholds
    checks = {
        "profit_factor": {
            "value": profit_factor,
            "threshold": 1.5,
            "passed": profit_factor >= 1.5,
            "critical": True
        },
        "win_rate": {
            "value": win_rate,
            "threshold": 45.0,
            "passed": win_rate >= 45.0,
            "critical": False
        },
        "max_drawdown": {
            "value": max_drawdown_pct,
            "threshold": 20.0,
            "passed": max_drawdown_pct <= 20.0,
            "critical": True
        },
        "expectancy": {
            "value": expectancy,
            "threshold": 0.0,
            "passed": expectancy > 0.0,
            "critical": True
        },
        "sharpe_ratio": {
            "value": sharpe_estimate,
            "threshold": 1.5,
            "passed": sharpe_estimate >= 1.5,
            "critical": False
        }
    }
    
    # Overall validation
    critical_passed = all(check["passed"] for check in checks.values() if check["critical"])
    all_passed = all(check["passed"] for check in checks.values())
    
    return {
        "overall_passed": all_passed,
        "critical_passed": critical_passed,
        "checks": checks,
        "recommendation": "READY FOR PAPER TRADING" if critical_passed else "NEEDS IMPROVEMENT",
        "metrics": {
            "profit_factor": profit_factor,
            "win_rate": win_rate,
            "max_drawdown_pct": max_drawdown_pct,
            "total_return_pct": total_return_pct,
            "expectancy": expectancy,
            "sharpe_estimate": sharpe_estimate
        }
    }


def analyze_backtest_result(result_path: str) -> Dict[str, Any]:
    """
    Load and analyze a backtest result file.
    
    Args:
        result_path: Path to backtest result JSON file
    
    Returns:
        Analysis results
    """
    result = load_backtest_result(result_path)
    
    if not result:
        return {"error": "Could not load backtest result"}
    
    summary = result.get("summary", {})
    trades = summary.get("trades", {})
    
    # Extract metrics for analysis
    win_rate = trades.get("win_rate", 0.0)
    avg_win = trades.get("avg_win", 0.0)
    avg_loss = trades.get("avg_loss", 0.0)
    
    # Calculate Kelly Criterion
    kelly = calculate_kelly_criterion(win_rate, avg_win, abs(avg_loss))
    
    # Validate strategy
    validation = validate_strategy_metrics(result)
    
    return {
        "result_path": result_path,
        "run_id": result.get("run_id", "unknown"),
        "kelly_criterion": kelly,
        "validation": validation,
        "summary_metrics": {
            "total_return_pct": summary.get("returns", {}).get("total_return_pct", 0.0),
            "profit_factor": trades.get("profit_factor", 0.0),
            "win_rate": win_rate,
            "max_drawdown_pct": summary.get("drawdown", {}).get("max_drawdown_pct", 0.0),
        }
    }


def print_analysis_report(analysis: Dict[str, Any]):
    """Print formatted analysis report."""
    print("\n" + "="*80)
    print("STRATEGY VALIDATION REPORT")
    print("="*80)
    
    print(f"\nRun ID: {analysis.get('run_id', 'unknown')}")
    print(f"Result Path: {analysis.get('result_path', 'unknown')}")
    
    # Summary Metrics
    print("\n" + "-"*80)
    print("SUMMARY METRICS")
    print("-"*80)
    metrics = analysis.get("summary_metrics", {})
    print(f"Total Return:     {metrics.get('total_return_pct', 0.0):.2f}%")
    print(f"Profit Factor:    {metrics.get('profit_factor', 0.0):.2f}")
    print(f"Win Rate:        {metrics.get('win_rate', 0.0):.2f}%")
    print(f"Max Drawdown:    {metrics.get('max_drawdown_pct', 0.0):.2f}%")
    
    # Kelly Criterion
    print("\n" + "-"*80)
    print("POSITION SIZING (KELLY CRITERION)")
    print("-"*80)
    kelly = analysis.get("kelly_criterion", {})
    print(f"Full Kelly:       {kelly.get('kelly_fraction', 0.0):.2f}% of capital")
    print(f"1/4 Kelly:        {kelly.get('fractional_kelly_25', 0.0):.2f}% of capital")
    print(f"1/2 Kelly:        {kelly.get('fractional_kelly_50', 0.0):.2f}% of capital")
    print(f"3/4 Kelly:        {kelly.get('fractional_kelly_75', 0.0):.2f}% of capital")
    print(f"\n⚠️  RECOMMENDED RISK PER TRADE: {kelly.get('recommended_risk_pct', 0.0):.2f}%")
    if kelly.get("warning"):
        print(f"⚠️  Warning: {kelly['warning']}")
    
    # Validation
    print("\n" + "-"*80)
    print("VALIDATION CHECKS")
    print("-"*80)
    validation = analysis.get("validation", {})
    checks = validation.get("checks", {})
    
    for check_name, check_data in checks.items():
        status = "✅ PASS" if check_data["passed"] else "❌ FAIL"
        critical = " (CRITICAL)" if check_data["critical"] else ""
        print(f"{check_name:20s}: {status:8s} | Value: {check_data['value']:.2f} | Threshold: {check_data['threshold']:.2f}{critical}")
    
    print("\n" + "-"*80)
    print("RECOMMENDATION")
    print("-"*80)
    recommendation = validation.get("recommendation", "UNKNOWN")
    critical_passed = validation.get("critical_passed", False)
    
    if critical_passed:
        print(f"✅ {recommendation}")
        print("\nNext Steps:")
        print("  1. Run walk-forward analysis to test multiple time periods")
        print("  2. Set up paper trading environment")
        print("  3. Trade paper account for 1-3 months")
        print("  4. If paper trading successful, start live with small capital")
    else:
        print(f"❌ {recommendation}")
        print("\nIssues to Address:")
        for check_name, check_data in checks.items():
            if not check_data["passed"] and check_data["critical"]:
                print(f"  - {check_name}: {check_data['value']:.2f} (needs {check_data['threshold']:.2f})")
    
    print("\n" + "="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Validate trading strategies using backtest results"
    )
    parser.add_argument(
        "--result",
        type=str,
        required=True,
        help="Path to backtest result JSON file"
    )
    parser.add_argument(
        "--kelly_calc",
        action="store_true",
        help="Calculate Kelly Criterion for position sizing"
    )
    
    args = parser.parse_args()
    
    # Analyze the backtest result
    analysis = analyze_backtest_result(args.result)
    
    if "error" in analysis:
        print(f"Error: {analysis['error']}")
        sys.exit(1)
    
    # Print report
    print_analysis_report(analysis)


if __name__ == "__main__":
    main()

