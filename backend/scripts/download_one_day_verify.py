"""
Download one day of data from GCS to verify structure matches local organization.

This script downloads May 23, 2023 data and saves it locally to verify:
1. The GCS path structure
2. The filename format
3. That it matches what we're searching for
"""
import asyncio
import os
import sys
from pathlib import Path
from datetime import date

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from unified_cloud_services import UnifiedCloudService, CloudTarget
    UCS_AVAILABLE = True
except ImportError:
    UCS_AVAILABLE = False
    print("❌ unified-cloud-services not installed")
    sys.exit(1)


async def download_and_verify():
    """Download one day and verify structure."""
    
    bucket_name = os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET")
    if not bucket_name:
        print("❌ UNIFIED_CLOUD_SERVICES_GCS_BUCKET not set")
        return
    
    print(f"📦 GCS Bucket: {bucket_name}")
    print(f"{'='*70}\n")
    
    # Test date
    test_date = date(2023, 5, 23)
    date_str = test_date.strftime("%Y-%m-%d")
    
    # Test instrument IDs (try both formats)
    instrument_with_suffix = "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN"
    instrument_no_suffix = "BINANCE-FUTURES:PERPETUAL:BTC-USDT"
    
    print(f"🔍 Testing download for:")
    print(f"   Date: {date_str}")
    print(f"   Instrument (with @LIN): {instrument_with_suffix}")
    print(f"   Instrument (no suffix): {instrument_no_suffix}\n")
    
    # Initialize UCS
    ucs = UnifiedCloudService()
    target = CloudTarget(
        gcs_bucket=bucket_name,
        bigquery_dataset="market_data"
    )
    
    # Try downloading trades data with @LIN suffix (GCS format)
    print(f"📥 Attempting download with @LIN suffix...\n")
    gcs_path_with_suffix = f"raw_tick_data/by_date/day-{date_str}/data_type-trades/{instrument_with_suffix}.parquet"
    print(f"   GCS Path: {gcs_path_with_suffix}\n")
    
    try:
        df = await ucs.download_from_gcs(
            target=target,
            gcs_path=gcs_path_with_suffix,
            format="parquet"
        )
        
        print(f"   ✅ SUCCESS with @LIN suffix!")
        print(f"      Rows: {len(df):,}")
        print(f"      Columns: {list(df.columns)}")
        
        # Save to verify local structure
        local_output = Path(f"/app/data_downloads/raw_tick_data/by_date/day-{date_str}/data_type-trades/{instrument_with_suffix}.parquet")
        local_output.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(local_output, index=False, engine="pyarrow", compression="snappy")
        print(f"      Saved to: {local_output}")
        print(f"      File size: {local_output.stat().st_size / 1024 / 1024:.2f} MB")
        
        print(f"\n✅ Verified: GCS uses format WITH @LIN suffix")
        print(f"   GCS format: {instrument_with_suffix}.parquet")
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "No such object" in error_msg:
            print(f"   ❌ NOT FOUND with @LIN suffix")
            print(f"   Trying without @LIN suffix...\n")
            
            # Try without @LIN suffix
            gcs_path_no_suffix = f"raw_tick_data/by_date/day-{date_str}/data_type-trades/{instrument_no_suffix}.parquet"
            print(f"   GCS Path: {gcs_path_no_suffix}\n")
            
            try:
                df = await ucs.download_from_gcs(
                    target=target,
                    gcs_path=gcs_path_no_suffix,
                    format="parquet"
                )
                
                print(f"   ✅ SUCCESS without @LIN suffix!")
                print(f"      Rows: {len(df):,}")
                print(f"      Columns: {list(df.columns)}")
                
                # Save to verify local structure
                local_output = Path(f"/app/data_downloads/raw_tick_data/by_date/day-{date_str}/data_type-trades/{instrument_no_suffix}.parquet")
                local_output.parent.mkdir(parents=True, exist_ok=True)
                df.to_parquet(local_output, index=False, engine="pyarrow", compression="snappy")
                print(f"      Saved to: {local_output}")
                print(f"      File size: {local_output.stat().st_size / 1024 / 1024:.2f} MB")
                
                print(f"\n✅ Verified: GCS uses format WITHOUT @LIN suffix")
                print(f"   GCS format: {instrument_no_suffix}.parquet")
                
                return True
                
            except Exception as e2:
                print(f"   ❌ Also failed without @LIN suffix: {e2}")
                return False
        else:
            print(f"   ❌ Error: {error_msg}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    asyncio.run(download_and_verify())

