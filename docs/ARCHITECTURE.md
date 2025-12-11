# Execution Services Architecture: Unified Cloud Streaming

## Overview

Execution-services uses **unified-cloud-services** for byte-range streaming from GCS, converting data on-the-fly to NautilusTrader format, and storing it in a catalog (local or GCS). The system is designed to minimize conversion overhead, reuse converted data, and efficiently handle large datasets.

---

## Catalog System

### What is the Catalog?

The **catalog** is NautilusTrader's `ParquetDataCatalog` - a directory structure that stores converted Parquet files in NautilusTrader's format.

**Structure:**
```
catalog_root/
├── data/
│   ├── trade_tick/
│   │   └── BTCUSDT-PERP.BINANCE/
│   │       ├── 20230523T020000000000000_20230523T022000000000000.parquet
│   │       └── 20230523T022000000000000_20230523T024000000000000.parquet
│   └── order_book_deltas/
│       └── BTCUSDT-PERP.BINANCE/
│           └── <timestamp_range>.parquet
└── instruments/
    └── BTCUSDT-PERP.BINANCE.parquet
```

**File Naming Convention:**
- Format: `{start_timestamp}_{end_timestamp}.parquet`
- Timestamps are in ISO format (nanoseconds precision)
- Example: `20230523T020000000000000_20230523T022000000000000.parquet` contains 20 minutes of data

### Catalog Storage Options

#### Option 1: Local Catalog (Default for Development)

```python
catalog = ParquetDataCatalog("backend/data/parquet/")
```

**Storage**: Local directory on filesystem
- ✅ Fast access
- ✅ Works offline
- ❌ Requires local storage space
- ❌ Not shared across instances

#### Option 2: GCS Catalog (Recommended for Production)

```python
catalog = ParquetDataCatalog(
    path="gcs://execution-store-cefi-central-element-323112/nautilus-catalog/",
    fs_protocol="gcs",
    fs_storage_options={
        "project": "central-element-323112",
        "token": "/path/to/service-account.json",  # Optional if GOOGLE_APPLICATION_CREDENTIALS set
    }
)
```

**Storage**: GCS bucket
- ✅ No local storage needed
- ✅ Shared across instances
- ✅ Scalable
- ✅ Converted data persists across runs
- ⚠️ Network latency (but NautilusTrader streams efficiently)

**GCS Bucket Structure:**
```
gs://execution-store-cefi-central-element-323112/
└── nautilus-catalog/
    ├── data/
    │   ├── trade_tick/
    │   │   └── BTCUSDT-PERP.BINANCE/
    │   │       └── <timestamp_range>.parquet
    │   └── order_book_deltas/
    └── instruments/
        └── BTCUSDT-PERP.BINANCE.parquet
```

### CatalogManager

The `CatalogManager` class handles catalog initialization and supports both local and GCS paths:

```python
from backend.catalog_manager import CatalogManager

# Local catalog
catalog_manager = CatalogManager(
    catalog_path="backend/data/parquet/"
)

# GCS catalog
catalog_manager = CatalogManager(
    catalog_path="gcs://execution-store-cefi-central-element-323112/nautilus-catalog/",
    gcs_project_id="central-element-323112"
)

catalog = catalog_manager.get_catalog()
```

