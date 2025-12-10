"""
Generic Error Handling Service

Reusable error handling logic that works across all domains (market_data, features, strategy, ml, execution).
"""

import logging
import asyncio
import functools
import time
from datetime import datetime, timezone
from typing import Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from unified_cloud_services.models.error import ErrorSeverity, ErrorCategory, ErrorContext

logger = logging.getLogger(__name__)


class ErrorRecoveryStrategy(str, Enum):
    """Error recovery strategies"""

    RETRY = "retry"
    SKIP = "skip"
    FAIL_FAST = "fail_fast"
    FALLBACK = "fallback"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class EnhancedError:
    """Enhanced error with structured information"""

    message: str
    category: ErrorCategory
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    recovery_strategy: ErrorRecoveryStrategy = ErrorRecoveryStrategy.RETRY
    context: ErrorContext = field(default_factory=ErrorContext)
    original_error: Exception | None = None
    retry_count: int = 0
    max_retries: int = 3
    additional_info: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            "error_type": "EnhancedError",
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "recovery_strategy": self.recovery_strategy.value,
            "context": self.context.to_dict(),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "original_error": {
                "type": (type(self.original_error).__name__ if self.original_error else None),
                "message": str(self.original_error) if self.original_error else None,
            },
            "additional_info": self.additional_info,
        }


@dataclass
class ErrorHandlingConfig:
    """Configuration for error handling operations"""

    enable_error_classification: bool = True
    enable_auto_recovery: bool = True
    enable_error_reporting: bool = True
    strict_mode: bool = False
    max_retries_default: int = 3
    retry_delay_base: float = 1.0
    retry_delay_multiplier: float = 2.0
    log_all_errors: bool = True
    error_reporting_threshold: int = 10
    recovery_strategies: dict[ErrorCategory, ErrorRecoveryStrategy] = field(
        default_factory=lambda: {
            ErrorCategory.NETWORK: ErrorRecoveryStrategy.RETRY,
            ErrorCategory.API: ErrorRecoveryStrategy.RETRY,
            ErrorCategory.RATE_LIMIT: ErrorRecoveryStrategy.RETRY,
            ErrorCategory.AUTHENTICATION: ErrorRecoveryStrategy.MANUAL_INTERVENTION,
            ErrorCategory.DATA_VALIDATION: ErrorRecoveryStrategy.SKIP,
            ErrorCategory.STORAGE: ErrorRecoveryStrategy.RETRY,
            ErrorCategory.CONFIGURATION: ErrorRecoveryStrategy.MANUAL_INTERVENTION,
            ErrorCategory.SYSTEM: ErrorRecoveryStrategy.FAIL_FAST,
            ErrorCategory.BUSINESS_LOGIC: ErrorRecoveryStrategy.SKIP,
        }
    )


