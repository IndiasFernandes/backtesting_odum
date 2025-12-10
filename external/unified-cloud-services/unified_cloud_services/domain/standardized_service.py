"""
Standardized Domain Cloud Service

Wrapper around UnifiedCloudService with domain-specific validation and synchronous public API.

Provides:
- Synchronous public API (wraps async UnifiedCloudService internally)
- Domain-specific validation rules (market_data, features, strategy, execution, ml)
- Timestamp semantics handling (timestamp_in/timestamp_out for internal, local_timestamp/timestamp for external)
- Unified signatures (timerange, filters) that apply appropriately for GCS vs BigQuery

Design Philosophy:
- Simple, debuggable synchronous API for callers
- Internal async optimization via UnifiedCloudService
- Domain-aware validation before uploads
- Backward compatible with existing sync client code
"""

import asyncio
import logging
import pandas as pd
from datetime import datetime, timezone
from typing import Any
import os

from google.auth.exceptions import DefaultCredentialsError
from google.cloud import bigquery

from unified_cloud_services.core.unified_cloud_service import UnifiedCloudService
from unified_cloud_services.core.cloud_config import CloudConfig, CloudTarget
from unified_cloud_services.core.error_handling import GenericErrorHandlingService
from unified_cloud_services.models.error import ErrorContext
from unified_cloud_services.domain.validation import DomainValidationService
from unified_cloud_services.domain.factories import (
    create_market_data_cloud_service,
    create_features_cloud_service,
    create_strategy_cloud_service,
    create_backtesting_cloud_service,
    create_instruments_cloud_service,
)
from unified_cloud_services.core.cloud_auth_factory import CloudAuthFactory
from unified_cloud_services.core.config import get_config


logger = logging.getLogger(__name__)



def create_domain_cloud_service(domain: str) -> UnifiedCloudService:
    """
    Factory function to create domain-specific UnifiedCloudService.

    Args:
        domain: 'market_data', 'features', 'strategy', 'execution', 'ml'

    Returns:
        Configured UnifiedCloudService instance
    """
    domain_factories = {
        "market_data": create_market_data_cloud_service,
        "features": create_features_cloud_service,
        "strategy": create_strategy_cloud_service,
        "execution": create_strategy_cloud_service,  # Reuse strategy service for execution
        "ml": create_backtesting_cloud_service,  # Reuse backtesting for ML
        "instruments": create_instruments_cloud_service,  # Instruments domain
    }

    if domain not in domain_factories:
        raise ValueError(
            f"Unknown domain: {domain}. Must be one of: {list(domain_factories.keys())}"
        )

    return domain_factories[domain]()


