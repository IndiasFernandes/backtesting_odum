"""
Test Configuration Helpers

Provides utilities for testing configuration and secret manager access uniformly.
Sets up test environment variables automatically so tests can run without manual exports.
"""

import os
import pytest
from typing import Dict, Optional
from pathlib import Path
from unittest.mock import Mock, patch


class TestConfigManager:
    """
    Manages test environment variables and secret manager mocks.

    Automatically sets up test environment so tests don't require manual env var exports.
    """

    DEFAULT_TEST_ENV = {
        "ENVIRONMENT": "test",
        "GOOGLE_CLOUD_PROJECT": "test-project-123",
        "GOOGLE_CLOUD_REGION": "us-central1",
        "BIGQUERY_LOCATION": "us-central1",
        "LOG_LEVEL": "DEBUG",
        "DEBUG": "true",
        # Service-specific defaults
        "FEATURES_GCS_BUCKET": "test-features-bucket",
        "FEATURES_DATASET": "test_features_data",
        "GCS_BUCKET": "test-market-data-bucket",
        "BIGQUERY_DATASET": "test_market_data",
        "STRATEGY_GCS_BUCKET": "test-strategy-bucket",
        "STRATEGY_DATASET": "test_strategy_orders",
        "ML_FEATURES_BUCKET": "test-ml-features-bucket",
        "ML_FEATURES_DATASET": "test_ml_features",
    }

    DEFAULT_TEST_SECRETS = {
        "tardis-api-key": "test-tardis-api-key-12345",
        "binance-api-key": "test-binance-api-key-12345",
        "binance-secret-key": "test-binance-secret-key-12345",
        "database-password": "test-db-password-12345",
    }

    def __init__(self):
        self.original_env: Dict[str, Optional[str]] = {}
        self.test_secrets: Dict[str, str] = {}
        self._secret_manager_mock = None

    def setup_test_env(self, custom_env: Optional[Dict[str, str]] = None):
        """
        Set up test environment variables.

        Args:
            custom_env: Optional custom environment variables to override defaults
        """
        # Save original values
        for key in self.DEFAULT_TEST_ENV.keys():
            self.original_env[key] = os.environ.get(key)

        # Set test environment variables
        env_vars = {**self.DEFAULT_TEST_ENV}
        if custom_env:
            env_vars.update(custom_env)

        for key, value in env_vars.items():
            os.environ[key] = value

    def teardown_test_env(self):
        """Restore original environment variables."""
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.original_env.clear()

    def setup_test_secrets(self, custom_secrets: Optional[Dict[str, str]] = None):
        """
        Set up test secrets.

        Args:
            custom_secrets: Optional custom secrets to override defaults
        """
        self.test_secrets = {**self.DEFAULT_TEST_SECRETS}
        if custom_secrets:
            self.test_secrets.update(custom_secrets)

    def get_secret_manager_mock(self):
        """
        Get a mock Secret Manager client that returns test secrets.

        Returns:
            Mock Secret Manager client
        """
        if self._secret_manager_mock is None:
            mock_client = Mock()

            def access_secret_version(request):
                secret_name = request["name"].split("/")[-3]  # Extract secret name from path
                version = request["name"].split("/")[-1]

                if secret_name in self.test_secrets:
                    mock_response = Mock()
                    mock_response.payload.data = self.test_secrets[secret_name].encode("UTF-8")
                    return mock_response
                else:
                    raise Exception(f"Secret {secret_name} not found in test secrets")

            mock_client.access_secret_version = Mock(side_effect=access_secret_version)
            self._secret_manager_mock = mock_client

        return self._secret_manager_mock


@pytest.fixture
def test_config_manager():
    """
    Pytest fixture that provides TestConfigManager instance.

    Automatically sets up and tears down test environment.
    """
    manager = TestConfigManager()
    manager.setup_test_env()
    manager.setup_test_secrets()

    yield manager

    manager.teardown_test_env()


@pytest.fixture
def mock_secret_manager(test_config_manager):
    """
    Pytest fixture that mocks Secret Manager with test secrets.

    Returns:
        Mock Secret Manager client
    """
    with patch(
        "unified_cloud_services.core.secret_manager.SecretManagerClient"
    ) as mock_client_class:
        mock_client = test_config_manager.get_secret_manager_mock()
        mock_instance = Mock()
        mock_instance.client = mock_client
        mock_instance.get_secret = Mock(
            side_effect=lambda name, version="latest": test_config_manager.test_secrets.get(name)
        )
        mock_client_class.return_value = mock_instance

        yield mock_instance


@pytest.fixture
def mock_cloud_auth_factory():
    """
    Pytest fixture that mocks CloudAuthFactory for testing.

    Returns test credentials without requiring actual GCP credentials.
    """
    with (
        patch("unified_cloud_services.core.cloud_auth_factory.CloudAuthFactory") as mock_factory,
        patch("unified_cloud_services.core.secret_manager.CloudAuthFactory") as mock_secret_factory,
    ):
        # Mock create_authenticated_secret_client
        mock_secret_client = Mock()
        mock_factory.create_authenticated_secret_client = Mock(return_value=mock_secret_client)

        # Mock create_authenticated_bigquery_client
        mock_bq_client = Mock()
        mock_factory.create_authenticated_bigquery_client = Mock(return_value=mock_bq_client)

        # Mock create_authenticated_storage_client
        mock_storage_client = Mock()
        mock_factory.create_authenticated_storage_client = Mock(return_value=mock_storage_client)

        yield mock_factory


def assert_config_loaded(config_instance, expected_project_id: str = "test-project-123"):
    """
    Assert that a config instance loaded values correctly.

    Args:
        config_instance: Config instance (BaseServiceConfig or subclass)
        expected_project_id: Expected project ID
    """
    assert config_instance.gcp_project_id == expected_project_id
    assert config_instance.environment == "test"
    assert config_instance.gcp_region == "us-central1"
    assert config_instance.bigquery_location == "us-central1"


def assert_secret_retrieved(secret_value: str, expected_secret: str):
    """
    Assert that a secret was retrieved correctly.

    Args:
        secret_value: Retrieved secret value
        expected_secret: Expected secret value
    """
    assert secret_value == expected_secret
    assert secret_value is not None
    assert len(secret_value) > 0
