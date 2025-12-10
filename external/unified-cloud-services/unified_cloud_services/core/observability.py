"""
Generic Observability Service

Reusable observability logic that works across all domains (market_data, features, strategy, ml, execution).
"""

import logging
import functools
import time
import asyncio
from datetime import datetime, timezone
from typing import Any, Callable
from contextlib import contextmanager

from unified_cloud_services.models.observability import OperationContext

logger = logging.getLogger(__name__)


class GenericObservabilityService:
    """
    Generic observability service for all handlers and operations.

    Provides reusable logging, monitoring, and performance tracking
    that works across all domains.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize generic observability service.

        Args:
            config: Configuration with observability settings
        """
        self.config = config
        self.enable_performance_monitoring = config.get("enable_performance_monitoring", True)
        self.enable_memory_monitoring = config.get("enable_memory_monitoring", True)
        self.enable_structured_logging = config.get("enable_structured_logging", True)
        self.log_level = config.get("log_level", "INFO")
        self.output_dir = config.get("output_dir", "logs")

        # Initialize monitoring components (lazy-loaded)
        self._performance_monitor = None
        self._memory_monitor = None
        self._operation_contexts: dict[str, OperationContext] = {}

        # Setup logging
        self._setup_centralized_logging()

        logger.info(
            f"✅ GenericObservabilityService initialized: "
            f"performance={self.enable_performance_monitoring}, "
            f"memory={self.enable_memory_monitoring}, "
            f"structured={self.enable_structured_logging}"
        )

    def _setup_centralized_logging(self) -> None:
        """Setup centralized logging configuration"""
        if self.enable_structured_logging:
            # Basic structured logging setup
            logging.basicConfig(
                level=getattr(logging, self.log_level.upper()),
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            logger.info("✅ Structured logging configured")

    @property
    def performance_monitor(self):
        """Lazy performance monitor initialization (override in subclasses)"""
        return None

    @property
    def memory_monitor(self):
        """Lazy memory monitor initialization (override in subclasses)"""
        return None

    def create_operation_logger(
        self, operation: str, component: str | None = None
    ) -> logging.LoggerAdapter:
        """
        Create centralized logger for specific operation/component.

        Args:
            operation: Operation name
            component: Component name (optional)

        Returns:
            Logger instance
        """
        logger_name = f"{component}.{operation}" if component else operation
        operation_logger = logging.getLogger(logger_name)

        # Add operation context to all log records
        class OperationAdapter(logging.LoggerAdapter):
            def process(self, msg, kwargs):
                return f"[{operation}] {msg}", kwargs

        return OperationAdapter(operation_logger, {})

    @contextmanager
    def track_operation(self, operation_name: str, component: str | None = None, **metadata):
        """
        Generic operation tracking context manager.

        Usage:
            with observability.track_operation('data_processing', component='features_service') as ctx:
                # Operation code here
                ctx.add_metric('records_processed', 1000)
        """
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"
        context = OperationContext(
            operation_name=operation_name,
            component=component or "unknown",
            operation_id=operation_id,
            start_time=datetime.now(timezone.utc),
            metadata=metadata,
        )

        self._operation_contexts[operation_id] = context

        operation_logger = self.create_operation_logger(operation_name, component)
        operation_logger.info(
            f"🚀 Started operation: {operation_name}",
            extra={"operation_id": operation_id, "metadata": metadata},
        )

        enhanced_context = None
        try:
            # Enhanced context with helper methods
            class EnhancedContext:
                def __init__(self, base_context, service):
                    self._service = service
                    self.operation_name = getattr(base_context, "operation_name")
                    self.start_time: datetime = getattr(base_context, "start_time")
                    self.end_time: datetime = getattr(base_context, "end_time")
                    self.component = getattr(base_context, "component")
                    self.operation_id = getattr(base_context, "operation_id")
                    self.metadata = getattr(base_context, "metadata")
                    self.performance_metrics = getattr(base_context, "performance_metrics")
                    self.success = getattr(base_context, "success")
                    self.error = getattr(base_context, "error")

                @property
                def duration(self) -> float | None:
                    """Calculate operation duration"""
                    if self.end_time and self.start_time:
                        return (self.end_time - self.start_time).total_seconds()
                    return None

                def log_progress(self, message: str, **extra_data):
                    """Log operation progress with context"""
                    operation_logger.info(
                        f"📊 {message}",
                        extra={
                            "operation_id": operation_id,
                            "progress": True,
                            **extra_data,
                        },
                    )

                def add_metric(self, name: str, value: Any):
                    """Add custom metric to operation context"""
                    self.metadata[f"metric_{name}"] = value

                def warn_if_memory_high(self):
                    """Check and warn if memory usage is high (override in subclasses)"""
                    return False

            enhanced_context = EnhancedContext(context, self)
            yield enhanced_context

        except Exception as e:
            context.success = False
            context.error = str(e)
            if enhanced_context:
                enhanced_context.success = False
                enhanced_context.error = str(e)
            operation_logger.error(
                f"❌ Operation failed: {e}",
                extra={"operation_id": operation_id, "error": str(e)},
                exc_info=True,
            )
            raise

        finally:
            # Finalize operation tracking
            context.end_time = datetime.now(timezone.utc)
            if enhanced_context:
                enhanced_context.end_time = context.end_time

            # Log operation completion
            duration = context.duration
            if context.success:
                operation_logger.info(
                    f"✅ Completed operation: {operation_name} ({duration:.2f}s)",
                    extra={
                        "operation_id": operation_id,
                        "duration": duration,
                        "success": True,
                        "metadata": context.metadata,
                    },
                )
            else:
                operation_logger.error(
                    f"❌ Failed operation: {operation_name} ({duration:.2f}s)",
                    extra={
                        "operation_id": operation_id,
                        "duration": duration,
                        "success": False,
                        "error": context.error,
                        "metadata": context.metadata,
                    },
                )

            # Cleanup context
            self._operation_contexts.pop(operation_id, None)

    def log_progress(
        self,
        operation: str,
        current: int,
        total: int,
        component: str | None = None,
        **extra_data,
    ):
        """
        Generic progress logging.

        Args:
            operation: Operation name
            current: Current progress count
            total: Total items
            component: Component name (optional)
            **extra_data: Additional data
        """
        operation_logger = self.create_operation_logger(operation, component)

        percentage = (current / total * 100) if total > 0 else 0
        progress_msg = f"📊 Progress: {operation} - {current}/{total} ({percentage:.1f}%)"

        operation_logger.info(
            progress_msg,
            extra={
                "progress": True,
                "current": current,
                "total": total,
                "percentage": percentage,
                **extra_data,
            },
        )

    def create_success_result(
        self, data: Any, operation: str | None = None, **metrics
    ) -> dict[str, Any]:
        """
        Create standardized success result with observability metadata.

        Args:
            data: Result data
            operation: Operation name
            **metrics: Additional metrics

        Returns:
            Standardized result dictionary
        """
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "observability_metrics": metrics,
        }

        if isinstance(data, dict):
            result.update(data)
            if "status" not in result:
                result["status"] = "success"
        else:
            result.update({"status": "success", "data": data})

        return result

    def create_error_result(
        self, error: Exception, operation: str | None = None, **context
    ) -> dict[str, Any]:
        """
        Create standardized error result with observability metadata.

        Args:
            error: Exception that occurred
            operation: Operation name
            **context: Additional context

        Returns:
            Standardized error result dictionary
        """
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "error": {
                "type": type(error).__name__,
                "message": str(error),
                "context": context,
            },
        }

    def get_operation_stats(self) -> dict[str, Any]:
        """Get current operation statistics for monitoring"""
        return {
            "active_operations": len(self._operation_contexts),
            "operations": list(self._operation_contexts.keys()),
            "performance_monitoring": self.enable_performance_monitoring,
            "memory_monitoring": self.enable_memory_monitoring,
            "structured_logging": self.enable_structured_logging,
        }

    def cleanup(self):
        """Cleanup resources and finalize monitoring"""
        logger.info("🧹 GenericObservabilityService cleanup completed")


