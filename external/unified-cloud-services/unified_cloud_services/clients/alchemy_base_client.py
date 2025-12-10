"""
Alchemy Base Client - Centralized Network Management

Provides core client functionality for Alchemy Web3 RPC interactions.
Domain services compose with this for their specific on-chain queries.

Features:
- API key caching (avoids repeated Secret Manager calls)
- Multi-chain RPC URL building
- Web3 provider management
- Rate limiting and retry handling

Architecture:
- unified-cloud-services: AlchemyBaseClient (network layer)
- instruments-service: Uses for on-chain data (Aave, Curve, Morpho)
- market-tick-data-handler: Uses for historical on-chain data

Supported Chains:
- Ethereum Mainnet
- Arbitrum
- Base
- Optimism
- Polygon
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

from unified_cloud_services import get_secret_with_fallback, get_config

logger = logging.getLogger(__name__)

# Check if web3 is available
try:
    from web3 import Web3
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    Web3 = None
    logger.warning("web3 package not available. Install with: pip install web3")

# Module-level API key cache (shared across all instances)
_ALCHEMY_API_KEY_CACHE: Optional[str] = None
_ALCHEMY_API_KEY_TIMESTAMP: Optional[datetime] = None
_ALCHEMY_API_KEY_TTL = timedelta(hours=24)

# Module-level Web3 client cache (per chain)
_WEB3_CLIENT_CACHE: Dict[str, Any] = {}


def clear_alchemy_api_key_cache():
    """Clear the module-level API key cache."""
    global _ALCHEMY_API_KEY_CACHE, _ALCHEMY_API_KEY_TIMESTAMP
    _ALCHEMY_API_KEY_CACHE = None
    _ALCHEMY_API_KEY_TIMESTAMP = None
    logger.info("🧹 Cleared Alchemy API key cache")


def clear_alchemy_web3_cache():
    """Clear the module-level Web3 client cache."""
    global _WEB3_CLIENT_CACHE
    _WEB3_CLIENT_CACHE.clear()
    logger.info("🧹 Cleared Alchemy Web3 client cache")


# Chain to Alchemy network mapping
CHAIN_TO_ALCHEMY_NETWORK = {
    "ETHEREUM": "eth-mainnet",
    "ETH": "eth-mainnet",
    "MAINNET": "eth-mainnet",
    "ARBITRUM": "arb-mainnet",
    "ARB": "arb-mainnet",
    "BASE": "base-mainnet",
    "OPTIMISM": "opt-mainnet",
    "OP": "opt-mainnet",
    "POLYGON": "polygon-mainnet",
    "MATIC": "polygon-mainnet",
    # Testnets
    "SEPOLIA": "eth-sepolia",
    "GOERLI": "eth-goerli",
    "ARBITRUM_SEPOLIA": "arb-sepolia",
    "BASE_SEPOLIA": "base-sepolia",
}


@dataclass
class AlchemyClientConfig:
    """Configuration for Alchemy client."""
    
    # API base URL
    base_url_template: str = "https://{network}.g.alchemy.com/v2/{api_key}"
    
    # Default chain
    default_chain: str = "ETHEREUM"
    
    # Web3 settings
    request_timeout: int = 30
    
    # Caching
    api_key_cache_ttl: timedelta = field(default_factory=lambda: timedelta(hours=24))
    cache_web3_clients: bool = True
    
    # Secret Manager
    secret_name: str = "alchemy-api-key"
    fallback_env_var: str = "ALCHEMY_API_KEY"
    
    @classmethod
    def from_env(cls) -> "AlchemyClientConfig":
        """Create config from environment variables."""
        return cls(
            default_chain=get_config("ALCHEMY_DEFAULT_CHAIN", "ETHEREUM"),
            request_timeout=int(get_config("ALCHEMY_TIMEOUT", "30")),
            cache_web3_clients=get_config("ALCHEMY_CACHE_WEB3", "true").lower() == "true",
            secret_name=get_config("ALCHEMY_SECRET_NAME", "alchemy-api-key"),
            fallback_env_var="ALCHEMY_API_KEY",
        )


class AlchemyBaseClient:
    """
    Base client for Alchemy RPC API with centralized network management.
    
    Provides:
    - API key management (Secret Manager + caching)
    - RPC URL building for multiple chains
    - Web3 provider management with caching
    
    Domain services compose with this for their specific on-chain queries.
    """
    
    def __init__(
        self,
        config: Optional[AlchemyClientConfig] = None,
        api_key: Optional[str] = None,
        chain: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        """
        Initialize Alchemy base client.
        
        Args:
            config: Client configuration (defaults to env-based config)
            api_key: Optional API key (uses cached/Secret Manager if not provided)
            chain: Chain identifier (e.g., 'ETHEREUM', 'ARBITRUM')
            project_id: GCP project ID for Secret Manager
        """
        self.config = config or AlchemyClientConfig.from_env()
        self.project_id = project_id or get_config("GCP_PROJECT_ID", "")
        self.chain = (chain or self.config.default_chain).upper()
        
        # API key (lazy loaded)
        self._api_key = api_key
        
        logger.debug(f"✅ AlchemyBaseClient created for chain: {self.chain}")
    
    @property
    def api_key(self) -> str:
        """Get API key with caching."""
        global _ALCHEMY_API_KEY_CACHE, _ALCHEMY_API_KEY_TIMESTAMP
        
        # Return provided key if available
        if self._api_key:
            return self._api_key
        
        # Check cache validity
        if _ALCHEMY_API_KEY_CACHE and _ALCHEMY_API_KEY_TIMESTAMP:
            age = datetime.now(timezone.utc) - _ALCHEMY_API_KEY_TIMESTAMP
            if age < self.config.api_key_cache_ttl:
                logger.debug("✅ Using cached Alchemy API key")
                return _ALCHEMY_API_KEY_CACHE
        
        # Fetch from Secret Manager
        try:
            api_key = get_secret_with_fallback(
                project_id=self.project_id,
                secret_name=self.config.secret_name,
                fallback_env_var=self.config.fallback_env_var,
            )
            
            if api_key:
                api_key = api_key.strip()
                _ALCHEMY_API_KEY_CACHE = api_key
                _ALCHEMY_API_KEY_TIMESTAMP = datetime.now(timezone.utc)
                logger.info(f"✅ Retrieved and cached Alchemy API key (TTL: {self.config.api_key_cache_ttl})")
                return api_key
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to retrieve Alchemy API key: {e}")
        
        raise ValueError(
            "Alchemy API key required. Set ALCHEMY_SECRET_NAME (Secret Manager), "
            "ALCHEMY_API_KEY env var (fallback), or pass api_key parameter."
        )
    
    # =========================================================================
    # RPC URL HELPERS
    # =========================================================================
    
    def get_rpc_url(self, chain: Optional[str] = None) -> str:
        """
        Get Alchemy RPC URL for a chain.
        
        Args:
            chain: Chain identifier (uses default if not provided)
            
        Returns:
            Alchemy RPC URL
        """
        target_chain = (chain or self.chain).upper()
        network = CHAIN_TO_ALCHEMY_NETWORK.get(target_chain)
        
        if not network:
            raise ValueError(
                f"Unsupported chain: {target_chain}. "
                f"Supported: {list(CHAIN_TO_ALCHEMY_NETWORK.keys())}"
            )
        
        return self.config.base_url_template.format(
            network=network,
            api_key=self.api_key,
        )
    
    def get_network_name(self, chain: Optional[str] = None) -> str:
        """
        Get Alchemy network name for a chain.
        
        Args:
            chain: Chain identifier (uses default if not provided)
            
        Returns:
            Alchemy network name (e.g., 'eth-mainnet')
        """
        target_chain = (chain or self.chain).upper()
        network = CHAIN_TO_ALCHEMY_NETWORK.get(target_chain)
        
        if not network:
            raise ValueError(f"Unsupported chain: {target_chain}")
        
        return network
    
    # =========================================================================
    # WEB3 PROVIDER
    # =========================================================================
    
    def get_web3(self, chain: Optional[str] = None) -> Any:
        """
        Get Web3 provider for a chain.
        
        Args:
            chain: Chain identifier (uses default if not provided)
            
        Returns:
            Web3 instance
        """
        if not WEB3_AVAILABLE:
            raise ImportError(
                "web3 package not available. Install with: pip install web3"
            )
        
        target_chain = (chain or self.chain).upper()
        cache_key = f"{target_chain}_{self.api_key[:8] if self.api_key else 'default'}"
        
        # Check cache
        if self.config.cache_web3_clients and cache_key in _WEB3_CLIENT_CACHE:
            logger.debug(f"✅ Using cached Web3 client for {target_chain}")
            return _WEB3_CLIENT_CACHE[cache_key]
        
        # Create new Web3 instance
        rpc_url = self.get_rpc_url(target_chain)
        web3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': self.config.request_timeout}))
        
        # Cache if enabled
        if self.config.cache_web3_clients:
            _WEB3_CLIENT_CACHE[cache_key] = web3
            logger.info(f"✅ Created and cached Web3 client for {target_chain}")
        else:
            logger.info(f"✅ Created Web3 client for {target_chain} (no caching)")
        
        return web3
    
    def is_connected(self, chain: Optional[str] = None) -> bool:
        """
        Check if Web3 provider is connected.
        
        Args:
            chain: Chain identifier (uses default if not provided)
            
        Returns:
            True if connected
        """
        try:
            web3 = self.get_web3(chain)
            return web3.is_connected()
        except Exception as e:
            logger.warning(f"⚠️ Web3 connection check failed: {e}")
            return False
    
    def get_block_number(self, chain: Optional[str] = None) -> int:
        """
        Get current block number.
        
        Args:
            chain: Chain identifier (uses default if not provided)
            
        Returns:
            Current block number
        """
        web3 = self.get_web3(chain)
        return web3.eth.block_number
    
    def get_block_by_timestamp(self, timestamp: int, chain: Optional[str] = None) -> Optional[int]:
        """
        Get block number closest to a timestamp.
        
        This is an approximation using binary search.
        
        Args:
            timestamp: Unix timestamp
            chain: Chain identifier (uses default if not provided)
            
        Returns:
            Block number or None if not found
        """
        web3 = self.get_web3(chain)
        
        try:
            latest_block = web3.eth.block_number
            
            # Binary search for block
            low, high = 1, latest_block
            
            while low <= high:
                mid = (low + high) // 2
                block = web3.eth.get_block(mid)
                
                if block['timestamp'] == timestamp:
                    return mid
                elif block['timestamp'] < timestamp:
                    low = mid + 1
                else:
                    high = mid - 1
            
            # Return closest block
            return low if low <= latest_block else high
            
        except Exception as e:
            logger.error(f"❌ Failed to get block by timestamp: {e}")
            return None
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    def cleanup(self):
        """Cleanup resources (does not clear global cache)."""
        logger.debug("🧹 AlchemyBaseClient cleanup completed")
    
    def cleanup_with_cache_clear(self):
        """Cleanup resources and clear global caches."""
        self.cleanup()
        clear_alchemy_api_key_cache()
        clear_alchemy_web3_cache()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


# Factory function
def create_alchemy_base_client(
    config: Optional[AlchemyClientConfig] = None,
    api_key: Optional[str] = None,
    chain: Optional[str] = None,
    project_id: Optional[str] = None,
) -> AlchemyBaseClient:
    """
    Create an AlchemyBaseClient instance.
    
    Args:
        config: Optional client configuration
        api_key: Optional API key
        chain: Optional chain identifier
        project_id: Optional GCP project ID
        
    Returns:
        Configured AlchemyBaseClient
    """
    return AlchemyBaseClient(
        config=config,
        api_key=api_key,
        chain=chain,
        project_id=project_id,
    )

