"""
Cloud Authentication Factory

Centralized authentication logic for all Google Cloud services.
Eliminates duplication across cloud services.

Design Philosophy:
- Single source of truth for authentication
- Environment-aware credential handling
- Reusable across all cloud services
- Easy to test and maintain
"""

import os
import logging
from pathlib import Path

# Google Cloud imports
from google.cloud import storage, bigquery, secretmanager
from google.oauth2 import service_account
from unified_cloud_services.core.config import unified_config

logger = logging.getLogger(__name__)


def _find_credentials_file() -> str | None:
    """
    Auto-detect credentials file in development mode only.

    Searches common locations for credentials files.
    Only used in development mode - production uses VM service account.

    Returns:
        Path to credentials file if found, None otherwise
    """
    # Common credentials file names
    credentials_filenames = [
        "central-element-323112-e35fb0ddafe2.json",
        "credentials.json",
        "gcp-credentials.json",
        "service-account.json",
    ]

    # Search locations (in order of preference)
    search_locations = [
        Path.cwd(),  # Current directory
        Path.cwd().parent,  # Parent directory
        Path.cwd().parent.parent,  # Grandparent (unified-trading-system-repos root)
        Path.home(),  # Home directory
    ]

    # Search for credentials file
    for search_dir in search_locations:
        for filename in credentials_filenames:
            creds_path = search_dir / filename
            if creds_path.exists():
                logger.info(f"✅ Auto-detected credentials file: {creds_path}")
                return str(creds_path.resolve())

    return None


def _auto_detect_credentials(environment: str, credentials_path: str | None) -> str | None:
    """
    Auto-detect credentials file if not provided and in development mode.

    Args:
        environment: Environment type (development, production, etc.)
        credentials_path: Existing credentials path (if any)

    Returns:
        Credentials path (existing or auto-detected)
    """
    # Only auto-detect in development mode
    if environment.lower() not in ["development", "dev", "local"]:
        return credentials_path

    # If credentials path is explicitly set to empty string, don't auto-detect (use ADC)
    if credentials_path == "":
        return None

    # If credentials path already set and exists, use it
    if credentials_path and os.path.exists(credentials_path):
        return credentials_path

    # If GOOGLE_APPLICATION_CREDENTIALS env var is explicitly set to empty, don't auto-detect (use ADC)
    env_creds = unified_config.google_application_credentials_path
    if env_creds == "":
        return None
    if env_creds and os.path.exists(env_creds):
        return env_creds

    # Auto-detect credentials file only if not explicitly disabled
    # Check if GOOGLE_APPLICATION_CREDENTIALS env var is explicitly set to empty
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") == "":
        return None
    
    detected_path = _find_credentials_file()
    if detected_path:
        # Set environment variable for consistency
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = detected_path
        return detected_path

    return credentials_path


