"""
Generic Batch Processor

Base batch processor with shared timeframe logic, date range computation, and memory estimation.
Services extend this class with domain-specific logic.

Usage:
    class FeaturesBatchProcessor(GenericBatchProcessor):
        def _compute_required_periods(self, timeframe: str, **kwargs) -> int:
            enabled_calculators = kwargs.get('enabled_calculators', [])
            # Domain-specific lookback computation
            return 500  # Example: features need 500 candles
"""

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class GenericBatchProcessor:
    """
    Base batch processor with common logic for all services.
    Services should extend this class and implement domain-specific logic.
    """

    # Shared timeframe to minutes mapping
    TIMEFRAME_MINUTES = {
        "15s": 0.25,
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "1h": 60,
        "4h": 240,
        "24h": 1440,
    }

    def __init__(self):
        logger.info("Initialized GenericBatchProcessor")

    def _compute_required_periods(self, timeframe: str, **kwargs) -> int:
        """
        Compute the minimum required lookback periods for a given timeframe.
        This method should be overridden by domain-specific batch processors.

        Args:
            timeframe: Timeframe string (e.g., '5m', '1h')
            **kwargs: Domain-specific parameters

        Returns:
            Number of periods required for lookback
        """
        raise NotImplementedError("Subclasses must implement _compute_required_periods")

    def compute_required_lookback(self, timeframe: str, **kwargs) -> int:
        """
        Compute required lookback candles (alias for _compute_required_periods).

        Args:
            timeframe: Timeframe string
            **kwargs: Domain-specific parameters

        Returns:
            Number of candles required for lookback
        """
        return self._compute_required_periods(timeframe, **kwargs)

    def compute_query_date_range(
        self, start_date: datetime, end_date: datetime, timeframe: str, **kwargs
    ) -> tuple[datetime, datetime]:
        """
        Compute the actual query date range including lookback.

        Args:
            start_date: Desired start date
            end_date: Desired end date
            timeframe: Timeframe string
            **kwargs: Domain-specific parameters

        Returns:
            Tuple of (query_start_date, query_end_date)
        """
        required_periods = self._compute_required_periods(timeframe, **kwargs)
        minutes_per_period = self.TIMEFRAME_MINUTES.get(timeframe, 5)
        lookback_delta = timedelta(minutes=required_periods * minutes_per_period)
        query_start = start_date - lookback_delta
        query_end = end_date
        logger.info(
            f"Computed query date range: {query_start} to {query_end} "
            f"(lookback: {required_periods} periods = {lookback_delta})"
        )
        return query_start, query_end

    def compute_multi_timeframe_lookback(
        self, base_timeframe: str, target_timeframes: list[str], **kwargs
    ) -> dict[str, int]:
        """
        Compute lookback requirements for multiple timeframes.

        For batch processing with multi-timeframe features, we need to ensure
        sufficient data for ALL timeframes (not just base).

        Args:
            base_timeframe: Primary timeframe (e.g., '1m')
            target_timeframes: List of timeframes to generate (e.g., ['1m', '5m', '15m'])
            **kwargs: Domain-specific parameters

        Returns:
            Dictionary mapping timeframe to required lookback candles
        """
        lookback_by_timeframe = {}

        for tf in target_timeframes:
            # Compute lookback for this timeframe
            required_candles = self._compute_required_periods(tf, **kwargs)

            # If this timeframe is higher than base, we need more base candles
            base_minutes = self.TIMEFRAME_MINUTES.get(base_timeframe, 5)
            tf_minutes = self.TIMEFRAME_MINUTES.get(tf, 5)

            if tf_minutes > base_minutes:
                # Higher timeframe needs more base candles
                multiplier = tf_minutes / base_minutes
                required_base_candles = int(required_candles * multiplier)
            else:
                # Same or lower timeframe - use as-is
                required_base_candles = required_candles

            lookback_by_timeframe[tf] = max(required_base_candles, required_candles)

        # Return maximum across all timeframes
        max_lookback = max(lookback_by_timeframe.values())

        logger.info(
            f"Multi-timeframe lookback: max={max_lookback} candles, "
            f"by timeframe: {lookback_by_timeframe}"
        )

        return lookback_by_timeframe

    def estimate_memory_requirements(
        self, num_records: int, record_size_bytes: int, **kwargs
    ) -> dict[str, Any]:
        """
        Estimate memory requirements for batch processing.

        Args:
            num_records: Number of records to process
            record_size_bytes: Estimated bytes per record
            **kwargs: Additional parameters for estimation

        Returns:
            Dictionary with memory estimates
        """
        total_bytes = num_records * record_size_bytes
        total_mb = total_bytes / (1024 * 1024)
        estimate = {
            "num_records": num_records,
            "record_size_bytes": record_size_bytes,
            "total_bytes": total_bytes,
            "total_mb": round(total_mb, 2),
            "total_gb": round(total_mb / 1024, 2),
            **kwargs,
        }
        logger.info(f"Memory estimate: {estimate['total_mb']} MB ({estimate['total_gb']} GB)")
        return estimate

    def get_timeframe_multiplier(self, base_timeframe: str, target_timeframe: str) -> float:
        """
        Get multiplier for converting between timeframes.

        Args:
            base_timeframe: Source timeframe
            target_timeframe: Target timeframe

        Returns:
            Multiplier (e.g., 5m → 1h = 12.0)
        """
        base_minutes = self.TIMEFRAME_MINUTES.get(base_timeframe)
        target_minutes = self.TIMEFRAME_MINUTES.get(target_timeframe)
        if base_minutes is None or target_minutes is None:
            raise ValueError(f"Unsupported timeframe(s): {base_timeframe}, {target_timeframe}")
        return target_minutes / base_minutes
