# Clients/ Directory Deprecation Guide

**Date**: 2025-01-15
**Status**: FULLY DEPRECATED
**Migration Target**: `unified-cloud-services/domain/clients.py`

---

## Executive Summary

All service `clients/` directories have been **fully deprecated** and migrated to `unified-cloud-services/domain/clients.py`. This provides:

- ✅ Centralized domain data access
- ✅ Single source of truth for analytics platforms
- ✅ No service-to-service dependencies
- ✅ Consistent API across all domains

---

## Migration Guide

### Before (Deprecated)

```python
# ❌ DEPRECATED: Don't use service clients
from instruments_service.clients.instruments_client import InstrumentsClient
from market_data_processing_service.clients.candles_client import CandlesClient
from market_data_tick_handler.clients.data_client import MarketDataClient

client = InstrumentsClient()
client = CandlesClient()
client = MarketDataClient()
```

### After (Use This)

```python
# ✅ NEW: Use unified-cloud-services domain clients
from unified_cloud_services import (
    create_instruments_client,
    create_market_data_client,
    create_features_client
)

# Create clients
instruments_client = create_instruments_client()
market_data_client = create_market_data_client()
features_client = create_features_client(feature_type='delta_one')
```

---

## Domain Clients Available

### InstrumentsDomainClient

```python
from unified_cloud_services import create_instruments_client

client = create_instruments_client()

# Query instruments
instruments = client.get_instruments_for_date(
    date='2023-05-23',
    venue='BINANCE-FUTURES',
    instrument_type='PERPETUAL',
    base_currency='BTC'
)
```

### MarketDataDomainClient

**Split into two clients**:
- `MarketCandleDataDomainClient` - For processed candles
- `MarketTickDataDomainClient` - For raw tick data

```python
from unified_cloud_services import (
    create_market_candle_data_client,
    create_market_tick_data_client
)
from datetime import datetime

# For processed candles
candle_client = create_market_candle_data_client()
candles = candle_client.get_candles(
    date=datetime(2023, 5, 23),
    instrument_id='BINANCE-FUTURES:PERPETUAL:BTC-USDT',
    timeframe='15s',
    data_type='trades'
)

# For raw tick data (trades)
tick_client = create_market_tick_data_client()
trades = tick_client.get_tick_data(
    date=datetime(2023, 5, 23),
    instrument_id='BINANCE-FUTURES:PERPETUAL:BTC-USDT',
    data_type='trades'
)

# For raw tick data (book snapshots)
book_snapshots = tick_client.get_tick_data(
    date=datetime(2023, 5, 23),
    instrument_id='BINANCE-FUTURES:PERPETUAL:BTC-USDT',
    data_type='book_snapshot_5'
)

# Date range query
tick_range = tick_client.get_tick_data_range(
    start_date=datetime(2023, 5, 20),
    end_date=datetime(2023, 5, 23),
    instrument_id='BINANCE-FUTURES:PERPETUAL:BTC-USDT',
    data_type='trades'
)
```

**GCS Path Structure**:
```
# Tick Data (from market-tick-data-handler)
gs://market-data-tick/raw_tick_data/by_date/day-{YYYY-MM-DD}/data_type-{type}/{instrument}.parquet

# Examples:
gs://market-data-tick/raw_tick_data/by_date/day-2023-05-23/data_type-trades/BINANCE-FUTURES:PERPETUAL:BTC-USDT.parquet
gs://market-data-tick/raw_tick_data/by_date/day-2023-05-23/data_type-book_snapshot_5/BINANCE-FUTURES:PERPETUAL:BTC-USDT.parquet
gs://market-data-tick/raw_tick_data/by_date/day-2023-05-23/data_type-liquidations/BINANCE-FUTURES:PERPETUAL:BTC-USDT.parquet
gs://market-data-tick/raw_tick_data/by_date/day-2023-05-23/data_type-derivative_ticker/BINANCE-FUTURES:PERPETUAL:BTC-USDT.parquet

# Candles (from market-data-processing-service)
gs://market-data-tick/processed_candles/by_date/day-{YYYY-MM-DD}/timeframe-{tf}/data_type-{type}/{instrument}.parquet
```

**Deprecated**: `create_market_data_client()` still works but shows deprecation warning.

### FeaturesDomainClient

