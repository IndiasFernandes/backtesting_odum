"""
Centralized CSV Sampling Service

Provides unified CSV sampling logic for all services.
Follows DRY principle - centralized in unified-cloud-services.

Key Features:
- Environment-aware (only samples in non-production)
- Configurable sample size via CSV_SAMPLE_SIZE env var
- Smart sampling for different data types
- Production mode: No sampling (doesn't drop samples, just doesn't create CSV files)
"""

import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Any
from unified_cloud_services.core.config import unified_config

logger = logging.getLogger(__name__)


class SamplingService:
    """
    Centralized CSV sampling service for all services.

    Provides unified sampling logic that can be used across all services
    without duplication.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize sampling service.

        Args:
            config: Optional configuration dict with:
                - sample_size: Override CSV_SAMPLE_SIZE env var
                - sample_dir: Override CSV_SAMPLE_DIR env var
                - enable_sampling: Override ENABLE_CSV_SAMPLING env var
        """
        self.config = config or {}

        # Get sample size from config or env var (default: 10)
        self.sample_size = self.config.get("sample_size") or unified_config.csv_sample_size

        # Get sample directory from config or env var
        self.sample_dir = Path(self.config.get("sample_dir") or unified_config.csv_sample_dir)

        # Check if sampling is enabled (from config or env var)
        enable_sampling = self.config.get("enable_sampling")
        if enable_sampling is None:
            enable_sampling = unified_config.enable_csv_sampling
        self.enable_sampling = enable_sampling

        # Check environment (only sample in non-production)
        environment = unified_config.environment.lower()
        self.is_production = environment in ["production", "prod", "vm"]

        logger.info(
            f"📊 SamplingService initialized: size={self.sample_size}, "
            f"enabled={self.enable_sampling}, production={self.is_production}"
        )

    def should_sample(self) -> bool:
        """
        Check if sampling should be performed.

        Returns:
            True if sampling should be performed, False otherwise
        """
        # Production mode: Never sample (but doesn't drop samples from data)
        if self.is_production:
            return False

        # Check if sampling is enabled
        if not self.enable_sampling:
            return False

        return True

    def generate_csv_sample(
        self,
        df: pd.DataFrame,
        filename_prefix: str,
        data_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Generate CSV sample from DataFrame.

        Args:
            df: DataFrame to sample
            filename_prefix: Prefix for filename (e.g., 'instruments', 'candles')
            data_type: Optional data type for smart sampling (e.g., 'liquidations', 'book_snapshot_5')
            metadata: Optional metadata dict with additional info for filename

        Returns:
            Path to generated CSV file, or None if skipped/failed
        """
        if not self.should_sample():
            return None

        try:
            # Validation: Check DataFrame is valid
            if df.empty:
                logger.debug("⚠️ CSV sampling skipped: Empty DataFrame")
                return None

            if len(df.columns) == 0:
                logger.debug("⚠️ CSV sampling skipped: No columns in DataFrame")
                return None

            # Ensure sample directory exists
            self.sample_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            filename = self._generate_filename(filename_prefix, data_type, metadata)
            sample_path = self.sample_dir / filename

            # Smart sampling based on data type
            sample_df = self._smart_sample(df, data_type)

            # Save sample (fillna to avoid NaN in CSV)
            sample_df.fillna("").to_csv(sample_path, index=False)

            logger.info(f"📊 CSV sample: {sample_path} ({len(sample_df)} rows)")

            return str(sample_path)

        except Exception as e:
            logger.warning(f"⚠️ CSV sampling failed: {e}")
            return None

    def _smart_sample(self, df: pd.DataFrame, data_type: str | None = None) -> pd.DataFrame:
        """
        Smart sampling based on data type.

        Args:
            df: DataFrame to sample
            data_type: Optional data type for smart sampling

        Returns:
            Sampled DataFrame
        """
        # Determine sample size (min of configured size and actual data size)
        actual_sample_size = min(self.sample_size, len(df))

        if data_type == "liquidations":
            # Real data sampling: No filtering, show actual liquidation data (including zeros)
            sample_df = df.head(actual_sample_size)

            # Count non-zero liquidations for info
            liquidation_cols = [col for col in df.columns if "liquidation" in col.lower()]
            if liquidation_cols:
                # Check if any liquidation column has non-zero values
                non_zero_count = len(df[df[liquidation_cols[0]] > 0]) if liquidation_cols else 0
                logger.debug(
                    f"📊 Real liquidation sample: {len(sample_df)} rows "
                    f"({non_zero_count} with liquidations, {len(sample_df)-non_zero_count} zeros)"
                )

            return sample_df

        elif data_type == "book_snapshot_5" or data_type == "book_snapshot":
            # For book data: prioritize samples with valid spreads
            spread_columns = [
                col for col in df.columns if "spread" in col.lower() and "bps" in col.lower()
            ]

            if spread_columns:
                spread_col = spread_columns[0]  # Use first spread column found
                valid_spreads = df[df[spread_col].notna()]

                if not valid_spreads.empty:
                    sample_df = valid_spreads.head(actual_sample_size)
                    logger.debug(f"📊 Smart book sample: {len(sample_df)} rows with valid spreads")
                    return sample_df

            # Fallback: regular sampling
            return df.head(actual_sample_size)

        else:
            # Regular sampling for other data types
            return df.head(actual_sample_size)

    def _generate_filename(
        self,
        prefix: str,
        data_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate filename for CSV sample.

        Args:
            prefix: Filename prefix (e.g., 'instruments', 'candles')
            data_type: Optional data type
            metadata: Optional metadata dict with:
                - instrument_id: For instrument-specific samples
                - timeframe: For timeframe-specific samples
                - date: For date-specific samples

        Returns:
            Generated filename
        """
        parts = [prefix]

        # Add data type if provided
        if data_type:
            parts.append(data_type)

        # Add instrument ID if provided (sanitized)
        if metadata and "instrument_id" in metadata:
            instrument_id = str(metadata["instrument_id"]).replace(":", "_").replace("-", "_")
            parts.append(instrument_id)

        # Add timeframe if provided
        if metadata and "timeframe" in metadata:
            parts.append(metadata["timeframe"])

        # Add date if provided
        if metadata and "date" in metadata:
            date = metadata["date"]
            if isinstance(date, datetime):
                date_str = date.strftime("%Y%m%d")
            else:
                date_str = str(date)
            parts.append(date_str)

        # Add timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parts.append(timestamp)

        # Join parts and add extension
        filename = "_".join(parts) + ".csv"

        return filename


# Convenience function for easy usage
def create_sampling_service(config: dict[str, Any] | None = None) -> SamplingService:
    """
    Create a SamplingService instance.

    Args:
        config: Optional configuration dict

    Returns:
        SamplingService instance
    """
    return SamplingService(config)
