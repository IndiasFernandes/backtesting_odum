"""
Market Category Classification Utility

Provides functions to classify instruments by market category (CEFI, TRADFI, DEFI)
and determine the appropriate GCS bucket for each category.

Classification Rules:
- TRADFI: databento_symbol is filled (not empty) - databento sources venues for batch
- DEFI: chain is NOT "off-chain" - various defi venues
- CEFI: databento_symbol is NOT filled AND chain is "off-chain" - tardis
"""

import logging
import pandas as pd
from typing import Any
from unified_cloud_services.core.config import unified_config, get_config

logger = logging.getLogger(__name__)


def determine_market_category(instrument_row: dict[str, Any]) -> str:
    """
    Determine market category for an instrument based on classification rules.

    Args:
        instrument_row: Instrument record/dictionary with 'databento_symbol' and 'chain' fields

    Returns:
        Market category: "CEFI", "TRADFI", or "DEFI"

    Classification Rules:
        - TRADFI: databento_symbol is filled (not empty)
        - DEFI: chain is NOT "off-chain"
        - CEFI: databento_symbol is NOT filled AND chain is "off-chain"
    """
    databento_symbol = instrument_row.get("databento_symbol", "")
    chain = instrument_row.get("chain", "off-chain")

    # Check if databento_symbol is filled (TRADFI)
    if databento_symbol and str(databento_symbol).strip():
        return "TRADFI"

    # Check if chain is NOT "off-chain" (DEFI)
    if chain and str(chain).strip().lower() != "off-chain":
        return "DEFI"

    # Default to CEFI (databento_symbol not filled AND chain is off-chain)
    return "CEFI"


def get_bucket_for_category(category: str, test_mode: bool = False) -> str:
    """
    Get the GCS bucket name for a specific market category.

    Args:
        category: Market category ("CEFI", "TRADFI", or "DEFI")
        test_mode: Whether to use test bucket (default: False)

    Returns:
        Bucket name from environment variables

    Raises:
        ValueError: If category is invalid or bucket not configured
    """
    category_upper = category.upper()

    if category_upper not in ["CEFI", "TRADFI", "DEFI"]:
        raise ValueError(f"Invalid category: {category}. Must be one of: CEFI, TRADFI, DEFI")

    # Determine environment variable name
    if test_mode:
        env_var = f"INSTRUMENTS_GCS_BUCKET_{category_upper}_TEST"
    else:
        env_var = f"INSTRUMENTS_GCS_BUCKET_{category_upper}"

    # Get bucket from environment using get_config (handles both env vars and config)
    bucket = get_config(env_var, "")

    if not bucket:
        # Fallback to default bucket if category-specific bucket not configured
        logger.warning(
            f"⚠️ Category-specific bucket not configured for {category_upper}. "
            f"Using default bucket."
        )
        if test_mode:
            bucket = get_config("INSTRUMENTS_GCS_BUCKET_TEST", "instruments-store-test")
        else:
            bucket = get_config("INSTRUMENTS_GCS_BUCKET", "instruments-store")

    logger.debug(f"📦 Using bucket for {category_upper}: {bucket}")
    return bucket


def get_instruments_bucket_for_category(category: str, test_mode: bool = False) -> str:
    """
    Alias for get_bucket_for_category for consistency with market-tick-data-handler naming.

    Args:
        category: Market category ("CEFI", "TRADFI", or "DEFI")
        test_mode: Whether to use test bucket (default: False)

    Returns:
        Bucket name from environment variables
    """
    return get_bucket_for_category(category, test_mode=test_mode)


def get_market_data_bucket_for_category(category: str, test_mode: bool = False) -> str:
    """
    Get the GCS bucket name for market data for a specific market category.

    Args:
        category: Market category ("CEFI", "TRADFI", or "DEFI")
        test_mode: Whether to use test bucket (default: False)

    Returns:
        Bucket name from environment variables

    Raises:
        ValueError: If category is invalid or bucket not configured
    """
    category_upper = category.upper()

    if category_upper not in ["CEFI", "TRADFI", "DEFI"]:
        raise ValueError(f"Invalid category: {category}. Must be one of: CEFI, TRADFI, DEFI")

    # Determine environment variable name
    if test_mode:
        env_var = f"MARKET_DATA_GCS_BUCKET_{category_upper}_TEST"
    else:
        env_var = f"MARKET_DATA_GCS_BUCKET_{category_upper}"

    # Get bucket from environment using get_config
    bucket = get_config(env_var, "")

    if not bucket:
        # Fallback to default bucket if category-specific bucket not configured
        logger.warning(
            f"⚠️ Category-specific market data bucket not configured for {category_upper}. "
            f"Using default bucket."
        )
        if test_mode:
            bucket = get_config("MARKET_DATA_GCS_BUCKET_TEST", "market-data-tick-test")
        else:
            bucket = get_config("MARKET_DATA_GCS_BUCKET", "market-data-tick")

    logger.debug(f"📦 Using market data bucket for {category_upper}: {bucket}")
    return bucket


def filter_instruments_by_category(
    instruments_df: pd.DataFrame, category: str | None = None
) -> pd.DataFrame:
    """
    Filter instruments DataFrame by market category.

    Args:
        instruments_df: DataFrame with instrument definitions
        category: Optional market category to filter by ("CEFI", "TRADFI", "DEFI")
                  If None, returns all instruments with added 'market_category' column

    Returns:
        Filtered DataFrame (or DataFrame with market_category column if category is None)
    """
    if instruments_df.empty:
        return instruments_df

    # Add market_category column if not present
    if "market_category" not in instruments_df.columns:
        logger.debug("📊 Classifying instruments by market category...")
        instruments_df = instruments_df.copy()
        instruments_df["market_category"] = instruments_df.apply(
            lambda row: determine_market_category(row.to_dict()), axis=1
        )

    # Filter by category if specified
    if category:
        category_upper = category.upper()
        if category_upper not in ["CEFI", "TRADFI", "DEFI"]:
            raise ValueError(
                f"Invalid category: {category}. Must be one of: CEFI, TRADFI, DEFI"
            )

        filtered_df = instruments_df[
            instruments_df["market_category"] == category_upper
        ].copy()
        logger.debug(
            f"📊 Filtered to {len(filtered_df)} {category_upper} instruments "
            f"(from {len(instruments_df)} total)"
        )
        return filtered_df

    return instruments_df


def get_all_category_buckets(test_mode: bool = False) -> dict[str, str]:
    """
    Get all category bucket names.

    Args:
        test_mode: Whether to use test buckets (default: False)

    Returns:
        Dictionary mapping category to bucket name
    """
    return {
        "CEFI": get_bucket_for_category("CEFI", test_mode=test_mode),
        "TRADFI": get_bucket_for_category("TRADFI", test_mode=test_mode),
        "DEFI": get_bucket_for_category("DEFI", test_mode=test_mode),
    }