**Configuration:**
```bash
# Environment variables
export DATA_CATALOG_PATH="gcs://execution-store-cefi-central-element-323112/nautilus-catalog/"
export GCP_PROJECT_ID="central-element-323112"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

### Shared Catalog Strategy

**Recommended**: Use a **shared catalog** across all backtest runs.

**Benefits:**
- ✅ Reuse converted data - if catalog has data, skip conversion
- ✅ Efficient - only converts missing time ranges
- ✅ Faster subsequent runs - uses cached files
- ✅ Shared across runs - one conversion benefits all runs
- ✅ Works with GCS catalog - shared across instances

**How it works:**
1. Check catalog first: `catalog.query(..., start=start, end=end, limit=1)`
2. If data exists: Skip conversion entirely (fast!)
3. If data missing: Stream from GCS and convert
4. Write to catalog: Files are now available for future queries

**Cleanup:**
- Local catalog: Manual cleanup or time-based deletion
- GCS catalog: Use GCS lifecycle policies (e.g., delete after 90 days)

---

## Data Conversion Process

### Important: Data is Already Pre-Converted!

**✅ Data in GCS is already in NautilusTrader-compatible format!**

The `market-tick-data-handler` service transforms raw Tardis data to NautilusTrader schema format **before uploading to GCS**.

**GCS Bucket**: `market-data-tick-cefi-central-element-323112`
**GCS Path**: `raw_tick_data/by_date/day-{YYYY-MM-DD}/data_type-trades/{instrument_key}.parquet`

**Pre-converted Format:**
- ✅ Timestamps: `ts_event`, `ts_init` (nanoseconds)
- ✅ Columns: `size`, `trade_id`, `aggressor_side` (already renamed)
- ✅ Aggressor side: `int8` (1=buy, 2=sell)
- ✅ Schema matches NautilusTrader format

### What Conversion Does

The conversion in `execution-services` transforms the **pre-converted Parquet DataFrame** into NautilusTrader's `TradeTick` objects and writes them to the catalog.

**Conversion Steps:**

1. **Read Pre-Converted Parquet from GCS** (via unified-cloud-services streaming)
   ```python
   df = await ucs.download_from_gcs_streaming(
       target=cloud_target,
       gcs_path=gcs_path,
       timestamp_range=(start_time, end_time),
       use_byte_range=True,  # Only downloads relevant row groups!
   )
   ```

2. **Convert DataFrame → TradeTick Objects**
   - Convert `aggressor_side` (int8: 1/2) → `AggressorSide` enum
   - Create typed objects: `Price`, `Quantity`, `TradeId`
   - Use `instrument_id` from config (NOT from DataFrame's `instrument_key` column)

3. **Write to Catalog**
   ```python
   catalog.write_data(trade_ticks)  # Creates Parquet files
   ```

**Why Conversion is Still Needed:**
- NautilusTrader requires `TradeTick` objects (not DataFrames)
- `TradeTick` objects require specific types (`Price`, `Quantity`, `TradeId`, `AggressorSide` enum)
- Catalog format requires NautilusTrader objects

**Conversion is minimal** since data is already pre-converted - we just need object creation!

### Edge Cases Handled

1. **Aggressor Side Conversion**:
   - Handles `int8` (1/2) from pre-converted format
   - Handles legacy string formats ('buy'/'sell') for backward compatibility
   - Defaults to `BUYER` if value cannot be mapped

2. **Timestamp Format Detection**:
   - Handles nanoseconds (pre-converted format) - no conversion needed
   - Handles microseconds/milliseconds (legacy format) - converts to nanoseconds
   - Falls back to `ts_event` if `ts_init` is missing

3. **Column Name Variations**:
   - Pre-converted: `size`, `trade_id`, `aggressor_side`
   - Legacy: `amount` → `size`, `id` → `trade_id`, `side` → `aggressor_side`

4. **Instrument ID**:
   - ⚠️ **Important**: `instrument_id` is passed as parameter, NOT extracted from DataFrame
   - DataFrame's `instrument_key` column is ignored during conversion
   - `instrument_id` is created from config before calling conversion function

---

## Streaming Architecture

### Unified Cloud Services Integration

**execution-services** uses **unified-cloud-services** for efficient byte-range streaming from GCS.

**Key Features:**
- ✅ Byte-range streaming - only downloads needed row groups
- ✅ Timestamp filtering - filters at Parquet metadata level
- ✅ FUSE mount detection - automatically uses FUSE if available, falls back to direct GCS
- ✅ Efficient - streams only needed time ranges

### Streaming Flow

#### 1. Startup Validation: Check Data Exists in GCS

**Purpose**: Verify data files exist in GCS bucket before starting backtest

```python
from unified_cloud_services import UnifiedCloudService, CloudTarget

