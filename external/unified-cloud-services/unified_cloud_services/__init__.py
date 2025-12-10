"""
Unified Cloud Services Package

Standalone package for cloud operations across the unified trading system.
Provides GCS, BigQuery, domain-specific validation, error handling, and observability services.

CLI Commands (after pip install):
    ucs-setup     - Install gcsfuse and set up GCS FUSE mounting
    ucs-status    - Show GCS FUSE status and mount points
    ucs-mount     - Mount a GCS bucket
    ucs-unmount   - Unmount a GCS bucket
"""

__version__ = "1.3.0"


def _check_gcsfuse_on_import():
    """
    Optional check for gcsfuse on first import.
    Only runs once and can be disabled via UCS_SKIP_GCSFUSE_CHECK=1.
    """
    import os
    
    # Skip if disabled
    if os.environ.get("UCS_SKIP_GCSFUSE_CHECK", "").lower() in ("1", "true", "yes"):
        return
    
    # Only check once per process
    if getattr(_check_gcsfuse_on_import, "_checked", False):
        return
    _check_gcsfuse_on_import._checked = True
    
    # Only hint if gcsfuse is not installed (non-intrusive)
    try:
        from unified_cloud_services.core.gcsfuse_helper import check_gcsfuse_available
        if not check_gcsfuse_available():
            import sys
            # Print to stderr to not interfere with stdout
            print(
                "\n💡 GCS FUSE not found. For fast local I/O, run: ucs-setup\n"
                "   (Disable this message: export UCS_SKIP_GCSFUSE_CHECK=1)\n",
                file=sys.stderr,
            )
    except Exception:
        pass  # Don't fail import if check fails


# Run check (non-blocking, can be disabled)
_check_gcsfuse_on_import()

