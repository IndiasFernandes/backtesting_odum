# System Review: Data Flow & Architecture

**Date:** 2025-12-10  
**Purpose:** Review entire system architecture, data sources, and integration points before proceeding with UCS integration.

---

## Executive Summary

**Current State:**
- ✅ UCS installed and tested
- ✅ Can download trades, book snapshots, and instruments from GCS
- ⚠️ Data is being downloaded to multiple locations
- ⚠️ Need to streamline: Read directly from GCS → Catalog → Backtest

**Key Insight:** For backtesting, we should read directly from GCS bucket and use it in the NautilusTrader catalog, not download to local files first.

---

## 1. Data Sources (GCS Buckets)

### Available Data Types

Based on unified-cloud-services repository:

#### 1.1 Trades (`data_type-trades`)
**Location:** `market-data-tick-cefi-central-element-323112`  
**Path Pattern:** `raw_tick_data/by_date/day-{YYYY-MM-DD}/data_type-trades/{INSTRUMENT}.parquet`

**Schema (from UCS):**
- `instrument_key` - Full instrument identifier
- `price` - Trade price
- `size` - Trade size/amount
- `aggressor_side` - Buyer (1) or Seller (2)
- `trade_id` - Unique trade identifier
- `ts_event` - Event timestamp (nanoseconds)
- `ts_init` - Initialization timestamp (nanoseconds)

**Example:**
```
BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN
```

**File Size:** ~30-64 MB per day per instrument  
**Rows:** ~3M trades per day

---

#### 1.2 Book Snapshots (`data_type-book_snapshot_5`)
**Location:** `market-data-tick-cefi-central-element-323112`  
**Path Pattern:** `raw_tick_data/by_date/day-{YYYY-MM-DD}/data_type-book_snapshot_5/{INSTRUMENT}.parquet`

**Schema:**
- Order book depth snapshots (5 levels)
- Timestamp information
- Bid/ask prices and sizes

**File Size:** ~30-66 MB per day per instrument  
**Use Case:** Rebuild order book depth for backtesting

---

#### 1.3 Instruments
**Location:** `instruments-store-cefi-central-element-323112`  
**Path Pattern:** `instrument_availability/by_date/day-{YYYY-MM-DD}/instruments.parquet`

**Schema:**
- `instrument_key` - Full identifier (e.g., `BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN`)
- `venue` - Exchange name
- `instrument_type` - Type (PERPETUAL, SPOT, etc.)
- `symbol` - Trading pair
- `venue_type` - Venue classification
- `available_from_datetime` - Start availability
- `available_to_datetime` - End availability
- Plus 50+ other metadata fields

**File Size:** ~82 KB per day  
**Rows:** ~2,900 instruments per day

---

## 2. Current Data Flow (Issues)

### Problem: Multiple Download Locations

**Current Flow:**
```
GCS Bucket
    ↓
Download to local files (data_downloads/)
    ↓
Convert to catalog format (backend/data/parquet/)
    ↓
Load into NautilusTrader catalog
    ↓
Backtest
```

**Issues:**
1. ❌ Downloads data to local files first (wasteful)
2. ❌ Multiple copies of same data
3. ❌ Disk space usage
4. ❌ Slower startup (download + convert)

---

## 3. Proposed Data Flow (Optimal)

### Solution: Direct GCS → Catalog → Backtest

**Optimal Flow:**
```
GCS Bucket
    ↓ (UCS byte-range streaming)
Read directly from GCS (no local download)
    ↓
Convert to NautilusTrader format (in-memory)
    ↓
Write to catalog (backend/data/parquet/)
    ↓
Backtest (reads from catalog)
```

