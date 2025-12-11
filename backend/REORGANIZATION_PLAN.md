# Backend Core Files Reorganization Plan

## Problem Analysis

### Current Issues

1. **`backtest_engine.py` is 2471 lines** - Violates Single Responsibility Principle
   - Contains: instrument creation, venue config, data config, validation, execution, results extraction
   - Should be split into focused modules

2. **Flat structure** - All 13 files in root `backend/` directory
   - Hard to navigate and understand dependencies
   - No clear separation of concerns

3. **Mixed responsibilities** - Some files combine multiple concerns

## Proposed Structure (Following Python Best Practices)

Based on Context7 best practices and PEP 8 module organization:

```
backend/
├── __init__.py
├── run_backtest.py              # CLI entrypoint (keep in root)
│
├── core/                         # Core backtest orchestration
│   ├── __init__.py
│   ├── engine.py                # Main BacktestEngine (orchestrator only)
│   └── node_builder.py          # BacktestNode configuration builder
│
├── config/                       # Configuration management
│   ├── __init__.py
│   ├── loader.py                 # ConfigLoader (from config_loader.py)
│   └── validator.py              # Config validation utilities
│
├── data/                         # Data management
│   ├── __init__.py
│   ├── catalog.py                # CatalogManager (from catalog_manager.py)
│   ├── converter.py              # DataConverter (from data_converter.py)
│   └── loader.py                 # UCSDataLoader (from ucs_data_loader.py)
│
├── instruments/                  # Instrument management
│   ├── __init__.py
│   ├── registry.py               # InstrumentRegistry (from instrument_registry.py)
│   ├── utils.py                  # InstrumentUtils (from instrument_utils.py)
│   └── factory.py                # Instrument creation (from backtest_engine._create_and_register_instrument)
│
├── execution/                    # Execution-related modules
│   ├── __init__.py
│   ├── algorithms.py             # ExecutionAlgorithms (from execution_algorithms.py)
│   └── router.py                 # SmartOrderRouter (from smart_router.py)
│
├── strategies/                   # Strategy modules
│   ├── __init__.py
│   ├── base.py                   # TempBacktestStrategy (from strategy.py)
│   └── evaluator.py              # StrategyEvaluator (from strategy_evaluator.py)
│
├── results/                      # Results and reporting
│   ├── __init__.py
│   ├── serializer.py             # ResultSerializer (from results.py)
│   └── extractor.py              # Result extraction from engine (from backtest_engine)
│
└── utils/                        # Shared utilities
    ├── __init__.py
    └── validation.py             # Validation utilities (if any)
```

## Detailed Breakdown

### 1. Split `backtest_engine.py` (2471 lines → ~6 focused modules)

**Current responsibilities:**
- Instrument creation/registration → `instruments/factory.py`
- Venue configuration → `core/node_builder.py`
- Data configuration → `data/config_builder.py` (new)
- Data validation → `data/validator.py` (new)
- Execution algorithm building → `execution/builder.py` (new)
- Strategy configuration → `strategies/config.py` (new)
- Backtest execution → `core/engine.py` (orchestrator)
- Result extraction → `results/extractor.py`
- Position closing → `results/position_manager.py` (new)
- Timeline building → `results/timeline.py` (new)

**New `core/engine.py` (~200 lines):**
- Main `BacktestEngine` class
- Orchestrates the backtest flow
- Delegates to specialized modules
- Clean, focused interface

### 2. Reorganize Existing Files

