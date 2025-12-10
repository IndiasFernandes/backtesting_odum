"""
Service Wrapper Base Class

Generic base class for wrapping UnifiedCloudService with domain-specific logic.
Eliminates duplication of wrapper patterns across services.

Usage:
    class FeaturesServiceWrapper(ServiceWrapper):
        def __init__(self, cloud_target: CloudTarget):
            super().__init__('features', cloud_target)

        def upload_features(self, data: pd.DataFrame, table_name: str):
            # Domain-specific validation
            self._validate_features(data)
            # Call parent upload method
            return self.upload_to_bigquery(data, table_name, validate=True)
"""

import asyncio
import logging
from typing import Any, Union
import pandas as pd

from unified_cloud_services.core.cloud_config import CloudTarget, CloudConfig
from unified_cloud_services.core.unified_cloud_service import UnifiedCloudService
from unified_cloud_services.core.error_handling import GenericErrorHandlingService

logger = logging.getLogger(__name__)


class ServiceWrapper:
    """
    Base class for wrapping UnifiedCloudService with domain-specific logic.

    Provides:
    - Async event loop management
    - Error handling integration
    - Domain-specific validation hooks
    - Synchronous wrapper methods for async operations
    """

    def __init__(
        self,
        domain: str,
        cloud_target: CloudTarget,
        config: CloudConfig | None = None,
    ):
        """
        Initialize service wrapper.

        Args:
            domain: Domain name (e.g., 'features', 'strategy', 'market_data')
            cloud_target: Cloud target configuration
            config: Optional cloud config
        """
        self.domain = domain
        self.cloud_target = cloud_target
        self.config = config or CloudConfig()

        # Create UnifiedCloudService instance
        self.unified_service = UnifiedCloudService(self.config)

        # Initialize error handling
        self.error_handling = GenericErrorHandlingService(
            config={
                "enable_error_classification": True,
                "enable_auto_recovery": True,
                "strict_mode": False,
            }
        )

        # Track async event loop state
        self._event_loop = None
        self._loop_thread = None

        logger.info(f"✅ {self.__class__.__name__} initialized: domain={domain}")

    def _run_async(self, coro):
        """
        Run async coroutine in sync context.

        Handles event loop creation and management automatically.
        """
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we need to use a different approach
                # Create new event loop in thread (for nested sync/async calls)
                import threading

                result = [None]
                exception = [None]

                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result[0] = new_loop.run_until_complete(coro)
                    except Exception as e:
                        exception[0] = e
                    finally:
                        new_loop.close()

                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()

                if exception[0]:
                    raise exception[0]
                return result[0]
            else:
                # Loop exists but not running, use it
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop exists, create one
            return asyncio.run(coro)

    # =================================================================
    # WRAPPED CLOUD OPERATIONS (Synchronous wrappers)
    # =================================================================

    def upload_to_gcs(
        self,
        data: Union[pd.DataFrame, bytes, str, Any],
        gcs_path: str,
        format: str = "parquet",
        metadata: dict[str, str] | None = None,
        **kwargs,
    ) -> str:
        """
        Upload data to GCS (synchronous wrapper).

        Subclasses can override to add domain-specific validation.

        Args:
            data: Data to upload
            gcs_path: Path within bucket
            format: File format
            metadata: Optional metadata
            **kwargs: Additional arguments

        Returns:
            Full GCS path
        """

        async def _upload():
            return await self.unified_service.upload_to_gcs(
                data=data,
                target=self.cloud_target,
                gcs_path=gcs_path,
                format=format,
                metadata=metadata,
            )

        return self._run_async(_upload())

    def download_from_gcs(
        self, gcs_path: str, format: str = "parquet"
    ) -> Union[pd.DataFrame, bytes, str, Any]:
        """
        Download data from GCS (synchronous wrapper).

        Args:
            gcs_path: Path within bucket
            format: Expected format

        Returns:
            Downloaded data
        """

        async def _download():
            return await self.unified_service.download_from_gcs(
                target=self.cloud_target, gcs_path=gcs_path, format=format
            )

        return self._run_async(_download())

    def upload_to_bigquery(
        self,
        data: pd.DataFrame,
        table_name: str,
        write_mode: str = "append",
        partition_field: str = "timestamp",
        clustering_fields: list[str] | None = None,
        validate: bool = True,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Upload DataFrame to BigQuery (synchronous wrapper).

        Subclasses can override _validate_before_upload() to add domain-specific validation.

        Args:
            data: DataFrame to upload
            table_name: Table name
            write_mode: Write mode
            partition_field: Partition field
            clustering_fields: Clustering fields
            validate: Whether to validate before upload
            **kwargs: Additional arguments

        Returns:
            Upload result
        """
        # Domain-specific validation hook
        if validate:
            self._validate_before_upload(data, table_name, **kwargs)

        async def _upload():
            return await self.unified_service.upload_to_bigquery(
                data=data,
                target=self.cloud_target,
                table_name=table_name,
                write_mode=write_mode,
                partition_field=partition_field,
                clustering_fields=clustering_fields,
            )

        return self._run_async(_upload())

    def query_bigquery(self, query: str, parameters: dict[str, Any] | None = None) -> pd.DataFrame:
        """
        Execute BigQuery query (synchronous wrapper).

        Args:
            query: SQL query
            parameters: Query parameters

        Returns:
            Query results as DataFrame
        """

        async def _query():
            return await self.unified_service.query_bigquery(
                query=query, target=self.cloud_target, parameters=parameters
            )

        return self._run_async(_query())

    def list_gcs_files(self, prefix: str) -> list[dict[str, Any]]:
        """
        List GCS files (synchronous wrapper).

        Args:
            prefix: Path prefix

        Returns:
            List of file dictionaries
        """

        async def _list():
            return await self.unified_service.list_gcs_files(
                target=self.cloud_target, prefix=prefix
            )

        return self._run_async(_list())

    def check_gcs_path_exists(self, gcs_path: str) -> bool:
        """
        Check if GCS path exists (synchronous wrapper).

        Uses batch list_blobs for performance.

        Args:
            gcs_path: GCS path to check

        Returns:
            True if path exists
        """
        # Extract prefix from path
        prefix = "/".join(gcs_path.split("/")[:-1]) + "/" if "/" in gcs_path else ""

        files = self.list_gcs_files(prefix)
        existing_paths = {f["name"] for f in files}

        return gcs_path in existing_paths

    # =================================================================
    # DOMAIN-SPECIFIC VALIDATION HOOKS (Override in subclasses)
    # =================================================================

    def _validate_before_upload(self, data: pd.DataFrame, table_name: str, **kwargs) -> None:
        """
        Validate data before upload (domain-specific hook).

        Subclasses should override this to add domain-specific validation.
        Raise ValueError if validation fails.

        Args:
            data: DataFrame to validate
            table_name: Target table name
            **kwargs: Additional context
        """
        # Base implementation: no validation
        # Subclasses override for domain-specific rules
        pass

    def _validate_before_download(self, gcs_path: str, **kwargs) -> None:
        """
        Validate before download (domain-specific hook).

        Subclasses can override to add validation.

        Args:
            gcs_path: GCS path to download
            **kwargs: Additional context
        """
        # Base implementation: no validation
        pass
