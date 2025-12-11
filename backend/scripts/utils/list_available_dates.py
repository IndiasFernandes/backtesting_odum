#!/usr/bin/env python3
"""
List available dates in the GCS bucket for Binance BTC-USDT
"""

import sys
import os
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from unified_cloud_services import UnifiedCloudService, CloudTarget
from google.cloud import storage

async def list_available_dates():
    """List available dates for Binance BTC-USDT"""
    print("=" * 60)
    print("LISTING AVAILABLE DATES")
    print("=" * 60)
    
    # Set credentials
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        creds_path = Path(".secrets/gcs/gcs-service-account.json")
        if creds_path.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds_path)
    
    ucs = UnifiedCloudService()
    target = CloudTarget(
        gcs_bucket="market-data-tick-cefi-central-element-323112",
        bigquery_dataset="market_tick_data"
    )
    
    # Get GCS client
    await ucs.ensure_warmed_connections()
    gcs_client = ucs._get_gcs_client()
    bucket = gcs_client.bucket(target.gcs_bucket)
    
    # List files matching pattern
    prefix = "raw_tick_data/by_date/day-"
    instrument = "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN"
    
    print(f"\n📂 Searching for: {prefix}*/data_type-trades/{instrument}.parquet")
    print()
    
    dates = set()
    blobs = bucket.list_blobs(prefix=prefix)
    
    for blob in blobs:
        if instrument in blob.name and "data_type-trades" in blob.name:
            # Extract date from path: raw_tick_data/by_date/day-2023-05-23/...
            parts = blob.name.split("/")
            for part in parts:
                if part.startswith("day-"):
                    date = part.replace("day-", "")
                    dates.add(date)
                    break
    
    if dates:
        sorted_dates = sorted(dates)
        print(f"✅ Found {len(sorted_dates)} dates with data:")
        print()
        for date in sorted_dates:
            print(f"   - {date}")
        
        print()
        print(f"📅 First date: {sorted_dates[0]}")
        print(f"📅 Last date: {sorted_dates[-1]}")
        
        # Check if May 26 exists
        if "2023-05-26" in dates:
            print()
            print("✅ May 26, 2023 EXISTS!")
        else:
            print()
            print("❌ May 26, 2023 NOT FOUND")
            print(f"   Closest dates:")
            for date in sorted_dates:
                if date > "2023-05-26":
                    print(f"   - {date} (after)")
                    break
            for date in reversed(sorted_dates):
                if date < "2023-05-26":
                    print(f"   - {date} (before)")
                    break
    else:
        print("❌ No dates found")
        print("   Checking if bucket is accessible...")
        
        # Try to list bucket contents
        try:
            blobs = list(bucket.list_blobs(max_results=10))
            print(f"   Found {len(blobs)} files in bucket (showing first 10):")
            for blob in blobs:
                print(f"   - {blob.name}")
        except Exception as e:
            print(f"   Error listing bucket: {e}")

if __name__ == "__main__":
    asyncio.run(list_available_dates())

