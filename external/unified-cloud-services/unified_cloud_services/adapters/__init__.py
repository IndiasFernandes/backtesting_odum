"""
Adapters Package for Unified Cloud Services

Provides shared adapters for DeFi protocols, data providers, and other external services.
"""

from unified_cloud_services.adapters.defi import (
    BaseDefiAdapter,
    TheGraphClient,
)

__all__ = [
    "BaseDefiAdapter",
    "TheGraphClient",
]

