"""
Centralized API Clients for Unified Cloud Services

This module provides base clients for external API integrations.
Domain services compose with these for their specific endpoints.

Available Clients:
- TardisBaseClient: Base client for Tardis API (crypto exchanges)
- DatabentoBaseClient: Base client for Databento API (TradFi market data)
- TheGraphBaseClient: Base client for The Graph API (DeFi subgraphs)
- AlchemyBaseClient: Base client for Alchemy RPC (on-chain data)

Architecture:
- unified-cloud-services: Network layer (session management, retries, caching)
- instruments-service: Uses for instrument definition fetching
- market-tick-data-handler: Uses for historical data downloads
"""

from unified_cloud_services.clients.tardis_base_client import (
    TardisBaseClient,
    TardisClientConfig,
    create_tardis_base_client,
    clear_tardis_api_key_cache,
)
from unified_cloud_services.clients.databento_base_client import (
    DatabentoBaseClient,
    DatabentoClientConfig,
    create_databento_base_client,
    clear_databento_api_key_cache,
    clear_databento_client_cache,
    DATABENTO_AVAILABLE,
)
from unified_cloud_services.clients.thegraph_base_client import (
    TheGraphBaseClient,
    TheGraphClientConfig,
    create_thegraph_base_client,
    clear_thegraph_api_key_cache,
    get_thegraph_singleton,
    get_cached_query_result,
    set_cached_query_result,
    clear_query_result_cache,
)
from unified_cloud_services.clients.alchemy_base_client import (
    AlchemyBaseClient,
    AlchemyClientConfig,
    create_alchemy_base_client,
    clear_alchemy_api_key_cache,
    clear_alchemy_web3_cache,
    WEB3_AVAILABLE,
    CHAIN_TO_ALCHEMY_NETWORK,
)

__all__ = [
    # Tardis (crypto exchanges)
    "TardisBaseClient",
    "TardisClientConfig",
    "create_tardis_base_client",
    "clear_tardis_api_key_cache",
    # Databento (TradFi)
    "DatabentoBaseClient",
    "DatabentoClientConfig",
    "create_databento_base_client",
    "clear_databento_api_key_cache",
    "clear_databento_client_cache",
    "DATABENTO_AVAILABLE",
    # The Graph (DeFi subgraphs)
    "TheGraphBaseClient",
    "TheGraphClientConfig",
    "create_thegraph_base_client",
    "clear_thegraph_api_key_cache",
    "get_thegraph_singleton",
    "get_cached_query_result",
    "set_cached_query_result",
    "clear_query_result_cache",
    # Alchemy (on-chain RPC)
    "AlchemyBaseClient",
    "AlchemyClientConfig",
    "create_alchemy_base_client",
    "clear_alchemy_api_key_cache",
    "clear_alchemy_web3_cache",
    "WEB3_AVAILABLE",
    "CHAIN_TO_ALCHEMY_NETWORK",
]
