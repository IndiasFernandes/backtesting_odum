"""
Test Uniform Configuration Access

Tests that all services access environment variables and secret manager uniformly.
These tests run without requiring manual env var exports.
"""

import pytest
import os
from unittest.mock import Mock
from unified_cloud_services import BaseServiceConfig, CloudTarget
from unified_cloud_services.testing.test_config_helpers import (
    test_config_manager,
    mock_secret_manager,
    mock_cloud_auth_factory,
    assert_config_loaded,
    assert_secret_retrieved,
)


class FeaturesConfig(BaseServiceConfig):
    """Test config for features service."""

    base_timeframe: str = "5m"
    features_dataset: str = "test_features_data"


class MarketDataConfig(BaseServiceConfig):
    """Test config for market data service."""

    market_data_dataset: str = "test_market_data"


class StrategyConfig(BaseServiceConfig):
    """Test config for strategy service."""

    strategy_dataset: str = "test_strategy_orders"


class MLTrainingConfig(BaseServiceConfig):
    """Test config for ML training service."""

    ml_features_dataset: str = "test_ml_features"


class TestUniformConfigAccess:
    """Test that all services access config uniformly."""

    def test_base_service_config_loads_env_vars(self, test_config_manager):
        """Test that BaseServiceConfig loads environment variables correctly."""
        config = BaseServiceConfig()

        assert_config_loaded(config)
        assert config.log_level == "DEBUG"
        assert config.debug is True

    def test_features_config_loads_env_vars(self, test_config_manager):
        """Test that features service config loads correctly."""
        config = FeaturesConfig()

        assert_config_loaded(config)
        assert config.features_dataset == "test_features_data"
        assert config.base_timeframe == "5m"

    def test_market_data_config_loads_env_vars(self, test_config_manager):
        """Test that market data service config loads correctly."""
        config = MarketDataConfig()

        assert_config_loaded(config)
        assert config.market_data_dataset == "test_market_data"

    def test_strategy_config_loads_env_vars(self, test_config_manager):
        """Test that strategy service config loads correctly."""
        config = StrategyConfig()

        assert_config_loaded(config)
        assert config.strategy_dataset == "test_strategy_orders"

    def test_ml_training_config_loads_env_vars(self, test_config_manager):
        """Test that ML training service config loads correctly."""
        config = MLTrainingConfig()

        assert_config_loaded(config)
        assert config.ml_features_dataset == "test_ml_features"

    def test_config_custom_env_vars(self, test_config_manager):
        """Test that config can use custom environment variables."""
        test_config_manager.setup_test_env(
            {"GOOGLE_CLOUD_PROJECT": "custom-project-456", "LOG_LEVEL": "WARNING"}
        )

        config = BaseServiceConfig()
        assert config.gcp_project_id == "custom-project-456"
        assert config.log_level == "WARNING"

    def test_config_get_cloud_target(self, test_config_manager):
        """Test that config.get_cloud_target() works uniformly."""
        config = FeaturesConfig()
        cloud_target = config.get_cloud_target()

        assert isinstance(cloud_target, CloudTarget)
        assert cloud_target.project_id == "test-project-123"
        assert cloud_target.region == "us-central1"
        assert cloud_target.bigquery_location == "us-central1"

    def test_config_is_test_environment(self, test_config_manager):
        """Test that config.is_test_environment() works correctly."""
        config = BaseServiceConfig()
        assert config.is_test_environment() is True

        # Test production environment
        test_config_manager.setup_test_env({"ENVIRONMENT": "production"})
        config_prod = BaseServiceConfig()
        assert config_prod.is_test_environment() is False


