#!/usr/bin/env python3
"""
List all available dates and files in GCS bucket.
Shows structure: by_date/day-YYYY-MM-DD/data_type-{trades|book_snapshot_5}/
"""
import os
import sys
from datetime import datetime
from google.cloud import storage
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def list_gcs_structure(bucket_name: str, prefix: str = "raw_tick_data/by_date/"):
    """List all dates and files in GCS bucket."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    print(f"🔍 Listing GCS bucket: {bucket_name}")
    print(f"📁 Prefix: {prefix}\n")
    
    # List all blobs with the prefix
    blobs = bucket.list_blobs(prefix=prefix, delimiter='/')
    
    # Get all prefixes (folders)
    prefixes = set()
    files_by_date = {}
    
    for blob in blobs:
        # Extract date from path: raw_tick_data/by_date/day-2023-05-23/data_type-trades/...
        parts = blob.name.split('/')
        if len(parts) >= 4 and parts[2].startswith('day-'):
            date_str = parts[2]  # day-2023-05-23
            data_type = parts[3]  # data_type-trades or data_type-book_snapshot_5
            
            if date_str not in files_by_date:
                files_by_date[date_str] = {'trades': [], 'book_snapshot_5': []}
            
            if 'trades' in data_type:
                files_by_date[date_str]['trades'].append(blob.name)
            elif 'book_snapshot_5' in data_type:
                files_by_date[date_str]['book_snapshot_5'].append(blob.name)
    
    # Also get prefixes (folders)
    blobs_with_prefix = bucket.list_blobs(prefix=prefix, delimiter='/')
    for page in blobs_with_prefix.pages:
        for prefix_name in page.prefixes:
            if 'day-' in prefix_name:
                date_str = prefix_name.split('/')[-2] if prefix_name.endswith('/') else prefix_name.split('/')[-1]
                prefixes.add(date_str)
    
    # Sort dates
    sorted_dates = sorted(files_by_date.keys())
    
    print(f"📅 Found {len(sorted_dates)} date(s) with data:\n")
    
    for date_str in sorted_dates:
        print(f"\n{'='*80}")
        print(f"📆 {date_str}")
        print(f"{'='*80}")
        
        trades_files = files_by_date[date_str]['trades']
        book_files = files_by_date[date_str]['book_snapshot_5']
        
        print(f"\n📊 TRADES ({len(trades_files)} file(s)):")
        print(f"   Path: {prefix}{date_str}/data_type-trades/")
        for f in sorted(trades_files):
            filename = f.split('/')[-1]
            print(f"   - {filename}")
        
        print(f"\n📚 BOOK SNAPSHOT 5 ({len(book_files)} file(s)):")
        print(f"   Path: {prefix}{date_str}/data_type-book_snapshot_5/")
        for f in sorted(book_files):
            filename = f.split('/')[-1]
            print(f"   - {filename}")
    
    # Check specifically for May 26
    may26 = 'day-2023-05-26'
    print(f"\n\n{'='*80}")
    print(f"🔍 Checking for {may26}:")
    print(f"{'='*80}")
    
    if may26 in files_by_date:
        print(f"✅ {may26} EXISTS")
        print(f"   Trades: {len(files_by_date[may26]['trades'])} file(s)")
        print(f"   Book: {len(files_by_date[may26]['book_snapshot_5'])} file(s)")
    else:
        print(f"❌ {may26} NOT FOUND")
    
    # Check May 23 specifically
    may23 = 'day-2023-05-23'
    print(f"\n\n{'='*80}")
    print(f"🔍 Detailed listing for {may23}:")
    print(f"{'='*80}")
    
    if may23 in files_by_date:
        print(f"✅ {may23} EXISTS")
        print(f"\n📊 TRADES files ({len(files_by_date[may23]['trades'])}):")
        for f in sorted(files_by_date[may23]['trades']):
            print(f"   {f}")
        print(f"\n📚 BOOK SNAPSHOT 5 files ({len(files_by_date[may23]['book_snapshot_5'])}):")
        for f in sorted(files_by_date[may23]['book_snapshot_5']):
            print(f"   {f}")
    else:
        print(f"❌ {may23} NOT FOUND")
    
    return files_by_date


if __name__ == "__main__":
    bucket_name = os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET") or os.getenv("GCS_BUCKET")
    
    if not bucket_name:
        print("❌ Error: UNIFIED_CLOUD_SERVICES_GCS_BUCKET or GCS_BUCKET not set")
        sys.exit(1)
    
    print(f"Using bucket: {bucket_name}\n")
    
    try:
        list_gcs_structure(bucket_name)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