ucs = UnifiedCloudService()
cloud_target = CloudTarget(
    gcs_bucket=config["data_catalog"]["gcs_bucket"],
    project_id=config["environment"]["GCS_PROJECT_ID"],
)

# Check if trade data file exists in GCS (remote check - no FUSE needed)
gcs_trades_path = config["data_catalog"]["trades_path"]
exists_map = await ucs.check_gcs_files_exist_batch(
    target=cloud_target,
    gcs_paths=[gcs_trades_path],
)

if not exists_map.get(gcs_trades_path, False):
    validation_errors.append(
        f"ERROR: Trade data file not found in GCS: {gcs_trades_path}"
    )
```

**Key Points:**
- ✅ Checks remote GCS bucket directly (doesn't need FUSE mount)
- ✅ Runs once at startup
- ✅ Validates data availability before processing

#### 2. Check Catalog First

**Purpose**: Skip conversion if catalog files already exist

```python
# Check if catalog already has data for this time range
existing = catalog.query(
    data_cls=TradeTick,
    instrument_ids=[instrument_id],
    start=start_time,
    end=end_time,
    limit=1  # Just check if any data exists
)

if existing:
    # Catalog files already exist - skip conversion!
    print("Status: ✓ Using existing catalog data")
else:
    # Catalog doesn't have data - stream and convert
    # ... streaming conversion logic ...
```

**Benefits:**
- ✅ Avoids redundant conversion - if catalog has data, skip it
- ✅ Works for local and GCS catalogs - `catalog.query()` works for both
- ✅ Time-range specific - checks exact time range needed
- ✅ Efficient - only converts what's missing

#### 3. Stream Bytes Chunks Using Unified Cloud Services

**Purpose**: Stream data chunks (handles FUSE vs direct GCS automatically)

```python
# unified-cloud-services ALREADY handles FUSE detection automatically!

for chunk_start, chunk_end in time_chunks:
    # unified-cloud-services checks FUSE mount first, falls back to direct GCS
    df = await ucs.download_from_gcs_streaming(
        target=cloud_target,
        gcs_path=gcs_trades_path,
        timestamp_range=(chunk_start, chunk_end),  # Only this range!
        use_byte_range=True,  # Byte-range streaming
    )
    
    # unified-cloud-services automatically:
    # 1. Checks if FUSE mount exists → uses local path if available
    # 2. Falls back to direct GCS streaming if no FUSE mount
    # 3. Uses byte-range streaming for efficiency
    
    # Convert chunk to NautilusTrader format
    trade_ticks = convert_dataframe_to_trade_ticks(df, instrument_id, ...)
    
    # Write chunk to catalog immediately (incremental)
    catalog.write_data(trade_ticks)
```

**Key Points:**
- ✅ unified-cloud-services handles FUSE detection automatically
- ✅ No need to manually check FUSE - UCS does it internally
- ✅ Streams only needed time ranges (byte-range streaming)
- ✅ Works whether FUSE is mounted or not
- ✅ Processes in chunks (memory efficient)

#### 4. Write Chunks Incrementally to Catalog

**Purpose**: Write converted chunks as they're processed

```python
# Write chunks incrementally as they're converted
catalog.write_data(trade_ticks)  # Can be called multiple times

# NautilusTrader queries catalog (works immediately)
trades = catalog.query(
    data_cls=TradeTick,
    instrument_ids=[instrument_id],
    start=start_time,
    end=end_time,
)
```

**Key Points:**
- ✅ `catalog.write_data()` can be called multiple times with chunks
- ✅ NautilusTrader can query catalog as soon as data is written
- ✅ Works for both local and GCS catalogs

### Complete Flow Diagram

```
Startup:
  └─> Check GCS bucket (remote) → File exists? ✓
  
Backtest Run:
  └─> Check catalog → Data exists?
      ├─> Yes → Use catalog (fast!)
      └─> No → Stream from GCS
          └─> unified-cloud-services:
              ├─> Check FUSE mount? → Use local path if available
              └─> No FUSE? → Stream directly from GCS (byte-range)
          └─> Convert chunk → Write to catalog
          └─> NautilusTrader queries catalog