class TestUniformSecretManagerAccess:
    """Test that all services access secret manager uniformly."""

    def test_get_secret_with_fallback_from_secret_manager(
        self, test_config_manager, mock_secret_manager
    ):
        """Test that get_secret_with_fallback works with Secret Manager."""
        from unified_cloud_services import get_secret_with_fallback

        secret_value = get_secret_with_fallback(
            secret_name="tardis-api-key",
            project_id="test-project-123",
            fallback_env_var="TARDIS_API_KEY",
        )

        assert_secret_retrieved(secret_value, "test-tardis-api-key-12345")

    def test_get_secret_with_fallback_from_env_var(self, test_config_manager):
        """Test that get_secret_with_fallback falls back to env var."""
        from unified_cloud_services import get_secret_with_fallback

        # Set env var but not secret
        os.environ["CUSTOM_API_KEY"] = "env-var-api-key-12345"

        secret_value = get_secret_with_fallback(
            secret_name="non-existent-secret",
            project_id="test-project-123",
            fallback_env_var="CUSTOM_API_KEY",
        )

        assert_secret_retrieved(secret_value, "env-var-api-key-12345")

        # Cleanup
        os.environ.pop("CUSTOM_API_KEY", None)

    def test_get_secrets_with_fallback(self, test_config_manager, mock_secret_manager):
        """Test that get_secrets_with_fallback works for multiple secrets."""
        from unified_cloud_services import get_secrets_with_fallback

        secret_mappings = {
            "tardis-api-key": "TARDIS_API_KEY",
            "binance-api-key": "BINANCE_API_KEY",
        }

        secrets = get_secrets_with_fallback(
            secret_mappings=secret_mappings, project_id="test-project-123"
        )

        assert secrets["TARDIS_API_KEY"] == "test-tardis-api-key-12345"
        assert secrets["BINANCE_API_KEY"] == "test-binance-api-key-12345"

    def test_secret_manager_client_initialization(
        self, test_config_manager, mock_cloud_auth_factory
    ):
        """Test that SecretManagerClient initializes uniformly."""
        from unified_cloud_services import SecretManagerClient

        client = SecretManagerClient(project_id="test-project-123", credentials_path=None)

        # Client should be initialized (mocked)
        assert client.project_id == "test-project-123"

    def test_unified_cloud_service_get_secret(self, test_config_manager, mock_cloud_auth_factory):
        """Test that UnifiedCloudService.get_secret() works uniformly."""
        from unified_cloud_services import UnifiedCloudService, CloudTarget
        import asyncio

        # Create cloud target
        cloud_target = CloudTarget(
            project_id="test-project-123",
            gcs_bucket="test-bucket",
            bigquery_dataset="test_dataset",
        )

        # Create service (will use mocked clients)
        service = UnifiedCloudService()

        # Mock the secret client pool
        mock_secret_client = Mock()
        mock_response = Mock()
        mock_response.payload.data = b"test-secret-value-12345"
        mock_secret_client.access_secret_version = Mock(return_value=mock_response)
        service._secret_client_pool = [mock_secret_client]

        # Test async get_secret
        async def test_get_secret():
            secret = await service.get_secret("test-secret", cloud_target)
            assert secret == "test-secret-value-12345"

        asyncio.run(test_get_secret())


class TestServiceSpecificConfigPatterns:
    """Test that services use config patterns uniformly."""

    def test_all_services_extend_base_service_config(self):
        """Test that all service configs extend BaseServiceConfig."""
        assert issubclass(FeaturesConfig, BaseServiceConfig)
        assert issubclass(MarketDataConfig, BaseServiceConfig)
        assert issubclass(StrategyConfig, BaseServiceConfig)
        assert issubclass(MLTrainingConfig, BaseServiceConfig)

    def test_all_services_have_cloud_target_method(self, test_config_manager):
        """Test that all services can get CloudTarget from config."""
        configs = [
            FeaturesConfig(),
            MarketDataConfig(),
            StrategyConfig(),
            MLTrainingConfig(),
        ]

        for config in configs:
            cloud_target = config.get_cloud_target()
            assert isinstance(cloud_target, CloudTarget)
            assert cloud_target.project_id == "test-project-123"

    def test_all_services_respect_test_environment(self, test_config_manager):
        """Test that all services respect ENVIRONMENT=test."""
        configs = [
            FeaturesConfig(),
            MarketDataConfig(),
            StrategyConfig(),
            MLTrainingConfig(),
        ]

        for config in configs:
            assert config.is_test_environment() is True
            assert config.environment == "test"


class TestConfigEnvVarPriority:
    """Test that config respects environment variable priority."""

    def test_env_var_overrides_default(self, test_config_manager):
        """Test that environment variables override defaults."""
        test_config_manager.setup_test_env(
            {"GOOGLE_CLOUD_PROJECT": "override-project-789", "LOG_LEVEL": "ERROR"}
        )

        config = BaseServiceConfig()
        assert config.gcp_project_id == "override-project-789"
        assert config.log_level == "ERROR"

    def test_custom_field_overrides_env_var(self, test_config_manager):
        """Test that explicit field values override env vars."""
        config = FeaturesConfig(base_timeframe="1h")
        assert config.base_timeframe == "1h"  # Explicit value wins


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
