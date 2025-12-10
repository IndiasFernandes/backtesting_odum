"""
Pytest configuration and fixtures for unified-cloud-services tests.

Provides:
- Test bucket configuration
- Automatic test bucket creation and permission setup
- Real GCP credentials setup
- Cloud target fixtures for test environment
"""

# ============================================================================
# CRITICAL: Load .env file FIRST, before ANY imports that depend on env vars
# ============================================================================
import os
from pathlib import Path

def _load_env_early():
    """Load .env file and resolve relative credential paths."""
    tests_dir = Path(__file__).parent
    project_root = tests_dir.parent
    env_path = project_root / ".env"
    
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=env_path, override=True)
            
            # Resolve relative GOOGLE_APPLICATION_CREDENTIALS path
            creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if creds_path and not Path(creds_path).is_absolute():
                abs_creds_path = (project_root / creds_path).resolve()
                if abs_creds_path.exists():
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(abs_creds_path)
                else:
                    parent_creds = project_root.parent / creds_path
                    if parent_creds.exists():
                        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(parent_creds.resolve())
        except ImportError:
            pass

_load_env_early()

# ============================================================================
# Now safe to import modules that depend on environment variables
# ============================================================================
import pytest
import json
from typing import Optional
from google.cloud import storage
from google.oauth2 import service_account
from unified_cloud_services import CloudTarget, get_secret_with_fallback
from unified_cloud_services.core.config import unified_config


def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get configuration value from environment or unified_config."""
    env_value = os.getenv(key)
    if env_value is not None:
        return env_value
    
    config_key = key.lower()
    if hasattr(unified_config, config_key):
        return getattr(unified_config, config_key)
    
    return default


def cred_file_exists() -> Optional[str]:
    """Find GCP credentials file in common locations."""
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and Path(creds_path).exists():
        return creds_path
    return None


@pytest.fixture(scope="session")
def gcp_credentials():
    """Setup GCP credentials for tests."""
    cred_file = cred_file_exists()
    if not cred_file:
        pytest.skip("GCP credentials file not found")
    return cred_file


@pytest.fixture(scope="session")
def gcp_project_id():
    """GCP project ID for tests."""
    return get_config("GCP_PROJECT_ID", "central-element-323112")


@pytest.fixture(scope="session")
def test_instruments_bucket():
    """Test instruments bucket name."""
    return get_config("INSTRUMENTS_GCS_BUCKET_TEST", "instruments-store-test-central-element-323112")


@pytest.fixture(scope="session")
def test_market_data_bucket():
    """Test market data bucket name."""
    return get_config("MARKET_DATA_GCS_BUCKET_TEST", "market-data-tick-test-central-element-323112")


@pytest.fixture(scope="session")
def test_bigquery_dataset():
    """BigQuery dataset for tests."""
    return get_config("INSTRUMENTS_BIGQUERY_DATASET", "instruments")


def get_service_account_email(credentials_file: str) -> Optional[str]:
    """Extract service account email from credentials file."""
    try:
        with open(credentials_file, "r") as f:
            creds = json.load(f)
            return creds.get("client_email")
    except Exception:
        return None


def ensure_test_bucket_exists(
    project_id: str,
    bucket_name: str,
    credentials_file: str,
    location: str = "asia-northeast1",
) -> bool:
    """Ensure test bucket exists and service account has permissions."""
    try:
        credentials = service_account.Credentials.from_service_account_file(credentials_file)
        storage_client = storage.Client(project=project_id, credentials=credentials)
        
        bucket = storage_client.bucket(bucket_name)
        if bucket.exists():
            try:
                bucket.reload()
                return True
            except Exception as e:
                pytest.skip(f"Test bucket exists but not accessible: {e}")
                return False
        
        print(f"📦 Creating test bucket: {bucket_name} in {location}")
        bucket.create(location=location)
        print(f"✅ Created test bucket: {bucket_name}")
        
        service_account_email = get_service_account_email(credentials_file)
        if service_account_email:
            try:
                policy = bucket.get_iam_policy(requested_policy_version=3)
                binding_found = False
                for binding in policy.bindings:
                    if binding["role"] == "roles/storage.objectAdmin":
                        member = f"serviceAccount:{service_account_email}"
                        if member not in binding["members"]:
                            binding["members"].add(member)
                        binding_found = True
                        break
                
                if not binding_found:
                    policy.bindings.append({
                        "role": "roles/storage.objectAdmin",
                        "members": {f"serviceAccount:{service_account_email}"},
                    })
                
                bucket.set_iam_policy(policy)
                print(f"✅ Granted permissions to {service_account_email}")
            except Exception as e:
                print(f"⚠️  Could not set IAM policy: {e}")
        
        return True
    except Exception as e:
        pytest.skip(f"Could not create/access test bucket {bucket_name}: {e}")
        return False


@pytest.fixture(scope="session")
def ensure_test_resources(gcp_credentials, gcp_project_id, test_instruments_bucket, test_market_data_bucket):
    """Ensure test resources (buckets) exist and have proper permissions."""
    if not gcp_credentials:
        pytest.skip("GCP credentials required for test resource setup")
    
    location = get_config("GCS_LOCATION", "asia-northeast1")
    
    ensure_test_bucket_exists(
        project_id=gcp_project_id,
        bucket_name=test_instruments_bucket,
        credentials_file=gcp_credentials,
        location=location,
    )
    
    ensure_test_bucket_exists(
        project_id=gcp_project_id,
        bucket_name=test_market_data_bucket,
        credentials_file=gcp_credentials,
        location=location,
    )
    
    yield


@pytest.fixture(scope="session")
def test_instruments_cloud_target(gcp_project_id, test_instruments_bucket, test_bigquery_dataset, ensure_test_resources):
    """Cloud target configured for test instruments bucket."""
    return CloudTarget(
        project_id=gcp_project_id,
        gcs_bucket=test_instruments_bucket,
        bigquery_dataset=test_bigquery_dataset,
    )


@pytest.fixture(scope="session")
def test_market_data_cloud_target(gcp_project_id, test_market_data_bucket, test_bigquery_dataset, ensure_test_resources):
    """Cloud target configured for test market data bucket."""
    return CloudTarget(
        project_id=gcp_project_id,
        gcs_bucket=test_market_data_bucket,
        bigquery_dataset=test_bigquery_dataset,
    )


@pytest.fixture(autouse=True)
def setup_test_environment(gcp_credentials, test_instruments_bucket, test_market_data_bucket):
    """Automatically setup test environment for all tests."""
    # Set test buckets in environment
    os.environ["INSTRUMENTS_GCS_BUCKET_TEST"] = test_instruments_bucket
    os.environ["MARKET_DATA_GCS_BUCKET_TEST"] = test_market_data_bucket
    
    # Set category-specific test buckets
    if "INSTRUMENTS_GCS_BUCKET_CEFI_TEST" not in os.environ:
        os.environ["INSTRUMENTS_GCS_BUCKET_CEFI_TEST"] = "instruments-store-test-cefi-central-element-323112"
    if "INSTRUMENTS_GCS_BUCKET_TRADFI_TEST" not in os.environ:
        os.environ["INSTRUMENTS_GCS_BUCKET_TRADFI_TEST"] = "instruments-store-test-tradfi-central-element-323112"
    if "INSTRUMENTS_GCS_BUCKET_DEFI_TEST" not in os.environ:
        os.environ["INSTRUMENTS_GCS_BUCKET_DEFI_TEST"] = "instruments-store-test-defi-central-element-323112"
    
    yield



