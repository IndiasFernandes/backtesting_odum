"""Core cloud service modules"""

from unified_cloud_services.core.cloud_config import CloudConfig, CloudTarget
from unified_cloud_services.core.config import BaseServiceConfig
from unified_cloud_services.core.cloud_auth_factory import CloudAuthFactory
from unified_cloud_services.core.unified_cloud_service import UnifiedCloudService
from unified_cloud_services.core.batch_processor import GenericBatchProcessor
from unified_cloud_services.core.schema_validator import SchemaValidator
from unified_cloud_services.core.table_manager import TableManager
from unified_cloud_services.core.service_wrapper import ServiceWrapper
from unified_cloud_services.core.secret_manager import (
    SecretManagerClient,
    get_secret_with_fallback,
    get_secrets_with_fallback,
    create_secret_if_not_exists,
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
from unified_cloud_services.core.observability import GenericObservabilityService, observe_operation
from unified_cloud_services.core.gcsfuse_helper import (
    GCSFuseHelper,
    check_gcsfuse_available,
    get_bucket_mount_path,
    ensure_bucket_mounted,
)

__all__ = [
    "CloudConfig",
    "CloudTarget",
    "BaseServiceConfig",
    "CloudAuthFactory",
    "UnifiedCloudService",
    "GenericBatchProcessor",
    "SchemaValidator",
    "TableManager",
    "ServiceWrapper",
    "SecretManagerClient",
    "get_secret_with_fallback",
    "get_secrets_with_fallback",
    "create_secret_if_not_exists",
    "GenericErrorHandlingService",
    "ErrorRecoveryStrategy",
    "EnhancedError",
    "ErrorHandlingConfig",
    "with_error_handling",
    "handle_api_errors",
    "handle_storage_errors",
    "create_error_context",
    "is_retryable_error",
    "GenericObservabilityService",
    "observe_operation",
    # GCS FUSE helpers
    "GCSFuseHelper",
    "check_gcsfuse_available",
    "get_bucket_mount_path",
    "ensure_bucket_mounted",
]
