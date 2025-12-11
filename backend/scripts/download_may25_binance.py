"""
Download Binance Futures data for May 25, 2023:
- Trades data
- Book snapshot data
Show columns and basic info.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from unified_cloud_services import UnifiedCloudService, CloudTarget
import pandas as pd

async def download_and_inspect():
    """Download Binance Futures data for May 25 and inspect columns."""
    
    bucket_name = os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET")
    if not bucket_name:
        print("❌ UNIFIED_CLOUD_SERVICES_GCS_BUCKET not set")
        return
    
    print(f"📦 GCS Bucket: {bucket_name}")
    print(f"{'='*70}\n")
    
    date_str = "2023-05-25"
    instrument_id = "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN"
    
    print(f"📥 Downloading Binance Futures data for:")
    print(f"   Date: {date_str}")
    print(f"   Instrument: {instrument_id}\n")
    
    # Initialize UCS
    ucs = UnifiedCloudService()
    target = CloudTarget(
        gcs_bucket=bucket_name,
        bigquery_dataset="market_data"
    )
    
    # Download trades data
    print(f"{'='*70}")
    print(f"1. TRADES DATA")
    print(f"{'='*70}\n")
    
    trades_path = f"raw_tick_data/by_date/day-{date_str}/data_type-trades/{instrument_id}.parquet"
    print(f"📥 Downloading trades from: {trades_path}\n")
    
    try:
        trades_df = await ucs.download_from_gcs(
            target=target,
            gcs_path=trades_path,
            format="parquet"
        )
        
        print(f"✅ Trades data downloaded successfully!")
        print(f"   Rows: {len(trades_df):,}")
        print(f"   Columns: {len(trades_df.columns)}")
        print(f"   Memory usage: {trades_df.memory_usage(deep=True).sum() / 1024**2:.2f} MB\n")
        
        print(f"📊 TRADES COLUMNS:\n")
        for i, col in enumerate(trades_df.columns, 1):
            dtype = trades_df[col].dtype
            non_null = trades_df[col].notna().sum()
            null_count = trades_df[col].isna().sum()
            print(f"   {i:2d}. {col:20s} ({dtype}) - {non_null:,} non-null, {null_count:,} null")
        
        # Show time range if timestamp columns exist
        print(f"\n📅 TRADES TIME RANGE:\n")
        if 'ts_event' in trades_df.columns:
            trades_df['ts_event_dt'] = pd.to_datetime(trades_df['ts_event'], unit='ns')
            print(f"   Start: {trades_df['ts_event_dt'].min()}")
            print(f"   End:   {trades_df['ts_event_dt'].max()}")
            print(f"   Duration: {trades_df['ts_event_dt'].max() - trades_df['ts_event_dt'].min()}")
        elif 'timestamp' in trades_df.columns:
            # Try microseconds
            if trades_df['timestamp'].dtype in ['int64', 'int32']:
                trades_df['timestamp_dt'] = pd.to_datetime(trades_df['timestamp'], unit='us')
            else:
                trades_df['timestamp_dt'] = pd.to_datetime(trades_df['timestamp'])
            print(f"   Start: {trades_df['timestamp_dt'].min()}")
            print(f"   End:   {trades_df['timestamp_dt'].max()}")
            print(f"   Duration: {trades_df['timestamp_dt'].max() - trades_df['timestamp_dt'].min()}")
        
        # Show sample data
        print(f"\n📋 TRADES SAMPLE DATA (first 5 rows):\n")
        print(trades_df.head().to_string())
        
        # Save locally
        output_path = Path(f"data/may25_binance_trades.parquet")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        trades_df.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")
        print(f"\n💾 Saved trades to: {output_path}")
        print(f"   File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
        
    except Exception as e:
        print(f"❌ Failed to download trades: {e}")
        import traceback
        traceback.print_exc()
        trades_df = None
    
    # Download book snapshot data
    print(f"\n{'='*70}")
    print(f"2. BOOK SNAPSHOT DATA")
    print(f"{'='*70}\n")
    
    book_path = f"raw_tick_data/by_date/day-{date_str}/data_type-book_snapshot_5/{instrument_id}.parquet"
    print(f"📥 Downloading book snapshots from: {book_path}\n")
    
    try:
        book_df = await ucs.download_from_gcs(
            target=target,
            gcs_path=book_path,
            format="parquet"
        )
        
        print(f"✅ Book snapshot data downloaded successfully!")
        print(f"   Rows: {len(book_df):,}")
        print(f"   Columns: {len(book_df.columns)}")
        print(f"   Memory usage: {book_df.memory_usage(deep=True).sum() / 1024**2:.2f} MB\n")
        
        print(f"📊 BOOK SNAPSHOT COLUMNS:\n")
        for i, col in enumerate(book_df.columns, 1):
            dtype = book_df[col].dtype
            non_null = book_df[col].notna().sum()
            null_count = book_df[col].isna().sum()
            print(f"   {i:2d}. {col:20s} ({dtype}) - {non_null:,} non-null, {null_count:,} null")
        
        # Show time range if timestamp columns exist
        print(f"\n📅 BOOK SNAPSHOT TIME RANGE:\n")
        if 'ts_event' in book_df.columns:
            book_df['ts_event_dt'] = pd.to_datetime(book_df['ts_event'], unit='ns')
            print(f"   Start: {book_df['ts_event_dt'].min()}")
            print(f"   End:   {book_df['ts_event_dt'].max()}")
            print(f"   Duration: {book_df['ts_event_dt'].max() - book_df['ts_event_dt'].min()}")
        elif 'timestamp' in book_df.columns:
            if book_df['timestamp'].dtype in ['int64', 'int32']:
                book_df['timestamp_dt'] = pd.to_datetime(book_df['timestamp'], unit='us')
            else:
                book_df['timestamp_dt'] = pd.to_datetime(book_df['timestamp'])
            print(f"   Start: {book_df['timestamp_dt'].min()}")
            print(f"   End:   {book_df['timestamp_dt'].max()}")
            print(f"   Duration: {book_df['timestamp_dt'].max() - book_df['timestamp_dt'].min()}")
        
        # Show sample data
        print(f"\n📋 BOOK SNAPSHOT SAMPLE DATA (first 5 rows):\n")
        print(book_df.head().to_string())
        
        # Save locally
        output_path = Path(f"data/may25_binance_book.parquet")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        book_df.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")
        print(f"\n💾 Saved book snapshots to: {output_path}")
        print(f"   File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
        
    except Exception as e:
        print(f"❌ Failed to download book snapshots: {e}")
        import traceback
        traceback.print_exc()
        book_df = None
    
    # Summary
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}\n")
    
    if trades_df is not None:
        print(f"✅ Trades: {len(trades_df):,} rows, {len(trades_df.columns)} columns")
    else:
        print(f"❌ Trades: Failed")
    
    if book_df is not None:
        print(f"✅ Book snapshots: {len(book_df):,} rows, {len(book_df.columns)} columns")
    else:
        print(f"❌ Book snapshots: Failed")
    
    print(f"\n📁 Files saved to: data/")


if __name__ == "__main__":
    # Load .env if available
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
    
    asyncio.run(download_and_inspect())