```python
from unified_cloud_services import create_features_client

# Delta-one features
delta_one_client = create_features_client(feature_type='delta_one')
features = delta_one_client.get_features(
    date=datetime(2023, 5, 23),
    instrument_id='BINANCE-FUTURES:PERPETUAL:BTC-USDT'
)

# Volatility features
volatility_client = create_features_client(feature_type='volatility')
vol_features = volatility_client.get_features(
    date=datetime(2023, 5, 23),
    instrument_id='DERIBIT:OPTION:BTC-USD:20251231:50000:CALL'
)

# On-chain features
onchain_client = create_features_client(feature_type='onchain')
onchain_features = onchain_client.get_features(
    date=datetime(2023, 5, 23),
    instrument_id='AAVE_V3_ETH:A_TOKEN:aUSDT@ETHEREUM'
)

# Calendar features
calendar_client = create_features_client(feature_type='calendar')
calendar_features = calendar_client.get_features(
    date=datetime(2023, 5, 23),
    instrument_id='GLOBAL:CALENDAR:USDT'
)
```

---

## Service-Specific Access Pattern

**For services accessing dependency data**, use `cloud_data_provider.py` pattern:

```python
# In features-service/app/core/cloud_data_provider.py
from unified_cloud_services import StandardizedDomainCloudService, CloudTarget

class CloudDataProvider:
    def __init__(self):
        cloud_target = CloudTarget(
            project_id=os.getenv('GCP_PROJECT_ID', 'central-element-323112'),
            gcs_bucket=os.getenv('MARKET_DATA_GCS_BUCKET', 'market-data-tick'),
            bigquery_dataset=os.getenv('MARKET_DATA_BIGQUERY_DATASET', 'market_data_hft')
        )

        self.market_data_service = StandardizedDomainCloudService(
            domain='market_data',
            cloud_target=cloud_target
        )
```

**Why not use domain clients in services?**
- Services should use `StandardizedDomainCloudService` directly
- Domain clients are for analytics platforms and cross-service quality gates
- Services maintain domain boundaries via `cloud_data_provider.py`

---

## Analytics Platform Usage

**For analytics platforms** that need to access multiple domains:

```python
from unified_cloud_services import (
    create_instruments_client,
    create_market_candle_data_client,
    create_market_tick_data_client,
    create_features_client
)

# Initialize all clients
instruments = create_instruments_client()
candles = create_market_candle_data_client()
ticks = create_market_tick_data_client()
features = create_features_client(feature_type='delta_one')

# Query across domains
instruments_df = instruments.get_instruments_for_date('2023-05-23')
candles_df = candles.get_candles(
    date=datetime(2023, 5, 23),
    instrument_id='BINANCE-FUTURES:PERPETUAL:BTC-USDT'
)
ticks_df = ticks.get_tick_data(
    date=datetime(2023, 5, 23),
    instrument_id='BINANCE-FUTURES:PERPETUAL:BTC-USDT',
    data_type='trades'
)
features_df = features.get_features(
    date=datetime(2023, 5, 23),
    instrument_id='BINANCE-FUTURES:PERPETUAL:BTC-USDT'
)

# Plot/analyze centrally
# ... analytics code ...
```

---

## High-Level Scripts

**For ad-hoc queries**, use scripts in `scripts/query_buckets_and_datasets/`:

```bash
# Query instruments
python scripts/query_buckets_and_datasets/query_domain_data.py instruments --date 2023-05-23 --venue BINANCE-FUTURES

# Query candles
python scripts/query_buckets_and_datasets/query_domain_data.py candles --date 2023-05-23 --instrument-id "BINANCE-FUTURES:PERPETUAL:BTC-USDT" --timeframe 1m

# Query tick data
python scripts/query_buckets_and_datasets/query_domain_data.py tick_data --date 2023-05-23 --instrument-id "BINANCE-FUTURES:PERPETUAL:BTC-USDT" --data-type trades --hour 10

# Query features
python scripts/query_buckets_and_datasets/query_domain_data.py features --date 2023-05-23 --instrument-id "BINANCE-FUTURES:PERPETUAL:BTC-USDT" --feature-type delta_one
```

---

## Deprecation Timeline

1. **Phase 1 (Complete)**: Create domain clients in `unified-cloud-services`
2. **Phase 2 (Complete)**: Update documentation
3. **Phase 3 (In Progress)**: Add deprecation warnings to service clients
4. **Phase 4 (Future)**: Remove service clients directories

---

## References

- [EXAMPLES_VS_CLIENTS_ARCHITECTURE.md](./EXAMPLES_VS_CLIENTS_ARCHITECTURE.md) - Architecture discussion
- [UNIFIED_REPOSITORY_STRUCTURE.md](./UNIFIED_REPOSITORY_STRUCTURE.md) - Repository structure
- `unified-cloud-services/domain/clients.py` - Domain clients implementation

---

*Last Updated: 2025-11-30*
*Status: Migration Complete - Clients Fully Deprecated*
