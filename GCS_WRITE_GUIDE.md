# GCS Bucket Write Guide

## ✅ Good News: Write Permissions Are Working!

I tested your setup and **you CAN write to the GCS bucket**. The service account has the necessary permissions.

## Common Issues and Solutions

### Issue 1: Trying to Write to Read-Only Mounted Volume

**Problem**: The `data_downloads` directory is mounted as **read-only** (`:ro`) in `docker-compose.yml`:

```yaml
volumes:
  - ./data_downloads:/app/data_downloads:ro  # ← READ-ONLY!
```

**Solution**: Use the GCS API directly instead of trying to write to the mounted directory.

### Issue 2: Writing Through FUSE Mount

**Problem**: If using GCS FUSE mount, you need proper permissions and mount options.

**Solution**: Use unified-cloud-services API methods instead.

## How to Write to GCS Bucket

### Method 1: Using unified-cloud-services (Recommended)

```python
from unified_cloud_services import UnifiedCloudService, CloudTarget
import pandas as pd
from pathlib import Path

# Initialize UCS
ucs = UnifiedCloudService()
target = CloudTarget(
    gcs_bucket="market-data-tick-cefi-central-element-323112",
    bigquery_dataset="market_data"
)

# Upload a DataFrame
df = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6]})
gcs_path = "backtest_results/my_results.parquet"

# Upload using UCS
standardized_service = ucs.get_standardized_service(target)
standardized_service.upload_to_gcs(
    data=df,
    gcs_path=gcs_path,
    format="parquet"  # or "json", "csv", etc.
)
```

### Method 2: Using Google Cloud Storage Client Directly

```python
from google.cloud import storage
import pandas as pd

# Initialize client
client = storage.Client()
bucket = client.bucket("market-data-tick-cefi-central-element-323112")

# Upload a file
blob = bucket.blob("backtest_results/my_results.parquet")
df = pd.DataFrame({"col1": [1, 2, 3]})
blob.upload_from_string(
    df.to_parquet(index=False),
    content_type="application/octet-stream"
)
```

### Method 3: Upload Backtest Results to GCS

Create a helper function to upload backtest results:

```python
# backend/gcs_uploader.py
import os
from pathlib import Path
from google.cloud import storage
from typing import Dict, Any
import json

class GCSUploader:
    """Upload backtest results to GCS bucket."""
    
    def __init__(self, bucket_name: str = None):
        self.bucket_name = bucket_name or os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET")
        if not self.bucket_name:
            raise ValueError("GCS bucket name not provided")
        
        self.client = storage.Client()
        self.bucket = self.client.bucket(self.bucket_name)
    
    def upload_backtest_result(self, result: Dict[str, Any], run_id: str) -> str:
        """
        Upload backtest result JSON to GCS.
        
        Args:
            result: Backtest result dictionary
            run_id: Unique run identifier
            
        Returns:
            GCS path where file was uploaded
        """
        gcs_path = f"backtest_results/{run_id}/summary.json"
        blob = self.bucket.blob(gcs_path)
        
        # Upload JSON
        blob.upload_from_string(
            json.dumps(result, indent=2, default=str),
            content_type="application/json"
        )
        
        print(f"✅ Uploaded backtest result to: gs://{self.bucket_name}/{gcs_path}")
        return gcs_path
    
    def upload_file(self, local_path: Path, gcs_path: str) -> str:
        """
        Upload a local file to GCS.
        
        Args:
            local_path: Local file path
            gcs_path: GCS destination path
            
        Returns:
            GCS path where file was uploaded
        """
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_filename(str(local_path))
        
        print(f"✅ Uploaded file to: gs://{self.bucket_name}/{gcs_path}")
        return gcs_path
```

### Method 4: Using unified-cloud-services Standardized Service

```python
from unified_cloud_services.domain.standardized_service import StandardizedDomainCloudService
from unified_cloud_services.core.cloud_config import CloudTarget
import pandas as pd

# Create standardized service
target = CloudTarget(
    gcs_bucket="market-data-tick-cefi-central-element-323112",
    bigquery_dataset="market_data"
)

service = StandardizedDomainCloudService(
    domain="market_data",
    cloud_target=target
)

# Upload data
df = pd.DataFrame({"data": [1, 2, 3]})
service.upload_to_gcs(
    data=df,
    gcs_path="backtest_results/test.parquet",
    format="parquet"
)
```

