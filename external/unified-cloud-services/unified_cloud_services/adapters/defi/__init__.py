"""
DeFi Adapters Package

Provides base classes and shared utilities for DeFi protocol adapters.
"""

from unified_cloud_services.adapters.defi.base_adapter import BaseDefiAdapter
from unified_cloud_services.adapters.defi.the_graph_client import TheGraphClient

__all__ = [
    "BaseDefiAdapter",
    "TheGraphClient",
]