```

---

## Performance Benefits

### GCS Catalog vs Local Catalog

| Operation | Local Catalog | GCS Catalog |
|-----------|--------------|-------------|
| **First Run** | Stream + Convert + Write Local | Stream + Convert + Write GCS |
| **Subsequent Runs** | Read Local (fast) | Read GCS (streams efficiently) |
| **Storage** | Requires local space | No local storage needed |
| **Sharing** | Not shared | Shared across instances |
| **Persistence** | Lost on instance termination | Persists across runs |

### Conversion Caching

**Without Catalog Check:**
- Every run: Stream + Convert + Write (~5-10 min)

**With Catalog Check:**
- First run: Stream + Convert + Write (~5-10 min)
- Subsequent runs: Read catalog (~30-60 sec) - **10x faster!**

**Benefits:**
- ✅ Only converts missing time ranges
- ✅ Reuses converted data across runs
- ✅ Faster subsequent runs
- ✅ Reduced GCS egress costs

---

## Configuration

### Environment Variables

```bash
# Catalog configuration
export DATA_CATALOG_PATH="gcs://execution-store-cefi-central-element-323112/nautilus-catalog/"
export GCP_PROJECT_ID="central-element-323112"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

# Unified cloud services configuration
export UNIFIED_CLOUD_LOCAL_PATH="/app/data_downloads"
export UNIFIED_CLOUD_SERVICES_USE_PARQUET="true"
export UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS="false"
```

### Config File

```json
{
  "environment": {
    "DATA_CATALOG_PATH": "gcs://execution-store-cefi-central-element-323112/nautilus-catalog/",
    "GCP_PROJECT_ID": "central-element-323112",
    "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/service-account.json"
  },
  "data_catalog": {
    "source": "gcs",
    "gcs_bucket": "market-data-tick-cefi-central-element-323112",
    "trades_path": "raw_tick_data/by_date/day-2023-05-23/data_type-trades/BTC-USDT.parquet"
  }
}
```

---

## Key Points Summary

1. **Catalog System**:
   - Can be local or GCS (NautilusTrader supports both via fsspec)
   - GCS catalog recommended for production (shared, persistent, scalable)
   - Shared catalog strategy recommended (reuse converted data)

2. **Data Conversion**:
   - Data is already pre-converted to NautilusTrader schema format in GCS
   - Conversion is minimal (DataFrame → TradeTick objects)
   - Handles edge cases (aggressor side, timestamps, column names)

3. **Streaming Architecture**:
   - Uses unified-cloud-services for byte-range streaming
   - Automatically handles FUSE mount detection
   - Streams only needed time ranges
   - Processes in chunks (memory efficient)

4. **Performance**:
   - Check catalog first - skip conversion if data exists
   - Subsequent runs are 10x faster (read catalog vs convert)
   - Only converts missing time ranges
   - Reduces GCS egress costs

5. **Implementation**:
   - `CatalogManager` handles local/GCS catalog initialization
   - unified-cloud-services handles streaming (FUSE detection, byte-range)
   - Conversion logic handles pre-converted format and edge cases
   - Incremental writes to catalog (chunks)

---

## Recommendations

### For Development/Local
- Use local catalog: `backend/data/parquet/`
- Fast, works offline, easy to debug

### For Production/VM
- Use GCS catalog: `gcs://execution-store-cefi-central-element-323112/nautilus-catalog/`
- No local storage needed, shared across instances
- NautilusTrader streams efficiently from GCS
- Converted data persists across runs

### Best Practices
- ✅ Always check catalog first before converting
- ✅ Use shared catalog (not unique per run)
- ✅ Process in chunks (memory efficient)
- ✅ Use GCS catalog for production (persistent, shared)
- ✅ Set up GCS lifecycle policies for cleanup

---

## References

- [NautilusTrader Catalog Documentation](https://nautilustrader.io/docs/latest/concepts/data)
- unified-cloud-services: Byte-range streaming, FUSE detection, GCS access
- CatalogManager: `backend/catalog_manager.py`
- DataConverter: `backend/data_converter.py`
