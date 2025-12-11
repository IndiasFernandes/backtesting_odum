"""
Test script to verify GCS file exists for May 23, 2023.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.api.data_checker import _convert_instrument_id_to_gcs_format
from backend.data.loader import UCSDataLoader

async def test_gcs_file():
    """Test if GCS file exists."""
    
    # Test parameters
    config_instrument_id = "BTC-USDT.BINANCE"
    date_str = "2023-05-23"
    
    print(f"🔍 Testing GCS file existence:")
    print(f"   Config ID: {config_instrument_id}")
    print(f"   Date: {date_str}\n")
    
    # Convert to GCS format
    gcs_instrument_id = _convert_instrument_id_to_gcs_format(config_instrument_id)
    print(f"   GCS format: {gcs_instrument_id}\n")
    
    # Initialize UCS loader
    try:
        ucs_loader = UCSDataLoader()
        print(f"✅ UCS loader initialized\n")
    except Exception as e:
        print(f"❌ Failed to initialize UCS loader: {e}\n")
        return
    
    # Check trades
    print(f"📊 Checking trades data...")
    try:
        has_trades = await ucs_loader.check_local_file_exists(date_str, gcs_instrument_id, "trades")
        print(f"   Local check: {has_trades}")
        
        # Try list_available_dates
        dates = await ucs_loader.list_available_dates(gcs_instrument_id, "trades")
        print(f"   Available dates: {dates}")
        
        # Check if May 23 is in the list
        from datetime import date
        target_date = date(2023, 5, 23)
        if target_date in dates:
            print(f"   ✅ May 23, 2023 found in available dates!")
        else:
            print(f"   ❌ May 23, 2023 NOT in available dates")
            if dates:
                print(f"   Available dates: {dates[:5]}... (showing first 5)")
        
    except Exception as e:
        print(f"   ❌ Error checking trades: {e}")
        import traceback
        traceback.print_exc()
    
    # Check book
    print(f"\n📊 Checking book snapshot data...")
    try:
        dates = await ucs_loader.list_available_dates(gcs_instrument_id, "book_snapshot_5")
        print(f"   Available dates: {dates}")
        
        from datetime import date
        target_date = date(2023, 5, 23)
        if target_date in dates:
            print(f"   ✅ May 23, 2023 found in available dates!")
        else:
            print(f"   ❌ May 23, 2023 NOT in available dates")
            if dates:
                print(f"   Available dates: {dates[:5]}... (showing first 5)")
        
    except Exception as e:
        print(f"   ❌ Error checking book: {e}")
        import traceback
        traceback.print_exc()
    
    # Try direct GCS check using google.cloud.storage
    print(f"\n📊 Direct GCS check...")
    try:
        from google.cloud import storage
        
        bucket_name = os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET")
        if not bucket_name:
            print(f"   ❌ UNIFIED_CLOUD_SERVICES_GCS_BUCKET not set")
            return
        
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        # Build expected path
        gcs_path = f"raw_tick_data/by_date/day-{date_str}/data_type-trades/{gcs_instrument_id}.parquet"
        print(f"   Checking: {gcs_path}")
        
        blob = bucket.blob(gcs_path)
        if blob.exists():
            print(f"   ✅ File EXISTS!")
            print(f"      Size: {blob.size / 1024 / 1024:.2f} MB")
        else:
            print(f"   ❌ File NOT FOUND")
            
            # List files in the directory to see what's actually there
            prefix = f"raw_tick_data/by_date/day-{date_str}/data_type-trades/"
            print(f"\n   Listing files in: {prefix}")
            blobs = list(bucket.list_blobs(prefix=prefix, max_results=10))
            if blobs:
                print(f"   Found {len(blobs)} file(s):")
                for b in blobs:
                    print(f"      {b.name}")
            else:
                print(f"   No files found in this directory")
                
                # Check if the day directory exists
                day_prefix = f"raw_tick_data/by_date/day-{date_str}/"
                day_blobs = list(bucket.list_blobs(prefix=day_prefix, max_results=10))
                if day_blobs:
                    print(f"\n   Found {len(day_blobs)} file(s) in day directory:")
                    for b in day_blobs[:5]:
                        print(f"      {b.name}")
                else:
                    print(f"\n   Day directory also empty - date may not exist")
        
    except Exception as e:
        print(f"   ❌ Error in direct GCS check: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_gcs_file())