class GenericErrorHandlingService:
    """
    Generic error handling service.

    Provides reusable error classification, retry logic, and recovery strategies
    that work across all domains.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize generic error handling service.

        Args:
            config: Configuration with error handling settings
        """
        self.config = config

        # Initialize error handling configuration
        self.error_config = ErrorHandlingConfig(
            enable_error_classification=config.get("enable_error_classification", True),
            enable_auto_recovery=config.get("enable_auto_recovery", True),
            enable_error_reporting=config.get("enable_error_reporting", True),
            strict_mode=config.get("strict_mode", False),
            max_retries_default=config.get("max_retries_default", 3),
            retry_delay_base=config.get("retry_delay_base", 1.0),
            retry_delay_multiplier=config.get("retry_delay_multiplier", 2.0),
            log_all_errors=config.get("log_all_errors", True),
            error_reporting_threshold=config.get("error_reporting_threshold", 10),
        )

        # Error tracking statistics
        self._error_counts: dict[str, int] = {}
        self._error_history: list[EnhancedError] = []
        self._recovery_success_rates: dict[ErrorCategory, dict[str, int]] = {}

        logger.info(
            f"✅ GenericErrorHandlingService initialized: "
            f"classification={self.error_config.enable_error_classification}, "
            f"auto_recovery={self.error_config.enable_auto_recovery}, "
            f"strict_mode={self.error_config.strict_mode}"
        )

    def classify_error(self, error: Exception) -> ErrorCategory:
        """
        Classify error into appropriate category.

        Generic error classification logic that works across all domains.
        """
        error_type = type(error).__name__.lower()
        error_message = str(error).lower()

        # Network-related errors
        network_keywords = [
            "connection",
            "timeout",
            "network",
            "dns",
            "socket",
            "unreachable",
        ]
        if any(keyword in error_message for keyword in network_keywords):
            return ErrorCategory.NETWORK

        if error_type in ["connectionerror", "timeout", "connecttimeout"]:
            return ErrorCategory.NETWORK

        # Authentication errors (check before API errors as 401/403 can be both)
        auth_keywords = ["auth", "unauthorized", "forbidden", "token", "credential"]
        auth_status_codes = ["401", "403"]
        if any(keyword in error_message for keyword in auth_keywords) or any(
            code in error_message for code in auth_status_codes
        ):
            return ErrorCategory.AUTHENTICATION

        # API-related errors
        api_keywords = [
            "api",
            "http",
            "status",
            "response",
            "400",
            "404",
            "500",
            "502",
            "503",
        ]
        if any(keyword in error_message for keyword in api_keywords):
            return ErrorCategory.API

        if error_type in ["httperror", "requestexception"]:
            return ErrorCategory.API

        # Rate limiting
        rate_limit_keywords = ["rate limit", "too many requests", "429", "throttle"]
        if any(keyword in error_message for keyword in rate_limit_keywords):
            return ErrorCategory.RATE_LIMIT

        # Configuration errors
        config_keywords = ["config", "setting", "environment", "not set"]
        config_specific_patterns = [
            "missing api key",
            "environment variable",
            "configuration missing",
        ]
        if any(keyword in error_message for keyword in config_keywords) or any(
            pattern in error_message for pattern in config_specific_patterns
        ):
            return ErrorCategory.CONFIGURATION

        # Data validation
        validation_keywords = [
            "validation",
            "invalid",
            "malformed",
            "parse",
            "schema",
            "format",
        ]
        if any(keyword in error_message for keyword in validation_keywords):
            return ErrorCategory.DATA_VALIDATION

        if error_type in ["valueerror", "typeerror", "keyerror"]:
            return ErrorCategory.DATA_VALIDATION

        # Storage errors
        storage_keywords = [
            "storage",
            "file",
            "disk",
            "gcs",
            "bucket",
            "blob",
            "upload",
            "download",
        ]
        if any(keyword in error_message for keyword in storage_keywords):
            return ErrorCategory.STORAGE

        if error_type in ["filenotfounderror", "permissionerror", "ioerror"]:
            return ErrorCategory.STORAGE

        # System errors
        system_keywords = ["system", "memory", "process", "thread", "resource"]
        if any(keyword in error_message for keyword in system_keywords):
            return ErrorCategory.SYSTEM

        if error_type in ["memoryerror", "systemexit", "keyboardinterrupt"]:
            return ErrorCategory.SYSTEM

        return ErrorCategory.BUSINESS_LOGIC

    def determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """
        Determine error severity based on category and error type.

        Generic severity determination logic.
        """
        # Critical severity
        if category in [ErrorCategory.AUTHENTICATION, ErrorCategory.CONFIGURATION]:
            return ErrorSeverity.CRITICAL

        # System errors are often critical too
        if category == ErrorCategory.SYSTEM and type(error).__name__ in [
            "MemoryError",
            "SystemExit",
        ]:
            return ErrorSeverity.CRITICAL

        # High severity
        if category in [ErrorCategory.SYSTEM, ErrorCategory.STORAGE]:
            return ErrorSeverity.HIGH

        # Medium severity
        if category in [
            ErrorCategory.NETWORK,
            ErrorCategory.API,
            ErrorCategory.RATE_LIMIT,
        ]:
            return ErrorSeverity.MEDIUM

        # Low severity
        return ErrorSeverity.LOW

    def handle_error(
        self,
        error: Exception,
        context: ErrorContext | None = None,
        custom_recovery: ErrorRecoveryStrategy | None = None,
        max_retries: int | None = None,
    ) -> EnhancedError:
        """
        Handle and classify an error with recovery strategy.

        Args:
            error: Exception to handle
            context: Optional error context
            custom_recovery: Override recovery strategy
            max_retries: Override max retry count

        Returns:
            EnhancedError with classification and recovery information
        """
        if not self.error_config.enable_error_classification:
            return EnhancedError(
                message=str(error),
                category=ErrorCategory.BUSINESS_LOGIC,
                context=context or ErrorContext(),
                original_error=error,
            )

        # Classify the error
        category = self.classify_error(error)
        severity = self.determine_severity(error, category)
        recovery_strategy = custom_recovery or self.error_config.recovery_strategies.get(
            category, ErrorRecoveryStrategy.RETRY
        )

        # Create enhanced error
        enhanced_error = EnhancedError(
            message=str(error),
            category=category,
            severity=severity,
            recovery_strategy=recovery_strategy,
            context=context or ErrorContext(),
            original_error=error,
            max_retries=max_retries or self.error_config.max_retries_default,
        )

        # Log the error
        if self.error_config.log_all_errors:
            self.log_error(enhanced_error)

        # Update error tracking
        self.update_error_counts(category)
        self._error_history.append(enhanced_error)

        # Trim history if too long
        if len(self._error_history) > 1000:
            self._error_history = self._error_history[-500:]

        return enhanced_error

    def log_error(self, enhanced_error: EnhancedError):
        """Log enhanced error with structured information"""
        error_data = enhanced_error.to_dict()
        log_message = f"[{enhanced_error.category.value}] {enhanced_error.message}"
        extra_data = {"error_data": error_data}

        if enhanced_error.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"🚨 {log_message}", extra=extra_data)
        elif enhanced_error.severity == ErrorSeverity.HIGH:
            logger.error(f"❌ {log_message}", extra=extra_data)
        elif enhanced_error.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"⚠️ {log_message}", extra=extra_data)
        else:
            logger.info(f"ℹ️ {log_message}", extra=extra_data)

    def update_error_counts(self, category: ErrorCategory):
        """Update error counts for monitoring"""
        key = f"{category.value}_errors"
        self._error_counts[key] = self._error_counts.get(key, 0) + 1

        if category not in self._recovery_success_rates:
            self._recovery_success_rates[category] = {"attempts": 0, "successes": 0}

        self._recovery_success_rates[category]["attempts"] += 1

    def execute_with_error_handling(
        self,
        operation: Callable,
        *args,
        context: ErrorContext | None = None,
        max_retries: int | None = None,
        custom_recovery: ErrorRecoveryStrategy | None = None,
        **kwargs,
    ) -> Any:
        """
        Execute operation with comprehensive error handling (sync version).

        Args:
            operation: Operation to execute
            *args: Arguments for operation
            context: Error context for tracking
            max_retries: Override retry count
            custom_recovery: Override recovery strategy
            **kwargs: Keyword arguments for operation

        Returns:
            Operation result or raises final error
        """
        retries = max_retries or self.error_config.max_retries_default
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            try:
                result = operation(*args, **kwargs)

                # Success - update recovery stats if this was a retry
                if attempt > 0 and last_error:
                    enhanced_error = self.handle_error(last_error, context, custom_recovery)
                    category = enhanced_error.category
                    if category in self._recovery_success_rates:
                        self._recovery_success_rates[category]["successes"] += 1

                return result

            except Exception as e:
                last_error = e
                enhanced_error = self.handle_error(e, context, custom_recovery, retries)

                if attempt < retries:
                    if enhanced_error.recovery_strategy == ErrorRecoveryStrategy.RETRY:
                        delay = self.error_config.retry_delay_base * (
                            self.error_config.retry_delay_multiplier**attempt
                        )
                        logger.info(
                            f"🔄 Retrying after {delay:.2f}s (attempt {attempt + 1}/{retries})"
                        )
                        time.sleep(delay)
                        continue
                    elif enhanced_error.recovery_strategy == ErrorRecoveryStrategy.SKIP:
                        logger.warning("⏭️ Skipping operation due to error recovery strategy")
                        return None
                    elif enhanced_error.recovery_strategy == ErrorRecoveryStrategy.FALLBACK:
                        logger.info("🔄 Using fallback recovery strategy")
                        return self._execute_fallback_strategy(enhanced_error, context)
                    else:
                        break
                else:
                    logger.error(f"❌ All {retries} retry attempts failed")

        # All retries exhausted or fail-fast strategy
        if self.error_config.strict_mode or (
            last_error and enhanced_error.recovery_strategy == ErrorRecoveryStrategy.FAIL_FAST
        ):
            raise last_error
        else:
            logger.error(f"❌ Operation failed after {retries} attempts: {last_error}")
            return None

    async def execute_with_error_handling_async(
        self,
        operation: Callable,
        *args,
        context: ErrorContext = None,
        max_retries: int = None,
        custom_recovery: ErrorRecoveryStrategy = None,
        **kwargs,
    ) -> Any:
        """
        Execute async operation with comprehensive error handling.

        Args:
            operation: Async operation to execute
            *args: Arguments for operation
            context: Error context for tracking
            max_retries: Override retry count
            custom_recovery: Override recovery strategy
            **kwargs: Keyword arguments for operation

        Returns:
            Operation result or raises final error
        """
        retries = max_retries or self.error_config.max_retries_default
        last_error = None

        for attempt in range(retries + 1):
            try:
                result = await operation(*args, **kwargs)

                if attempt > 0:
                    logger.info(f"✅ Operation succeeded on attempt {attempt + 1}")
                return result

            except Exception as e:
                last_error = e
                enhanced_error = self.handle_error(e, context, custom_recovery, retries)

                if attempt < retries:
                    if enhanced_error.recovery_strategy == ErrorRecoveryStrategy.RETRY:
                        delay = self.error_config.retry_delay_base * (
                            self.error_config.retry_delay_multiplier**attempt
                        )
                        logger.info(
                            f"🔄 Retrying after {delay:.2f}s (attempt {attempt + 1}/{retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    elif enhanced_error.recovery_strategy == ErrorRecoveryStrategy.SKIP:
                        logger.warning("⏭️ Skipping operation due to error recovery strategy")
                        return None
                    elif enhanced_error.recovery_strategy == ErrorRecoveryStrategy.FALLBACK:
                        logger.info("🔄 Using fallback recovery strategy")
                        return self._execute_fallback_strategy(enhanced_error, context)
                    else:
                        break
                else:
                    logger.error(f"❌ All {retries} retry attempts failed")

        # All retries exhausted or fail-fast strategy
        if self.error_config.strict_mode or (
            last_error and enhanced_error.recovery_strategy == ErrorRecoveryStrategy.FAIL_FAST
        ):
            raise last_error
        else:
            logger.error(f"❌ Operation failed after {retries} attempts: {last_error}")
            return None

    def _execute_fallback_strategy(
        self, enhanced_error: EnhancedError, context: ErrorContext = None
    ) -> Any:
        """Execute fallback recovery strategy"""
        logger.info("🔄 Executing fallback strategy")

        if enhanced_error.category == ErrorCategory.NETWORK:
            return {"status": "fallback", "data": None, "error": "network_fallback"}
        elif enhanced_error.category == ErrorCategory.API:
            return {"status": "fallback", "data": None, "error": "api_fallback"}
        elif enhanced_error.category == ErrorCategory.STORAGE:
            return {"status": "fallback", "data": None, "error": "storage_fallback"}
        else:
            return {"status": "fallback", "data": None, "error": "generic_fallback"}

    def get_error_stats(self) -> dict[str, Any]:
        """Get current error statistics for monitoring"""
        total_errors = sum(self._error_counts.values())

        recovery_rates = {}
        for category, stats in self._recovery_success_rates.items():
            attempts = stats["attempts"]
            successes = stats["successes"]
            recovery_rates[category.value] = {
                "success_rate": successes / attempts if attempts > 0 else 0.0,
                "attempts": attempts,
                "successes": successes,
            }

        return {
            "total_errors": total_errors,
            "error_breakdown": self._error_counts.copy(),
            "recovery_success_rates": recovery_rates,
            "error_history_count": len(self._error_history),
            "configuration": {
                "classification_enabled": self.error_config.enable_error_classification,
                "auto_recovery_enabled": self.error_config.enable_auto_recovery,
                "strict_mode": self.error_config.strict_mode,
                "max_retries_default": self.error_config.max_retries_default,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_recent_errors(self, count: int = 10) -> list[EnhancedError]:
        """Get recent errors for debugging"""
        return self._error_history[-count:] if self._error_history else []

    def track_external_error(
        self,
        error_message: str,
        category: ErrorCategory | None = None,
        severity: ErrorSeverity | None = None,
    ):
        """Track external errors that don't go through execute_with_error_handling"""
        try:
            enhanced_error = EnhancedError(
                message=error_message,
                category=category or ErrorCategory.BUSINESS_LOGIC,
                severity=severity or ErrorSeverity.MEDIUM,
                context=ErrorContext(operation="external_error", component="error_tracking"),
            )

            self._error_history.append(enhanced_error)
            self.update_error_counts(enhanced_error.category)
            logger.debug(f"📊 External error tracked: {error_message}")

        except Exception as e:
            logger.debug(f"Error tracking failed: {e}")

    def reset_error_stats(self):
        """Reset error statistics and history"""
        self._error_counts.clear()
        self._error_history.clear()
        self._recovery_success_rates.clear()
        logger.info("📊 Error statistics reset")

    def cleanup(self):
        """Cleanup resources and reset statistics"""
        self.reset_error_stats()
        logger.info("🧹 GenericErrorHandlingService cleanup completed")


# =================================================================
# DECORATORS FOR AUTOMATIC ERROR HANDLING
# =================================================================


def with_error_handling(
    category: ErrorCategory | None = None,
    severity: ErrorSeverity | None = None,
    recovery_strategy: ErrorRecoveryStrategy | None = None,
    max_retries: int = 3,
    reraise: bool = True,
):
    """
    Decorator for automatic error handling.

    Usage:
        @with_error_handling(category=ErrorCategory.API, max_retries=2)
        async def api_call():
            return await make_api_call()
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract error handling service from args if available
            error_service = None
            for arg in args:
                if hasattr(arg, "error_handling") and hasattr(
                    arg.error_handling, "execute_with_error_handling"
                ):
                    error_service = arg.error_handling
                    break

            if error_service:
                context = ErrorContext(operation=func.__name__, component=func.__module__)

                return await error_service.execute_with_error_handling_async(
                    func,
                    *args,
                    context=context,
                    max_retries=max_retries,
                    custom_recovery=recovery_strategy,
                    **kwargs,
                )
            else:
                # Fallback to basic error handling
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"❌ Error in {func.__name__}: {e}")
                    if reraise:
                        raise
                    return None

        return wrapper

    return decorator


def handle_api_errors(max_retries: int = 3):
    """Decorator specifically for API error handling"""
    return with_error_handling(
        category=ErrorCategory.API,
        recovery_strategy=ErrorRecoveryStrategy.RETRY,
        max_retries=max_retries,
        reraise=False,
    )


def handle_storage_errors(max_retries: int = 2):
    """Decorator specifically for storage error handling"""
    return with_error_handling(
        category=ErrorCategory.STORAGE,
        recovery_strategy=ErrorRecoveryStrategy.RETRY,
        max_retries=max_retries,
        reraise=False,
    )


def create_error_context(operation: str, component: str = None, **additional_data) -> ErrorContext:
    """
    Create error context for consistent error tracking.

    Args:
        operation: Operation being performed
        component: Component performing the operation
        **additional_data: Additional context data

    Returns:
        ErrorContext object
    """
    return ErrorContext(
        operation=operation,
        component=component or "unknown",
        additional_data=additional_data,
    )


def is_retryable_error(error: Exception) -> bool:
    """
    Check if error is retryable.

    Args:
        error: Exception to check

    Returns:
        True if error should be retried
    """
    error_message = str(error).lower()

    retryable_patterns = [
        "timeout",
        "connection",
        "network",
        "temporary",
        "dns",
        "429",
        "500",
        "502",
        "503",
        "504",
        "rate limit",
        "too many requests",
        "socket",
    ]

    error_type = type(error).__name__.lower()
    retryable_types = ["connectionerror", "timeout", "connecttimeout"]

    return (
        any(pattern in error_message for pattern in retryable_patterns)
        or error_type in retryable_types
    )
