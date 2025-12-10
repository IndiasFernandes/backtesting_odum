"""
Google Cloud Secret Manager utilities for secure API key retrieval.

Generic utilities for retrieving secrets from Google Cloud Secret Manager,
with fallback to environment variables for local development.

This module provides reusable Secret Manager utilities for all trading system repositories.
"""

import os
import logging
from threading import Lock
from google.auth.exceptions import DefaultCredentialsError
from google.api_core import exceptions as gcp_exceptions

from unified_cloud_services.core.cloud_auth_factory import CloudAuthFactory
from unified_cloud_services.core.config import unified_config

logger = logging.getLogger(__name__)

# Module-level cache for secrets: {project_id: {secret_name: secret_value}}
# Secrets are static and don't change during runtime, so caching avoids repeated Secret Manager calls
_SECRET_CACHE: dict[str, dict[str, str]] = {}
_CACHE_LOCK = Lock()

# Module-level cache for Secret Manager clients: {project_id: client}
# Client initialization involves GCP API setup which is slow (~0.5s)
_CLIENT_CACHE: dict[str, "SecretManagerClient"] = {}
_CLIENT_LOCK = Lock()


class SecretManagerClient:
    """Generic client for retrieving secrets from Google Cloud Secret Manager."""

    def __init__(self, project_id: str, credentials_path: str | None = None):
        """
        Initialize the Secret Manager client.

        Args:
            project_id: GCP project ID
            credentials_path: Path to service account credentials (optional)
        """
        self.project_id = project_id
        self.client = None
        self._initialize_client(credentials_path)

    def _resolve_credentials_path(self, credentials_path: str | None) -> str | None:
        """
        Resolve credentials file path, checking multiple locations.

        Generic credential resolution logic reusable across all repos.

        Checks:
        1. Path as-is (absolute or relative to current directory)
        2. Relative to project root (where pyproject.toml exists)
        3. Try finding the file by name in common locations

        Returns:
            Resolved absolute path if found, None otherwise
        """
        if not credentials_path or not credentials_path.strip():
            return None

        # Try absolute path first
        if os.path.isabs(credentials_path):
            if os.path.exists(credentials_path):
                return os.path.abspath(credentials_path)
            return None

        # Clean the path (remove leading ./)
        clean_path = credentials_path.lstrip("./")
        filename = os.path.basename(clean_path)

        # Try relative to current directory
        current_dir = os.path.abspath(os.getcwd())
        current_dir_path = os.path.join(current_dir, clean_path)
        if os.path.exists(current_dir_path):
            return os.path.abspath(current_dir_path)

        # Also try just filename in current directory
        current_dir_filename = os.path.join(current_dir, filename)
        if os.path.exists(current_dir_filename):
            return os.path.abspath(current_dir_filename)

        # Find project root by walking up directory tree
        # Prefer directories that have BOTH pyproject.toml AND the credentials file
        check_dir = current_dir
        project_root = None
        best_project_root = None  # Directory with both pyproject.toml and credentials

        for level in range(15):  # Walk up max 15 levels (more generous)
            pyproject_path = os.path.join(check_dir, "pyproject.toml")
            credentials_test_path = os.path.join(check_dir, filename)

            if os.path.exists(pyproject_path):
                # Found a project root candidate
                if not project_root:
                    project_root = check_dir  # First one found

                # Check if this directory also has the credentials file (preferred)
                if os.path.exists(credentials_test_path):
                    best_project_root = check_dir
                    logger.debug(
                        f"✅ Found ideal project root (has both pyproject.toml and credentials) at level {level}: {best_project_root}"
                    )
                    break  # Found the best match, stop searching

                logger.debug(
                    f"Found project root candidate at level {level}: {check_dir} (no credentials here)"
                )

            parent_dir = os.path.dirname(check_dir)
            if parent_dir == check_dir:  # Reached filesystem root
                break
            check_dir = parent_dir

        # Use best project root if found, otherwise use first project root
        search_root = best_project_root or project_root

        if search_root:
            # Try relative path from project root
            project_root_path = os.path.join(search_root, clean_path)
            if os.path.exists(project_root_path):
                logger.debug(f"✅ Found credentials relative to project root: {project_root_path}")
                return os.path.abspath(project_root_path)

            # Try just the filename in project root
            project_root_filename = os.path.join(search_root, filename)
            if os.path.exists(project_root_filename):
                logger.debug(f"✅ Found credentials file in project root: {project_root_filename}")
                return os.path.abspath(project_root_filename)

        # Last resort: Try to find file by name walking up from current directory
        # This handles cases where the file exists but project root detection failed
        search_dir = current_dir
        for level in range(20):  # Walk up more levels to handle deeply nested structures
            # Try both with and without the leading path components
            test_path = os.path.join(search_dir, clean_path)
            if os.path.exists(test_path):
                logger.debug(f"✅ Found credentials by walking up (level {level}): {test_path}")
                return os.path.abspath(test_path)

            test_filename = os.path.join(search_dir, filename)
            if os.path.exists(test_filename):
                logger.debug(
                    f"✅ Found credentials filename by walking up (level {level}): {test_filename}"
                )
                return os.path.abspath(test_filename)

            parent_dir = os.path.dirname(search_dir)
            if parent_dir == search_dir:  # Reached filesystem root
                break
            search_dir = parent_dir

        # Not found
        return None

    def _initialize_client(self, credentials_path: str | None = None):
        """Initialize the Secret Manager client using CloudAuthFactory."""
        try:
            # Use CloudAuthFactory for consistent authentication across all services
            environment = unified_config.environment.lower()
            is_development = environment in ["development", "dev", "local"]

            # Handle credentials path for development
            # If None and GOOGLE_APPLICATION_CREDENTIALS is explicitly empty, use ADC
            if is_development and credentials_path is None:
                env_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
                if env_creds == "":
                    # Explicitly set to empty string to use ADC
                    credentials_path = ""
                elif env_creds:
                    # Use the env var value
                    credentials_path = env_creds

            # Resolve credentials path for development
            if is_development and credentials_path and credentials_path != "":
                resolved_path = self._resolve_credentials_path(credentials_path)
                if resolved_path:
                    credentials_path = resolved_path
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
                    logger.debug(f"✅ DEVELOPMENT: Using resolved credentials: {credentials_path}")

            # Use CloudAuthFactory for client creation
            self.client = CloudAuthFactory.create_authenticated_secret_client(
                project_id=self.project_id, credentials_path=credentials_path
            )

            logger.info("✅ Secret Manager client initialized successfully")

        except DefaultCredentialsError as e:
            logger.error(f"Google Cloud credentials not found or invalid: {e}")
            self.client = None
        except Exception as e:
            logger.error(f"Unexpected error initializing Secret Manager client: {e}")
            self.client = None

    def get_secret(self, secret_name: str, version: str = "latest") -> str | None:
        """
        Retrieve a secret from Secret Manager.

        Args:
            secret_name: Name of the secret (without project prefix)
            version: Secret version (default: "latest")

        Returns:
            Secret value as string, or None if not found
        """
        if not self.client:
            logger.error("Secret Manager client not available - cannot retrieve secrets")
            return None

        try:
            # Construct the resource name
            secret_path = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"
            logger.debug(f"Attempting to retrieve secret from path: {secret_path}")

            # Access the secret version
            response = self.client.access_secret_version(request={"name": secret_path})

            # Decode the secret value
            secret_value = response.payload.data.decode("UTF-8")
            logger.info(f"✅ Successfully retrieved secret: {secret_name}")
            return secret_value

        except gcp_exceptions.NotFound:
            logger.error(
                f"Secret not found in Secret Manager: {secret_name} (project: {self.project_id})"
            )
            return None
        except gcp_exceptions.PermissionDenied:
            logger.error(
                f"Permission denied accessing secret: {secret_name} (project: {self.project_id})"
            )
            return None
        except gcp_exceptions.Unauthenticated:
            logger.error(f"Authentication failed when accessing secret: {secret_name}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving secret {secret_name}: {e}")
            return None

    def get_secrets(self, secret_names: list, version: str = "latest") -> dict[str, str | None]:
        """
        Retrieve multiple secrets from Secret Manager.

        Args:
            secret_names: List of secret names
            version: Secret version (default: "latest")

        Returns:
            Dictionary mapping secret names to their values
        """
        secrets = {}
        for secret_name in secret_names:
            secrets[secret_name] = self.get_secret(secret_name, version)
        return secrets


