"""Domain-specific services and validation"""

from unified_cloud_services.domain.standardized_service import StandardizedDomainCloudService
from unified_cloud_services.domain.validation import DomainValidationService, DomainValidationConfig
from unified_cloud_services.domain.factories import (
    create_market_data_cloud_service,
    create_features_cloud_service,
    create_strategy_cloud_service,
    create_backtesting_cloud_service,
)
from unified_cloud_services.domain.clients import (
    InstrumentsDomainClient,
    MarketCandleDataDomainClient,
    MarketTickDataDomainClient,
    ExecutionDomainClient,
    MarketDataDomainClient,  # Deprecated, kept for backward compatibility
    create_instruments_client,
    create_market_candle_data_client,
    create_market_tick_data_client,
    create_execution_client,
    create_market_data_client,  # Deprecated, kept for backward compatibility
    create_features_client,
)

__all__ = [
    "StandardizedDomainCloudService",
    "DomainValidationService",
    "DomainValidationConfig",
    "create_market_data_cloud_service",
    "create_features_cloud_service",
    "create_strategy_cloud_service",
    "create_backtesting_cloud_service",
    # Domain clients (for analytics platforms and cross-service quality gates)
    "InstrumentsDomainClient",
    "MarketCandleDataDomainClient",
    "MarketTickDataDomainClient",
    "ExecutionDomainClient",
    "MarketDataDomainClient",  # Deprecated
    "create_instruments_client",
    "create_market_candle_data_client",
    "create_market_tick_data_client",
    "create_execution_client",
    "create_market_data_client",  # Deprecated
    "create_features_client",
]