## Required IAM Permissions

Your service account needs these permissions:

- ✅ `storage.objects.create` - Create/upload objects
- ✅ `storage.objects.delete` - Delete objects (for overwrites)
- ✅ `storage.objects.get` - Read objects
- ✅ `storage.objects.list` - List objects

**Roles that include these permissions:**
- `roles/storage.objectAdmin` (full control)
- `roles/storage.objectCreator` (create only)
- `roles/storage.admin` (bucket admin)

## Testing Write Permissions

Run this test to verify write access:

```bash
docker-compose exec backend python3 -c "
from google.cloud import storage
import os

bucket_name = os.getenv('UNIFIED_CLOUD_SERVICES_GCS_BUCKET')
client = storage.Client()
bucket = client.bucket(bucket_name)

# Test write
blob = bucket.blob('test_write_permission.txt')
blob.upload_from_string('test', content_type='text/plain')
print('✅ Write test: SUCCESS')

# Clean up
blob.delete()
print('✅ Cleanup: Deleted test file')
"
```

## Common Write Scenarios

### 1. Upload Backtest Results

```python
from backend.gcs_uploader import GCSUploader

uploader = GCSUploader()
uploader.upload_backtest_result(result_dict, run_id="test-001")
```

### 2. Upload Parquet Files

```python
import pandas as pd
from google.cloud import storage

df = pd.read_parquet("local_file.parquet")
client = storage.Client()
bucket = client.bucket("market-data-tick-cefi-central-element-323112")
blob = bucket.blob("data/my_data.parquet")
blob.upload_from_string(df.to_parquet(index=False))
```

### 3. Upload JSON Files

```python
import json
from google.cloud import storage

data = {"key": "value"}
client = storage.Client()
bucket = client.bucket("market-data-tick-cefi-central-element-323112")
blob = bucket.blob("results/data.json")
blob.upload_from_string(json.dumps(data), content_type="application/json")
```

## Why You Can't Write to `/app/data_downloads`

The `data_downloads` directory is mounted as **read-only** (`:ro`) because:

1. **It's meant for reading market data** - not writing
2. **Prevents accidental overwrites** of source data
3. **Follows best practices** - separate read and write paths

**Write to these locations instead:**
- `backend/data/parquet/` - For catalog data (local)
- `backend/backtest_results/` - For backtest results (local)
- **GCS bucket directly** - For cloud storage (use API)

## Integration Example: Upload Backtest Results

Add this to `backend/api/server.py`:

```python
from backend.gcs_uploader import GCSUploader

def _run_backtest_sync(request: BacktestRunRequest, log_queue: queue.Queue):
    # ... existing backtest code ...
    
    # After backtest completes
    if result:
        # Save locally (existing code)
        ResultSerializer.save_fast(result, output_dir)
        
        # Upload to GCS (new)
        try:
            uploader = GCSUploader()
            uploader.upload_backtest_result(result, result['run_id'])
        except Exception as e:
            print(f"⚠️  Failed to upload to GCS: {e}")
            # Don't fail the backtest if upload fails
```

## Troubleshooting

### Error: "Permission denied"
- ✅ Check service account has `storage.objects.create` permission
- ✅ Verify `GOOGLE_APPLICATION_CREDENTIALS` points to correct file
- ✅ Check bucket name is correct

### Error: "Bucket not found"
- ✅ Verify bucket name: `market-data-tick-cefi-central-element-323112`
- ✅ Check `UNIFIED_CLOUD_SERVICES_GCS_BUCKET` env var

### Error: "Cannot write to mounted directory"
- ✅ Don't write to `/app/data_downloads` (it's read-only)
- ✅ Use GCS API methods instead
- ✅ Write to local paths first, then upload

## Summary

✅ **You CAN write to GCS** - permissions are correct
✅ **Use GCS API** - don't try to write to mounted volumes
✅ **Use unified-cloud-services** - recommended method
✅ **Write locally first** - then upload to GCS if needed

The key is to use the **GCS API** (via `google.cloud.storage` or `unified-cloud-services`) rather than trying to write to the mounted filesystem.