# =================================================================
# DECORATOR FOR AUTOMATIC OPERATION TRACKING
# =================================================================


def observe_operation(operation_name: str | None = None, component: str | None = None):
    """
    Decorator for automatic operation observability.

    Usage:
        @observe_operation('download_data', 'download_handler')
        async def download_function():
            # Function automatically tracked with observability
    """

    def decorator(func: Callable):
        op_name = operation_name or func.__name__

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Extract observability service from args if available
                observability_service = None
                filtered_args = []

                for arg in args:
                    if hasattr(arg, "observability") and hasattr(
                        arg.observability, "track_operation"
                    ):
                        observability_service = arg.observability
                    else:
                        filtered_args.append(arg)

                if observability_service:
                    with observability_service.track_operation(op_name, component):
                        return await func(*filtered_args, **kwargs)
                else:
                    return await func(*args, **kwargs)

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Extract observability service from args if available
                observability_service = None
                filtered_args = []

                for arg in args:
                    if hasattr(arg, "observability") and hasattr(
                        arg.observability, "track_operation"
                    ):
                        observability_service = arg.observability
                    else:
                        filtered_args.append(arg)

                if observability_service:
                    with observability_service.track_operation(op_name, component):
                        return func(*filtered_args, **kwargs)
                else:
                    return func(*args, **kwargs)

            return sync_wrapper

    return decorator
