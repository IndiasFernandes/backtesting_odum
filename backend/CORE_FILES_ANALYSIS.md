# Core Backend Files Analysis

## Summary

Analysis of core backend files to identify unused or potentially unused modules.

## Files Status

### ✅ **Active Core Files** (Used in production)

- `__init__.py` - Package initialization
- `backtest_engine.py` - Core backtest orchestration (imported by run_backtest.py, API)
- `catalog_manager.py` - Catalog management (imported by backtest_engine.py)
- `config_loader.py` - Config loading (imported by backtest_engine.py, API)
- `data_converter.py` - Data conversion (imported by backtest_engine.py)
- `execution_algorithms.py` - Execution algorithms (imported by backtest_engine.py)
- `instrument_registry.py` - Instrument registry (imported by instrument_utils.py, API)
- `instrument_utils.py` - Instrument utilities (imported by backtest_engine.py, API)
- `results.py` - Result serialization (imported by backtest_engine.py, run_backtest.py)
- `run_backtest.py` - CLI entrypoint (standalone script)
- `strategy_evaluator.py` - Strategy evaluation (imported by backtest_engine.py)
- `strategy.py` - Strategy implementation (imported by backtest_engine.py)
- `ucs_data_loader.py` - UCS data loader (imported by backtest_engine.py)

### ⚠️ **Potentially Unused Core Files**

#### `smart_router.py`
- **Status**: Not currently imported or used
- **Purpose**: Multi-venue order routing for live execution
- **References**: Only mentioned in documentation (docs/live/ARCHITECTURE.md)
- **Recommendation**: 
  - ✅ **Keep** - Planned for future use in live execution
  - Added TODO comment indicating future use
  - Documented in architecture docs as planned feature

## Recommendations

### `smart_router.py`
- Keep the file as it's planned for future use
- TODO comment added to clarify status
- Consider moving to `backend/live/` directory when live execution is implemented
- Or create `backend/routing/` subdirectory if more routing-related modules are added

## Future Organization

Consider creating subdirectories for better organization:

```
backend/
├── core/              # Core backtest functionality
│   ├── backtest_engine.py
│   ├── catalog_manager.py
│   ├── config_loader.py
│   └── data_converter.py
├── execution/         # Execution-related modules
│   ├── execution_algorithms.py
│   └── smart_router.py  # Future: move here when live execution is added
├── instruments/       # Instrument-related modules
│   ├── instrument_registry.py
│   └── instrument_utils.py
├── strategies/        # Strategy-related modules
│   ├── strategy.py
│   └── strategy_evaluator.py
├── data/             # Data loading modules
│   └── ucs_data_loader.py
└── results/          # Result-related modules
    └── results.py
```

However, current flat structure is acceptable for current project size.

## Notes

- All core files serve a purpose in the backtesting system
- `smart_router.py` is the only file not currently used but is planned for future use
- No files need to be removed from core backend directory
- Scripts reorganization is separate (see `scripts/REORGANIZATION_PLAN.md`)

---

*Last updated: December 2025*