**Benefits:**
- ✅ No local file downloads
- ✅ Byte-range streaming (only read what's needed)
- ✅ Catalog caching (converted once, reused)
- ✅ Faster startup
- ✅ Less disk space

---

## 4. NautilusTrader Catalog Structure

### Catalog Path Structure

Based on NautilusTrader documentation:

```
backend/data/parquet/
├── instruments/
│   └── crypto_perpetual/
│       └── {instrument_id}.parquet
├── data/
│   ├── trade_tick/
│   │   └── {instrument_id}/
│   │       └── {timestamp_range}.parquet
│   └── order_book_deltas/
│       └── {instrument_id}/
│           └── {timestamp_range}.parquet
```

### Catalog Operations

**Initialize:**
```python
from nautilus_trader.persistence.catalog import ParquetDataCatalog

catalog = ParquetDataCatalog("backend/data/parquet/")
```

**Write Data:**
```python
catalog.write_data([instrument])  # Write instrument
catalog.write_data(trade_ticks)   # Write trades
catalog.write_data(order_book_deltas)  # Write book data
```

**Query Data:**
```python
# Query trades for time window
trades = catalog.trade_ticks(
    instrument_ids=[instrument_id],
    start=start_time,
    end=end_time
)

# Query order book deltas
deltas = catalog.order_book_deltas(
    instrument_ids=[instrument_id],
    start=start_time,
    end=end_time
)
```

---

## 5. UCS Integration Points

### 5.1 Download from GCS (UCS)

**Trades:**
```python
from unified_cloud_services import UnifiedCloudService, CloudTarget

ucs = UnifiedCloudService()
target = CloudTarget(
    gcs_bucket="market-data-tick-cefi-central-element-323112",
    bigquery_dataset="market_tick_data"
)

# Full file or streaming
df = await ucs.download_from_gcs_streaming(
    target=target,
    gcs_path="raw_tick_data/by_date/day-2023-05-25/data_type-trades/BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN.parquet",
    timestamp_range=(start_ts, end_ts),  # Optional: byte-range streaming
    timestamp_column="ts_event",
    use_byte_range=True
)
```

**Book Snapshots:**
```python
df = await ucs.download_from_gcs_streaming(
    target=target,
    gcs_path="raw_tick_data/by_date/day-2023-05-25/data_type-book_snapshot_5/BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN.parquet",
    timestamp_range=(start_ts, end_ts),
    timestamp_column="ts_event",
    use_byte_range=True
)
```

**Instruments:**
```python
target = CloudTarget(
    gcs_bucket="instruments-store-cefi-central-element-323112",
    bigquery_dataset="instruments_data"
)

df = await ucs.download_from_gcs(
    target=target,
    gcs_path="instrument_availability/by_date/day-2023-05-25/instruments.parquet",
    format="parquet"
)
```

---

### 5.2 Convert to NautilusTrader Format

**Current Converter (`backend/data_converter.py`):**

```python
from backend.data_converter import DataConverter

# Convert trades
trades_count = DataConverter.convert_trades_parquet_to_catalog(
    parquet_path,  # Currently expects local file
    instrument_id,
    catalog,
    price_precision=2,
    size_precision=3
)

# Convert book snapshots
deltas_count = DataConverter.convert_orderbook_parquet_to_catalog(
    parquet_path,  # Currently expects local file
    instrument_id,
    catalog,
    price_precision=2,
    size_precision=3
)
```

**Issue:** Converter expects local file path, but we want to pass DataFrame directly.

**Solution:** Modify converter to accept DataFrame OR file path.

---

## 6. Integration Architecture

### 6.1 New Flow: GCS → Catalog

```python
# 1. Download from GCS (UCS)
df = await ucs.download_from_gcs_streaming(...)

# 2. Convert DataFrame to NautilusTrader objects
trade_ticks = DataConverter.dataframe_to_trade_ticks(df, instrument_id)

# 3. Write to catalog
catalog.write_data(trade_ticks)

# 4. Backtest uses catalog
trades = catalog.trade_ticks(instrument_ids=[instrument_id], start=start, end=end)
```

---

### 6.2 Catalog Caching Strategy

**First Run:**
1. Check catalog for data
2. If not found → Download from GCS → Convert → Write to catalog
3. Use catalog data

**Subsequent Runs:**
1. Check catalog for data
2. If found → Use catalog data directly (no GCS download)
3. Fast startup!

**Cache Invalidation:**
- Catalog data persists across runs
- Only re-download if:
  - Time window extends beyond cached data
  - User explicitly requests refresh

---

## 7. Data Paths Summary

### GCS Bucket Paths

| Data Type | Bucket | Path Pattern |
|-----------|--------|--------------|
| **Trades** | `market-data-tick-cefi-central-element-323112` | `raw_tick_data/by_date/day-{date}/data_type-trades/{instrument}.parquet` |
| **Book Snapshots** | `market-data-tick-cefi-central-element-323112` | `raw_tick_data/by_date/day-{date}/data_type-book_snapshot_5/{instrument}.parquet` |
| **Instruments** | `instruments-store-cefi-central-element-323112` | `instrument_availability/by_date/day-{date}/instruments.parquet` |

### Local Catalog Paths

| Data Type | Catalog Path |
|-----------|--------------|
| **Instruments** | `backend/data/parquet/instruments/crypto_perpetual/{instrument_id}.parquet` |
| **Trades** | `backend/data/parquet/data/trade_tick/{instrument_id}/{timestamp_range}.parquet` |
| **Book Deltas** | `backend/data/parquet/data/order_book_deltas/{instrument_id}/{timestamp_range}.parquet` |

---

## 8. Key Integration Points

### 8.1 BacktestEngine Integration

**Current (`backend/backtest_engine.py`):**
- Loads data from local files
- Converts to catalog format
- Uses catalog for backtesting

**Proposed:**
- Use UCS to download from GCS (if not in catalog)
- Convert DataFrame → NautilusTrader objects
- Write to catalog
- Use catalog for backtesting

---

### 8.2 DataConverter Enhancement

**Current:** Expects local file path  
**Proposed:** Accept DataFrame OR file path

```python
@staticmethod
def convert_trades_dataframe_to_catalog(
    df: pd.DataFrame,
    instrument_id: InstrumentId,
    catalog: ParquetDataCatalog,
    price_precision: int = 2,
    size_precision: int = 3
) -> int:
    """Convert DataFrame directly to catalog format."""
    # Convert DataFrame rows to TradeTick objects
    # Write to catalog
    pass
```

---

## 9. Recommendations

### Immediate Actions

1. ✅ **Keep UCS Integration** - Already tested and working
2. ✅ **Modify DataConverter** - Accept DataFrame input
3. ✅ **Update BacktestEngine** - Use UCS for GCS downloads
4. ✅ **Remove Local Downloads** - Read directly from GCS
5. ✅ **Use Catalog Caching** - Convert once, reuse many times

### Architecture Changes

1. **Remove:** Local file downloads (`data_downloads/raw_tick_data/`)
2. **Keep:** Catalog directory (`backend/data/parquet/`)
3. **Add:** UCS integration for GCS access
4. **Enhance:** DataConverter to accept DataFrames

---

## 10. Data Schema Mapping

### GCS Schema → NautilusTrader Schema

**Trades:**
| GCS Column | NautilusTrader Field | Conversion |
|------------|----------------------|------------|
| `ts_event` | `ts_event` | Direct (nanoseconds) |
| `ts_init` | `ts_init` | Direct (nanoseconds) |
| `price` | `price` | `Price(value, precision)` |
| `size` | `size` | `Quantity(value, precision)` |
| `aggressor_side` | `aggressor_side` | `AggressorSide.BUYER` (1) or `SELLER` (2) |
| `trade_id` | `trade_id` | `TradeId(str(trade_id))` |
| `instrument_key` | `instrument_id` | `InstrumentId.from_str()` |

**Book Snapshots:**
- Convert to `OrderBookDeltas` objects
- Rebuild depth from snapshots

---

## 11. Performance Considerations

### Byte-Range Streaming Benefits

**Full File Download:**
- 48 MB file → Download entire file
- Time: ~7 seconds
- Memory: 548 MB

**5-Minute Window (Streaming):**
- 48 MB file → Download only 0.1 MB (0.13%)
- Time: ~5 seconds
- Memory: <1 MB
- **99.64% bandwidth reduction!**

**For Backtesting:**
- Only download time windows needed
- Cache converted data in catalog
- Subsequent runs use cached catalog

---

## 12. Next Steps

### Phase 1: Enhance DataConverter
- [ ] Add `convert_trades_dataframe_to_catalog()` method
- [ ] Add `convert_orderbook_dataframe_to_catalog()` method
- [ ] Keep existing file-based methods for backward compatibility

### Phase 2: Update BacktestEngine
- [ ] Integrate UCS for GCS downloads
- [ ] Check catalog first, download only if needed
- [ ] Use DataFrame-based converter methods

### Phase 3: Remove Local Downloads
- [ ] Remove `data_downloads/raw_tick_data/` usage
- [ ] Update config to use GCS paths directly
- [ ] Test end-to-end flow

---

## Summary

**Current State:**
- ✅ UCS installed and tested
- ✅ Can download trades, snapshots, instruments
- ⚠️ Data downloaded to local files first

**Target State:**
- ✅ Read directly from GCS (UCS)
- ✅ Convert to catalog format (in-memory)
- ✅ Cache in catalog for reuse
- ✅ Backtest uses catalog

**Key Change:** Eliminate local file downloads, use GCS → Catalog directly.

---

*Last Updated: 2025-12-10*