| Current File | New Location | Notes |
|-------------|--------------|-------|
| `config_loader.py` | `config/loader.py` | Rename class to `ConfigLoader` (no change) |
| `catalog_manager.py` | `data/catalog.py` | Rename class to `CatalogManager` (no change) |
| `data_converter.py` | `data/converter.py` | Rename class to `DataConverter` (no change) |
| `ucs_data_loader.py` | `data/loader.py` | Rename class to `UCSDataLoader` (no change) |
| `instrument_registry.py` | `instruments/registry.py` | Keep as-is |
| `instrument_utils.py` | `instruments/utils.py` | Keep as-is |
| `execution_algorithms.py` | `execution/algorithms.py` | Keep as-is |
| `smart_router.py` | `execution/router.py` | Keep as-is |
| `strategy.py` | `strategies/base.py` | Keep as-is |
| `strategy_evaluator.py` | `strategies/evaluator.py` | Keep as-is |
| `results.py` | `results/serializer.py` | Rename class to `ResultSerializer` (no change) |
| `backtest_engine.py` | **SPLIT** → Multiple modules | See breakdown above |

### 3. New Modules to Create

**`data/config_builder.py`** (~400 lines)
- `DataConfigBuilder` class
- Methods from `backtest_engine._build_data_config*`
- Handles GCS/local data discovery
- Data conversion orchestration

**`data/validator.py`** (~300 lines)
- `DataValidator` class
- Methods from `backtest_engine` validation logic
- File existence checks
- Time window validation

**`core/node_builder.py`** (~200 lines)
- `BacktestNodeBuilder` class
- Venue configuration building
- Strategy configuration building
- Execution algorithm configuration

**`results/extractor.py`** (~400 lines)
- `ResultExtractor` class
- Extract orders, fills, PnL from engine
- Performance metrics calculation
- Delegates to StrategyEvaluator

**`results/timeline.py`** (~300 lines)
- `TimelineBuilder` class
- Build timeline from events
- Order/fill/rejection event processing

**`results/position_manager.py`** (~100 lines)
- `PositionManager` class
- Position closing logic
- Unrealized PnL realization

**`instruments/factory.py`** (~200 lines)
- `InstrumentFactory` class
- Instrument creation from config
- Catalog registration

## Migration Strategy

### Phase 1: Create New Structure (Non-Breaking)
1. Create new directory structure
2. Move files to new locations with `__init__.py` exports
3. Update imports gradually
4. Keep old files temporarily with deprecation warnings

### Phase 2: Split `backtest_engine.py`
1. Extract instrument creation → `instruments/factory.py`
2. Extract data config building → `data/config_builder.py`
3. Extract validation → `data/validator.py`
4. Extract result extraction → `results/extractor.py`
5. Refactor `core/engine.py` to use new modules

### Phase 3: Update Imports
1. Update `run_backtest.py`
2. Update API endpoints
3. Update tests
4. Remove old files

### Phase 4: Cleanup
1. Remove deprecated imports
2. Update documentation
3. Verify all tests pass

## Benefits

1. **Single Responsibility** - Each module has one clear purpose
2. **Maintainability** - Easier to find and modify code
3. **Testability** - Smaller modules are easier to test
4. **Readability** - Clear structure improves understanding
5. **Scalability** - Easy to add new features without bloating files

## File Size Targets

Following best practices (files should be <500 lines ideally):

| Module | Target Size | Current Size |
|--------|-------------|--------------|
| `core/engine.py` | ~200 lines | 2471 lines (split) |
| `data/config_builder.py` | ~400 lines | (extracted) |
| `data/validator.py` | ~300 lines | (extracted) |
| `results/extractor.py` | ~400 lines | (extracted) |
| `results/timeline.py` | ~300 lines | (extracted) |
| Other modules | <300 lines | Already good |

## Import Examples

### Before:
```python
from backend.backtest_engine import BacktestEngine
from backend.config_loader import ConfigLoader
from backend.data_converter import DataConverter
```

### After:
```python
from backend.core.engine import BacktestEngine
from backend.config.loader import ConfigLoader
from backend.data.converter import DataConverter
```

## Notes

- All public APIs remain the same (class names unchanged)
- Only import paths change
- Backward compatibility can be maintained with `__init__.py` re-exports
- Follows PEP 8 and Python packaging best practices
- Aligns with Context7 module organization guidelines

---

*Created: December 2025*
*Based on Context7 Python best practices and PEP 8*

