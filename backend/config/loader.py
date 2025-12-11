"""Load and validate external JSON configuration files."""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

from backend.utils.paths import resolve_path
from backend.utils.validation import validate_config_structure, validate_iso8601, validate_path_exists


class ConfigLoader:
    """Loads and validates external JSON configuration files."""
    
    def __init__(self, config_path: str):
        """
        Initialize config loader.
        
        Args:
            config_path: Path to JSON config file
        """
        self.config_path = Path(config_path)
        self.config: Optional[Dict[str, Any]] = None
    
    def load(self) -> Dict[str, Any]:
        """
        Load and validate configuration from JSON file.
        
        Returns:
            Validated configuration dictionary
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        
        # Validate structure
        validate_config_structure(self.config)
        
        # Validate time window
        time_window = self.config["time_window"]
        start = validate_iso8601(time_window["start"])
        end = validate_iso8601(time_window["end"])
        
        if start >= end:
            raise ValueError(f"Invalid time window: start ({start}) must be before end ({end})")
        
        # Resolve and validate data paths
        env = self.config["environment"]
        base_path = env.get("UNIFIED_CLOUD_LOCAL_PATH", "/app/data_downloads")
        
        catalog = self.config["data_catalog"]
        trades_path_str = catalog["trades_path"]
        book_path_str = catalog["book_snapshot_5_path"]
        
        # Skip path validation if paths contain wildcards (for auto-discovery)
        # Wildcard paths will be discovered at runtime
        if "*" not in trades_path_str and "*" not in book_path_str:
            trades_path = resolve_path(trades_path_str, base_path)
            book_path = resolve_path(book_path_str, base_path)
            
            # Validate paths exist (if not FUSE-mounted, they should exist)
            if os.getenv("UNIFIED_CLOUD_SERVICES_USE_DIRECT_GCS", "false").lower() != "true":
                validate_path_exists(trades_path)
                validate_path_exists(book_path)
        else:
            # Paths contain wildcards - skip validation (will be discovered at runtime)
            pass
        
        return self.config
    
    def get_instrument_id(self) -> str:
        """Get instrument ID from config."""
        if not self.config:
            raise RuntimeError("Config not loaded. Call load() first.")
        return self.config["instrument"]["id"]
    
    def get_time_window(self) -> tuple:
        """Get time window as (start, end) datetime tuple."""
        if not self.config:
            raise RuntimeError("Config not loaded. Call load() first.")
        time_window = self.config["time_window"]
        start = validate_iso8601(time_window["start"])
        end = validate_iso8601(time_window["end"])
        return start, end
    
    def get_data_paths(self) -> tuple:
        """Get (trades_path, book_snapshot_5_path) as resolved Path objects."""
        if not self.config:
            raise RuntimeError("Config not loaded. Call load() first.")
        env = self.config["environment"]
        base_path = env.get("UNIFIED_CLOUD_LOCAL_PATH", "/app/data_downloads")
        catalog = self.config["data_catalog"]
        trades_path = resolve_path(catalog["trades_path"], base_path)
        book_path = resolve_path(catalog["book_snapshot_5_path"], base_path)
        return trades_path, book_path

