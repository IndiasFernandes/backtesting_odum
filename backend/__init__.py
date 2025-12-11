"""NautilusTrader Backtesting System - Backward Compatible Imports."""

# Backward compatibility: Re-export from new locations
from backend.config.loader import ConfigLoader
from backend.data.catalog import CatalogManager
from backend.data.converter import DataConverter
from backend.data.loader import UCSDataLoader
from backend.instruments.registry import *
from backend.instruments.utils import *
from backend.execution.algorithms import (
    TWAPExecAlgorithm,
    VWAPExecAlgorithm,
    IcebergExecAlgorithm,
)
from backend.execution.router import SmartOrderRouter
from backend.strategies.base import TempBacktestStrategy, TempBacktestStrategyConfig
from backend.strategies.evaluator import StrategyEvaluator
from backend.results.serializer import ResultSerializer
# Core engine - backward compatibility
from backend.core.engine import BacktestEngine

__all__ = [
    # Config
    'ConfigLoader',
    # Data
    'CatalogManager',
    'DataConverter',
    'UCSDataLoader',
    # Execution
    'TWAPExecAlgorithm',
    'VWAPExecAlgorithm',
    'IcebergExecAlgorithm',
    'SmartOrderRouter',
    # Strategies
    'TempBacktestStrategy',
    'TempBacktestStrategyConfig',
    'StrategyEvaluator',
    # Results
    'ResultSerializer',
    # Core
    'BacktestEngine',
]
