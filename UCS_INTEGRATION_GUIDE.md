# Unified Cloud Services (UCS) Integration Guide

This guide covers integrating Unified Cloud Services into the execution-services repository for GCS operations.

## Overview

Unified Cloud Services (UCS) provides:
1. **GCS FUSE mounting** (via `ucs-mount`) - Auto-detects mounts, no code changes needed
2. **Data download** from GCS buckets (instruments, market data)
3. **Results upload** to GCS bucket (keyed by strategy ID)

**Repository:** https://github.com/IggyIkenna/unified-cloud-services

---

## Quick Start

### 1. Install UCS

```bash
# Option A: Using setup script
bash backend/scripts/setup_ucs.sh

# Option B: Manual installation
pip install git+https://github.com/IggyIkenna/unified-cloud-services.git
```

### 2. Test Connection

```bash
# Basic connection test
python3 backend/scripts/test_ucs_connection.py

# Test with specific buckets
python3 backend/scripts/test_ucs_connection.py \
  --bucket execution-store-cefi-central-element-323112 \
  --instruments-bucket instruments-store-cefi-central-element-323112 \
  --market-data-bucket market-data-tick-cefi-central-element-323112

# Test upload functionality
python3 backend/scripts/test_ucs_connection.py --test-upload
```

### 3. Configure Environment

UCS auto-detects GCS FUSE mounts, so no code changes are needed if using FUSE. For direct GCS access:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
export UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=true
```

---

## GCS Buckets Reference

### Input Buckets

| Data Type | Bucket Name | Path Pattern |
|-----------|-------------|--------------|
| **Instruments** | `instruments-store-cefi-central-element-323112` | `instrument_availability/by_date/day-{YYYY-MM-DD}/instruments.parquet` |
| **Market Tick Data** | `market-data-tick-cefi-central-element-323112` | `raw_tick_data/by_date/day-{YYYY-MM-DD}/data_type-trades/{INSTRUMENT}.parquet` |
| **Book Snapshots** | `market-data-tick-cefi-central-element-323112` | `raw_tick_data/by_date/day-{YYYY-MM-DD}/data_type-book_snapshot_5/{INSTRUMENT}.parquet` |

### Output Bucket

| Data Type | Bucket Name | Path Pattern |
|-----------|-------------|--------------|
| **Backtest Results** | `execution-store-cefi-central-element-323112` | `backtest_results/{run_id}/summary.json`<br>`backtest_results/{run_id}/orders.parquet`<br>`backtest_results/{run_id}/fills.parquet`<br>`backtest_results/{run_id}/positions.parquet`<br>`backtest_results/{run_id}/equity_curve.parquet` |

---

## UCS Usage Examples

### 1. Download Instrument Definitions

```python
import asyncio
from unified_cloud_services import UnifiedCloudService, CloudTarget

async def load_instruments(date: str):
    ucs = UnifiedCloudService()
    target = CloudTarget(
        gcs_bucket='instruments-store-cefi-central-element-323112',
        bigquery_dataset='instruments_data'
    )
    
    # Full file download (~82 KB, ~3s)
    df = await ucs.download_from_gcs(
        target=target,
        gcs_path=f'instrument_availability/by_date/day-{date}/instruments.parquet',
        format='parquet'
    )
    
    # Filter to specific instrument
    inst = df[df['instrument_key'] == 'BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN']
    tick_size = inst.iloc[0]['tick_size']
    
    return df

# Usage
instruments = asyncio.run(load_instruments('2023-05-23'))
```

### 2. Download Tick Data (Full File)

```python
async def load_full_day():
    ucs = UnifiedCloudService()
    target = CloudTarget(
        gcs_bucket='market-data-tick-cefi-central-element-323112',
        bigquery_dataset='market_tick_data'
    )
    
    # Full file: 48 MB, 3.2M rows, ~7s
    df = await ucs.download_from_gcs(
        target=target,
        gcs_path='raw_tick_data/by_date/day-2023-05-23/data_type-trades/BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN.parquet',
        format='parquet'
    )
    return df
