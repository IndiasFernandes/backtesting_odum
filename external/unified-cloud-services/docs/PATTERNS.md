# Unified Cloud Services Usage Patterns

## Canonical Pattern

All services in the unified trading system should use **direct instantiation** of `StandardizedDomainCloudService`:

```python
from unified_cloud_services import StandardizedDomainCloudService, CloudTarget
import os

# Create CloudTarget
cloud_target = CloudTarget(
    project_id=os.getenv('GCP_PROJECT_ID', 'central-element-323112'),
    gcs_bucket=os.getenv('MARKET_DATA_GCS_BUCKET', 'market-data-tick'),
    bigquery_dataset=os.getenv('MARKET_DATA_BIGQUERY_DATASET', 'market_data_hft'),
    bigquery_location=os.getenv('BIGQUERY_LOCATION', 'asia-northeast1')
)

# Direct instantiation (canonical pattern)
cloud_service = StandardizedDomainCloudService(
    domain='market_data',
    cloud_target=cloud_target
)
```

## Factory Functions Explained

### What `create_market_data_service()` Does

The factory function is a convenience wrapper:

```python
# From unified-cloud-services/unified_cloud_services/__init__.py
def create_market_data_service(cloud_target=None):
    """Factory for market data operations"""
    return StandardizedDomainCloudService('market_data', cloud_target)
```

**What it does**: Simply returns `StandardizedDomainCloudService('market_data', cloud_target)`

**When to use**:
- ✅ Internal service code where domain is obvious
- ✅ Quick setup scripts
- ⚠️ **NOT recommended for client code** (use direct instantiation for clarity)

## Service Containers: Not Needed

**Decision**: No service containers in microservices architecture.

**Rationale**: In microservices, each service is independent. Service containers add unnecessary complexity for dependency injection that isn't needed at this scale.

**Pattern**: Services create dependencies directly where needed:

```python
# ✅ CORRECT: Create services directly in handlers
class DownloadHandler(ModeHandler):
    def __init__(self, config):
        super().__init__(config)

        # Create cloud service directly
        cloud_target = CloudTarget(...)
        self.cloud_service = StandardizedDomainCloudService(
            domain='market_data',
            cloud_target=cloud_target
        )

        # Create other services as needed
        self.observability = ObservabilityService(config)
        self.data_orchestration = DataOrchestrationService(config)
```

## Environment Variable Naming

**Decision**: Service-specific environment variable prefixes are fine.

**Rationale**:
- Different services may deploy with different configurations
- Allows service-specific overrides when needed
- Both services point to same underlying resources (market_data domain)

**Pattern**:
```python
# instruments-service uses INSTRUMENTS_* prefix
INSTRUMENTS_GCS_BUCKET=market-data-tick
INSTRUMENTS_BIGQUERY_DATASET=market_data_hft

# market-tick-data-handler uses MARKET_DATA_* prefix
MARKET_DATA_GCS_BUCKET=market-data-tick
MARKET_DATA_BIGQUERY_DATASET=market_data_hft
```

**Note**: Both point to the same `market_data` domain resources, but service-specific prefixes allow deployment flexibility.

## Secret Management

### Storing Secrets

Use the generic `store_secret.py` script from `unified-cloud-services` to store any secret:

```bash
# From unified-cloud-services directory
python scripts/store_secret.py --secret-name SECRET_NAME --secret-value SECRET_VALUE [--project-id PROJECT_ID]
```

**Prerequisites:**
1. GCP authentication:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
   # OR
   gcloud auth application-default login
   ```
2. Secret Manager Admin permissions

**Examples:**
```bash
# Store GitHub token using service account (default)
python scripts/store_secret.py --secret-name github-token --secret-value YOUR_TOKEN

# Store GitHub token using your personal gcloud auth credentials
# Use --use-adc when you need your personal account permissions
python scripts/store_secret.py --secret-name github-token --secret-value YOUR_TOKEN --use-adc

# Store API key with custom project
python scripts/store_secret.py --secret-name my-api-key --secret-value KEY_VALUE --project-id my-project

# Store from environment variable
python scripts/store_secret.py --secret-name github-token --secret-value "$GITHUB_TOKEN"
```

**Authentication Methods:**
- **Default (service account)**: Uses `GOOGLE_APPLICATION_CREDENTIALS` from `.env` file or auto-detects credentials file
- **Personal account (`--use-adc`)**: Uses Application Default Credentials from `gcloud auth application-default login`
  
**When to use `--use-adc`:**
- Your personal account has Secret Manager Admin permissions but service account doesn't
- You're running the script interactively and want to use your personal credentials
- The service account lacks required permissions for the operation

### Retrieving Secrets

Secrets are automatically retrieved with fallback to environment variables:

```python
from unified_cloud_services import get_secret_with_fallback