class CloudAuthFactory:
    """
    **CENTRALIZED CLOUD AUTHENTICATION FACTORY**

    Single source of truth for all Google Cloud authentication.
    Eliminates duplication across multiple services.
    """

    @staticmethod
    def create_authenticated_gcs_client(
        project_id: str | None = None,
        credentials_path: str | None = None,
        environment: str | None = None,
    ) -> storage.Client:
        """
        Create authenticated GCS client with environment awareness

        Args:
            project_id: Google Cloud project ID (defaults to env var)
            credentials_path: Path to credentials file (defaults to env var)
            environment: Environment type (defaults to env var)

        Returns:
            Authenticated GCS client
        """

        # Get values from environment if not provided
        project_id = project_id or unified_config.gcp_project_id
        credentials_path = credentials_path or unified_config.google_application_credentials_path
        environment = environment or unified_config.environment

        # Auto-detect credentials in development mode only
        credentials_path = _auto_detect_credentials(environment, credentials_path)

        if environment.lower() in ["development", "dev", "local"]:
            if credentials_path and os.path.exists(credentials_path):
                logger.debug(f"✅ GCS DEVELOPMENT: Using explicit credentials: {credentials_path}")
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )
                return storage.Client(project=project_id, credentials=credentials)
            else:
                raise ValueError(
                    f"Development environment requires GOOGLE_APPLICATION_CREDENTIALS. "
                    f"Current path: {credentials_path}"
                )

        elif environment.lower() in ["production", "prod", "vm"]:
            if credentials_path:
                logger.warning(
                    f"⚠️ GCS PRODUCTION: Credentials file should not be used in production"
                )

            logger.debug("✅ GCS PRODUCTION: Using VM service account authentication")
            return storage.Client(project=project_id)

        else:
            logger.warning(
                f"⚠️ GCS UNKNOWN ENVIRONMENT: {environment}, using default authentication"
            )
            if credentials_path and os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )
                return storage.Client(project=project_id, credentials=credentials)
            else:
                return storage.Client(project=project_id)

    @staticmethod
    def create_authenticated_bigquery_client(
        project_id: str | None = None,
        credentials_path: str | None = None,
        environment: str | None = None,
    ) -> bigquery.Client:
        """
        Create authenticated BigQuery client with environment awareness

        Args:
            project_id: Google Cloud project ID (defaults to env var)
            credentials_path: Path to credentials file (defaults to env var)
            environment: Environment type (defaults to env var)

        Returns:
            Authenticated BigQuery client
        """

        # Get values from environment if not provided
        project_id = project_id or unified_config.gcp_project_id
        credentials_path = credentials_path or unified_config.google_application_credentials_path
        environment = environment or unified_config.environment

        # Auto-detect credentials in development mode only
        credentials_path = _auto_detect_credentials(environment, credentials_path)

        if environment.lower() in ["development", "dev", "local"]:
            if credentials_path and os.path.exists(credentials_path):
                logger.debug(
                    f"✅ BigQuery DEVELOPMENT: Using explicit credentials: {credentials_path}"
                )
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )
                return bigquery.Client(project=project_id, credentials=credentials)
            else:
                raise ValueError(
                    f"Development environment requires GOOGLE_APPLICATION_CREDENTIALS. "
                    f"Current path: {credentials_path}"
                )

        elif environment.lower() in ["production", "prod", "vm"]:
            if credentials_path:
                logger.warning(
                    f"⚠️ BigQuery PRODUCTION: Credentials file should not be used in production"
                )

            logger.debug("✅ BigQuery PRODUCTION: Using VM service account authentication")
            return bigquery.Client(project=project_id)

        else:
            logger.warning(
                f"⚠️ BigQuery UNKNOWN ENVIRONMENT: {environment}, using default authentication"
            )
            if credentials_path and os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )
                return bigquery.Client(project=project_id, credentials=credentials)
            else:
                return bigquery.Client(project=project_id)

    @staticmethod
    def create_authenticated_secret_client(
        project_id: str | None = None,
        credentials_path: str | None = None,
        environment: str | None = None,
    ) -> secretmanager.SecretManagerServiceClient:
        """
        Create authenticated Secret Manager client with environment awareness

        Args:
            project_id: Google Cloud project ID (defaults to env var)
            credentials_path: Path to credentials file (defaults to env var)
            environment: Environment type (defaults to env var)

        Returns:
            Authenticated Secret Manager client
        """

        # Get values from environment if not provided
        project_id = project_id or unified_config.gcp_project_id
        credentials_path = credentials_path or unified_config.google_application_credentials_path
        environment = environment or unified_config.environment

        # Auto-detect credentials in development mode only
        # Track if original was empty string (to use ADC)
        was_empty_string = credentials_path == ""
        credentials_path = _auto_detect_credentials(environment, credentials_path)

        if environment.lower() in ["development", "dev", "local"]:
            if credentials_path and os.path.exists(credentials_path):
                logger.debug(
                    f"✅ SecretManager DEVELOPMENT: Using explicit credentials: {credentials_path}"
                )
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )
                return secretmanager.SecretManagerServiceClient(credentials=credentials)
            elif credentials_path is None and was_empty_string:
                # None returned from empty string means use Application Default Credentials (gcloud auth)
                logger.debug(
                    "✅ SecretManager DEVELOPMENT: Using Application Default Credentials (gcloud auth)"
                )
                return secretmanager.SecretManagerServiceClient()
            elif credentials_path == "":
                # Empty string means user wants to use Application Default Credentials (gcloud auth)
                logger.debug(
                    "✅ SecretManager DEVELOPMENT: Using Application Default Credentials (gcloud auth)"
                )
                return secretmanager.SecretManagerServiceClient()
            else:
                raise ValueError(
                    f"Development environment requires GOOGLE_APPLICATION_CREDENTIALS. "
                    f"Current path: {credentials_path}. "
                    f"Set to empty string to use gcloud auth application-default login"
                )

        elif environment.lower() in ["production", "prod", "vm"]:
            if credentials_path:
                logger.warning(
                    f"⚠️ SecretManager PRODUCTION: Credentials file should not be used in production"
                )

            logger.debug("✅ SecretManager PRODUCTION: Using VM service account authentication")
            return secretmanager.SecretManagerServiceClient()

        else:
            logger.warning(
                f"⚠️ SecretManager UNKNOWN ENVIRONMENT: {environment}, using default authentication"
            )
            if credentials_path and os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )
                return secretmanager.SecretManagerServiceClient(credentials=credentials)
            else:
                return secretmanager.SecretManagerServiceClient()

    @staticmethod
    def validate_authentication(project_id: str | None = None) -> dict[str, bool]:
        """
        Validate authentication for all Google Cloud services

        Args:
            project_id: Project ID to test against

        Returns:
            Dict with validation results for each service
        """
        project_id = project_id or unified_config.gcp_project_id

        validation = {"gcs": False, "bigquery": False, "secret_manager": False}

        # Test GCS
        try:
            gcs_client = CloudAuthFactory.create_authenticated_gcs_client(project_id)
            # Test with a simple operation
            list(gcs_client.list_buckets(max_results=1))
            validation["gcs"] = True
            logger.info("✅ GCS authentication validated")
        except Exception as e:
            logger.warning(f"❌ GCS authentication failed: {e}")

        # Test BigQuery
        try:
            bq_client = CloudAuthFactory.create_authenticated_bigquery_client(project_id)
            # Test with a simple query
            query = "SELECT 1 as test_auth LIMIT 1"
            job = bq_client.query(query)
            job.result(timeout=30)
            validation["bigquery"] = True
            logger.info("✅ BigQuery authentication validated")
        except Exception as e:
            logger.warning(f"❌ BigQuery authentication failed: {e}")

        # Test Secret Manager
        try:
            sm_client = CloudAuthFactory.create_authenticated_secret_client(project_id)
            # Test by listing secrets (this validates permissions)
            parent = f"projects/{project_id}"
            list(sm_client.list_secrets(request={"parent": parent}, timeout=30))
            validation["secret_manager"] = True
            logger.info("✅ Secret Manager authentication validated")
        except Exception as e:
            logger.warning(f"❌ Secret Manager authentication failed: {e}")

        return validation


# Convenience functions for backward compatibility
def create_gcs_client(project_id: str | None = None) -> storage.Client:
    """Convenience function for GCS client creation"""
    return CloudAuthFactory.create_authenticated_gcs_client(project_id)


def create_bigquery_client(project_id: str | None = None) -> bigquery.Client:
    """Convenience function for BigQuery client creation"""
    return CloudAuthFactory.create_authenticated_bigquery_client(project_id)


def create_secret_manager_client(
    project_id: str | None = None,
) -> secretmanager.SecretManagerServiceClient:
    """Convenience function for Secret Manager client creation"""
    return CloudAuthFactory.create_authenticated_secret_client(project_id)
