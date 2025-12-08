"""Path resolution utilities for FUSE-mounted data."""
import os
from pathlib import Path
from typing import Optional, List
import glob


def resolve_path(path: str, base_path: Optional[str] = None) -> Path:
    """
    Resolve a path relative to UNIFIED_CLOUD_LOCAL_PATH or provided base.
    
    Args:
        path: Relative or absolute path
        base_path: Optional base path (defaults to UNIFIED_CLOUD_LOCAL_PATH env var)
    
    Returns:
        Resolved Path object
    """
    if base_path is None:
        base_path = os.getenv("UNIFIED_CLOUD_LOCAL_PATH", "/app/data_downloads")
    
    if os.path.isabs(path):
        return Path(path)
    
    return Path(base_path) / path


def ensure_dir(path: Path) -> None:
    """Ensure directory exists, create if needed."""
    path.mkdir(parents=True, exist_ok=True)


def discover_data_files(base_path: Path, pattern: str, instrument_id: str) -> List[Path]:
    """
    Discover data files matching a pattern, handling wildcards for date folders.
    
    Args:
        base_path: Base path to search from
        pattern: File pattern (may contain wildcards like day-*)
        instrument_id: Instrument ID to match in filename
    
    Returns:
        List of discovered file paths
    """
    discovered = []
    
    # Handle wildcard patterns (e.g., "raw_tick_data/by_date/day-*/data_type-trades/BINANCE-FUTURES:PERPETUAL:BTC-USDT.parquet")
    if "*" in pattern:
        # Replace wildcard with glob pattern
        search_pattern = str(base_path / pattern)
        matches = glob.glob(search_pattern, recursive=True)
        discovered = [Path(m) for m in matches if Path(m).exists()]
    else:
        # No wildcard, resolve directly
        resolved = (base_path / pattern).resolve()
        if resolved.exists():
            discovered = [resolved]
    
    # Filter by instrument ID if present in filename
    if instrument_id:
        # Extract symbol from instrument ID (e.g., "BTC-USDT" from "BTC-USDT.BINANCE-FUTURES")
        symbol = instrument_id.split(".")[0] if "." in instrument_id else instrument_id
        # Also try full instrument ID format
        instrument_variants = [
            instrument_id,
            instrument_id.replace(".", ":"),  # BTC-USDT.BINANCE-FUTURES -> BTC-USDT:BINANCE-FUTURES
            symbol,
        ]
        
        filtered = []
        for path in discovered:
            path_str = str(path)
            if any(variant in path_str for variant in instrument_variants):
                filtered.append(path)
        discovered = filtered
    
    return discovered

