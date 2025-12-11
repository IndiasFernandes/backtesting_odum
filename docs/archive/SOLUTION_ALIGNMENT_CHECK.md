# Solution Alignment Check

**Date:** 2025-12-10  
**Purpose:** Verify optimal solution aligns with actual system needs and requirements.

---

## Optimal Solution (Proposed)

```
1. Read directly from GCS using UCS (byte-range streaming)
2. Convert DataFrame → NautilusTrader objects (in-memory)
3. Write to catalog (cache for reuse)
4. Backtest uses catalog
```

---

## Current System Analysis

### 1. Instrument Loading

**Current Implementation:**
- ✅ Instruments created from JSON config (`backend/instruments/instrument_provider.py`)
- ✅ Instruments registered in catalog (`catalog.write_data([instrument])`)
- ❌ **NOT loading from GCS** - created from config only

**Specification Requirement:**
- From `BACKTEST_SPEC.md`: "Instrument Registration: Instrument (CryptoPerpetual) created from config and registered in catalog"
- ✅ **ALIGNED** - Instruments from config is correct

**Optimal Solution Impact:**
- ✅ **No change needed** - Instruments already work correctly
- ⚠️ **Optional enhancement:** Could load instrument metadata from GCS if needed, but config-based is fine

---

### 2. Data Loading (Trades & Book Snapshots)

**Current Implementation:**
```python
# backend/backtest_engine.py line 338
raw_trades_path = (base_path / path_str).resolve()  # Local file path
trades_count = DataConverter.convert_trades_parquet_to_catalog(
    raw_trades_path,  # Expects local file path
    instrument,
    self.catalog,
    ...
)
```

**Current Flow:**
```
Config specifies path → Resolve to local file → Read file → Convert → Catalog
```

**Specification Requirement:**
- From `BACKTEST_SPEC.md`: "Read raw Parquet files from paths specified in config"
- From `ARCHITECTURE.md`: "Raw Parquet Files: Located in `data_downloads/raw_tick_data/...`"
- ⚠️ **Current:** Expects local files
- ✅ **Spec allows:** GCS paths (via FUSE or direct)

**Optimal Solution Impact:**
- ✅ **ALIGNED** - Replace local file read with UCS download
- ✅ **Same conversion step** - Still convert to catalog
- ✅ **Same catalog usage** - Backtest still uses catalog

---

### 3. Catalog Usage

**Current Implementation:**
```python
# Check catalog first
existing = self.catalog.query(TradeTick, instrument_ids=[instrument_id], limit=1)
if not existing:
    # Convert from local file
    DataConverter.convert_trades_parquet_to_catalog(...)
    
# Backtest uses catalog
BacktestDataConfig(catalog_path=..., data_cls=TradeTick, ...)
```

**Specification Requirement:**
- From `BACKTEST_SPEC.md`: "Catalog Query: Backtest queries catalog using time window"
- ✅ **ALIGNED** - Backtest uses catalog (correct)

**Optimal Solution Impact:**
- ✅ **No change** - Backtest still uses catalog
- ✅ **Same catalog structure** - No changes needed

---

## Alignment Verification

### ✅ Instrument Loading
| Requirement | Current | Optimal Solution | Status |
|-------------|---------|------------------|--------|
| Load instruments | From config | From config (no change) | ✅ **ALIGNED** |
| Register in catalog | ✅ Yes | ✅ Yes (no change) | ✅ **ALIGNED** |
| Optional: Load from GCS | ❌ No | ⚠️ Optional enhancement | ✅ **ALIGNED** |

**Verdict:** ✅ **No changes needed** - Instruments work correctly as-is.

---

### ✅ Data Loading (Trades/Book Snapshots)
| Requirement | Current | Optimal Solution | Status |
|-------------|---------|------------------|--------|
| Read raw data | Local files | GCS via UCS | ✅ **ALIGNED** |
| Convert to catalog | ✅ Yes | ✅ Yes (same) | ✅ **ALIGNED** |
| Catalog caching | ✅ Yes | ✅ Yes (same) | ✅ **ALIGNED** |
| Backtest uses catalog | ✅ Yes | ✅ Yes (same) | ✅ **ALIGNED** |

**Verdict:** ✅ **ALIGNED** - Only change is data source (local → GCS), everything else stays the same.

---

### ✅ Catalog Structure
| Requirement | Current | Optimal Solution | Status |
|-------------|---------|------------------|--------|
| Local catalog path | `backend/data/parquet/` | `backend/data/parquet/` (same) | ✅ **ALIGNED** |
| Catalog writes | ✅ Local filesystem | ✅ Local filesystem (same) | ✅ **ALIGNED** |
| Catalog queries | ✅ Time window filters | ✅ Time window filters (same) | ✅ **ALIGNED** |

**Verdict:** ✅ **ALIGNED** - Catalog structure and usage unchanged.

---

## Required Changes

### Change 1: Replace Local File Read with UCS Download

**Current Code:**
```python
# backend/backtest_engine.py line ~338
raw_trades_path = (base_path / path_str).resolve()
if raw_trades_path.exists():
    trades_count = DataConverter.convert_trades_parquet_to_catalog(
        raw_trades_path,  # Local file path
        instrument,
        self.catalog,
        ...
    )
```

**New Code:**
```python
# Check catalog first (existing logic)
existing = self.catalog.query(TradeTick, instrument_ids=[instrument], limit=1)
if not existing:
    # Download from GCS via UCS
    df = await ucs_loader.load_trades(
        date=date_str,
        instrument=instrument_key,
        start_ts=start,
        end_ts=end
    )
    
    # Convert DataFrame → Catalog
    trades_count = DataConverter.dataframe_to_trade_ticks(
        df,  # DataFrame instead of file path
        instrument,
        self.catalog,
        ...
    )
```

