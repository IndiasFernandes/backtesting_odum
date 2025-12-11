"""
List actual files in GCS bucket for May 23, 2023 to see what exists.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from google.cloud import storage

def list_gcs_files():
    """List files in GCS for May 23, 2023."""
    
    bucket_name = os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET")
    if not bucket_name:
        print("❌ UNIFIED_CLOUD_SERVICES_GCS_BUCKET not set")
        return
    
    print(f"📦 Bucket: {bucket_name}\n")
    
    date_str = "2023-05-23"
    
    # Initialize GCS client
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    # List all files for this date
    prefix = f"raw_tick_data/by_date/day-{date_str}/"
    print(f"🔍 Listing files with prefix: {prefix}\n")
    
    blobs = list(bucket.list_blobs(prefix=prefix))
    
    if not blobs:
        print(f"❌ No files found with prefix: {prefix}")
        
        # Try listing parent directory
        parent_prefix = "raw_tick_data/by_date/"
        print(f"\n🔍 Trying parent directory: {parent_prefix}")
        parent_blobs = list(bucket.list_blobs(prefix=parent_prefix, max_results=20))
        if parent_blobs:
            print(f"   Found {len(parent_blobs)} file(s) in parent:")
            for b in parent_blobs[:10]:
                print(f"      {b.name}")
        return
    
    print(f"✅ Found {len(blobs)} file(s)\n")
    
    # Group by data type
    trades_files = []
    book_files = []
    other_files = []
    
    for blob in blobs:
        if "data_type-trades" in blob.name:
            trades_files.append(blob)
        elif "data_type-book" in blob.name:
            book_files.append(blob)
        else:
            other_files.append(blob)
    
    print(f"📊 Breakdown:")
    print(f"   Trades: {len(trades_files)}")
    print(f"   Book: {len(book_files)}")
    print(f"   Other: {len(other_files)}\n")
    
    # Show trades files
    if trades_files:
        print(f"📋 Trades Files ({len(trades_files)}):\n")
        for blob in trades_files[:10]:
            filename = blob.name.split("/")[-1]
            print(f"   {filename}")
            print(f"      Full path: {blob.name}")
            print(f"      Size: {blob.size / 1024 / 1024:.2f} MB")
        
        if len(trades_files) > 10:
            print(f"   ... and {len(trades_files) - 10} more")
    
    # Show book files
    if book_files:
        print(f"\n📋 Book Files ({len(book_files)}):\n")
        for blob in book_files[:10]:
            filename = blob.name.split("/")[-1]
            print(f"   {filename}")
            print(f"      Full path: {blob.name}")
            print(f"      Size: {blob.size / 1024 / 1024:.2f} MB")
        
        if len(book_files) > 10:
            print(f"   ... and {len(book_files) - 10} more")
    
    # Check specific expected path
    print(f"\n🔍 Checking expected paths:\n")
    
    expected_paths = [
        f"raw_tick_data/by_date/day-{date_str}/data_type-trades/BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN.parquet",
        f"raw_tick_data/by_date/day-{date_str}/data_type-trades/BINANCE-FUTURES:PERPETUAL:BTC-USDT.parquet",
        f"raw_tick_data/by_date/day-{date_str}/data_type-trades/BINANCE-FUTURES%3APERPETUAL%3ABTC-USDT%40LIN.parquet",
    ]
    
    for expected_path in expected_paths:
        blob = bucket.blob(expected_path)
        exists = blob.exists()
        status = "✅ EXISTS" if exists else "❌ NOT FOUND"
        print(f"   {status}: {expected_path}")
        if exists:
            print(f"      Size: {blob.size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    list_gcs_files()