def get_secret_with_fallback(
    secret_name: str,
    project_id: str,
    fallback_env_var: str | None = None,
    credentials_path: str | None = None,
    version: str = "latest",
) -> str | None:
    """
    Get secret from Secret Manager with fallback to environment variable.

    Includes module-level caching to avoid repeated Secret Manager calls.
    Secrets are static and don't change during runtime, so caching is safe.

    Generic utility reusable across all repos.

    Args:
        secret_name: Name of the secret in Secret Manager
        project_id: GCP project ID
        fallback_env_var: Environment variable name for fallback (optional)
        credentials_path: Path to service account credentials (optional)
        version: Secret version (default: "latest")

    Returns:
        Secret value as string, or None if not found
    """
    # Check cache first (thread-safe)
    with _CACHE_LOCK:
        if project_id in _SECRET_CACHE:
            if secret_name in _SECRET_CACHE[project_id]:
                cached_value = _SECRET_CACHE[project_id][secret_name]
                logger.debug(f"✅ Using cached secret: {secret_name}")
                return cached_value

    # Try environment variable first (fastest, no network call)
    if fallback_env_var:
        env_value = getattr(unified_config, fallback_env_var, None)
        if env_value:
            logger.debug(f"✅ Retrieved secret from environment variable: {fallback_env_var}")
            # Cache it
            with _CACHE_LOCK:
                if project_id not in _SECRET_CACHE:
                    _SECRET_CACHE[project_id] = {}
                _SECRET_CACHE[project_id][secret_name] = env_value
            return env_value

    logger.info(f"Attempting to retrieve secret: {secret_name} (project: {project_id})")

    # Try Secret Manager (with client caching for performance)
    try:
        # Use cached client if available (saves ~0.5s per call)
        with _CLIENT_LOCK:
            cache_key = f"{project_id}_{credentials_path or 'default'}"
            if cache_key in _CLIENT_CACHE:
                secret_client = _CLIENT_CACHE[cache_key]
                logger.debug(f"✅ Using cached Secret Manager client for {project_id}")
            else:
                secret_client = SecretManagerClient(project_id, credentials_path)
                if secret_client.client is not None:
                    _CLIENT_CACHE[cache_key] = secret_client
                    logger.debug(f"✅ Cached Secret Manager client for {project_id}")

        if secret_client.client is None:
            logger.warning(
                "Secret Manager client initialization failed - skipping Secret Manager lookup"
            )
        else:
            secret_value = secret_client.get_secret(secret_name, version)

            if secret_value:
                logger.info(f"✅ Retrieved secret from Secret Manager: {secret_name}")
                # Cache it (thread-safe)
                with _CACHE_LOCK:
                    if project_id not in _SECRET_CACHE:
                        _SECRET_CACHE[project_id] = {}
                    _SECRET_CACHE[project_id][secret_name] = secret_value
                return secret_value
            else:
                logger.warning(f"Secret {secret_name} not found in Secret Manager or returned None")

    except Exception as e:
        logger.error(f"Exception during Secret Manager retrieval: {e}")

    logger.error(f"Secret {secret_name} not found in Secret Manager or environment variable")
    return None


