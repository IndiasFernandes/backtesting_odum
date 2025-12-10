"""
Date Utilities for CLI Operations

Common date parsing and validation utilities used across all services.
Provides standardized date handling across all CLI handlers.

Moved from market-tick-data-handler to eliminate duplication.
Used by: market-tick-data-handler, instruments-service, and other services.

Functions:
- parse_date(): Parse date strings to timezone-aware datetime objects
- validate_date_range(): Validate date range parameters
- get_date_range(): Generate date range from start/end parameters
"""

import logging
import re
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> datetime:
    """
    Parse date string to timezone-aware datetime.

    Converts date strings in YYYY-MM-DD format to UTC timezone-aware
    datetime objects for consistent processing across all services.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Timezone-aware datetime object in UTC

    Raises:
        ValueError: If date format is invalid

    Example:
        >>> date = parse_date("2023-10-26")
        >>> print(date)  # 2023-10-26 00:00:00+00:00
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as e:
        raise ValueError(f"Invalid date format '{date_str}'. Use YYYY-MM-DD format.") from e


def validate_date_range(start_date: str, end_date: str) -> tuple[datetime, datetime]:
    """
    Validate and parse a date range.

    Ensures start_date <= end_date and both are valid dates.
    Common pattern found across multiple handlers in services.

    Args:
        start_date: Start date string in YYYY-MM-DD format
        end_date: End date string in YYYY-MM-DD format

    Returns:
        Tuple of (parsed_start_date, parsed_end_date)

    Raises:
        ValueError: If dates are invalid or start_date > end_date

    Example:
        >>> start, end = validate_date_range("2023-10-25", "2023-10-26")
        >>> print(f"Range: {start} to {end}")
    """
    try:
        # **DEFENSIVE PARSING** - handle both strings and datetime objects
        if isinstance(start_date, str):
            start = parse_date(start_date)
        elif isinstance(start_date, datetime):
            start = start_date
        else:
            raise ValueError(f"Invalid start_date type: {type(start_date)}")

        if isinstance(end_date, str):
            end = parse_date(end_date)
        elif isinstance(end_date, datetime):
            end = end_date
        else:
            raise ValueError(f"Invalid end_date type: {type(end_date)}")

        if start > end:
            raise ValueError(f"Start date {start_date} must be <= end date {end_date}")

        return start, end

    except ValueError as e:
        logger.error(f"Date range validation failed: {e}")
        raise


def get_date_range(start_date: str, end_date: str) -> list[datetime]:
    """
    Generate list of dates between start and end (inclusive)

    Creates a list of datetime objects for each day between start_date
    and end_date (inclusive). Useful for iterating over date ranges
    in batch processing operations.

    Args:
        start_date: Start date string in YYYY-MM-DD format
        end_date: End date string in YYYY-MM-DD format

    Returns:
        List of datetime objects for each day in range

    Example:
        >>> dates = get_date_range("2023-10-25", "2023-10-27")
        >>> len(dates)  # 3 days
        >>> print([d.strftime('%Y-%m-%d') for d in dates])
        # ['2023-10-25', '2023-10-26', '2023-10-27']
    """
    start, end = validate_date_range(start_date, end_date)

    dates = []
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)

    logger.debug(f"Generated {len(dates)} dates from {start_date} to {end_date}")
    return dates


def format_date_for_path(date: datetime) -> str:
    """
    Format date for use in file/directory paths.

    Standard format used throughout the system for GCS paths and
    local directory structures.

    Args:
        date: Datetime object to format

    Returns:
        Date string in day-YYYY-MM-DD format

    Example:
        >>> date = parse_date("2023-10-26")
        >>> format_date_for_path(date)  # "day-2023-10-26"
    """
    return f"day-{date.strftime('%Y-%m-%d')}"


def get_date_from_path(path: str) -> datetime | None:
    """
    Extract date from a standardized path format.

    Reverse operation of format_date_for_path(). Useful for parsing
    dates from GCS blob paths and directory names.

    Args:
        path: Path string containing day-YYYY-MM-DD format

    Returns:
        Parsed datetime object, or None if no valid date found

    Example:
        >>> date = get_date_from_path("gs://bucket/by_date/day-2023-10-26/data.parquet")
        >>> print(date)  # 2023-10-26 00:00:00+00:00
    """

    # Match day-YYYY-MM-DD pattern
    pattern = r"day-(\d{4}-\d{2}-\d{2})"
    match = re.search(pattern, path)

    if match:
        try:
            return parse_date(match.group(1))
        except ValueError:
            logger.warning(f"Found date pattern in path but couldn't parse: {match.group(1)}")

    return None
