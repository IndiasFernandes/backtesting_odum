"""Legacy backtest engine - redirects to new modular engine."""
# Backward compatibility: redirect to new modular engine
from backend.core.engine import BacktestEngine

# Re-export for backward compatibility
__all__ = ['BacktestEngine']
