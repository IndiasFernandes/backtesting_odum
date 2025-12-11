"""
Verify GCS bucket structure matches local folder organization.

Downloads one day of data and checks the actual GCS paths.
"""
import asyncio
import os
from datetime import date
from pathlib import Path

try:
    from unified_cloud_services import UnifiedCloudService, CloudTarget
    UCS_AVAILABLE = True
except ImportError:
    UCS_AVAILABLE = False
    print("❌ unified-cloud-services not installed")
    exit(1)


async def verify_gcs_structure():
    """Verify GCS bucket structure matches expected paths."""
    
    # Get bucket name from env
    bucket_name = os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET")
    if not bucket_name:
        print("❌ UNIFIED_CLOUD_SERVICES_GCS_BUCKET not set")
        print("   Set it in .env file or environment")
        return
    
    print(f"📦 GCS Bucket: {bucket_name}")
    print(f"{'='*60}\n")
    
    # Initialize UCS
    ucs = UnifiedCloudService()
    target = CloudTarget(
        gcs_bucket=bucket_name,
        bigquery_dataset="market_data"
    )
    
    # Test instrument ID (try both formats)
    instrument_id_full = "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN"
    instrument_id_no_suffix = "BINANCE-FUTURES:PERPETUAL:BTC-USDT"
    test_date = date(2023, 5, 23)
    date_str = test_date.strftime("%Y-%m-%d")
    
    print(f"🔍 Checking structure for:")
    print(f"   Date: {date_str}")
    print(f"   Instrument (full): {instrument_id_full}")
    print(f"   Instrument (no suffix): {instrument_id_no_suffix}")
    print(f"\n{'='*60}\n")
    
    # Expected paths (what we're searching for)
    expected_paths = {
        "trades_encoded_full": f"raw_tick_data/by_date/day-{date_str}/data_type-trades/{instrument_id_full.replace(':', '%3A').replace('@', '%40')}.parquet",
        "trades_raw_full": f"raw_tick_data/by_date/day-{date_str}/data_type-trades/{instrument_id_full}.parquet",
        "trades_encoded_no_suffix": f"raw_tick_data/by_date/day-{date_str}/data_type-trades/{instrument_id_no_suffix.replace(':', '%3A')}.parquet",
        "trades_raw_no_suffix": f"raw_tick_data/by_date/day-{date_str}/data_type-trades/{instrument_id_no_suffix}.parquet",
        "book_encoded_full": f"raw_tick_data/by_date/day-{date_str}/data_type-book_snapshot_5/{instrument_id_full.replace(':', '%3A').replace('@', '%40')}.parquet",
        "book_raw_full": f"raw_tick_data/by_date/day-{date_str}/data_type-book_snapshot_5/{instrument_id_full}.parquet",
        "book_encoded_no_suffix": f"raw_tick_data/by_date/day-{date_str}/data_type-book_snapshot_5/{instrument_id_no_suffix.replace(':', '%3A')}.parquet",
        "book_raw_no_suffix": f"raw_tick_data/by_date/day-{date_str}/data_type-book_snapshot_5/{instrument_id_no_suffix}.parquet",
    }
    
    print("📋 Expected GCS Paths:\n")
    for name, path in expected_paths.items():
        print(f"   {name}:")
        print(f"      {path}")
    
    print(f"\n{'='*60}\n")
    print("🔍 Checking which paths actually exist in GCS...\n")
    
    # Check each path
    found_paths = {}
    for name, gcs_path in expected_paths.items():
        try:
            # Try to check if file exists using GCS client
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(gcs_path)
            
            if blob.exists():
                found_paths[name] = True
                print(f"   ✅ {name}: EXISTS")
                print(f"      Size: {blob.size / 1024 / 1024:.2f} MB")
            else:
                found_paths[name] = False
                print(f"   ❌ {name}: NOT FOUND")
        except Exception as e:
            found_paths[name] = False
            error_msg = str(e)
            if "404" in error_msg or "No such object" in error_msg:
                print(f"   ❌ {name}: NOT FOUND")
            else:
                print(f"   ⚠️  {name}: ERROR - {error_msg[:100]}")
    
    print(f"\n{'='*60}\n")
    
    # List actual files in the directory
    print("📂 Listing actual files in GCS bucket...\n")
    
    prefix = f"raw_tick_data/by_date/day-{date_str}/data_type-trades/"
    print(f"   Prefix: {prefix}\n")
    
    try:
        # List files in the trades directory
        # Note: UCS might have a list method, but for now we'll try to discover
        # by attempting common patterns
        
        # Try to list using GCS client directly if available
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        blobs = list(bucket.list_blobs(prefix=prefix, max_results=20))
        if blobs:
            print(f"   Found {len(blobs)} file(s) in trades directory:\n")
            for blob in blobs:
                print(f"      {blob.name}")
        else:
            print(f"   ❌ No files found with prefix: {prefix}")
            print(f"   Trying alternative prefixes...\n")
            
            # Try listing the day directory
            day_prefix = f"raw_tick_data/by_date/day-{date_str}/"
            day_blobs = list(bucket.list_blobs(prefix=day_prefix, max_results=50))
            if day_blobs:
                print(f"   Found {len(day_blobs)} file(s) in day directory:\n")
                for blob in day_blobs[:10]:  # Show first 10
                    print(f"      {blob.name}")
                if len(day_blobs) > 10:
                    print(f"      ... and {len(day_blobs) - 10} more")
            else:
                print(f"   ❌ No files found in day directory either")
                
    except Exception as e:
        print(f"   ⚠️  Error listing files: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*60}\n")
    print("📊 Summary:\n")
    
    trades_found = any(found_paths.get(k, False) for k in found_paths.keys() if "trades" in k)
    book_found = any(found_paths.get(k, False) for k in found_paths.keys() if "book" in k)
    
    print(f"   Trades data: {'✅ FOUND' if trades_found else '❌ NOT FOUND'}")
    print(f"   Book data: {'✅ FOUND' if book_found else '❌ NOT FOUND'}")
    
    if not trades_found and not book_found:
        print(f"\n⚠️  No data found with expected paths.")
        print(f"   Check:")
        print(f"   1. Bucket name is correct: {bucket_name}")
        print(f"   2. Date exists: {date_str}")
        print(f"   3. File naming convention matches")
        print(f"   4. Service account has read permissions")


if __name__ == "__main__":
    asyncio.run(verify_gcs_structure())

