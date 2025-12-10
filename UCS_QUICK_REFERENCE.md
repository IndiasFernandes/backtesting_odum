# UCS Quick Reference

## Installation

```bash
# Quick install
bash backend/scripts/setup_ucs.sh

# Or manual
pip install git+https://github.com/IggyIkenna/unified-cloud-services.git
```

## Test Connection

```bash
# Basic test
python3 backend/scripts/test_ucs_connection.py

# Full test with upload
python3 backend/scripts/test_ucs_connection.py --test-upload
```

## Basic Usage

```python
from unified_cloud_services import UnifiedCloudService, CloudTarget
import asyncio

# Initialize
ucs = UnifiedCloudService()
target = CloudTarget(
    gcs_bucket='your-bucket-name',
    bigquery_dataset='dataset_name'
)

# Download
df = await ucs.download_from_gcs(
    target=target,
    gcs_path='path/to/file.parquet',
    format='parquet'
)

# Upload
await ucs.upload_to_gcs(
    target=target,
    gcs_path='path/to/output.json',
    data={'key': 'value'},
    format='json'
)
```

## Buckets

- **Instruments**: `instruments-store-cefi-central-element-323112`
- **Market Data**: `market-data-tick-cefi-central-element-323112`
- **Results**: `execution-store-cefi-central-element-323112`

## Key Points

✅ **Auto-detects FUSE mounts** - No code changes needed  
✅ **Works with local files** - Falls back automatically  
✅ **Supports streaming** - Byte-range for large files  

## Docs

- Full Guide: `UCS_INTEGRATION_GUIDE.md`
- Setup Summary: `UCS_SETUP_SUMMARY.md`

