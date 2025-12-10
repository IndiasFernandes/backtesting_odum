"""
Unified Cloud Services Configuration

Centralized configuration management using Pydantic BaseSettings.
All domain services should extend this base config for consistency.

ARCHITECTURE:
- UnifiedCloudServicesConfig: Base settings class with common fields
- Domain services extend this with their specific fields
- Single source of truth for environment variable access
- Automatic .env file loading
- Type validation via Pydantic

MIGRATION FROM os.getenv:
- Before: os.getenv("GCP_PROJECT_ID", "default")
- After: unified_config.gcp_project_id

Usage:
    from unified_cloud_services import UnifiedCloudServicesConfig, unified_config
    
    # Access config directly
    project_id = unified_config.gcp_project_id
    
    # Or extend for domain-specific config
    class MyServiceConfig(UnifiedCloudServicesConfig):
        my_custom_field: str = Field(default="value")
"""

import logging
from typing import Optional
from pydantic import Field, AliasChoices, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class UnifiedCloudServicesConfig(BaseSettings):
    """
    Base configuration class for all unified trading system services.
    
    Provides:
    - Common GCP/cloud configuration
    - API key management (with Secret Manager fallback)
    - Environment detection
    - Validation via Pydantic
    
    Domain services should extend this class:
    
        class InstrumentsServiceConfig(UnifiedCloudServicesConfig):
            databento_secret_name: str = Field(default="databento-api-key")
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from .env
        env_nested_delimiter="__",  # Support nested config via ENV__NESTED
    )
    
    # =========================================================================
    # ENVIRONMENT & SERVICE IDENTIFICATION
    # =========================================================================
    
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "ENV"),
        description="Environment (development, test, staging, production)",
    )
    
    service_name: str = Field(
        default="unified-cloud-services",
        validation_alias=AliasChoices("SERVICE_NAME"),
        description="Service identifier for logging/metrics",
    )
    
    # =========================================================================
    # GCP CONFIGURATION
    # =========================================================================
    
    gcp_project_id: str = Field(
        default="",
        validation_alias=AliasChoices("GCP_PROJECT_ID", "GOOGLE_CLOUD_PROJECT", "PROJECT_ID"),
        description="GCP project ID for all cloud operations",
    )
    
    google_application_credentials_path: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_APPLICATION_CREDENTIALS"),
        description="Path to GCP service account credentials JSON",
    )
    
    # Alias for backward compatibility
    @property
    def google_application_credentials(self) -> str:
        """Alias for google_application_credentials_path."""
        return self.google_application_credentials_path
    
    gcs_region: str = Field(
        default="us-central1",
        validation_alias=AliasChoices("GCS_REGION", "GOOGLE_CLOUD_REGION"),
        description="Default GCS region for bucket operations",
    )
    
    gcs_location: str = Field(
        default="US",
        validation_alias=AliasChoices("GCS_LOCATION"),
        description="GCS multi-region location",
    )
    
    # =========================================================================
    # GCS BUCKET CONFIGURATION
    # =========================================================================
    
    # Primary buckets
    gcs_bucket: str = Field(
        default="",
        validation_alias=AliasChoices("GCS_BUCKET"),
        description="Primary GCS bucket",
    )
    
    instruments_gcs_bucket: str = Field(
        default="instrument-definitions",
        validation_alias=AliasChoices("INSTRUMENTS_GCS_BUCKET"),
        description="Bucket for instrument definitions",
    )
    
    market_data_gcs_bucket: str = Field(
        default="market-data-tick",
        validation_alias=AliasChoices("MARKET_DATA_GCS_BUCKET"),
        description="Bucket for market tick data",
    )
    
    features_gcs_bucket: str = Field(
        default="features-data",
        validation_alias=AliasChoices("FEATURES_GCS_BUCKET"),
        description="Bucket for computed features",
    )
    
    execution_gcs_bucket: str = Field(
        default="execution-store-cefi-central-element-323112",
        validation_alias=AliasChoices("EXECUTION_GCS_BUCKET"),
        description="Bucket for execution/backtest results",
    )
    
    execution_bigquery_dataset: str = Field(
        default="execution",
        validation_alias=AliasChoices("EXECUTION_BIGQUERY_DATASET"),
        description="BigQuery dataset for execution data",
    )
    
    # Test buckets
    market_data_gcs_bucket_test: str = Field(
        default="market-data-tick-test",
        validation_alias=AliasChoices("MARKET_DATA_GCS_BUCKET_TEST"),
        description="Test bucket for market data",
    )
    
    # =========================================================================
    # BIGQUERY CONFIGURATION
    # =========================================================================
    
    bigquery_dataset: str = Field(
        default="market_data",
        validation_alias=AliasChoices("BIGQUERY_DATASET", "BQ_DATASET"),
        description="Default BigQuery dataset",
    )
    
    bigquery_location: str = Field(
        default="US",
        validation_alias=AliasChoices("BIGQUERY_LOCATION", "BQ_LOCATION"),
        description="BigQuery dataset location",
    )
    
    # =========================================================================
    # API KEYS (Direct - prefer Secret Manager for production)
    # =========================================================================
    
    tardis_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("TARDIS_API_KEY"),
        description="Tardis API key (prefer Secret Manager)",
    )
    
    databento_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("DATABENTO_API_KEY"),
        description="Databento API key (prefer Secret Manager)",
    )
    
    the_graph_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("THE_GRAPH_API_KEY", "GRAPH_API_KEY"),
        description="The Graph API key (prefer Secret Manager)",
    )
    
    alchemy_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ALCHEMY_API_KEY"),
        description="Alchemy API key (prefer Secret Manager)",
    )
    
    aavescan_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("AAVESCAN_API_KEY"),
        description="AaveScan API key (prefer Secret Manager)",
    )
    
    # =========================================================================
    # SECRET MANAGER CONFIGURATION
    # =========================================================================
    
    use_secret_manager: bool = Field(
        default=True,
        validation_alias=AliasChoices("USE_SECRET_MANAGER"),
        description="Use GCP Secret Manager for API keys",
    )
    
    tardis_secret_name: str = Field(
        default="tardis-api-key",
        validation_alias=AliasChoices("TARDIS_SECRET_NAME"),
        description="Secret Manager secret name for Tardis API key",
    )
    
    databento_secret_name: str = Field(
        default="databento-api-key",
        validation_alias=AliasChoices("DATABENTO_SECRET_NAME"),
        description="Secret Manager secret name for Databento API key",
    )
    
    thegraph_secret_name: str = Field(
        default="THE_GRAPH_API_KEY",
        validation_alias=AliasChoices("THEGRAPH_SECRET_NAME", "GRAPH_SECRET_NAME"),
        description="Secret Manager secret name for The Graph API key",
    )
    
    alchemy_secret_name: str = Field(
        default="alchemy-api-key",
        validation_alias=AliasChoices("ALCHEMY_SECRET_NAME"),
        description="Secret Manager secret name for Alchemy API key",
    )
    
    aavescan_secret_name: str = Field(
        default="aavescan-api-key",
        validation_alias=AliasChoices("AAVESCAN_SECRET_NAME"),
        description="Secret Manager secret name for AaveScan API key",
    )
    
    # =========================================================================
    # API CLIENT CONFIGURATION
    # =========================================================================
    
    # Tardis
    tardis_base_url: str = Field(
        default="https://api.tardis.dev/v1",
        validation_alias=AliasChoices("TARDIS_BASE_URL", "TARDIS_API_URL"),
        description="Tardis API base URL",
    )
    
    tardis_datasets_url: str = Field(
        default="https://datasets.tardis.dev/v1",
        validation_alias=AliasChoices("TARDIS_DATASETS_URL"),
        description="Tardis datasets (CSV) base URL",
    )
    
    tardis_timeout: int = Field(
        default=30,
        validation_alias=AliasChoices("TARDIS_TIMEOUT"),
        description="Tardis API timeout in seconds",
    )
    
    tardis_max_retries: int = Field(
        default=3,
        validation_alias=AliasChoices("TARDIS_MAX_RETRIES"),
        description="Maximum retry attempts for Tardis API",
    )
    
    # Databento
    databento_timeout: int = Field(
        default=60,
        validation_alias=AliasChoices("DATABENTO_TIMEOUT"),
        description="Databento API timeout in seconds",
    )
    
    # The Graph
    thegraph_gateway_url: str = Field(
        default="https://gateway.thegraph.com/api",
        validation_alias=AliasChoices("THEGRAPH_GATEWAY_URL"),
        description="The Graph Gateway API base URL",
    )
    
    thegraph_studio_url: str = Field(
        default="https://api.studio.thegraph.com/query",
        validation_alias=AliasChoices("THEGRAPH_STUDIO_URL"),
        description="The Graph Studio API base URL",
    )
    
    thegraph_timeout: int = Field(
        default=30,
        validation_alias=AliasChoices("THEGRAPH_TIMEOUT"),
        description="The Graph API timeout in seconds",
    )
    
    # Alchemy
    alchemy_default_chain: str = Field(
        default="ETHEREUM",
        validation_alias=AliasChoices("ALCHEMY_DEFAULT_CHAIN"),
        description="Default blockchain for Alchemy RPC",
    )
    
    alchemy_timeout: int = Field(
        default=30,
        validation_alias=AliasChoices("ALCHEMY_TIMEOUT"),
        description="Alchemy API timeout in seconds",
    )
    
    # =========================================================================
    # CSV SAMPLING CONFIGURATION (Development/Debugging)
    # =========================================================================
    
    enable_csv_sampling: bool = Field(
        default=False,
        validation_alias=AliasChoices("ENABLE_CSV_SAMPLING"),
        description="Enable CSV sampling for debugging",
    )
    
    csv_sample_size: int = Field(
        default=20000,
        validation_alias=AliasChoices("CSV_SAMPLE_SIZE"),
        description="Number of rows to include in CSV samples",
    )
    
    csv_sample_dir: str = Field(
        default="data/samples",
        validation_alias=AliasChoices("CSV_SAMPLE_DIR"),
        description="Directory for CSV sample files",
    )
    
    # =========================================================================
    # LOGGING & DEBUGGING
    # =========================================================================
    
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("LOG_LEVEL"),
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    
    enable_debug: bool = Field(
        default=False,
        validation_alias=AliasChoices("ENABLE_DEBUG", "DEBUG"),
        description="Enable debug mode",
    )
    
    # Alias for backward compatibility with tests expecting 'debug'
    @property
    def debug(self) -> bool:
        """Alias for enable_debug (backward compatibility)."""
        return self.enable_debug
    
    testing_mode: bool = Field(
        default=False,
        validation_alias=AliasChoices("TESTING_MODE"),
        description="Enable testing mode (skips some validations)",
    )
    
    # =========================================================================
    # VALIDATORS
    # =========================================================================
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid Python logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Normalize environment name."""
        return v.lower()
    
    # =========================================================================
    # HELPER PROPERTIES
    # =========================================================================
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment in ("production", "prod")
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment in ("development", "dev", "local")
    
    @property
    def is_testing(self) -> bool:
        """Check if running in test environment."""
        return self.environment in ("test", "testing") or self.testing_mode


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