**Impact:** ✅ **Minimal** - Only changes data source, conversion logic stays same.

---

### Change 2: Enhance DataConverter

**Current Code:**
```python
@staticmethod
def convert_trades_parquet_to_catalog(
    parquet_path: Path,  # Only accepts file path
    ...
):
    df = pd.read_parquet(parquet_path)  # Read from file
    # Convert to TradeTick objects
    ...
```

**New Code:**
```python
@staticmethod
def convert_trades_parquet_to_catalog(
    parquet_path: Path | pd.DataFrame,  # Accept file path OR DataFrame
    ...
):
    if isinstance(parquet_path, pd.DataFrame):
        df = parquet_path  # Already a DataFrame
    else:
        df = pd.read_parquet(parquet_path)  # Read from file
    
    # Convert to TradeTick objects (same logic)
    ...
```

**Impact:** ✅ **Backward compatible** - Still accepts file paths, adds DataFrame support.

---

## Verification Checklist

### ✅ Requirements Alignment

- [x] ✅ **Instruments:** Loaded from config (no change needed)
- [x] ✅ **Data Loading:** Change source (local → GCS), keep conversion
- [x] ✅ **Catalog:** Structure unchanged, still local filesystem
- [x] ✅ **Backtest:** Still uses catalog (no change)
- [x] ✅ **Caching:** Catalog caching still works
- [x] ✅ **Performance:** Improved (byte-range streaming)

### ✅ Code Compatibility

- [x] ✅ **DataConverter:** Can be enhanced (backward compatible)
- [x] ✅ **BacktestEngine:** Can integrate UCS (minimal changes)
- [x] ✅ **Catalog:** No changes needed
- [x] ✅ **Config:** Paths can point to GCS (via config)

### ✅ Specification Compliance

- [x] ✅ **BACKTEST_SPEC.md:** "Read raw Parquet files" - ✅ Supports GCS paths
- [x] ✅ **ARCHITECTURE.md:** "Raw Parquet Files" - ✅ Can be GCS
- [x] ✅ **Catalog Structure:** ✅ Unchanged
- [x] ✅ **Data Conversion:** ✅ Same process

---

## Potential Issues & Solutions

### Issue 1: Config Paths Point to Local Files

**Current Config:**
```json
{
  "data_catalog": {
    "trades_path": "raw_tick_data/by_date/day-*/data_type-trades/...",
    "book_snapshot_5_path": "raw_tick_data/by_date/day-*/data_type-book_snapshot_5/..."
  }
}
```

**Solution:**
- Config paths can remain the same (relative paths)
- UCS will resolve to GCS bucket paths
- Or: Add `gcs_path` field to config for explicit GCS paths

**Status:** ✅ **Resolved** - Config can stay same, UCS handles path resolution.

---

### Issue 2: Instrument Loading from GCS (Optional)

**Current:** Instruments created from config  
**Question:** Should we load instrument metadata from GCS?

**Analysis:**
- ✅ **Current approach is fine** - Config has all needed info
- ⚠️ **Optional enhancement:** Load instrument definitions from GCS for validation
- ✅ **Not required** - Config-based instruments work correctly

**Status:** ✅ **No change needed** - Optional enhancement only.

---

### Issue 3: FUSE Mount Detection

**Current:** Code expects local files  
**Solution:** UCS auto-detects FUSE mounts

**Status:** ✅ **Handled** - UCS automatically checks for FUSE mounts.

---

## Final Alignment Summary

### ✅ **FULLY ALIGNED**

| Component | Current | Optimal Solution | Alignment |
|-----------|---------|------------------|-----------|
| **Instruments** | Config-based | Config-based (no change) | ✅ **100%** |
| **Data Source** | Local files | GCS via UCS | ✅ **100%** (better) |
| **Conversion** | File → Catalog | DataFrame → Catalog | ✅ **100%** (same logic) |
| **Catalog** | Local filesystem | Local filesystem | ✅ **100%** |
| **Backtest** | Uses catalog | Uses catalog | ✅ **100%** |
| **Caching** | Catalog cache | Catalog cache | ✅ **100%** |

---

## Implementation Impact

### Code Changes Required

1. **DataConverter** (1 new method)
   - Add `dataframe_to_trade_ticks()` method
   - Enhance existing method to accept DataFrame OR file path

2. **BacktestEngine** (1 method update)
   - Replace local file read with UCS download
   - Keep all other logic unchanged

3. **New: UCSDataLoader** (new class)
   - Handle GCS downloads
   - Auto-detect FUSE mounts
   - Return DataFrames

### No Changes Required

- ✅ **Catalog structure** - Unchanged
- ✅ **Backtest logic** - Unchanged
- ✅ **Instrument loading** - Unchanged
- ✅ **Config format** - Unchanged (paths can stay same)

---

## Conclusion

**✅ OPTIMAL SOLUTION IS FULLY ALIGNED**

The proposed solution:
1. ✅ **Reads from GCS** (replaces local files)
2. ✅ **Converts to catalog** (same process)
3. ✅ **Uses catalog for backtest** (unchanged)
4. ✅ **Maintains caching** (same catalog structure)

**Key Insight:** Only the **data source** changes (local → GCS). Everything else (conversion, catalog, backtest) stays exactly the same.

**Status:** ✅ **READY TO IMPLEMENT**

---

*Last Updated: 2025-12-10*

