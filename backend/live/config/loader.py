"""
Configuration loader for live execution system.

Purpose: Load and validate JSON configuration files for live trading.
Service: Live service only (port 8001)

Similar to backtest ConfigLoader but adapted for live trading configuration.
"""
import json
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional


class LiveConfigLoader:
    """Loads and validates live trading JSON configuration files."""
    
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
        
        Supports environment variable substitution: ${VAR_NAME} or ${VAR_NAME:-default}
        
        Returns:
            Validated configuration dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            content = f.read()
        
        # Substitute environment variables
        content = self._substitute_env_vars(content)
        
        # Parse JSON
        self.config = json.loads(content)
        
        # Validate structure
        self._validate_structure()
        
        return self.config
    
    def _substitute_env_vars(self, content: str) -> str:
        """
        Substitute environment variables in config content.
        
        Supports:
        - ${VAR_NAME} - required, raises error if not set
        - ${VAR_NAME:-default} - optional with default value
        """
        def replace_var(match):
            var_expr = match.group(1)
            
            # Check for default value syntax: VAR_NAME:-default
            if ':-' in var_expr:
                var_name, default_value = var_expr.split(':-', 1)
                return os.getenv(var_name, default_value)
            else:
                value = os.getenv(var_expr)
                if value is None:
                    raise ValueError(f"Environment variable {var_expr} is not set and no default provided")
                return value
        
        # Match ${VAR_NAME} or ${VAR_NAME:-default}
        pattern = r'\$\{([^}]+)\}'
        return re.sub(pattern, replace_var, content)
    
    def _validate_structure(self):
        """Validate configuration structure."""
        if not isinstance(self.config, dict):
            raise ValueError("Config must be a JSON object")
        
        # Required top-level sections
        required_sections = ['trading_node']
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required section: {section}")
        
        # Validate trading_node section
        trading_node = self.config['trading_node']
        if not isinstance(trading_node, dict):
            raise ValueError("trading_node must be an object")
        
        # Validate data_clients (if present)
        if 'data_clients' in trading_node:
            if not isinstance(trading_node['data_clients'], list):
                raise ValueError("data_clients must be an array")
            for client in trading_node['data_clients']:
                if not isinstance(client, dict):
                    raise ValueError("Each data_client must be an object")
                if 'name' not in client:
                    raise ValueError("data_client must have 'name' field")
        
        # Validate exec_clients (if present)
        if 'exec_clients' in trading_node:
            if not isinstance(trading_node['exec_clients'], list):
                raise ValueError("exec_clients must be an array")
        
        # Validate risk_engine (if present)
        if 'risk_engine' in self.config:
            risk_engine = self.config['risk_engine']
            if not isinstance(risk_engine, dict):
                raise ValueError("risk_engine must be an object")
            if 'enabled' in risk_engine and not isinstance(risk_engine['enabled'], bool):
                raise ValueError("risk_engine.enabled must be a boolean")
    
    def get_trading_node_config(self) -> Dict[str, Any]:
        """Get trading_node configuration section."""
        if not self.config:
            raise RuntimeError("Config not loaded. Call load() first.")
        return self.config.get('trading_node', {})
    
    def get_risk_engine_config(self) -> Dict[str, Any]:
        """Get risk_engine configuration section."""
        if not self.config:
            raise RuntimeError("Config not loaded. Call load() first.")
        return self.config.get('risk_engine', {})
    
    def get_router_config(self) -> Dict[str, Any]:
        """Get router configuration section."""
        if not self.config:
            raise RuntimeError("Config not loaded. Call load() first.")
        return self.config.get('router', {})
    
    def get_external_adapters_config(self) -> Dict[str, Any]:
        """Get external_adapters configuration section."""
        if not self.config:
            raise RuntimeError("Config not loaded. Call load() first.")
        return self.config.get('external_adapters', {})

