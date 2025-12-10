# Factory Functions Removal

## Summary

Removed redundant factory functions (`create_market_data_service`, `create_features_service`, etc.) from `unified-cloud-services` to avoid technical debt.

## Date
2025-01-15

## Rationale

Since we standardized on direct instantiation of `StandardizedDomainCloudService` with explicit domain parameters, the factory functions became redundant:

**Before (Factory)**:
```python
from unified_cloud_services import create_market_data_service
service = create_market_data_service(cloud_target)  # Domain hidden
```

**After (Direct)**:
```python
from unified_cloud_services import StandardizedDomainCloudService
service = StandardizedDomainCloudService(domain='market_data', cloud_target=cloud_target)  # Domain explicit
```

**Benefits**:
- ✅ Explicit about domain (no hidden magic)
- ✅ Aligns with `StandardizedDomainCloudService` API
- ✅ Reduces technical debt
- ✅ Clearer code

## Changes Made

### 1. Removed Factory Functions from unified-cloud-services

**File**: `unified-cloud-services/unified_cloud_services/__init__.py`

**Removed**:
- `create_market_data_service()`
- `create_features_service()`
- `create_strategy_service()`
- `create_execution_service()`
- `create_ml_service()`

**Replaced with**: Deprecation notice directing users to use direct instantiation

### 2. Refactored All Services

All services updated to use direct instantiation:

- ✅ `market-tick-data-handler`
- ✅ `instruments-service`
- ✅ `market-data-processing-service`
- ✅ `features-data-service`
- ✅ `strategy-service`
- ✅ `ml-training-service`
- ✅ `tk-execution-middleware`
- ✅ `unified-trading-deployment` scripts
- ✅ Examples

### 3. Updated Documentation

- ✅ `docs/REPOSITORY_INTEGRATION.md`
- ✅ `docs/UNIFIED_CLOUD_SERVICES_PATTERNS.md`
- ✅ `market-tick-data-handler/docs/UNIFIED_CLOUD_SERVICES_DEVIATIONS.md`
- ✅ `instruments-service/docs/USAGE_GUIDE.md`

## Migration Guide

### From Factory to Direct Instantiation

**Before**:
```python
from unified_cloud_services import create_market_data_service, CloudTarget

cloud_target = CloudTarget(...)
service = create_market_data_service(cloud_target=cloud_target)
```

**After**:
```python
from unified_cloud_services import StandardizedDomainCloudService, CloudTarget

cloud_target = CloudTarget(...)
service = StandardizedDomainCloudService(
    domain='market_data',
    cloud_target=cloud_target
)
```

## Remaining Uses

Factory functions are still referenced in:
- `market-tick-data-handler/market_data_tick_handler/archive/` - Archive files (deprecated)
- `market-tick-data-handler/market_data_tick_handler/archive/services/migrated_to_unified_cloud_services/` - Archive files (deprecated)

These are in archive directories and can be ignored.

## Impact

- ✅ **No breaking changes** - All active code refactored
- ✅ **Reduced technical debt** - No redundant abstractions
- ✅ **Clearer code** - Domain is explicit
- ✅ **Consistent pattern** - All services use same approach
