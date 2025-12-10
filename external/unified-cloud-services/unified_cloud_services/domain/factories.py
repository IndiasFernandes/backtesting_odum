"""
Factory Functions for Domain-Specific Cloud Services

Factory functions to create domain-specific UnifiedCloudService instances
with appropriate configuration for each domain.

REFACTORED: Uses centralized config instead of raw os.getenv
"""

import logging
from unified_cloud_services.core.unified_cloud_service import UnifiedCloudService
from unified_cloud_services.core.cloud_config import CloudConfig
from unified_cloud_services.core.config import get_config

logger = logging.getLogger(__name__)


def create_market_data_cloud_service() -> UnifiedCloudService:
    """Factory for market data operations (current repo)"""
    config = CloudConfig(
        default_project_id=get_config("MARKET_DATA_PROJECT", "central-element-323112"),
        connection_pool_size=3,
        max_concurrent_uploads=5,
    )
    return UnifiedCloudService(config)


def create_features_cloud_service() -> UnifiedCloudService:
    """Factory for ML features operations"""
    config = CloudConfig(
        default_project_id=get_config("FEATURES_PROJECT", "central-element-323112"),
        connection_pool_size=2,
        max_concurrent_uploads=3,
    )
    return UnifiedCloudService(config)


def create_strategy_cloud_service() -> UnifiedCloudService:
    """Factory for strategy and execution operations"""
    config = CloudConfig(
        default_project_id=get_config("STRATEGY_PROJECT", "central-element-323112"),
        connection_pool_size=2,
        max_concurrent_uploads=3,
    )
    return UnifiedCloudService(config)


def create_backtesting_cloud_service() -> UnifiedCloudService:
    """Factory for backtesting and simulation operations"""
    config = CloudConfig(
        default_project_id=get_config("BACKTESTING_PROJECT", "central-element-323112"),
        connection_pool_size=4,  # Higher for large backtesting datasets
        max_concurrent_uploads=8,
    )
    return UnifiedCloudService(config)


def create_instruments_cloud_service() -> UnifiedCloudService:
    """Factory for instruments domain operations"""
    config = CloudConfig(
        default_project_id=get_config("INSTRUMENTS_PROJECT", "central-element-323112"),
        connection_pool_size=2,
        max_concurrent_uploads=3,
    )
    return UnifiedCloudService(config)