def clear_secret_cache(project_id: str | None = None, clear_clients: bool = False):
    """
    Clear secret cache and optionally client cache.

    Useful for testing or when secrets need to be refreshed.

    Args:
        project_id: If provided, clear only secrets for this project. Otherwise clear all.
        clear_clients: If True, also clear cached Secret Manager clients.
    """
    with _CACHE_LOCK:
        if project_id:
            if project_id in _SECRET_CACHE:
                del _SECRET_CACHE[project_id]
                logger.debug(f"Cleared secret cache for project: {project_id}")
        else:
            _SECRET_CACHE.clear()
            logger.debug("Cleared all secret caches")

    if clear_clients:
        with _CLIENT_LOCK:
            if project_id:
                # Clear clients for specific project
                keys_to_delete = [k for k in _CLIENT_CACHE if k.startswith(f"{project_id}_")]
                for key in keys_to_delete:
                    del _CLIENT_CACHE[key]
                logger.debug(f"Cleared client cache for project: {project_id}")
            else:
                _CLIENT_CACHE.clear()
                logger.debug("Cleared all client caches")


def get_secrets_with_fallback(
    secret_mappings: dict[str, str],
    project_id: str,
    credentials_path: str | None = None,
) -> dict[str, str | None]:
    """
    Get multiple secrets from Secret Manager with environment variable fallbacks.

    Generic utility reusable across all repos.

    Args:
        secret_mappings: Dictionary mapping secret names to environment variable names
        project_id: GCP project ID
        credentials_path: Path to service account credentials (optional)

    Returns:
        Dictionary with configuration values
    """
    config = {}

    try:
        secret_client = SecretManagerClient(project_id, credentials_path)

        for secret_name, env_var in secret_mappings.items():
            # Try Secret Manager first
            secret_value = secret_client.get_secret(secret_name)

            if secret_value:
                config[env_var] = secret_value
                logger.info(f"✅ Retrieved {secret_name} from Secret Manager")
            else:
                # Fallback to environment variable
                env_value = getattr(unified_config, env_var, None)
                if env_value:
                    config[env_var] = env_value
                    logger.info(f"✅ Retrieved {env_var} from environment variable")
                else:
                    config[env_var] = None
                    logger.warning(f"⚠️ Neither secret {secret_name} nor env var {env_var} found")

    except Exception as e:
        logger.error(f"Error retrieving secrets: {e}")
        # Fallback to environment variables only
        for secret_name, env_var in secret_mappings.items():
            config[env_var] = getattr(unified_config, env_var, None)

    return config