from unified_cloud_services.core.cloud_config import CloudConfig, CloudTarget
from unified_cloud_services.core.config import (
    UnifiedCloudServicesConfig,
    BaseServiceConfig,
    unified_config,
    get_unified_config,
)
from unified_cloud_services.core.unified_cloud_service import UnifiedCloudService
from unified_cloud_services.core.batch_processor import GenericBatchProcessor
from unified_cloud_services.core.date_utils import (
    parse_date,
    validate_date_range,
    get_date_range,
    format_date_for_path,
    get_date_from_path,
)
from unified_cloud_services.core.performance_monitor import (
    PerformanceMonitor,
    PerformanceMetrics,
    SystemMetrics,
    performance_monitor,
    record_performance,
    get_performance_monitor,
    start_performance_monitoring,
    stop_performance_monitoring,
    get_performance_summary,
    monitor_api_call,
    monitor_data_processing,
    monitor_file_operation,
)
from unified_cloud_services.core.memory_monitor import (
    MemoryMonitor,
    get_memory_monitor,
    check_memory_threshold,
    log_memory_status_standalone,
)
from unified_cloud_services.core.http_session_pool import (
    get_http_session,
    clear_pool as clear_http_pool,
)
from unified_cloud_services.core.web3_client_pool import (
    get_web3_client,
    clear_pool as clear_web3_pool,
)
from unified_cloud_services.core.gcsfuse_helper import (
    GCSFuseHelper,
    check_gcsfuse_available,
    get_bucket_mount_path,
    ensure_bucket_mounted,
)
from unified_cloud_services.core.date_filter_service import DateFilterService
from unified_cloud_services.core.subgraph_service import SubgraphService
from unified_cloud_services.core.schema_validator import SchemaValidator
from unified_cloud_services.core.table_manager import TableManager
from unified_cloud_services.core.service_wrapper import ServiceWrapper
from unified_cloud_services.domain.standardized_service import (
    StandardizedDomainCloudService,
    create_domain_cloud_service,
    get_config,
)
from unified_cloud_services.domain.validation import DomainValidationService, DomainValidationConfig
from unified_cloud_services.domain.factories import (
    create_market_data_cloud_service,
    create_features_cloud_service,
    create_strategy_cloud_service,
    create_backtesting_cloud_service,
)
from unified_cloud_services.domain.clients import (
    InstrumentsDomainClient,
    MarketCandleDataDomainClient,
    MarketTickDataDomainClient,
    ExecutionDomainClient,
    MarketDataDomainClient,  # Deprecated, kept for backward compatibility
    create_instruments_client,
    create_market_candle_data_client,
    create_market_tick_data_client,
    create_execution_client,
    create_market_data_client,  # Deprecated, kept for backward compatibility
    create_features_client,
)
from unified_cloud_services.models.validation import ValidationResult
from unified_cloud_services.models.error import ErrorSeverity, ErrorCategory, ErrorContext
from unified_cloud_services.models.observability import OperationContext
from unified_cloud_services.models.instrument import (
    Venue,
    InstrumentType,
)
from unified_cloud_services.models.venue_config import (
    VenueMapping,
    DataTypeConfig,
    ExchangeInstrumentConfig,
)
from unified_cloud_services.models.schemas import (
    InstrumentKey,
    ValidationConfig,
    DownloadTarget,
    OrchestrationResult,
)
from unified_cloud_services.models.nautilus_schema import (
    NAUTILUS_TRADES_SCHEMA,
    NAUTILUS_BOOK_SNAPSHOT_5_SCHEMA,
    NAUTILUS_SCHEMA_MAP,
    convert_to_nautilus_instrument_id,
    convert_from_nautilus_instrument_id,
    transform_to_nautilus,
    transform_trades_to_nautilus,
    transform_book_snapshot_to_nautilus,
    get_nautilus_schema,
    get_nautilus_pyarrow_schema,
)
from unified_cloud_services.core.error_handling import (
    GenericErrorHandlingService,
    ErrorRecoveryStrategy,
    EnhancedError,
    ErrorHandlingConfig,
    with_error_handling,
    handle_api_errors,
    handle_storage_errors,
    create_error_context,
    is_retryable_error,
)
from unified_cloud_services.core.secret_manager import (
    SecretManagerClient,
    get_secret_with_fallback,
    get_secrets_with_fallback,
    create_secret_if_not_exists,
    clear_secret_cache,
)
from unified_cloud_services.core.observability import GenericObservabilityService, observe_operation
from unified_cloud_services.core.sampling_service import SamplingService, create_sampling_service
from unified_cloud_services.core.market_category import (
    determine_market_category,
    get_bucket_for_category,
    get_instruments_bucket_for_category,
    get_market_data_bucket_for_category,
    filter_instruments_by_category,
    get_all_category_buckets,
)
from unified_cloud_services.adapters.defi import (
    BaseDefiAdapter,
    TheGraphClient,
)
from unified_cloud_services.clients.tardis_base_client import (
    TardisBaseClient,
    TardisClientConfig,
    create_tardis_base_client,
    clear_tardis_api_key_cache,
)
from unified_cloud_services.clients.databento_base_client import (
    DatabentoBaseClient,
    DatabentoClientConfig,
    create_databento_base_client,
    clear_databento_api_key_cache,
    clear_databento_client_cache,
    DATABENTO_AVAILABLE,
)
from unified_cloud_services.clients.thegraph_base_client import (
    TheGraphBaseClient,
    TheGraphClientConfig,
    create_thegraph_base_client,
    clear_thegraph_api_key_cache,
)
from unified_cloud_services.clients.alchemy_base_client import (
    AlchemyBaseClient,
    AlchemyClientConfig,
    create_alchemy_base_client,
    clear_alchemy_api_key_cache,
    clear_alchemy_web3_cache,
    WEB3_AVAILABLE,
    CHAIN_TO_ALCHEMY_NETWORK,
)

# ⚠️ DEPRECATED: Factory functions removed - use direct instantiation instead
# All services should use: StandardizedDomainCloudService(domain='market_data', cloud_target=cloud_target)
# This avoids technical debt and makes domain explicit

