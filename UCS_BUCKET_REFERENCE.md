# UCS Bucket Reference Guide

Complete reference for which buckets to use for uploads and downloads based on UCS documentation.

---

## Bucket Naming Convention

UCS uses environment variables with defaults:

| Environment Variable | Default Value | Purpose |
|---------------------|---------------|---------|
| `UNIFIED_CLOUD_SERVICES_GCS_BUCKET` | `market-data-tick-cefi-central-element-323112` | Main market data bucket |
| `GCS_BUCKET` | `execution-store-cefi-central-element-323112` | Results/output bucket |
| `INSTRUMENTS_BUCKET` | `instruments-store-cefi-central-element-323112` | Instruments bucket |

---

## Input Buckets (Download)

### 1. Instruments Bucket

**Bucket:** `instruments-store-cefi-central-element-323112`

**Path Pattern:**
```
instrument_availability/by_date/day-{YYYY-MM-DD}/instruments.parquet
```

**Example:**
```python
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

**File Size:** ~82 KB/day, ~2,900 instruments

---

### 2. Market Tick Data Bucket

**Bucket:** `market-data-tick-cefi-central-element-323112`

**Path Patterns:**

**Trades:**
```
raw_tick_data/by_date/day-{YYYY-MM-DD}/data_type-trades/{INSTRUMENT}.parquet
```

**Book Snapshots:**
```
raw_tick_data/by_date/day-{YYYY-MM-DD}/data_type-book_snapshot_5/{INSTRUMENT}.parquet
```

**Example:**
```python
target = CloudTarget(
    gcs_bucket="market-data-tick-cefi-central-element-323112",
    bigquery_dataset="market_tick_data"
)

# Download trades
df = await ucs.download_from_gcs_streaming(
    target=target,
    gcs_path="raw_tick_data/by_date/day-2023-05-23/data_type-trades/BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN.parquet",
    timestamp_range=(start_ts, end_ts),
    timestamp_column="ts_event",
    use_byte_range=True
)
```

**File Sizes:**
- Trades: 30-64 MB/day per instrument
- Book snapshots: 30-66 MB/day per instrument

---

## Output Bucket (Upload)

### Execution Results Bucket

**Bucket:** `execution-store-cefi-central-element-323112`

**Path Pattern:**
```
backtest_results/{run_id}/
├── summary.json
├── orders.parquet
├── fills.parquet
├── positions.parquet
└── equity_curve.parquet
```

**Example:**
```python
target = CloudTarget(
    gcs_bucket="execution-store-cefi-central-element-323112",
    bigquery_dataset="execution"
)

# Upload summary
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

**File Sizes (estimated per run):**
- `summary.json`: 2-5 KB
- `orders.parquet`: 50-200 KB
- `fills.parquet`: 50-200 KB
- `positions.parquet`: 100-500 KB
- `equity_curve.parquet`: 500 KB-2 MB
- **Total:** ~1-3 MB per run

---

## Complete Bucket Map

| Operation | Bucket | Path | Method |
|-----------|--------|------|--------|
| **Download Instruments** | `instruments-store-cefi-central-element-323112` | `instrument_availability/by_date/day-{date}/instruments.parquet` | `download_from_gcs()` |
| **Download Trades** | `market-data-tick-cefi-central-element-323112` | `raw_tick_data/by_date/day-{date}/data_type-trades/{instrument}.parquet` | `download_from_gcs_streaming()` |
| **Download Book Snapshots** | `market-data-tick-cefi-central-element-323112` | `raw_tick_data/by_date/day-{date}/data_type-book_snapshot_5/{instrument}.parquet` | `download_from_gcs_streaming()` |
| **Upload Summary** | `execution-store-cefi-central-element-323112` | `backtest_results/{run_id}/summary.json` | `upload_to_gcs()` |
| **Upload Orders** | `execution-store-cefi-central-element-323112` | `backtest_results/{run_id}/orders.parquet` | `upload_to_gcs()` |
| **Upload Fills** | `execution-store-cefi-central-element-323112` | `backtest_results/{run_id}/fills.parquet` | `upload_to_gcs()` |
| **Upload Positions** | `execution-store-cefi-central-element-323112` | `backtest_results/{run_id}/positions.parquet` | `upload_to_gcs()` |
| **Upload Equity Curve** | `execution-store-cefi-central-element-323112` | `backtest_results/{run_id}/equity_curve.parquet` | `upload_to_gcs()` |

---

## Instrument Naming Convention

Instruments use canonical format:

```
{VENUE}:{PRODUCT}:{SYMBOL}@{SETTLEMENT}
```

**Examples:**
- `BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN`
- `BYBIT:PERPETUAL:BTC-USDT@LIN`
- `OKX:PERPETUAL:BTC-USDT@LIN`
- `DERIBIT:PERPETUAL:BTC-USD@INV`

---

## Path Construction Examples

### Download Instruments

```python
date = "2023-05-23"
gcs_path = f"instrument_availability/by_date/day-{date}/instruments.parquet"
# Result: instrument_availability/by_date/day-2023-05-23/instruments.parquet
```

### Download Trades

```python
date = "2023-05-23"
instrument = "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN"
gcs_path = f"raw_tick_data/by_date/day-{date}/data_type-trades/{instrument}.parquet"
# Result: raw_tick_data/by_date/day-2023-05-23/data_type-trades/BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN.parquet
```

### Upload Results

```python
run_id = "BT-20231223-001"
filename = "summary.json"
gcs_path = f"backtest_results/{run_id}/{filename}"
# Result: backtest_results/BT-20231223-001/summary.json
```

---

## Multi-Day Operations

For multi-day backtests, UCS handles multiple files automatically:

```python
# UCS can discover files across multiple dates
# Or you can loop through dates:

dates = ["2023-05-23", "2023-05-24", "2023-05-25"]
all_data = []

for date in dates:
    df = await ucs.download_from_gcs_streaming(
        target=target,
        gcs_path=f"raw_tick_data/by_date/day-{date}/data_type-trades/{instrument}.parquet",
        timestamp_range=(start_ts, end_ts),
        timestamp_column="ts_event",
        use_byte_range=True
    )
    all_data.append(df)

# Combine all days
combined = pd.concat(all_data, ignore_index=True)
```

---

## Authentication (Already Handled)

UCS automatically uses:
- `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- Service account JSON file
- Auto-detects credentials in development mode

**No additional authentication needed** - UCS handles it all!

---

*Based on: https://github.com/IggyIkenna/unified-cloud-services*