```

### 3. Download Tick Data (Byte-Range Streaming)

```python
from datetime import datetime, timezone

async def stream_5min_window():
    ucs = UnifiedCloudService()
    target = CloudTarget(
        gcs_bucket='market-data-tick-cefi-central-element-323112',
        bigquery_dataset='market_tick_data'
    )
    
    # Stream only 5-minute window: 4,053 rows (0.13% of file), ~5s
    start_ts = datetime(2023, 5, 23, 0, 0, 0, tzinfo=timezone.utc)
    end_ts = datetime(2023, 5, 23, 0, 5, 0, tzinfo=timezone.utc)
    
    df = await ucs.download_from_gcs_streaming(
        target=target,
        gcs_path='raw_tick_data/by_date/day-2023-05-23/data_type-trades/BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN.parquet',
        timestamp_range=(start_ts, end_ts),
        timestamp_column='ts_event',
        use_byte_range=True
    )
    return df  # Only 4,053 rows instead of 3.2M
```

### 4. Upload Backtest Results

```python
async def save_backtest_results(run_id: str, summary: dict, fills_df, equity_df):
    ucs = UnifiedCloudService()
    target = CloudTarget(
        gcs_bucket='execution-store-cefi-central-element-323112',
        bigquery_dataset='execution'
    )
    
    # Upload summary JSON
    await ucs.upload_to_gcs(
        target=target,
        gcs_path=f'backtest_results/{run_id}/summary.json',
        data=summary,
        format='json'
    )
    
    # Upload fills Parquet
    await ucs.upload_to_gcs(
        target=target,
        gcs_path=f'backtest_results/{run_id}/fills.parquet',
        data=fills_df,
        format='parquet'
    )
    
    # Upload equity curve Parquet
    await ucs.upload_to_gcs(
        target=target,
        gcs_path=f'backtest_results/{run_id}/equity_curve.parquet',
        data=equity_df,
        format='parquet'
    )
```

---

## Integration Points

### 1. Update `requirements.txt`

Add UCS dependency:

```txt
nautilus-trader>=1.220.0
pandas>=2.0.0
pyarrow>=14.0.0
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
git+https://github.com/IggyIkenna/unified-cloud-services.git
```

### 2. Create UCS Service Wrapper

Create `backend/services/ucs_service.py`:

```python
"""Unified Cloud Services wrapper for execution-services."""
import os
from typing import Optional, Dict, Any
from datetime import datetime
import pandas as pd
from unified_cloud_services import UnifiedCloudService, CloudTarget

class UCSService:
    """Wrapper for UCS operations."""
    
    def __init__(self):
        self.ucs = UnifiedCloudService()
    
    def get_instruments_target(self) -> CloudTarget:
        """Get CloudTarget for instruments bucket."""
        return CloudTarget(
            gcs_bucket='instruments-store-cefi-central-element-323112',
            bigquery_dataset='instruments_data'
        )
    
    def get_market_data_target(self) -> CloudTarget:
        """Get CloudTarget for market data bucket."""
        return CloudTarget(
            gcs_bucket='market-data-tick-cefi-central-element-323112',
            bigquery_dataset='market_tick_data'
        )
    
    def get_results_target(self) -> CloudTarget:
        """Get CloudTarget for results bucket."""
        return CloudTarget(
            gcs_bucket='execution-store-cefi-central-element-323112',
            bigquery_dataset='execution'
        )
    
    async def download_instruments(self, date: str) -> pd.DataFrame:
        """Download instrument definitions for a date."""
        target = self.get_instruments_target()
        gcs_path = f'instrument_availability/by_date/day-{date}/instruments.parquet'
        return await self.ucs.download_from_gcs(
            target=target,
            gcs_path=gcs_path,
            format='parquet'
        )
    
    async def download_tick_data(
        self,
        date: str,
        instrument: str,
        data_type: str = 'trades',
        start_ts: Optional[datetime] = None,
        end_ts: Optional[datetime] = None,
        use_streaming: bool = True
    ) -> pd.DataFrame:
        """Download tick data, optionally with byte-range streaming."""
        target = self.get_market_data_target()
        gcs_path = f'raw_tick_data/by_date/day-{date}/data_type-{data_type}/{instrument}.parquet'
        
        if use_streaming and start_ts and end_ts:
            return await self.ucs.download_from_gcs_streaming(
                target=target,
                gcs_path=gcs_path,
                timestamp_range=(start_ts, end_ts),
                timestamp_column='ts_event',
                use_byte_range=True
            )
        else:
            return await self.ucs.download_from_gcs(
                target=target,
                gcs_path=gcs_path,
                format='parquet'
            )
    
    async def upload_result(
        self,
        run_id: str,
        filename: str,
        data: Any,
        format: str = 'json'
    ):
        """Upload a result file to GCS."""
        target = self.get_results_target()
        gcs_path = f'backtest_results/{run_id}/{filename}'
        await self.ucs.upload_to_gcs(
            target=target,
            gcs_path=gcs_path,
            data=data,
            format=format
        )