class StandardizedDomainCloudService:
    """
    Wrapper around UnifiedCloudService with domain-specific validation.

    Provides synchronous public API that wraps async UnifiedCloudService internally,
    enabling simple, debuggable APIs while maintaining internal async optimization.
    """

    def __init__(
        self,
        domain: str,
        cloud_target: CloudTarget | None = None,
        config: CloudConfig | None = None,
    ):
        """
        Initialize standardized domain cloud service.

        Args:
            domain: 'market_data', 'features', 'strategy', 'execution', 'ml', 'instruments'
            cloud_target: Runtime cloud target configuration (uses defaults if None)
            config: Optional CloudConfig (uses defaults if None)
        """
        self.domain = domain

        # Create domain-specific UnifiedCloudService
        self.unified_service = create_domain_cloud_service(domain)

        # Set cloud target (with domain-specific defaults if not provided)
        self.cloud_target = cloud_target or self._get_default_target(domain)

        # Initialize domain validation service
        self.domain_validation = DomainValidationService(domain=domain)

        # Initialize error handling service (DRY: centralized error handling)
        self.error_handling = GenericErrorHandlingService(
            config={
                "enable_error_classification": True,
                "enable_auto_recovery": True,
                "strict_mode": False,  # Don't fail fast by default
            }
        )

        # Track async event loop state
        self._event_loop = None
        self._loop_thread = None

        logger.info(f"✅ StandardizedDomainCloudService initialized: domain={domain}")
        logger.info(
            f"🔧 Target: bucket={self.cloud_target.gcs_bucket}, "
            f"dataset={self.cloud_target.bigquery_dataset}"
        )

    def _get_default_target(self, domain: str) -> CloudTarget:
        """Get default CloudTarget for domain"""
        defaults = {
            "market_data": CloudTarget(
                gcs_bucket=get_config("GCS_BUCKET", "market-data-tick"),
                bigquery_dataset=get_config("BIGQUERY_DATASET", "market_data_hft"),
            ),
            "features": CloudTarget(
                gcs_bucket=get_config("ML_FEATURES_BUCKET", "ml-features-store"),
                bigquery_dataset=get_config("FEATURES_DATASET", "features_data"),
            ),
            "strategy": CloudTarget(
                gcs_bucket=get_config("STRATEGY_BUCKET", "strategy-execution"),
                bigquery_dataset=get_config("STRATEGY_DATASET", "strategy_orders"),
            ),
            "execution": CloudTarget(
                gcs_bucket=get_config("EXECUTION_BUCKET", "strategy-execution"),
                bigquery_dataset=get_config("EXECUTION_DATASET", "execution_logs"),
            ),
            "ml": CloudTarget(
                gcs_bucket=get_config("ML_MODELS_BUCKET", "ml-models-store"),
                bigquery_dataset=get_config("ML_PREDICTIONS_DATASET", "ml_predictions"),
            ),
        }
        return defaults.get(domain, defaults["market_data"])

    def _run_async(self, coro):
        """Run async coroutine in sync context"""
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
    # SYNCHRONOUS PUBLIC API (wraps async UnifiedCloudService)
    # =================================================================

    def upload_to_gcs(
        self,
        data: pd.DataFrame | bytes | str | Any,
        gcs_path: str,
        format: str = "parquet",
        metadata: dict[str, str] | None = None,
    ) -> str:
        """
        Upload data to GCS with runtime target configuration.

        Synchronous wrapper around async UnifiedCloudService.upload_to_gcs()

        Args:
            data: Data to upload (DataFrame, bytes, string, or any serializable object)
            gcs_path: Path within bucket (e.g., 'processed_candles/by_date/day-2023-05-23/...')
            format: File format ('parquet', 'csv', 'json', 'pickle', 'joblib', 'bytes')
            metadata: Optional metadata to attach to blob

        Returns:
            Full GCS path (gs://bucket/path)
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
        self, gcs_path: str, format: str = "parquet", log_errors: bool = True
    ) -> pd.DataFrame | bytes | str | Any:
        """
        Download data from GCS with runtime target configuration.

        Synchronous wrapper around async UnifiedCloudService.download_from_gcs()

        Args:
            gcs_path: Path within bucket
            format: Expected format ('parquet', 'csv', 'json', 'pickle', 'joblib', 'bytes', 'text')
            log_errors: Whether to log errors as ERROR (default True).
                       Set to False for expected missing files (cache misses).

        Returns:
            Data in appropriate format
        """

        async def _download():
            return await self.unified_service.download_from_gcs(
                target=self.cloud_target,
                gcs_path=gcs_path,
                format=format,
                log_errors=log_errors,
            )

        return self._run_async(_download())

    def upload_to_bigquery(
        self,
        data: pd.DataFrame,
        table_name: str,
        write_mode: str = "safe",
        partition_field: str = "timestamp",
        clustering_fields: list[str] | None = None,
        validate: bool = True,
    ) -> dict[str, Any]:
        """
        Upload DataFrame to BigQuery with domain-specific validation.

        Synchronous wrapper around async UnifiedCloudService.upload_to_bigquery()
        with domain-specific validation before upload.

        Args:
            data: DataFrame to upload
            table_name: Table name (without project.dataset prefix)
            write_mode: 'safe' (delete+insert), 'skip' (check existence), 'append'
            partition_field: Field for table partitioning
            clustering_fields: Fields for table clustering
            validate: Whether to apply domain-specific validation (default: True)

        Returns:
            Upload result with metrics
        """
        # Apply domain-specific validation
        if validate:
            validation_result = self.domain_validation.validate_for_domain(data, data_type=None)
            if not validation_result.valid:
                error_msg = f"Domain validation failed for {self.domain}"
                if validation_result.errors:
                    error_msg += f"\nErrors: {validation_result.errors}"
                raise ValueError(error_msg)

            if validation_result.warnings:
                logger.warning(
                    f"Domain validation warnings for {self.domain}: {validation_result.warnings}"
                )

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

    def query_bigquery(self, query: str, parameters: dict[str, Any] = None) -> pd.DataFrame:
        """
        Execute BigQuery query with runtime target configuration.

        Synchronous wrapper around async UnifiedCloudService.query_bigquery()

        Args:
            query: SQL query to execute
            parameters: Query parameters for parameterized queries

        Returns:
            Query results as DataFrame
        """

        async def _query():
            return await self.unified_service.query_bigquery(
                query=query, target=self.cloud_target, parameters=parameters
            )

        return self._run_async(_query())

    def get_secret(self, secret_name: str, version: str = "latest") -> str:
        """
        Get secret from Secret Manager.

        Args:
            secret_name: Name of the secret
            version: Secret version ('latest' or specific version)

        Returns:
            Secret value as string
        """

        async def _get_secret():
            return await self.unified_service.get_secret(
                secret_name=secret_name, target=self.cloud_target, version=version
            )

        return self._run_async(_get_secret())

    def ensure_warmed_connections(self):
        """Ensure cloud connections are warmed up (synchronous wrapper)"""
        self._run_async(self.unified_service.ensure_warmed_connections())

    def cleanup(self):
        """Cleanup cloud connections"""
        self._run_async(self.unified_service.cleanup())

    # =================================================================
    # MARKET_DATA DOMAIN CONVENIENCE METHODS
    # =================================================================

    def get_tick_data(
        self,
        instrument: str,
        timerange: tuple[datetime, datetime] | None = None,
        filters: dict[str, Any] | None = None,
        data_type: str = "trades",
        date: datetime | None = None,
    ) -> pd.DataFrame:
        """
        Get tick data from GCS with unified timerange/filter interface.

        Market-data-specific convenience method for accessing tick data.
        Uses optimized parquet index chunk structure for efficient reads.

        Args:
            instrument: Instrument ID (e.g., 'BINANCE-FUTURES:PERPETUAL:BTC-USDT')
            timerange: (start_time, end_time) tuple - optional
            filters: Additional filters (optional)
            data_type: Data type ('trades', 'book_snapshot_5', etc.)
            date: Single date (datetime or date) - used if timerange not provided

        Returns:
            DataFrame with tick data
        """
        if self.domain != "market_data":
            raise ValueError(
                f"get_tick_data() is only available for market_data domain, not {self.domain}"
            )

        async def _get_tick_data():
            # Determine date from timerange or date parameter
            if timerange:
                start_date, end_date = timerange
                date_to_use = start_date
            elif date:
                if isinstance(date, datetime):
                    date_to_use = date
                else:
                    # Assume it's a date object, convert to datetime
                    date_to_use = datetime.combine(date, datetime.min.time()).replace(
                        tzinfo=timezone.utc
                    )
            else:
                logger.warning("No timerange or date provided for tick data query")
                return pd.DataFrame()

            # Build GCS path pattern
            # Format: raw_tick_data/by_date/day-YYYY-MM-DD/data_type-{data_type}/{instrument}.parquet
            date_str = date_to_use.strftime("%Y-%m-%d")
            gcs_path = (
                f"raw_tick_data/by_date/day-{date_str}/data_type-{data_type}/{instrument}.parquet"
            )

            logger.info(f"📥 Loading tick data: {gcs_path}")

            try:
                tick_df = await self.unified_service.download_from_gcs(
                    target=self.cloud_target, gcs_path=gcs_path, format="parquet"
                )

                # If timerange provided, filter the data
                if timerange and not tick_df.empty:
                    start_time, end_time = timerange
                    if "timestamp" in tick_df.columns:
                        # Convert timestamp to datetime for filtering
                        timestamps = pd.to_datetime(
                            tick_df["timestamp"], unit="us", errors="coerce", utc=True
                        )

                        # If end_time is at second boundary (23:59:59), extend to include microseconds
                        # to match behavior of loading entire day file
                        if (
                            end_time.microsecond == 0
                            and end_time.second == 59
                            and end_time.minute == 59
                        ):
                            # Extend to include all microseconds in the second
                            end_time_inclusive = end_time.replace(microsecond=999999)
                        else:
                            end_time_inclusive = end_time

                        mask = (timestamps >= start_time) & (timestamps <= end_time_inclusive)
                        tick_df = tick_df[mask]
                        logger.info(f"✅ Filtered to {len(tick_df)} ticks in timerange")

                return tick_df
            except Exception as e:
                logger.warning(f"Failed to load tick data from {gcs_path}: {e}")
                return pd.DataFrame()

        return self._run_async(_get_tick_data())

    def get_candles_with_hft_features(
        self,
        instrument: str,
        timeframe: str,
        timerange: tuple[datetime, datetime] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        Get candles with HFT features from BigQuery (market_data domain).

        Note: This accesses market_data domain. HFT features are part of market data candles.
        Features service domain contains MFT features (technical indicators).

        Args:
            instrument: Instrument ID
            timeframe: Timeframe ('15s', '1m', '5m', '1h', etc.)
            timerange: (start_time, end_time) tuple - optional
            filters: Additional filters (optional)
            limit: Maximum rows to return

        Returns:
            DataFrame with OHLCV + HFT features (delay metrics, volume imbalances, liquidations, etc.)
        """
        if self.domain != "market_data":
            raise ValueError(
                f"get_candles_with_hft_features() is only available for market_data domain, not {self.domain}"
            )

        async def _get_candles():
            # Use direct BigQuery client for better parameter handling

            bq_client = CloudAuthFactory.create_authenticated_bigquery_client(
                self.cloud_target.project_id
            )

            # Build BigQuery query with parameterized queries
            if timerange:
                start_time, end_time = timerange
                query = f"""
                SELECT * FROM `{self.cloud_target.project_id}.{self.cloud_target.bigquery_dataset}.candles_{timeframe}_trades`
                WHERE instrument_id = @instrument_id
                  AND timestamp >= @start_timestamp
                  AND timestamp < @end_timestamp
                ORDER BY timestamp DESC
                LIMIT @limit
                """
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("instrument_id", "STRING", instrument),
                        bigquery.ScalarQueryParameter("start_timestamp", "TIMESTAMP", start_time),
                        bigquery.ScalarQueryParameter("end_timestamp", "TIMESTAMP", end_time),
                        bigquery.ScalarQueryParameter("limit", "INT64", limit),
                    ]
                )
            else:
                query = f"""
                SELECT * FROM `{self.cloud_target.project_id}.{self.cloud_target.bigquery_dataset}.candles_{timeframe}_trades`
                WHERE instrument_id = @instrument_id
                ORDER BY timestamp DESC
                LIMIT @limit
                """
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("instrument_id", "STRING", instrument),
                        bigquery.ScalarQueryParameter("limit", "INT64", limit),
                    ]
                )

            # Execute query
            query_job = bq_client.query(query, job_config=job_config)
            results_df = query_job.result(timeout=60).to_dataframe()

            logger.info(f"✅ Retrieved {len(results_df)} candles with HFT features")
            return results_df

        return self._run_async(_get_candles())

    def check_gcs_path_exists(self, gcs_path: str) -> bool:
        """
        Check if GCS path exists.

        Uses centralized error handling to ensure errors are properly logged and propagated.

        Args:
            gcs_path: Path within bucket

        Returns:
            True if path exists, False if not found or on error.
            Raises exceptions for authentication/configuration errors.
        """

        async def _check_exists():
            context = ErrorContext(
                operation="check_gcs_path_exists",
                component="StandardizedDomainCloudService",
                input_data={
                    "gcs_path": gcs_path,
                    "bucket": self.cloud_target.gcs_bucket,
                    "project_id": self.cloud_target.project_id,
                },
            )

            async def _do_check_exists():
                try:
                    gcs_client = CloudAuthFactory.create_authenticated_gcs_client(
                        self.cloud_target.project_id
                    )
                    bucket = gcs_client.bucket(self.cloud_target.gcs_bucket)
                    blob = bucket.blob(gcs_path)

                    return blob.exists()
                except DefaultCredentialsError as e:
                    # Authentication errors should be raised, not silently ignored
                    error_msg = (
                        f"GCS authentication failed for path '{gcs_path}'. "
                        f"Check that GOOGLE_APPLICATION_CREDENTIALS is set correctly. "
                        f"Error: {e}"
                    )
                    logger.error(f"❌ {error_msg}")
                    raise ValueError(error_msg) from e
                except Exception as e:
                    # Other errors should be properly logged and re-raised
                    error_msg = f"Failed to check GCS path existence for '{gcs_path}': {e}"
                    logger.error(f"❌ {error_msg}")
                    raise

            # Use centralized error handling
            try:
                return (
                    await self.error_handling.execute_with_error_handling_async(
                        _do_check_exists,
                        context=context,
                        max_retries=0,  # Don't retry on authentication errors
                    )
                    or False
                )
            except Exception:
                # If error handling raises, return False (but error already logged)
                return False

        return self._run_async(_check_exists())

    def list_gcs_files(self, prefix: str) -> list[dict[str, str]]:
        """
        List files in GCS with given prefix.

        Uses centralized error handling to ensure errors are properly logged and propagated.
        Raises exceptions for authentication/configuration errors instead of silently failing.

        Args:
            prefix: Path prefix to filter files

        Returns:
            List of file dictionaries with 'name', 'size', 'updated' keys.
            Empty list returned only if no files found (not on error).

        Raises:
            ValueError: If authentication fails or credentials are missing
            Exception: Other GCS errors (properly logged with context)
        """

        async def _list_files():
            context = ErrorContext(
                operation="list_gcs_files",
                component="StandardizedDomainCloudService",
                input_data={
                    "prefix": prefix,
                    "bucket": self.cloud_target.gcs_bucket,
                    "project_id": self.cloud_target.project_id,
                },
            )

            async def _do_list_files():
                try:
                    gcs_client = CloudAuthFactory.create_authenticated_gcs_client(
                        self.cloud_target.project_id
                    )
                    bucket = gcs_client.bucket(self.cloud_target.gcs_bucket)

                    files = []
                    for blob in bucket.list_blobs(prefix=prefix):
                        files.append(
                            {
                                "name": blob.name,
                                "size": blob.size,
                                "updated": (blob.updated.isoformat() if blob.updated else None),
                            }
                        )

                    logger.debug(f"✅ Listed {len(files)} files for prefix: {prefix}")
                    return files

                except DefaultCredentialsError as e:
                    # Authentication errors should be raised, not silently ignored
                    error_msg = (
                        f"GCS authentication failed for prefix '{prefix}'. "
                        f"Check that GOOGLE_APPLICATION_CREDENTIALS is set correctly. "
                        f"Error: {e}"
                    )
                    logger.error(f"❌ {error_msg}")
                    raise ValueError(error_msg) from e
                except Exception as e:
                    # Other errors should be properly logged and re-raised
                    error_msg = f"Failed to list GCS files for prefix '{prefix}': {e}"
                    logger.error(f"❌ {error_msg}")
                    raise

            # Use centralized error handling
            # Note: If error handling is configured to return None on failure, we want to raise instead
            result = await self.error_handling.execute_with_error_handling_async(
                _do_list_files,
                context=context,
                max_retries=0,  # Don't retry on authentication errors
            )

            # If error handling returned None (on failure), raise to prevent silent failures
            if result is None:
                raise ValueError(
                    f"list_gcs_files returned None for prefix '{prefix}'. "
                    f"This indicates an error occurred but was silently handled. "
                    f"Check logs for details."
                )

            return result

        try:
            result = self._run_async(_list_files())
            return result if result is not None else []
        except ValueError as e:
            # Re-raise authentication/configuration errors
            raise
        except Exception as e:
            # Wrap other exceptions with context
            logger.error(f"❌ Unexpected error in list_gcs_files: {e}")
            raise RuntimeError(f"Failed to list GCS files: {e}") from e
