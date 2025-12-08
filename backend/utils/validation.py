"""Validation utilities for configs and timestamps."""
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


def validate_iso8601(timestamp: str) -> datetime:
    """
    Validate and parse ISO8601 timestamp.
    
    Args:
        timestamp: ISO8601 formatted string
    
    Returns:
        Parsed datetime object
    
    Raises:
        ValueError: If timestamp is invalid
    """
    try:
        return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid ISO8601 timestamp: {timestamp}") from e


def validate_path_exists(path: Path) -> None:
    """
    Validate that a path exists.
    
    Args:
        path: Path to validate
    
    Raises:
        FileNotFoundError: If path doesn't exist
    """
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")


def validate_config_structure(config: Dict[str, Any]) -> None:
    """
    Validate that config has all required top-level keys.
    
    Args:
        config: Configuration dictionary
    
    Raises:
        ValueError: If required keys are missing
    """
    required_keys = [
        "instrument",
        "venue",
        "data_catalog",
        "time_window",
        "strategy",
        "risk",
        "environment",
        "fx_stub"
    ]
    
    missing = [key for key in required_keys if key not in config]
    if missing:
        raise ValueError(f"Missing required config keys: {missing}")