__all__ = [
    # Core classes
    "UnifiedCloudService",
    "CloudConfig",
    "CloudTarget",
    "BaseServiceConfig",
    "UnifiedCloudServicesConfig",
    "unified_config",
    "get_unified_config",
    "GenericBatchProcessor",
    # Date utilities
    "parse_date",
    "validate_date_range",
    "get_date_range",
    "format_date_for_path",
    "get_date_from_path",
    # Performance monitoring
    "PerformanceMonitor",
    "PerformanceMetrics",
    "SystemMetrics",
    "performance_monitor",
    "record_performance",
    "get_performance_monitor",
    "start_performance_monitoring",
    "stop_performance_monitoring",
    "get_performance_summary",
    "monitor_api_call",
    "monitor_data_processing",
    "monitor_file_operation",
    # Memory monitoring
    "MemoryMonitor",
    "get_memory_monitor",
    "check_memory_threshold",
    "log_memory_status_standalone",
    # Connection pooling
    "get_http_session",
    "clear_http_pool",
    "get_web3_client",
    "clear_web3_pool",
    # GCS FUSE helpers
    "GCSFuseHelper",
    "check_gcsfuse_available",
    "get_bucket_mount_path",
    "ensure_bucket_mounted",
    # Service utilities
    "DateFilterService",
    "SubgraphService",
    "SchemaValidator",
    "TableManager",
    "ServiceWrapper",
    # Domain services
    "StandardizedDomainCloudService",
    "DomainValidationService",
    "DomainValidationConfig",
    "get_config",
    # Factory functions (UnifiedCloudService) - for internal use only
    "create_market_data_cloud_service",
    "create_features_cloud_service",
    "create_strategy_cloud_service",
    "create_backtesting_cloud_service",
    # ⚠️ DEPRECATED: Factory functions for StandardizedDomainCloudService removed
    # Use direct instantiation: StandardizedDomainCloudService(domain='market_data', cloud_target=cloud_target)
    # Generic factory
    "create_domain_cloud_service",
    # Models
    "ValidationResult",
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorContext",
    "OperationContext",
    "Venue",
    "InstrumentType",
    # Venue configuration classes (centralized business logic)
    "VenueMapping",
    "DataTypeConfig",
    "ExchangeInstrumentConfig",
    # Shared schemas
    "InstrumentKey",
    "ValidationConfig",
    "DownloadTarget",
    "OrchestrationResult",
    # NautilusTrader schemas and transformers
    "NAUTILUS_TRADES_SCHEMA",
    "NAUTILUS_BOOK_SNAPSHOT_5_SCHEMA",
    "NAUTILUS_SCHEMA_MAP",
    "convert_to_nautilus_instrument_id",
    "convert_from_nautilus_instrument_id",
    "transform_to_nautilus",
    "transform_trades_to_nautilus",
    "transform_book_snapshot_to_nautilus",
    "get_nautilus_schema",
    "get_nautilus_pyarrow_schema",
    # Error handling
    "GenericErrorHandlingService",
    "ErrorRecoveryStrategy",
    "EnhancedError",
    "ErrorHandlingConfig",
    "with_error_handling",
    "handle_api_errors",
    "handle_storage_errors",
    "create_error_context",
    "is_retryable_error",
    # Secret Manager
    "SecretManagerClient",
    "get_secret_with_fallback",
    "get_secrets_with_fallback",
    "create_secret_if_not_exists",
    "clear_secret_cache",
    # Observability
    "GenericObservabilityService",
    "observe_operation",
    # Sampling
    "SamplingService",
    "create_sampling_service",
    # Market category classification
    "determine_market_category",
    "get_bucket_for_category",
    "get_instruments_bucket_for_category",
    "get_market_data_bucket_for_category",
    "filter_instruments_by_category",
    "get_all_category_buckets",
    # DeFi adapters (shared base classes)
    "BaseDefiAdapter",
    "TheGraphClient",
    # Domain clients (for analytics platforms and cross-service quality gates)
    "InstrumentsDomainClient",
    "MarketCandleDataDomainClient",
    "MarketTickDataDomainClient",
    "ExecutionDomainClient",
    "MarketDataDomainClient",  # Deprecated
    "create_instruments_client",
    "create_market_candle_data_client",
    "create_market_tick_data_client",
    "create_execution_client",
    "create_market_data_client",  # Deprecated
    "create_features_client",
    # Centralized API clients (network layer abstraction)
    "TardisBaseClient",
    "TardisClientConfig",
    "create_tardis_base_client",
    "clear_tardis_api_key_cache",
    "DatabentoBaseClient",
    "DatabentoClientConfig",
    "create_databento_base_client",
    "clear_databento_api_key_cache",
    "clear_databento_client_cache",
    "DATABENTO_AVAILABLE",
    # The Graph (DeFi subgraphs)
    "TheGraphBaseClient",
    "TheGraphClientConfig",
    "create_thegraph_base_client",
    "clear_thegraph_api_key_cache",
    # Alchemy (on-chain RPC)
    "AlchemyBaseClient",
    "AlchemyClientConfig",
    "create_alchemy_base_client",
    "clear_alchemy_api_key_cache",
    "clear_alchemy_web3_cache",
    "WEB3_AVAILABLE",
    "CHAIN_TO_ALCHEMY_NETWORK",
]
