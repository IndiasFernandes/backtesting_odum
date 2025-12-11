"""
Quick script to check actual GCS paths and compare with what we're searching for.
Run this in the container to verify path structure.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from google.cloud import storage
except ImportError:
    print("❌ google-cloud-storage not available")
    sys.exit(1)


def check_gcs_paths():
    """Check actual GCS paths."""
    
    bucket_name = os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET")
    if not bucket_name:
        print("❌ UNIFIED_CLOUD_SERVICES_GCS_BUCKET not set")
        return
    
    print(f"📦 Bucket: {bucket_name}\n")
    
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    # Check May 23, 2023
    date_str = "2023-05-23"
    prefix = f"raw_tick_data/by_date/day-{date_str}/"
    
    print(f"🔍 Listing files with prefix: {prefix}\n")
    
    blobs = list(bucket.list_blobs(prefix=prefix, max_results=50))
    
    if not blobs:
        print(f"❌ No files found")
        return
    
    print(f"✅ Found {len(blobs)} files\n")
    
    # Group by type
    trades = [b for b in blobs if "data_type-trades" in b.name]
    book = [b for b in blobs if "data_type-book" in b.name]
    
    print(f"📊 Breakdown:")
    print(f"   Trades: {len(trades)}")
    print(f"   Book: {len(book)}\n")
    
    # Show actual filenames
    print(f"📋 Actual Trades Filenames:\n")
    for blob in trades[:10]:
        filename = blob.name.split("/")[-1]
        print(f"   {filename}")
    
    print(f"\n📋 Actual Book Filenames:\n")
    for blob in book[:10]:
        filename = blob.name.split("/")[-1]
        print(f"   {filename}")
    
    # Analyze pattern
    if trades:
        sample = trades[0].name.split("/")[-1]
        print(f"\n🔍 Pattern Analysis:\n")
        print(f"   Sample filename: {sample}")
        print(f"   Has colons (:): {':' in sample}")
        print(f"   Has @ symbol: {'@' in sample}")
        print(f"   URL-encoded: {'%3A' in sample or '%40' in sample}")
        
        # Extract instrument part
        instrument_part = sample.replace(".parquet", "")
        print(f"   Instrument ID: {instrument_part}")
        
        # Check what we're searching for
        print(f"\n🔍 What we're searching for:\n")
        
        # Test different formats
        test_formats = [
            ("BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN", "Full with @LIN"),
            ("BINANCE-FUTURES:PERPETUAL:BTC-USDT", "Without @LIN"),
            ("BINANCE-FUTURES%3APERPETUAL%3ABTC-USDT%40LIN", "URL-encoded full"),
            ("BINANCE-FUTURES%3APERPETUAL%3ABTC-USDT", "URL-encoded no suffix"),
        ]
        
        for inst_id, desc in test_formats:
            # Build expected path
            trades_dir = f"raw_tick_data/by_date/day-{date_str}/data_type-trades/"
            expected_path = trades_dir + inst_id + ".parquet"
            
            # Check if exists
            blob = bucket.blob(expected_path)
            exists = blob.exists()
            status = "✅" if exists else "❌"
            print(f"   {status} {desc}: {inst_id}")
            if exists:
                print(f"      Path: {expected_path}")
                print(f"      Size: {blob.size / 1024 / 1024:.2f} MB")
    
    print(f"\n{'='*70}\n")
    print(f"📝 Summary:")
    print(f"   Use the format that matches the actual filenames above")


if __name__ == "__main__":
    check_gcs_paths()

