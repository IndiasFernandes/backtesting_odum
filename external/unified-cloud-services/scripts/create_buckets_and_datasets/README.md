# Bucket Creation Scripts Summary

## Overview

All bucket creation scripts are located in `scripts/create_buckets_and_datasets/` and follow a consistent pattern:
- Check for existing buckets/datasets (don't recreate)
- Use environment variables with sensible defaults
- Verify region alignment (asia-northeast1)
- Provide clear output and next steps

## Available Scripts

### Domain-Specific Scripts

1. **`create_instruments_bucket.sh`**
   - Bucket: `instruments-store` (production), `instruments-store-test` (test)
   - Dataset: `instruments`
   - Service: `instruments-service`

2. **`create_market_data_tick_bucket.sh`**
   - Bucket: `market-data-tick` (production), `market-data-tick-test` (test)
   - Dataset: `market_data_hft`
   - Service: `market-tick-data-handler`
   - Note: Bucket already exists, script checks existence

3. **`create_market_data_processing_bucket.sh`**
   - Bucket: `market-data-tick` (shared with market-tick-data-handler)
   - Dataset: `market_data_hft` (shared with market-tick-data-handler)
   - Service: `market-data-processing-service`
   - Note: Verifies shared bucket/dataset exists

4. **`create_features_bucket.sh`**
   - Bucket: `features-store` (production), `features-store-test` (test)
   - Datasets: `features_data`, `volatility_features`, `onchain_features`, `calendar_features`
   - Services: `features-delta-one-service`, `features-volatility-service`, `features-onchain-service`, `calendar-features-service`

5. **`create_ml_bucket.sh`**
   - Bucket: `ml-models-store` (production), `ml-models-store-test` (test)
   - Dataset: `ml_predictions`
   - Service: `ml-training-service`

6. **`create_strategy_bucket.sh`**
   - Bucket: `strategy-store` (production), `strategy-store-test` (test)
   - Dataset: `strategy`
   - Service: `strategy-service`
   - Data: positions, exposures, risk, PnL, strategy instructions

7. **`create_execution_bucket.sh`**
   - Bucket: `execution-store` (production), `execution-store-test` (test)
   - Dataset: `execution`
   - Services: `execution-service`, `smart-execution-service`
   - Data: execution logs, fills, algo orders

## Usage

### Run Individual Script

```bash
cd scripts/create_buckets_and_datasets
./create_instruments_bucket.sh
```

### Run All Scripts

```bash
cd scripts/create_buckets_and_datasets
./create_all_domains.sh
```

### Environment Variables

All scripts respect environment variables:
- `GCP_PROJECT_ID` (default: `central-element-323112`)
- `GCS_REGION` (default: `asia-northeast1`)
- Domain-specific bucket/dataset variables (see each script)

## Region Consistency

All buckets and datasets use **`asia-northeast1`** region for consistency across the unified trading system.

## Related Documentation

- `docs/DOMAIN_BOUNDARIES.md` - Domain storage architecture
- `docs/UNIFIED_ARCHITECTURE_SPEC.md` - Complete architecture specification
