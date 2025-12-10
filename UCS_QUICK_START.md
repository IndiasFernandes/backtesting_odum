# UCS Quick Start - Upload & Download

Quick reference for using UCS to upload and download data.

---

## Setup

```bash
# Install UCS
pip install git+https://github.com/IggyIkenna/unified-cloud-services.git

# Set credentials (already done via .env)
export GOOGLE_APPLICATION_CREDENTIALS=.secrets/gcs/gcs-service-account.json
```

---

## Download Operations

### Download Instruments

```python
from unified_cloud_services import UnifiedCloudService, CloudTarget
import asyncio

ucs = UnifiedCloudService()
target = CloudTarget(
    gcs_bucket="instruments-store-cefi-central-element-323112",
    bigquery_dataset="instruments_data"
)

df = await ucs.download_from_gcs(
    target=target,
    gcs_path="instrument_availability/by_date/day-2023-05-23/instruments.parquet",
    format="parquet"
)
```

### Download Tick Data (Streaming)

```python
from datetime import datetime, timezone

target = CloudTarget(
    gcs_bucket="market-data-tick-cefi-central-element-323112",
    bigquery_dataset="market_tick_data"
)

start_ts = datetime(2023, 5, 23, 0, 0, 0, tzinfo=timezone.utc)
end_ts = datetime(2023, 5, 23, 0, 5, 0, tzinfo=timezone.utc)

df = await ucs.download_from_gcs_streaming(
    target=target,
    gcs_path="raw_tick_data/by_date/day-2023-05-23/data_type-trades/BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN.parquet",
    timestamp_range=(start_ts, end_ts),
    timestamp_column="ts_event",
    use_byte_range=True
)
```

---

## Upload Operations

### Upload Backtest Results

```python
target = CloudTarget(
    gcs_bucket="execution-store-cefi-central-element-323112",
    bigquery_dataset="execution"
)

# Upload summary JSON
await ucs.upload_to_gcs(
    target=target,
    gcs_path=f"backtest_results/{run_id}/summary.json",
    data=summary_dict,
    format="json"
)

# Upload Parquet files
await ucs.upload_to_gcs(
    target=target,
    gcs_path=f"backtest_results/{run_id}/orders.parquet",
    data=orders_df,
    format="parquet"
)
```

---

## Buckets

| Purpose | Bucket Name |
|---------|-------------|
| **Instruments** | `instruments-store-cefi-central-element-323112` |
| **Market Data** | `market-data-tick-cefi-central-element-323112` |
| **Results** | `execution-store-cefi-central-element-323112` |

---

## Key Methods

| Method | Purpose | Use Case |
|--------|---------|----------|
| `download_from_gcs()` | Full file download | Small files, instruments |
| `download_from_gcs_streaming()` | Byte-range streaming | Large files, time windows |
| `upload_to_gcs()` | Upload to GCS | Results, Parquet files |

---

## Full Guides

- **Upload/Download Details:** `UCS_UPLOAD_DOWNLOAD_GUIDE.md`
- **Bucket Reference:** `UCS_BUCKET_REFERENCE.md`
- **Authentication:** `UCS_AUTHENTICATION_EXPLAINED.md`

