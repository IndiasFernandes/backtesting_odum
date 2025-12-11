#!/usr/bin/env python3
"""
Test script for writing to GCS using unified-cloud-services.

This script demonstrates various ways to upload data to GCS using UCS.
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from unified_cloud_services import UnifiedCloudService, CloudTarget
    from unified_cloud_services.domain.standardized_service import StandardizedDomainCloudService
    UCS_AVAILABLE = True
except ImportError as e:
    print(f"❌ Error importing unified-cloud-services: {e}")
    print("   Make sure unified-cloud-services is installed")
    UCS_AVAILABLE = False

try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    print("❌ Error importing google.cloud.storage")
    GCS_AVAILABLE = False


def setup_credentials():
    """Setup GCS credentials from environment or default path."""
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    if not creds_path:
        # Try default path
        default_path = Path("/app/.secrets/gcs/gcs-service-account.json")
        if default_path.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(default_path)
            print(f"✅ Using default credentials: {default_path}")
            return str(default_path)
        else:
            print("⚠️  No credentials found. Set GOOGLE_APPLICATION_CREDENTIALS env var.")
            return None
    
    if not Path(creds_path).exists():
        print(f"⚠️  Credentials file not found: {creds_path}")
        return None
    
    print(f"✅ Using credentials: {creds_path}")
    return creds_path


def test_write_json_using_ucs():
    """Test writing JSON data using unified-cloud-services."""
    print("\n" + "="*60)
    print("Test 1: Writing JSON using unified-cloud-services")
    print("="*60)
    
    bucket_name = os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET")
    if not bucket_name:
        print("❌ UNIFIED_CLOUD_SERVICES_GCS_BUCKET not set")
        return False
    
    try:
        # Create standardized service
        target = CloudTarget(
            gcs_bucket=bucket_name,
            bigquery_dataset="market_data"
        )
        
        service = StandardizedDomainCloudService(
            domain="market_data",
            cloud_target=target
        )
        
        # Create test data
        test_data = {
            "test_id": "ucs_json_test",
            "timestamp": datetime.now().isoformat(),
            "message": "Hello from unified-cloud-services!",
            "data": {
                "value1": 123,
                "value2": "test",
                "value3": [1, 2, 3]
            }
        }
        
        # Upload JSON
        gcs_path = f"test_uploads/json_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        print(f"📤 Uploading JSON to: {gcs_path}")
        
        service.upload_to_gcs(
            data=test_data,
            gcs_path=gcs_path,
            format="json"
        )
        
        print(f"✅ Successfully uploaded JSON to: gs://{bucket_name}/{gcs_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_write_dataframe_using_ucs():
    """Test writing DataFrame (Parquet) using unified-cloud-services."""
    print("\n" + "="*60)
    print("Test 2: Writing DataFrame (Parquet) using unified-cloud-services")
    print("="*60)
    
    bucket_name = os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET")
    if not bucket_name:
        print("❌ UNIFIED_CLOUD_SERVICES_GCS_BUCKET not set")
        return False
    
    try:
        # Create standardized service
        target = CloudTarget(
            gcs_bucket=bucket_name,
            bigquery_dataset="market_data"
        )
        
        service = StandardizedDomainCloudService(
            domain="market_data",
            cloud_target=target
        )
        
        # Create test DataFrame
        df = pd.DataFrame({
            "timestamp": pd.date_range(start="2023-05-25", periods=10, freq="1min"),
            "price": [50000 + i * 10 for i in range(10)],
            "volume": [0.1 * (i + 1) for i in range(10)],
            "side": ["BUY" if i % 2 == 0 else "SELL" for i in range(10)]
        })
        
        print(f"📊 Created DataFrame with {len(df)} rows")
        print(f"   Columns: {list(df.columns)}")
        
        # Upload Parquet
        gcs_path = f"test_uploads/df_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        print(f"📤 Uploading Parquet to: {gcs_path}")
        
        service.upload_to_gcs(
            data=df,
            gcs_path=gcs_path,
            format="parquet"
        )
        
        print(f"✅ Successfully uploaded Parquet to: gs://{bucket_name}/{gcs_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_write_csv_using_ucs():
    """Test writing CSV using unified-cloud-services."""
    print("\n" + "="*60)
    print("Test 3: Writing CSV using unified-cloud-services")
    print("="*60)
    
    bucket_name = os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET")
    if not bucket_name:
        print("❌ UNIFIED_CLOUD_SERVICES_GCS_BUCKET not set")
        return False
    
    try:
        # Create standardized service
        target = CloudTarget(
            gcs_bucket=bucket_name,
            bigquery_dataset="market_data"
        )
        
        service = StandardizedDomainCloudService(
            domain="market_data",
            cloud_target=target
        )
        
        # Create test DataFrame
        df = pd.DataFrame({
            "symbol": ["BTC-USDT", "ETH-USDT", "BNB-USDT"],
            "price": [50000, 3000, 300],
            "volume_24h": [1000000, 500000, 200000]
        })
        
        print(f"📊 Created DataFrame with {len(df)} rows")
        
        # Upload CSV
        gcs_path = f"test_uploads/csv_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        print(f"📤 Uploading CSV to: {gcs_path}")
        
        service.upload_to_gcs(
            data=df,
            gcs_path=gcs_path,
            format="csv"
        )
        
        print(f"✅ Successfully uploaded CSV to: gs://{bucket_name}/{gcs_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_write_backtest_result_example():
    """Example: Upload a backtest result JSON."""
    print("\n" + "="*60)
    print("Test 4: Uploading Backtest Result (Example)")
    print("="*60)
    
    bucket_name = os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET")
    if not bucket_name:
        print("❌ UNIFIED_CLOUD_SERVICES_GCS_BUCKET not set")
        return False
    
    try:
        # Create standardized service
        target = CloudTarget(
            gcs_bucket=bucket_name,
            bigquery_dataset="market_data"
        )
        
        service = StandardizedDomainCloudService(
            domain="market_data",
            cloud_target=target
        )
        
        # Create example backtest result
        backtest_result = {
            "run_id": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "instrument": "BTC-USDT.BINANCE",
            "start": "2023-05-25T02:00:00Z",
            "end": "2023-05-25T02:05:00Z",
            "summary": {
                "total_trades": 100,
                "total_pnl": 1234.56,
                "win_rate": 0.65,
                "sharpe_ratio": 1.23
            },
            "execution_time": datetime.now().isoformat()
        }
        
        # Upload backtest result
        run_id = backtest_result["run_id"]
        gcs_path = f"backtest_results/{run_id}/summary.json"
        print(f"📤 Uploading backtest result to: {gcs_path}")
        
        service.upload_to_gcs(
            data=backtest_result,
            gcs_path=gcs_path,
            format="json"
        )
        
        print(f"✅ Successfully uploaded backtest result to: gs://{bucket_name}/{gcs_path}")
        print(f"   Run ID: {run_id}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_direct_gcs_client_comparison():
    """Compare with direct GCS client for reference."""
    print("\n" + "="*60)
    print("Test 5: Direct GCS Client (for comparison)")
    print("="*60)
    
    bucket_name = os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET")
    if not bucket_name:
        print("❌ UNIFIED_CLOUD_SERVICES_GCS_BUCKET not set")
        return False
    
    if not GCS_AVAILABLE:
        print("❌ google.cloud.storage not available")
        return False
    
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        # Create test data
        test_data = {
            "method": "direct_gcs_client",
            "timestamp": datetime.now().isoformat(),
            "message": "This is uploaded using google.cloud.storage directly"
        }
        
        # Upload using direct client
        gcs_path = f"test_uploads/direct_client_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        print(f"📤 Uploading using direct GCS client to: {gcs_path}")
        
        blob = bucket.blob(gcs_path)
        blob.upload_from_string(
            json.dumps(test_data, indent=2),
            content_type="application/json"
        )
        
        print(f"✅ Successfully uploaded using direct client to: gs://{bucket_name}/{gcs_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def list_uploaded_files():
    """List files in the test_uploads directory."""
    print("\n" + "="*60)
    print("Listing uploaded test files")
    print("="*60)
    
    bucket_name = os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET")
    if not bucket_name:
        print("❌ UNIFIED_CLOUD_SERVICES_GCS_BUCKET not set")
        return
    
    if not GCS_AVAILABLE:
        print("❌ google.cloud.storage not available")
        return
    
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        # List files in test_uploads directory
        blobs = list(bucket.list_blobs(prefix="test_uploads/"))
        
        if blobs:
            print(f"📁 Found {len(blobs)} file(s) in test_uploads/:")
            for blob in blobs[:10]:  # Show first 10
                size_mb = blob.size / (1024 * 1024) if blob.size else 0
                print(f"   - {blob.name} ({size_mb:.2f} MB)")
            if len(blobs) > 10:
                print(f"   ... and {len(blobs) - 10} more")
        else:
            print("📁 No files found in test_uploads/")
            
    except Exception as e:
        print(f"❌ Error listing files: {type(e).__name__}: {e}")


def main():
    """Run all tests."""
    print("="*60)
    print("GCS Write Test using unified-cloud-services")
    print("="*60)
    
    # Check prerequisites
    if not UCS_AVAILABLE:
        print("\n❌ unified-cloud-services not available. Cannot run tests.")
        return
    
    # Setup credentials
    creds_path = setup_credentials()
    if not creds_path:
        print("\n⚠️  Warning: Credentials not found. Tests may fail.")
    
    # Get bucket name
    bucket_name = os.getenv("UNIFIED_CLOUD_SERVICES_GCS_BUCKET")
    if not bucket_name:
        print("\n❌ UNIFIED_CLOUD_SERVICES_GCS_BUCKET not set")
        print("   Set it with: export UNIFIED_CLOUD_SERVICES_GCS_BUCKET=your-bucket-name")
        return
    
    print(f"\n📦 Bucket: {bucket_name}")
    print(f"🔑 Credentials: {creds_path or 'Not set'}")
    
    # Run tests
    results = []
    
    results.append(("JSON Upload", test_write_json_using_ucs()))
    results.append(("DataFrame/Parquet Upload", test_write_dataframe_using_ucs()))
    results.append(("CSV Upload", test_write_csv_using_ucs()))
    results.append(("Backtest Result Upload", test_write_backtest_result_example()))
    results.append(("Direct GCS Client", test_direct_gcs_client_comparison()))
    
    # List uploaded files
    list_uploaded_files()
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check errors above.")


if __name__ == "__main__":
    main()

