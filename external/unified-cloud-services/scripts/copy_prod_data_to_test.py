#!/usr/bin/env python3
"""
Copy production data to test buckets for Sep 23, 2024.

Ensures test buckets have data for CEFI, DEFI, and TRADFI categories
so tests can run against real data structure.

Usage:
    python scripts/copy_prod_data_to_test.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from google.cloud import storage
from google.oauth2 import service_account

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
except ImportError:
    pass


def get_config(key: str, default: str) -> str:
    """Get configuration from environment."""
    return os.getenv(key, default)


def get_storage_client(project_id: str, credentials_file: str):
    """Get GCS storage client."""
    credentials = service_account.Credentials.from_service_account_file(credentials_file)
    return storage.Client(project=project_id, credentials=credentials)


def copy_blob(
    source_bucket: storage.Bucket,
    dest_bucket: storage.Bucket,
    blob_name: str,
    dest_blob_name: str = None,
):
    """Copy a blob from source bucket to destination bucket."""
    if dest_blob_name is None:
        dest_blob_name = blob_name
    
    source_blob = source_bucket.blob(blob_name)
    if not source_blob.exists():
        print(f"⚠️  Source blob does not exist: {blob_name}")
        return False
    
    dest_blob = dest_bucket.blob(dest_blob_name)
    if dest_blob.exists():
        print(f"⏭️  Destination blob already exists: {dest_blob_name}")
        return True
    
    print(f"📋 Copying {blob_name} -> {dest_blob_name}")
    source_bucket.copy_blob(source_blob, dest_bucket, dest_blob_name)
    print(f"✅ Copied {blob_name}")
    return True


def copy_instruments_for_date(
    client: storage.Client,
    project_id: str,
    date: str,
    category: str = None,
):
    """Copy instrument definitions for a specific date."""
    # Production buckets
    if category:
        prod_bucket_name = get_config(
            f"INSTRUMENTS_GCS_BUCKET_{category}",
            f"instruments-store-{category.lower()}-central-element-323112",
        )
        test_bucket_name = get_config(
            f"INSTRUMENTS_GCS_BUCKET_{category}_TEST",
            f"instruments-store-test-{category.lower()}-central-element-323112",
        )
    else:
        prod_bucket_name = get_config(
            "INSTRUMENTS_GCS_BUCKET",
            "instruments-store-central-element-323112",
        )
        test_bucket_name = get_config(
            "INSTRUMENTS_GCS_BUCKET_TEST",
            "instruments-store-test-central-element-323112",
        )
    
    prod_bucket = client.bucket(prod_bucket_name)
    test_bucket = client.bucket(test_bucket_name)
    
    # Ensure test bucket exists
    if not test_bucket.exists():
        print(f"📦 Creating test bucket: {test_bucket_name}")
        location = get_config("GCS_LOCATION", "asia-northeast1")
        test_bucket.create(location=location)
    
    # Copy instruments parquet file
    instruments_path = f"instrument_availability/by_date/day-{date}/instruments.parquet"
    
    if not prod_bucket.blob(instruments_path).exists():
        print(f"⚠️  Production instruments not found for {date} in {prod_bucket_name}")
        return False
    
    return copy_blob(prod_bucket, test_bucket, instruments_path)


def copy_market_data_for_date(
    client: storage.Client,
    project_id: str,
    date: str,
    category: str = None,
):
    """Copy market data for a specific date (sample instruments only)."""
    # Production bucket
    if category:
        prod_bucket_name = get_config(
            f"MARKET_DATA_GCS_BUCKET_{category}",
            f"market-data-tick-{category.lower()}-central-element-323112",
        )
        test_bucket_name = get_config(
            f"MARKET_DATA_GCS_BUCKET_{category}_TEST",
            f"market-data-tick-test-{category.lower()}-central-element-323112",
        )
    else:
        prod_bucket_name = get_config(
            "MARKET_DATA_GCS_BUCKET",
            "market-data-tick-central-element-323112",
        )
        test_bucket_name = get_config(
            "MARKET_DATA_GCS_BUCKET_TEST",
            "market-data-tick-test-central-element-323112",
        )
    
    prod_bucket = client.bucket(prod_bucket_name)
    test_bucket = client.bucket(test_bucket_name)
    
    # Ensure test bucket exists
    if not test_bucket.exists():
        print(f"📦 Creating test bucket: {test_bucket_name}")
        location = get_config("GCS_LOCATION", "asia-northeast1")
        test_bucket.create(location=location)
    
    # Copy sample market data files (one instrument per category for testing)
    # This is a simplified copy - just ensure structure exists
    # Full data copy would be too large
    
    # List some sample files from production
    prefix = f"market_data/by_date/day-{date}/"
    blobs = list(prod_bucket.list_blobs(prefix=prefix, max_results=5))
    
    if not blobs:
        print(f"⚠️  No market data found for {date} in {prod_bucket_name}")
        return False
    
    copied = 0
    for blob in blobs[:3]:  # Copy first 3 files as samples
        blob_name = blob.name
        if copy_blob(prod_bucket, test_bucket, blob_name):
            copied += 1
    
    print(f"✅ Copied {copied} market data files for {date}")
    return copied > 0


def main():
    """Main function to copy production data to test buckets."""
    print("=" * 70)
    print("COPY PRODUCTION DATA TO TEST BUCKETS")
    print("=" * 70)
    
    # Configuration
    project_id = get_config("GCP_PROJECT_ID", "central-element-323112")
    credentials_file = get_config(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "central-element-323112-e35fb0ddafe2.json",
    )
    
    if not Path(credentials_file).exists():
        print(f"❌ Credentials file not found: {credentials_file}")
        sys.exit(1)
    
    # Test date: Sep 23, 2024
    test_date = "2024-09-23"
    
    print(f"\n📅 Test Date: {test_date}")
    print(f"📦 Project: {project_id}")
    print(f"🔑 Credentials: {credentials_file}\n")
    
    # Get storage client
    client = get_storage_client(project_id, credentials_file)
    
    # Copy instruments for each category
    categories = ["CEFI", "TRADFI", "DEFI"]
    
    print("\n" + "=" * 70)
    print("COPYING INSTRUMENTS")
    print("=" * 70)
    
    for category in categories:
        print(f"\n📊 Copying {category} instruments...")
        copy_instruments_for_date(client, project_id, test_date, category)
    
    # Copy market data samples
    print("\n" + "=" * 70)
    print("COPYING MARKET DATA SAMPLES")
    print("=" * 70)
    
    for category in categories:
        print(f"\n📊 Copying {category} market data samples...")
        copy_market_data_for_date(client, project_id, test_date, category)
    
    print("\n" + "=" * 70)
    print("✅ DATA COPY COMPLETE")
    print("=" * 70)
    print(f"\nTest buckets now have data for {test_date}")
    print("You can now run tests against real data structure.")


if __name__ == "__main__":
    main()



