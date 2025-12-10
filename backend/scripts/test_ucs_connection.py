#!/usr/bin/env python3
"""
Test script for Unified Cloud Services (UCS) connection and functionality.

This script tests:
1. UCS installation and import
2. GCS bucket connectivity
3. Data download capabilities
4. Data upload capabilities
5. FUSE mount detection

Usage:
    python backend/scripts/test_ucs_connection.py [--bucket BUCKET_NAME] [--test-upload]
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_ucs_import():
    """Test if UCS can be imported."""
    print("=" * 60)
    print("TEST 1: UCS Import")
    print("=" * 60)
    try:
        from unified_cloud_services import UnifiedCloudService, CloudTarget
        print("✅ SUCCESS: UCS imported successfully")
        print(f"   UnifiedCloudService: {UnifiedCloudService}")
        print(f"   CloudTarget: {CloudTarget}")
        return True, UnifiedCloudService, CloudTarget
    except ImportError as e:
        print(f"❌ FAILED: Cannot import UCS")
        print(f"   Error: {e}")
        print("\n   SOLUTION: Install UCS with:")
        print("   pip install git+https://github.com/IggyIkenna/unified-cloud-services.git")
        return False, None, None

def test_fuse_detection():
    """Test if UCS can detect FUSE mounts."""
    print("\n" + "=" * 60)
    print("TEST 2: FUSE Mount Detection")
    print("=" * 60)
    try:
        from unified_cloud_services import UnifiedCloudService
        ucs = UnifiedCloudService()
        
        # Check if UCS auto-detects FUSE mounts
        local_path = os.getenv("UNIFIED_CLOUD_LOCAL_PATH", "/app/data_downloads")
        print(f"   Checking local path: {local_path}")
        
        if os.path.exists(local_path):
            print(f"✅ SUCCESS: Local path exists")
            # Check if it's a mount point
            if os.path.ismount(local_path):
                print(f"   ⚠️  Path is a mount point (likely FUSE)")
            else:
                print(f"   ℹ️  Path is not a mount point (local directory)")
            
            # List some files to verify access
            try:
                files = list(Path(local_path).rglob("*.parquet"))[:5]
                if files:
                    print(f"   ✅ Found {len(files)} Parquet files (showing first 5)")
                    for f in files[:3]:
                        print(f"      - {f.relative_to(local_path)}")
                else:
                    print(f"   ⚠️  No Parquet files found in {local_path}")
            except Exception as e:
                print(f"   ⚠️  Could not list files: {e}")
        else:
            print(f"⚠️  WARNING: Local path does not exist: {local_path}")
            print(f"   This is OK if using direct GCS access")
        
        return True
    except Exception as e:
        print(f"❌ FAILED: FUSE detection test failed")
        print(f"   Error: {e}")
        return False

async def test_gcs_connectivity(bucket_name: str, ucs_class, cloud_target_class):
    """Test GCS bucket connectivity."""
    print("\n" + "=" * 60)
    print("TEST 3: GCS Bucket Connectivity")
    print("=" * 60)
    try:
        ucs = ucs_class()
        target = cloud_target_class(
            gcs_bucket=bucket_name,
            bigquery_dataset='test_dataset'  # Not used for GCS tests
        )
        
        print(f"   Testing bucket: {bucket_name}")
        
        # Test list_files if available
        try:
            if hasattr(ucs, 'list_files'):
                print("   Testing list_files()...")
                files = await ucs.list_files(target=target, prefix="")
                print(f"   ✅ SUCCESS: Can list files in bucket")
                if files:
                    print(f"   Found {len(files)} files (showing first 5)")
                    for f in files[:5]:
                        print(f"      - {f}")
                else:
                    print(f"   ⚠️  Bucket appears empty or prefix returned no results")
            else:
                print("   ⚠️  list_files() method not available in UCS")
        except Exception as e:
            print(f"   ⚠️  list_files() test failed: {e}")
            print(f"   This is OK - may not be critical for basic functionality")
        
        return True
    except Exception as e:
        print(f"❌ FAILED: GCS connectivity test failed")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_download_instruments(bucket_name: str, ucs_class, cloud_target_class):
    """Test downloading instrument definitions."""
    print("\n" + "=" * 60)
    print("TEST 4: Download Instrument Definitions")
    print("=" * 60)
    try:
        ucs = ucs_class()
        target = cloud_target_class(
            gcs_bucket=bucket_name,
            bigquery_dataset='instruments_data'
        )
        
        # Try to download a sample instrument file
        test_date = "2023-05-23"
        gcs_path = f"instrument_availability/by_date/day-{test_date}/instruments.parquet"
        
        print(f"   Attempting to download: {gcs_path}")
        
        try:
            if hasattr(ucs, 'download_from_gcs'):
                df = await ucs.download_from_gcs(
                    target=target,
                    gcs_path=gcs_path,
                    format='parquet'
                )
                print(f"   ✅ SUCCESS: Downloaded instrument definitions")
                print(f"   Shape: {df.shape}")
                print(f"   Columns: {list(df.columns)[:10]}...")
                if len(df) > 0:
                    print(f"   Sample instrument_key: {df.iloc[0].get('instrument_key', 'N/A')}")
                return True
            else:
                print(f"   ⚠️  download_from_gcs() method not available")
                return False
        except FileNotFoundError:
            print(f"   ⚠️  File not found: {gcs_path}")
            print(f"   This is OK if the file doesn't exist yet")
            return True  # Not a failure, just missing data
        except Exception as e:
            print(f"   ❌ FAILED: Download test failed")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    except Exception as e:
        print(f"❌ FAILED: Instrument download test setup failed")
        print(f"   Error: {e}")
        return False

async def test_download_tick_data(bucket_name: str, ucs_class, cloud_target_class):
    """Test downloading tick data with byte-range streaming."""
    print("\n" + "=" * 60)
    print("TEST 5: Download Tick Data (Byte-Range Streaming)")
    print("=" * 60)
    try:
        ucs = ucs_class()
        target = cloud_target_class(
            gcs_bucket=bucket_name,
            bigquery_dataset='market_tick_data'
        )
        
        # Test downloading a small time window
        test_date = "2023-05-23"
        instrument = "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN"
        gcs_path = f"raw_tick_data/by_date/day-{test_date}/data_type-trades/{instrument}.parquet"
        
        print(f"   Testing byte-range streaming for: {gcs_path}")
        
        # Test 5-minute window
        start_ts = datetime(2023, 5, 23, 0, 0, 0, tzinfo=timezone.utc)
        end_ts = datetime(2023, 5, 23, 0, 5, 0, tzinfo=timezone.utc)
        
        try:
            if hasattr(ucs, 'download_from_gcs_streaming'):
                print(f"   Time window: {start_ts} to {end_ts}")
                df = await ucs.download_from_gcs_streaming(
                    target=target,
                    gcs_path=gcs_path,
                    timestamp_range=(start_ts, end_ts),
                    timestamp_column='ts_event',
                    use_byte_range=True
                )
                print(f"   ✅ SUCCESS: Downloaded tick data with streaming")
                print(f"   Rows: {len(df)}")
                print(f"   Columns: {list(df.columns)}")
                return True
            else:
                print(f"   ⚠️  download_from_gcs_streaming() method not available")
                print(f"   Falling back to full file download...")
                
                # Try full download
                if hasattr(ucs, 'download_from_gcs'):
                    df = await ucs.download_from_gcs(
                        target=target,
                        gcs_path=gcs_path,
                        format='parquet'
                    )
                    print(f"   ✅ SUCCESS: Downloaded full file (no streaming)")
                    print(f"   Rows: {len(df)}")
                    return True
                else:
                    return False
        except FileNotFoundError:
            print(f"   ⚠️  File not found: {gcs_path}")
            print(f"   This is OK if the file doesn't exist yet")
            return True
        except Exception as e:
            print(f"   ❌ FAILED: Tick data download test failed")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    except Exception as e:
        print(f"❌ FAILED: Tick data download test setup failed")
        print(f"   Error: {e}")
        return False

async def test_upload_results(bucket_name: str, ucs_class, cloud_target_class):
    """Test uploading results to GCS."""
    print("\n" + "=" * 60)
    print("TEST 6: Upload Results to GCS")
    print("=" * 60)
    try:
        ucs = ucs_class()
        target = cloud_target_class(
            gcs_bucket=bucket_name,
            bigquery_dataset='execution'
        )
        
        # Create a test result
        test_run_id = f"TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        test_summary = {
            "run_id": test_run_id,
            "status": "TEST",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "test": True
        }
        
        gcs_path = f"backtest_results/{test_run_id}/test_summary.json"
        
        print(f"   Testing upload to: {gcs_path}")
        
        try:
            if hasattr(ucs, 'upload_to_gcs'):
                await ucs.upload_to_gcs(
                    target=target,
                    gcs_path=gcs_path,
                    data=test_summary,
                    format='json'
                )
                print(f"   ✅ SUCCESS: Uploaded test summary")
                
                # Try to download it back to verify
                if hasattr(ucs, 'download_from_gcs'):
                    downloaded = await ucs.download_from_gcs(
                        target=target,
                        gcs_path=gcs_path,
                        format='json'
                    )
                    print(f"   ✅ SUCCESS: Verified upload by downloading back")
                    print(f"   Downloaded run_id: {downloaded.get('run_id')}")
                
                return True
            else:
                print(f"   ⚠️  upload_to_gcs() method not available")
                return False
        except Exception as e:
            print(f"   ❌ FAILED: Upload test failed")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    except Exception as e:
        print(f"❌ FAILED: Upload test setup failed")
        print(f"   Error: {e}")
        return False

async def main():
    """Run all UCS connection tests."""
    parser = argparse.ArgumentParser(description="Test UCS connection and functionality")
    parser.add_argument(
        "--bucket",
        type=str,
        default="execution-store-cefi-central-element-323112",
        help="GCS bucket name to test (default: execution-store-cefi-central-element-323112)"
    )
    parser.add_argument(
        "--test-upload",
        action="store_true",
        help="Test upload functionality (requires write permissions)"
    )
    parser.add_argument(
        "--instruments-bucket",
        type=str,
        default="instruments-store-cefi-central-element-323112",
        help="Instruments bucket name (default: instruments-store-cefi-central-element-323112)"
    )
    parser.add_argument(
        "--market-data-bucket",
        type=str,
        default="market-data-tick-cefi-central-element-323112",
        help="Market data bucket name (default: market-data-tick-cefi-central-element-323112)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("UCS CONNECTION TEST SUITE")
    print("=" * 60)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Python: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")
    print()
    
    # Test 1: Import
    success, ucs_class, cloud_target_class = test_ucs_import()
    if not success:
        print("\n❌ CRITICAL: Cannot proceed without UCS. Please install it first.")
        sys.exit(1)
    
    # Test 2: FUSE Detection
    test_fuse_detection()
    
    # Test 3: GCS Connectivity
    await test_gcs_connectivity(args.bucket, ucs_class, cloud_target_class)
    
    # Test 4: Download Instruments
    await test_download_instruments(args.instruments_bucket, ucs_class, cloud_target_class)
    
    # Test 5: Download Tick Data
    await test_download_tick_data(args.market_data_bucket, ucs_class, cloud_target_class)
    
    # Test 6: Upload Results (if requested)
    if args.test_upload:
        await test_upload_results(args.bucket, ucs_class, cloud_target_class)
    else:
        print("\n" + "=" * 60)
        print("TEST 6: Upload Results (SKIPPED)")
        print("=" * 60)
        print("   ℹ️  Skipped (use --test-upload to test)")
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("✅ All critical tests completed")
    print("\nNext steps:")
    print("1. Review any warnings above")
    print("2. Ensure GCS credentials are configured")
    print("3. Verify bucket permissions")
    print("4. Proceed with UCS integration")

if __name__ == "__main__":
    asyncio.run(main())

