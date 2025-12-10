# Structure Refactor Import Issues

**Date**: 2025-01-15
**Status**: ✅ Resolved
**Repository**: `market-tick-data-handler`
**Session**: Structure refactor to match instruments-service pattern

## Issue Summary

During the refactoring of `market-tick-data-handler` to match `instruments-service` structure (moving services from `services/` to `app/core/`), multiple import path issues were encountered.

## Problems Encountered

### 1. Missing `validation_service.py` File
**Problem**: After moving files from `services/` to `app/core/`, the `validation_service.py` file was missing, causing `ModuleNotFoundError`.

**Root Cause**: The file was deleted from git and needed to be restored from git history.

**Resolution**:
```bash
git show e64bb7e:market_data_tick_handler/services/validation_service.py > market_data_tick_handler/app/core/validation_service.py
```

**Files Affected**:
- `market_data_tick_handler/app/core/validation_service.py` (restored)

---

### 2. Incorrect Relative Import Paths
**Problem**: After moving services to `app/core/`, relative imports were broken:
- `from ..utils.performance_monitor` → should be `from ...utils.performance_monitor`
- `from ..models import ValidationResult` → should be `from ...models import ValidationResult`

**Root Cause**: When files moved from `services/` (package root level) to `app/core/` (nested 2 levels), relative imports needed an extra `..` level.

**Resolution**: Updated all relative imports in `app/core/` files:
- `..utils` → `...utils` (3 levels up to package root)
- `..models` → `...models` (3 levels up to package root)

**Files Fixed**:
- `app/core/observability_service.py`
- `app/core/data_orchestration_service.py`
- `app/core/validation_service.py`

---

### 3. Indentation Error in `data_orchestration_service.py`
**Problem**: After fixing import paths, an indentation error was introduced:
```python
        # Create new persistent client
                    from ...utils.tardis_client import create_tardis_client_for_day
        self.persistent_tardis_client = await create_tardis_client_for_day(api_key)
```

**Root Cause**: Incorrect indentation when fixing the import statement.

**Resolution**: Fixed indentation:
```python
        # Create new persistent client
        from ...utils.tardis_client import create_tardis_client_for_day
        self.persistent_tardis_client = await create_tardis_client_for_day(api_key)
```

**Files Fixed**:
- `app/core/data_orchestration_service.py` (line 255)

---

### 4. Import Path in `gcs_quality_gates.py`
**Problem**: `gcs_quality_gates.py` uses absolute import instead of relative:
```python
from market_data_tick_handler.models import CandleSchemaConfig
```

**Status**: ✅ Acceptable - absolute import works correctly from `app/core/` level.

---

## Verification

After fixes, all imports work correctly:
```bash
✅ All services importable from app.core
✅ DownloadHandler imports work
```

## Lessons Learned

1. **Relative Import Depth**: When moving files deeper in the package hierarchy, relative imports need additional `..` levels
2. **Git History**: Always check git history when files are missing after refactoring
3. **Indentation**: Be careful with indentation when doing find/replace operations
4. **Import Patterns**: Absolute imports (`from market_data_tick_handler.models`) work from any level, but relative imports are more portable

## Prevention

1. Use automated import fixing tools (e.g., `isort`, `autoflake`)
2. Run import checks after structural refactoring
3. Test imports immediately after moving files
4. Consider using absolute imports for cross-package imports
