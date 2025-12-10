# Centralized Services Migration Guide

**Date**: 2025-11-06
**Status**: ✅ Centralized Services Implemented

## Overview

This document provides migration guidance for services to adopt centralized credentials handling and CSV sampling services from `unified-cloud-services`.

## Centralized Services

### 1. Credentials Handling ✅

**Location**: `unified-cloud-services/unified_cloud_services/core/cloud_auth_factory.py`

**What It Does**:
- Auto-detects credentials files in development mode only
- Production mode uses VM service account (no credentials file needed)
- Handles all GCS, BigQuery, and Secret Manager authentication

**Migration Steps**:
1. **Remove local credential detection code**:
   - Delete any `utils/credentials.py` or similar files
   - Remove credential auto-detection from CLI entry points
   - Remove credential search logic from service initialization

2. **Verify environment variable**:
   - Ensure `ENVIRONMENT` is set correctly:
     - Development: `ENVIRONMENT=development`
     - Production: `ENVIRONMENT=production`

3. **Test**:
   - Development mode: Credentials auto-detected
   - Production mode: Uses VM service account

**Example Migration**:
```python
# BEFORE (instruments-service - REMOVED)
from ..utils.credentials import auto_set_credentials
auto_set_credentials()

# AFTER (no code needed - handled automatically by unified-cloud-services)
from unified_cloud_services import create_market_data_service
service = create_market_data_service()  # Credentials auto-handled
```

### 2. CSV Sampling Service ✅

**Location**: `unified-cloud-services/unified_cloud_services/core/sampling_service.py`

**What It Does**:
- Environment-aware sampling (only in non-production)
- Configurable sample size via `CSV_SAMPLE_SIZE` env var
- Smart sampling for different data types
- Production mode: No CSV files created (but doesn't drop data samples)

**Migration Steps**:
1. **Remove local sampling code**:
   - Remove `csv_sample_size = int(os.getenv('CSV_SAMPLE_SIZE', 10))` from service classes
   - Remove local CSV sampling methods (e.g., `_generate_csv_sample()`, `_generate_csv_sample_smart()`)
   - Remove `utils/csv_sampling.py` if exists

2. **Add centralized service**:
   ```python
   from unified_cloud_services import create_sampling_service

   sampling_service = create_sampling_service()
   ```

3. **Replace sampling calls**:
   ```python
   # BEFORE
   self._generate_csv_sample_smart(candles_df, tick_file_info, timeframe)

   # AFTER
   sampling_service.generate_csv_sample(
       df=candles_df,
       filename_prefix='candles',
       data_type=tick_file_info['data_type'],
       metadata={'instrument_id': tick_file_info.get('instrument_id'), 'timeframe': timeframe}
   )
   ```

4. **Update environment variables** (if needed):
   - `CSV_SAMPLE_SIZE`: Number of rows to sample (default: 10)
   - `ENABLE_CSV_SAMPLING`: Enable/disable sampling (default: false)
   - `CSV_SAMPLE_DIR`: Directory for samples (default: `./data/samples`)

**Example Migration** (from `market-tick-data-handler`):
```python
# BEFORE
class CandleProcessingService:
    def __init__(self, service_container):
        self.csv_sample_size = int(os.getenv('CSV_SAMPLE_SIZE', 10))

    def _generate_csv_sample_smart(self, candles_df, tick_file_info, timeframe):
        # ... local sampling logic ...
        sample_df = candles_df.head(min(self.csv_sample_size, len(candles_df)))
        sample_df.to_csv(sample_path, index=False)

# AFTER
from unified_cloud_services import create_sampling_service

class CandleProcessingService:
    def __init__(self, service_container):
        self.sampling_service = create_sampling_service()

    def _upload_candles(self, candles_df, tick_file_info, timeframe):
        # ... upload logic ...
        # CSV sampling using centralized service
        self.sampling_service.generate_csv_sample(
            df=candles_df,
            filename_prefix='candles',
            data_type=tick_file_info['data_type'],
            metadata={'instrument_id': tick_file_info.get('instrument_id'), 'timeframe': timeframe}
        )
```

## Service Migration Checklist

### instruments-service ✅
- [x] Removed local credential detection
- [x] Removed local CSV sampling
- [x] Using centralized services

### market-tick-data-handler ⏳
- [ ] Remove `csv_sample_size` from `CandleProcessingService`
- [ ] Remove `_generate_csv_sample_smart()` and `_generate_csv_sample_optimized()` methods
- [ ] Add `create_sampling_service()` import
- [ ] Replace sampling calls with centralized service
- [ ] Verify no local credential detection exists

### features-delta-one-service ⏳
- [ ] Check for local sampling code
- [ ] Remove if exists, migrate to centralized service
- [ ] Verify no local credential detection exists

### ml-training-service ⏳
- [ ] Check for local sampling code
- [ ] Remove if exists, migrate to centralized service
- [ ] Verify no local credential detection exists

### strategy-service ⏳
- [ ] Check for local sampling code
- [ ] Remove if exists, migrate to centralized service
- [ ] Verify no local credential detection exists

### execution-service ⏳
- [ ] Check for local sampling code
- [ ] Remove if exists, migrate to centralized service
- [ ] Verify no local credential detection exists

## Benefits

1. **DRY**: No duplicate credential/sampling logic across services
2. **Consistency**: All services use same logic
3. **Environment Awareness**: Credentials only auto-detected in dev mode
4. **Centralized Configuration**: `CSV_SAMPLE_SIZE` controlled in one place
5. **Production Safety**: Production mode doesn't create CSV samples

## Testing

### Credentials
```bash
# Development mode (auto-detects)
ENVIRONMENT=development python -m {service} --mode {mode}

# Production mode (uses VM service account)
ENVIRONMENT=production python -m {service} --mode {mode}
```

### Sampling
```bash
# Development mode (samples if enabled)
ENVIRONMENT=development ENABLE_CSV_SAMPLING=true CSV_SAMPLE_SIZE=10 python -m {service} --mode {mode}

# Production mode (no sampling)
ENVIRONMENT=production python -m {service} --mode {mode}
```

## References

- [UNIFIED_ARCHITECTURE_PLAN.md](UNIFIED_ARCHITECTURE_PLAN.md#24-centralized-credentials-handling-) - Credentials handling details
- [UNIFIED_ARCHITECTURE_PLAN.md](UNIFIED_ARCHITECTURE_PLAN.md#25-centralized-sampling-service-) - Sampling service details
- [UNIFIED_ARCHITECTURE_SPEC.md](UNIFIED_ARCHITECTURE_SPEC.md#1413-centralized-credentials-handling-) - Technical specifications