# Retrieve secret (tries Secret Manager first, then environment variable)
secret_value = get_secret_with_fallback(
    secret_name='github-token',
    project_id='your-project-id',
    fallback_env_var='GITHUB_TOKEN'  # Optional: fallback env var name
)
```

**Benefits:**
- ✅ Secrets stored securely in Google Secret Manager
- ✅ Can safely commit `.env` files without exposing secrets
- ✅ Automatic fallback to environment variables for local development
- ✅ Works in GitHub Actions and other CI/CD environments

**Pattern**: All services should use this generic script instead of creating service-specific secret storage scripts.

## Domain Clients

For analytics platforms and cross-service data access, use **domain clients** instead of direct `StandardizedDomainCloudService`:

### Available Domain Clients

```python
from unified_cloud_services import (
    create_instruments_client,
    create_market_candle_data_client,
    create_market_tick_data_client,
    create_features_client,
)
```

### MarketTickDataDomainClient

```python
from unified_cloud_services import create_market_tick_data_client
from datetime import datetime

client = create_market_tick_data_client()

# Get trades
trades = client.get_tick_data(
    date=datetime(2023, 5, 23),
    instrument_id='BINANCE-FUTURES:PERPETUAL:BTC-USDT',
    data_type='trades'
)

# Get book snapshots
book = client.get_tick_data(
    date=datetime(2023, 5, 23),
    instrument_id='BINANCE-FUTURES:PERPETUAL:BTC-USDT',
    data_type='book_snapshot_5'
)

# Get date range
trades_range = client.get_tick_data_range(
    start_date=datetime(2023, 5, 20),
    end_date=datetime(2023, 5, 23),
    instrument_id='BINANCE-FUTURES:PERPETUAL:BTC-USDT',
    data_type='trades'
)
```

### GCS Path Structure

| Domain | Bucket | Path Pattern |
|--------|--------|--------------|
| Raw Tick Data | `market-data-tick` | `raw_tick_data/by_date/day-{YYYY-MM-DD}/data_type-{type}/{instrument}.parquet` |
| Processed Candles | `market-data-tick` | `processed_candles/by_date/day-{YYYY-MM-DD}/timeframe-{tf}/data_type-{type}/{instrument}.parquet` |
| Instruments | `instruments-store` | `by_date/day-{YYYY-MM-DD}/{venue}/instruments.parquet` |
| Features | `features-store` | `{feature_type}/by_date/day-{YYYY-MM-DD}/{instrument}.parquet` |

**Data Types** (for tick data and candles):
- `trades` - Trade executions
- `book_snapshot_5` - Order book snapshots (5 levels)
- `liquidations` - Liquidation events
- `derivative_ticker` - Derivative ticker data

## Implementation Status

### ✅ instruments-service
- Uses direct `StandardizedDomainCloudService` instantiation
- No service container
- Service-specific env var prefixes

### ✅ market-tick-data-handler
- Uses direct `StandardizedDomainCloudService` instantiation
- ServiceContainer deprecated (not used in active code)
- Service-specific env var prefixes
- Writes to `raw_tick_data/by_date/day-{date}/data_type-{type}/`

## CLI Data Queries

Use scripts in `scripts/query_buckets_and_datasets/` for ad-hoc queries:

```bash
# Query raw tick trades
python scripts/query_buckets_and_datasets/query_domain_data.py tick_data \
  --date 2023-05-23 \
  --instrument-id "BINANCE-FUTURES:PERPETUAL:BTC-USDT" \
  --data-type trades

# Query book snapshots
python scripts/query_buckets_and_datasets/query_domain_data.py tick_data \
  --date 2023-05-23 \
  --instrument-id "BINANCE-FUTURES:PERPETUAL:BTC-USDT" \
  --data-type book_snapshot_5

# Query candles
python scripts/query_buckets_and_datasets/query_domain_data.py candles \
  --date 2023-05-23 \
  --instrument-id "BINANCE-FUTURES:PERPETUAL:BTC-USDT" \
  --timeframe 15s

# Query instruments
python scripts/query_buckets_and_datasets/query_domain_data.py instruments \
  --date 2023-05-23 \
  --venue BINANCE-FUTURES

# Save output to CSV
python scripts/query_buckets_and_datasets/query_domain_data.py tick_data \
  --date 2023-05-23 \
  --instrument-id "BINANCE-FUTURES:PERPETUAL:BTC-USDT" \
  --data-type trades \
  --output trades.csv
```

## Migration Guide

### From Factory to Direct Instantiation

**Before**:
```python
from unified_cloud_services import create_market_data_service
cloud_service = create_market_data_service(cloud_target)
```

**After**:
```python
from unified_cloud_services import StandardizedDomainCloudService
cloud_service = StandardizedDomainCloudService(
    domain='market_data',
    cloud_target=cloud_target
)
```

### From ServiceContainer to Direct Creation

**Before**:
```python
from ...services import ServiceContainer
self.services = ServiceContainer(config)
cloud_service = self.services.standardized_cloud
```

**After**:
```python
from unified_cloud_services import StandardizedDomainCloudService, CloudTarget
cloud_target = CloudTarget(...)
self.cloud_service = StandardizedDomainCloudService(
    domain='market_data',
    cloud_target=cloud_target
)
```