def create_secret_if_not_exists(
    project_id: str,
    secret_name: str,
    secret_value: str,
    credentials_path: str | None = None,
) -> bool:
    """
    Create a secret in Secret Manager if it doesn't exist.

    Generic utility reusable across all repos.

    Args:
        project_id: GCP project ID
        secret_name: Name of the secret
        secret_value: Value to store
        credentials_path: Path to service account credentials (optional)

    Returns:
        True if secret was created or already exists, False otherwise
    """
    try:
        secret_client = SecretManagerClient(project_id, credentials_path)

        if not secret_client.client:
            logger.error("Secret Manager client not available")
            return False

        # Check if secret exists
        secret_path = f"projects/{project_id}/secrets/{secret_name}"

        try:
            secret_client.client.get_secret(request={"name": secret_path})
            logger.info(f"✅ Secret {secret_name} already exists")
            return True
        except gcp_exceptions.NotFound:
            # Secret doesn't exist, create it
            pass

        # Create the secret
        parent = f"projects/{project_id}"
        secret = {"replication": {"automatic": {}}}

        secret_client.client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_name,
                "secret": secret,
            }
        )

        # Add the secret version
        version_path = f"projects/{project_id}/secrets/{secret_name}"
        secret_version = {"data": secret_value.encode("UTF-8")}

        secret_client.client.add_secret_version(
            request={"parent": version_path, "payload": secret_version}
        )

        logger.info(f"✅ Successfully created secret: {secret_name}")
        return True

    except Exception as e:
        logger.error(f"❌ Error creating secret {secret_name}: {e}")
        return False