# Create a module-level config instance for easy access
# This is loaded once at import time
_unified_config: Optional[UnifiedCloudServicesConfig] = None


def get_unified_config() -> UnifiedCloudServicesConfig:
    """Get the singleton unified config instance."""
    global _unified_config
    if _unified_config is None:
        _unified_config = UnifiedCloudServicesConfig()
    return _unified_config


# Convenience alias
unified_config = get_unified_config()


# ============================================================================
# BACKWARD COMPATIBILITY ALIASES
# ============================================================================

# Alias for existing code expecting BaseServiceConfig
BaseServiceConfig = UnifiedCloudServicesConfig


def get_config(key: str, default: str = "") -> str:
    """
    Get a config value by key name.
    
    DEPRECATED: Use unified_config.field_name instead.
    
    This function provides backward compatibility with the old os.getenv pattern.
    New code should access config attributes directly:
        unified_config.gcp_project_id
    
    Args:
        key: Environment variable name (e.g., "GCP_PROJECT_ID")
        default: Default value if not found
        
    Returns:
        Config value as string
    """
    import os
    
    # First try the unified config (normalized to snake_case)
    config = get_unified_config()
    snake_key = key.lower().replace("-", "_")
    
    if hasattr(config, snake_key):
        value = getattr(config, snake_key)
        if value is not None:
            return str(value)
    
    # Fallback to environment variable (for non-standard keys)
    return os.getenv(key, default)
