# Test UCS Connection First

**IMPORTANT:** Test UCS connection before integrating into the main codebase.

---

## Do You Need to Clone the Repo?

**NO!** You don't need to clone the `unified-cloud-services` repository.

**Just install it via pip:**
```bash
pip install git+https://github.com/IggyIkenna/unified-cloud-services.git
```

The package is installable directly from GitHub - no cloning needed!

---

## Step 1: Install UCS

```bash
cd /Users/indiasfernandes/New\ Ikenna\ Repo/execution-services/data_downloads

# Option A: Install UCS only
pip install git+https://github.com/IggyIkenna/unified-cloud-services.git

# Option B: Install all dependencies (including UCS)
pip install -r backend/requirements.txt
```

**Verify installation:**
```bash
python3 -c "from unified_cloud_services import UnifiedCloudService; print('✅ UCS installed')"
```

---

## Step 2: Verify Environment Variables

Make sure your `.env` file is set up:

```bash
# Check if .env exists
cat .env

# Should contain:
# GCP_PROJECT_ID=central-element-323112
# GOOGLE_APPLICATION_CREDENTIALS=.secrets/gcs/gcs-service-account.json
# UNIFIED_CLOUD_SERVICES_GCS_BUCKET=market-data-tick-cefi-central-element-323112
# GCS_BUCKET=execution-store-cefi-central-element-323112
```

---

## Step 3: Verify Credentials

```bash
# Check if credentials file exists
ls -la .secrets/gcs/gcs-service-account.json

# Should show the file exists and is readable
```

---

## Step 4: Run Test Script

```bash
# Basic connectivity test (read-only)
python3 backend/scripts/test_ucs_connection.py

# Test with specific bucket
python3 backend/scripts/test_ucs_connection.py --bucket market-data-tick-cefi-central-element-323112

# Test upload functionality (requires write permissions)
python3 backend/scripts/test_ucs_connection.py --test-upload

# Test all buckets
python3 backend/scripts/test_ucs_connection.py \
  --instruments-bucket instruments-store-cefi-central-element-323112 \
  --market-data-bucket market-data-tick-cefi-central-element-323112
```

---

## Expected Output

If everything works, you should see:

```
============================================================
TEST 1: UCS Import
============================================================
✅ SUCCESS: UCS imported successfully
   UnifiedCloudService: <class 'unified_cloud_services.core.unified_cloud_service.UnifiedCloudService'>
   CloudTarget: <class 'unified_cloud_services.core.cloud_config.CloudTarget'>

============================================================
TEST 2: FUSE Mount Detection
============================================================
⚠️  WARNING: Local path does not exist: /app/data_downloads
   This is OK if using direct GCS access

============================================================
TEST 3: GCS Bucket Connectivity
============================================================
   Testing bucket: execution-store-cefi-central-element-323112
✅ SUCCESS: Can list files in bucket
   Found 5 files (showing first 5)
      - backtest_results/...
```

---

## Troubleshooting

### Error: "No module named 'unified_cloud_services'"

**Solution:**
```bash
pip install git+https://github.com/IggyIkenna/unified-cloud-services.git
```

### Error: "Could not find credentials"

**Solution:**
1. Check `.env` file exists
2. Check `GOOGLE_APPLICATION_CREDENTIALS` points to correct file
3. Verify `.secrets/gcs/gcs-service-account.json` exists

```bash
# Check environment variable
echo $GOOGLE_APPLICATION_CREDENTIALS

# Or load from .env
export $(cat .env | xargs)
```

### Error: "Permission denied" or "403 Forbidden"

**Solution:**
- Service account needs proper IAM permissions
- Check service account has:
  - `Storage Object Viewer` (for downloads)
  - `Storage Object Creator` (for uploads)

---

## What the Test Script Does

1. **Test 1: UCS Import** - Verifies UCS is installed
2. **Test 2: FUSE Detection** - Checks for GCS FUSE mounts (optional)
3. **Test 3: GCS Connectivity** - Tests bucket access
4. **Test 4: Instrument Download** - Downloads sample instruments
5. **Test 5: Tick Data Streaming** - Tests byte-range streaming
6. **Test 6: Results Upload** - Tests uploading results (if `--test-upload`)

---

## Next Steps

Once tests pass:

1. ✅ UCS is installed and working
2. ✅ Credentials are configured correctly
3. ✅ Buckets are accessible
4. ✅ Ready to integrate into `backtest_engine.py` and `results.py`

---

## Quick Test Command

```bash
# One-liner to test everything
python3 backend/scripts/test_ucs_connection.py --test-upload
```

This will test:
- UCS installation ✅
- GCS connectivity ✅
- Download capabilities ✅
- Upload capabilities ✅

