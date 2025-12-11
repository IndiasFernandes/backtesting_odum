"""
Download one day of data from GCS and verify the structure matches local organization.

This script:
1. Lists actual files in GCS for a given date
2. Downloads one file to verify it works
3. Compares GCS structure with local structure
"""
import asyncio
import os
import sys
from datetime import date
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from unified_cloud_services import UnifiedCloudService, CloudTarget
    from google.cloud import storage
    UCS_AVAILABLE = True
except ImportError:
    UCS_AVAILABLE = False
    print("❌ unified-cloud-services or google-cloud-storage not installed")
    exit(1)


async def download_and_verify():
    """Download one day and verify structure."""
    
    # Get bucket name from env
    bucket_name = os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET")
    if not bucket_name:
        print("❌ UNIFIED_CLOUD_SERVICES_GCS_BUCKET not set")
        print("   Set it in .env file or environment")
        return
    
    print(f"📦 GCS Bucket: {bucket_name}")
    print(f"{'='*70}\n")
    
    # Test date
    test_date = date(2023, 5, 23)
    date_str = test_date.strftime("%Y-%m-%d")
    
    print(f"🔍 Verifying structure for date: {date_str}\n")
    
    # Initialize GCS client
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    # List all files in the day directory
    day_prefix = f"raw_tick_data/by_date/day-{date_str}/"
    print(f"📂 Listing files with prefix: {day_prefix}\n")
    
    blobs = list(bucket.list_blobs(prefix=day_prefix, max_results=100))
    
    if not blobs:
        print(f"❌ No files found with prefix: {day_prefix}")
        print(f"   Check:")
        print(f"   1. Date exists in bucket: {date_str}")
        print(f"   2. Bucket name is correct: {bucket_name}")
        print(f"   3. Service account has read permissions")
        return
    
    print(f"✅ Found {len(blobs)} file(s)\n")
    
    # Group by data type
    trades_files = []
    book_files = []
    other_files = []
    
    for blob in blobs:
        if "data_type-trades" in blob.name:
            trades_files.append(blob)
        elif "data_type-book_snapshot" in blob.name:
            book_files.append(blob)
        else:
            other_files.append(blob)
    
    print(f"📊 File breakdown:")
    print(f"   Trades: {len(trades_files)}")
    print(f"   Book snapshots: {len(book_files)}")
    print(f"   Other: {len(other_files)}\n")
    
    # Show sample files
    print(f"📋 Sample Trades Files (first 5):\n")
    for blob in trades_files[:5]:
        filename = blob.name.split("/")[-1]
        print(f"   {filename}")
        print(f"      Full path: {blob.name}")
        print(f"      Size: {blob.size / 1024 / 1024:.2f} MB")
    
    if len(trades_files) > 5:
        print(f"   ... and {len(trades_files) - 5} more trades files")
    
    print(f"\n📋 Sample Book Snapshot Files (first 5):\n")
    for blob in book_files[:5]:
        filename = blob.name.split("/")[-1]
        print(f"   {filename}")
        print(f"      Full path: {blob.name}")
        print(f"      Size: {blob.size / 1024 / 1024:.2f} MB")
    
    if len(book_files) > 5:
        print(f"   ... and {len(book_files) - 5} more book files")
    
    print(f"\n{'='*70}\n")
    
    # Analyze filename patterns
    print(f"🔍 Analyzing filename patterns...\n")
    
    if trades_files:
        sample_trades = trades_files[0].name.split("/")[-1]
        print(f"   Sample trades filename: {sample_trades}")
        
        # Check for patterns
        has_colons = ":" in sample_trades
        has_at_symbol = "@" in sample_trades
        has_encoded = "%3A" in sample_trades or "%40" in sample_trades
        
        print(f"   Contains colons (:): {has_colons}")
        print(f"   Contains @ symbol: {has_at_symbol}")
        print(f"   URL-encoded: {has_encoded}")
        
        # Extract instrument ID pattern
        instrument_part = sample_trades.replace(".parquet", "")
        print(f"   Instrument ID pattern: {instrument_part}")
    
    if book_files:
        sample_book = book_files[0].name.split("/")[-1]
        print(f"\n   Sample book filename: {sample_book}")
    
    print(f"\n{'='*70}\n")
    
    # Compare with local structure
    print(f"📂 Comparing with local structure...\n")
    
    local_base = Path(os.getenv("UNIFIED_CLOUD_LOCAL_PATH", "/app/data_downloads"))
    local_day_dir = local_base / "raw_tick_data" / "by_date" / f"day-{date_str}"
    
    if local_day_dir.exists():
        print(f"   ✅ Local directory exists: {local_day_dir}\n")
        
        # List local files
        local_trades_dir = local_day_dir / "data_type-trades"
        local_book_dir = local_day_dir / "data_type-book_snapshot_5"
        
        if local_trades_dir.exists():
            local_trades_files = list(local_trades_dir.glob("*.parquet"))
            print(f"   Local trades files: {len(local_trades_files)}")
            if local_trades_files:
                print(f"      Sample: {local_trades_files[0].name}")
        
        if local_book_dir.exists():
            local_book_files = list(local_book_dir.glob("*.parquet"))
            print(f"   Local book files: {len(local_book_files)}")
            if local_book_files:
                print(f"      Sample: {local_book_files[0].name}")
    else:
        print(f"   ⚠️  Local directory not found: {local_day_dir}")
        print(f"      (This is OK if you're only using GCS)")
    
    print(f"\n{'='*70}\n")
    
    # Download one file to verify it works
    if trades_files:
        print(f"📥 Downloading sample file to verify...\n")
        
        sample_blob = trades_files[0]
        print(f"   File: {sample_blob.name}")
        print(f"   Size: {sample_blob.size / 1024 / 1024:.2f} MB\n")
        
        try:
            # Initialize UCS
            ucs = UnifiedCloudService()
            target = CloudTarget(
                gcs_bucket=bucket_name,
                bigquery_dataset="market_data"
            )
            
            # Download first 100 rows to verify
            print(f"   Downloading first 100 rows...")
            import pandas as pd
            
            # Use GCS client to download directly
            blob_data = sample_blob.download_as_bytes()
            import io
            df = pd.read_parquet(io.BytesIO(blob_data))
            
            # Limit to 100 rows for verification
            df_sample = df.head(100)
            
            print(f"   ✅ Download successful!")
            print(f"      Total rows in file: {len(df):,}")
            print(f"      Sample rows: {len(df_sample):,}")
            print(f"      Columns: {list(df.columns)}")
            
            if 'ts_event' in df.columns:
                df['ts_event_dt'] = pd.to_datetime(df['ts_event'], unit='ns')
                print(f"      Time range: {df['ts_event_dt'].min()} to {df['ts_event_dt'].max()}")
            
            print(f"\n   📊 Sample data (first 3 rows):")
            print(df_sample.head(3).to_string())
            
        except Exception as e:
            print(f"   ❌ Download failed: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*70}\n")
    print(f"✅ Verification complete!")
    print(f"\n📝 Key findings:")
    print(f"   1. GCS structure: raw_tick_data/by_date/day-YYYY-MM-DD/data_type-{'{trades|book_snapshot_5}'}/FILENAME.parquet")
    if trades_files:
        sample = trades_files[0].name.split("/")[-1]
        print(f"   2. Filename format: {sample}")
        print(f"   3. Use this format when building GCS paths in code")


if __name__ == "__main__":
    # Load .env if available
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
    
    asyncio.run(download_and_verify())

