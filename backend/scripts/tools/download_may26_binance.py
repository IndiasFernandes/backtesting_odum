#!/usr/bin/env python3
"""
Download Binance data for May 26, 2023:
1. Full parquet file
2. 5-minute window (byte-range streaming)
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from unified_cloud_services import UnifiedCloudService, CloudTarget
import pandas as pd

async def download_full_file():
    """Download full parquet file for May 26, 2023"""
    print("=" * 60)
    print("DOWNLOAD 1: Full Parquet File")
    print("=" * 60)
    
    ucs = UnifiedCloudService()
    target = CloudTarget(
        gcs_bucket="market-data-tick-cefi-central-element-323112",
        bigquery_dataset="market_tick_data"
    )
    
    # Note: May 26 doesn't exist, using May 25 instead
    date = "2023-05-25"
    instrument = "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN"
    gcs_path = f"raw_tick_data/by_date/day-{date}/data_type-trades/{instrument}.parquet"
    
    print(f"📥 Downloading full file...")
    print(f"   Date: {date} (Note: May 26 not available, using May 25)")
    print(f"   Instrument: {instrument}")
    print(f"   Path: {gcs_path}")
    
    try:
        df = await ucs.download_from_gcs(
            target=target,
            gcs_path=gcs_path,
            format="parquet"
        )
        
        print(f"\n✅ SUCCESS: Downloaded full file")
        print(f"   Rows: {len(df):,}")
        print(f"   Columns: {len(df.columns)}")
        print(f"   Columns: {list(df.columns)}")
        print(f"   Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        
        # Show time range
        if 'ts_event' in df.columns:
            df['ts_event_dt'] = pd.to_datetime(df['ts_event'], unit='ns')
            print(f"   Time range: {df['ts_event_dt'].min()} to {df['ts_event_dt'].max()}")
        
        # Save to local file
        output_path = Path(f"data/may25_binance_full.parquet")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")
        print(f"\n💾 Saved to: {output_path}")
        print(f"   File size: {output_path.stat().st_size / 1024**2:.2f} MB")
        
        return df
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None

async def download_5min_window():
    """Download 5-minute window using byte-range streaming"""
    print("\n" + "=" * 60)
    print("DOWNLOAD 2: 5-Minute Window (Byte-Range Streaming)")
    print("=" * 60)
    
    ucs = UnifiedCloudService()
    target = CloudTarget(
        gcs_bucket="market-data-tick-cefi-central-element-323112",
        bigquery_dataset="market_tick_data"
    )
    
    # Note: May 26 doesn't exist, using May 25 instead
    date = "2023-05-25"
    instrument = "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN"
    gcs_path = f"raw_tick_data/by_date/day-{date}/data_type-trades/{instrument}.parquet"
    
    # 5-minute window: first 5 minutes of the day
    start_ts = datetime(2023, 5, 25, 0, 0, 0, tzinfo=timezone.utc)
    end_ts = datetime(2023, 5, 25, 0, 5, 0, tzinfo=timezone.utc)
    
    print(f"📥 Downloading 5-minute window with byte-range streaming...")
    print(f"   Date: {date} (Note: May 26 not available, using May 25)")
    print(f"   Instrument: {instrument}")
    print(f"   Path: {gcs_path}")
    print(f"   Time window: {start_ts} to {end_ts}")
    
    try:
        df = await ucs.download_from_gcs_streaming(
            target=target,
            gcs_path=gcs_path,
            timestamp_range=(start_ts, end_ts),
            timestamp_column="ts_event",
            use_byte_range=True
        )
        
        print(f"\n✅ SUCCESS: Downloaded 5-minute window")
        print(f"   Rows: {len(df):,}")
        print(f"   Columns: {len(df.columns)}")
        print(f"   Columns: {list(df.columns)}")
        print(f"   Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        
        # Show time range
        if 'ts_event' in df.columns:
            df['ts_event_dt'] = pd.to_datetime(df['ts_event'], unit='ns')
            print(f"   Time range: {df['ts_event_dt'].min()} to {df['ts_event_dt'].max()}")
        
        # Show sample data
        if len(df) > 0:
            print(f"\n📊 Sample data (first 5 rows):")
            print(df.head().to_string())
        
        # Save to local file
        output_path = Path(f"data/may25_binance_5min.parquet")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")
        print(f"\n💾 Saved to: {output_path}")
        print(f"   File size: {output_path.stat().st_size / 1024**2:.2f} MB")
        
        return df
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Main function"""
    print("\n" + "=" * 60)
    print("BINANCE DATA DOWNLOAD - May 25, 2023")
    print("(Note: May 26 not available, using May 25)")
    print("=" * 60)
    print()
    
    # Set credentials if not already set
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        creds_path = Path(".secrets/gcs/gcs-service-account.json")
        if creds_path.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds_path)
            print(f"✅ Set GOOGLE_APPLICATION_CREDENTIALS to: {creds_path}")
        else:
            print(f"⚠️  Warning: Credentials file not found at {creds_path}")
    
    print()
    
    # Download full file
    full_df = await download_full_file()
    
    # Download 5-minute window
    window_df = await download_5min_window()
    
    # Summary
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    
    if full_df is not None:
        print(f"✅ Full file: {len(full_df):,} rows")
    else:
        print(f"❌ Full file: Failed")
    
    if window_df is not None:
        print(f"✅ 5-minute window: {len(window_df):,} rows")
        if full_df is not None:
            reduction = (1 - len(window_df) / len(full_df)) * 100
            print(f"   Data reduction: {reduction:.2f}%")
    else:
        print(f"❌ 5-minute window: Failed")
    
    print("\n✅ Downloads complete!")
    print(f"   Files saved to: data/")

if __name__ == "__main__":
    asyncio.run(main())