```

### 3. Update `backend/backtest_engine.py`

Add UCS integration for:
- Loading instruments from GCS
- Downloading tick data with streaming
- Uploading results to GCS

### 4. Update `backend/results.py`

Add Parquet export functions:
- `export_orders_parquet()`
- `export_fills_parquet()`
- `export_positions_parquet()`
- `export_equity_curve_parquet()`

---

## FUSE Mount vs Direct GCS Access

### FUSE Mount (Recommended for Production)

**Advantages:**
- Faster I/O (>200 MB/s)
- No code changes needed (UCS auto-detects)
- Works with existing file-based code

**Setup:**
```bash
# Install ucs-mount
pip install unified-cloud-services[gcsfuse]

# Mount bucket
ucs-mount gs://market-data-tick-cefi-central-element-323112 /app/data_downloads
```

**Code:** No changes needed - UCS auto-detects FUSE mounts.

### Direct GCS Access

**Advantages:**
- No FUSE setup required
- Works in environments without FUSE support
- Better for cloud functions/serverless

**Setup:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
export UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS=true
```

**Code:** Use UCS `download_from_gcs()` and `upload_to_gcs()` methods.

---

## Testing Checklist

- [ ] UCS installed successfully
- [ ] UCS imports without errors
- [ ] Can connect to GCS buckets
- [ ] Can download instrument definitions
- [ ] Can download tick data (full file)
- [ ] Can download tick data (byte-range streaming)
- [ ] Can upload results to GCS
- [ ] FUSE mount detection works (if using FUSE)
- [ ] Direct GCS access works (if not using FUSE)

---

## Troubleshooting

### Import Error

```
ImportError: No module named 'unified_cloud_services'
```

**Solution:**
```bash
pip install git+https://github.com/IggyIkenna/unified-cloud-services.git
```

### GCS Authentication Error

```
google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials
```

**Solution:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### Bucket Not Found

```
404 Bucket not found
```

**Solution:**
- Verify bucket name is correct
- Check GCS permissions
- Ensure service account has Storage Object Viewer/Admin role

### FUSE Mount Not Detected

**Solution:**
- Check mount point: `mount | grep gcsfuse`
- Verify `UNIFIED_CLOUD_LOCAL_PATH` env var points to mount
- UCS should auto-detect, but verify path exists

---

## Next Steps

1. ✅ Install UCS (`bash backend/scripts/setup_ucs.sh`)
2. ✅ Test connection (`python3 backend/scripts/test_ucs_connection.py`)
3. ⏳ Create UCS service wrapper (`backend/services/ucs_service.py`)
4. ⏳ Integrate into `backtest_engine.py` for data loading
5. ⏳ Add Parquet export functions to `results.py`
6. ⏳ Integrate upload functionality into `run_backtest.py`
7. ⏳ Update Dockerfile to include UCS
8. ⏳ Test end-to-end workflow

---

*Last Updated: December 2025*

