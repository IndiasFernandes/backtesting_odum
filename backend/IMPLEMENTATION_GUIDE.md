# Implementation Guide: Backend Reorganization

## Quick Start

This guide provides step-by-step instructions for reorganizing the backend following best practices.

## Prerequisites

- All tests passing
- Git branch created for reorganization
- Backup of current code

## Step-by-Step Implementation

### Step 1: Create Directory Structure

```bash
cd backend
mkdir -p core config data instruments execution strategies results utils
touch core/__init__.py config/__init__.py data/__init__.py \
      instruments/__init__.py execution/__init__.py \
      strategies/__init__.py results/__init__.py utils/__init__.py
```

### Step 2: Move Existing Files (Non-Breaking)

Move files to new locations while maintaining backward compatibility:

```python
# backend/__init__.py - Add backward-compatible imports
from backend.config.loader import ConfigLoader
from backend.data.catalog import CatalogManager
from backend.data.converter import DataConverter
from backend.data.loader import UCSDataLoader
from backend.instruments.registry import *
from backend.instruments.utils import *
from backend.execution.algorithms import *
from backend.execution.router import SmartOrderRouter
from backend.strategies.base import TempBacktestStrategy, TempBacktestStrategyConfig
from backend.strategies.evaluator import StrategyEvaluator
from backend.results.serializer import ResultSerializer

# Backward compatibility
__all__ = [
    'ConfigLoader',
    'CatalogManager',
    'DataConverter',
    'UCSDataLoader',
    'SmartOrderRouter',
    'TempBacktestStrategy',
    'TempBacktestStrategyConfig',
    'StrategyEvaluator',
    'ResultSerializer',
]
```

### Step 3: Move Files

```bash
# Move files to new locations
mv config_loader.py config/loader.py
mv catalog_manager.py data/catalog.py
mv data_converter.py data/converter.py
mv ucs_data_loader.py data/loader.py
mv instrument_registry.py instruments/registry.py
mv instrument_utils.py instruments/utils.py
mv execution_algorithms.py execution/algorithms.py
mv smart_router.py execution/router.py
mv strategy.py strategies/base.py
mv strategy_evaluator.py strategies/evaluator.py
mv results.py results/serializer.py
```

### Step 4: Update Imports in Moved Files

Update relative imports in moved files:

```python
# Example: data/converter.py
# Before:
from backend.instrument_utils import convert_instrument_id_to_gcs_format

# After:
from backend.instruments.utils import convert_instrument_id_to_gcs_format
```

### Step 5: Split `backtest_engine.py`

This is the most complex step. Extract methods into focused modules:

#### 5.1: Extract Instrument Factory

```python
# instruments/factory.py
class InstrumentFactory:
    @staticmethod
    def create_and_register(config: Dict[str, Any], catalog: ParquetDataCatalog) -> InstrumentId:
        # Move _create_and_register_instrument logic here
        ...
```

#### 5.2: Extract Data Config Builder

```python
# data/config_builder.py
class DataConfigBuilder:
    def build_with_book_check(self, ...) -> tuple[List[BacktestDataConfig], bool]:
        # Move _build_data_config_with_book_check logic here
        ...
```

#### 5.3: Extract Result Extractor

```python
# results/extractor.py
class ResultExtractor:
    @staticmethod
    def extract_results(engine, config, ...) -> Dict[str, Any]:
        # Move result extraction logic here
        ...
```

#### 5.4: Create New Engine

```python
# core/engine.py
class BacktestEngine:
    """Orchestrates backtest execution."""
    
    def __init__(self, config_loader, catalog_manager):
        self.config_loader = config_loader
        self.catalog_manager = catalog_manager
        self.instrument_factory = InstrumentFactory()
        self.data_builder = DataConfigBuilder()
        self.result_extractor = ResultExtractor()
    
    def run(self, ...):
        # Orchestrate using extracted modules
        instrument_id = self.instrument_factory.create_and_register(...)
        data_configs, has_book = self.data_builder.build_with_book_check(...)
        # ... run backtest ...
        results = self.result_extractor.extract_results(...)
        return results
```

### Step 6: Update All Imports

Update imports in:
- `run_backtest.py`
- `backend/api/server.py`
- All test files
- Any other files importing backend modules

### Step 7: Run Tests

```bash
# Run all tests
pytest backend/tests/

# Run specific tests
pytest backend/tests/test_backtest_engine.py
```

### Step 8: Update Documentation

Update:
- README.md
- API documentation
- Code comments
- Architecture docs

## Verification Checklist

- [ ] All directories created
- [ ] All files moved
- [ ] All imports updated
- [ ] `backtest_engine.py` split into modules
- [ ] All tests passing
- [ ] API endpoints working
- [ ] CLI working
- [ ] Documentation updated

## Rollback Plan

If issues arise:

```bash
# Revert to previous structure
git checkout <previous-branch>
# Or restore from backup
```

## Testing Strategy

1. **Unit Tests**: Test each new module independently
2. **Integration Tests**: Test module interactions
3. **End-to-End Tests**: Test full backtest flow
4. **Regression Tests**: Ensure no functionality lost

## Common Issues & Solutions

### Issue: Circular Imports
**Solution**: Use type hints with `from __future__ import annotations` or `TYPE_CHECKING`

### Issue: Import Path Errors
**Solution**: Update all imports systematically, use IDE refactoring tools

### Issue: Tests Failing
**Solution**: Update test imports, ensure test fixtures use new paths

## Timeline Estimate

- **Step 1-2**: 30 minutes (structure creation)
- **Step 3-4**: 1 hour (file moves, import updates)
- **Step 5**: 4-6 hours (splitting backtest_engine.py)
- **Step 6**: 1-2 hours (updating all imports)
- **Step 7**: 1 hour (testing)
- **Step 8**: 1 hour (documentation)

**Total**: ~8-12 hours

## Notes

- Work in small, incremental commits
- Test after each major change
- Keep backward compatibility during transition
- Update this guide as you discover issues

---

*See `REORGANIZATION_PLAN.md` for detailed module breakdown*

