"""
The Graph Base Client - Centralized Network Management

Provides core client functionality for The Graph API interactions.
Domain services compose with this for their specific subgraph queries.

Features:
- API key caching (avoids repeated Secret Manager calls)
- Session management with retries
- Subgraph URL management
- GraphQL query execution

Architecture:
- unified-cloud-services: TheGraphBaseClient (network layer)
- instruments-service: Uses for DEX pool discovery (Uniswap, Curve, Balancer)
- market-tick-data-handler: Uses for historical pool data

Reference:
- The Graph Network: https://gateway.thegraph.com/api/<API_KEY>/subgraphs/id/<SUBGRAPH_ID>
- Subgraph Studio: https://api.studio.thegraph.com/query/<ID>/<SUBGRAPH_NAME>/<VERSION>
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from unified_cloud_services import get_secret_with_fallback, get_config

logger = logging.getLogger(__name__)

# Module-level API key cache (shared across all instances)
_THEGRAPH_API_KEY_CACHE: Optional[str] = None
_THEGRAPH_API_KEY_TIMESTAMP: Optional[datetime] = None
_THEGRAPH_API_KEY_TTL = timedelta(hours=24)

# Module-level client singleton (shared across protocols within a run)
_THEGRAPH_CLIENT_SINGLETON: Optional["TheGraphBaseClient"] = None

# Module-level query result cache (avoids re-fetching same data across days)
# Format: {cache_key: (result, timestamp)}
_QUERY_RESULT_CACHE: Dict[str, tuple] = {}
_QUERY_CACHE_TTL = timedelta(hours=4)  # 4 hour TTL for query results


def get_thegraph_singleton(
    subgraph_url: Optional[str] = None,
    project_id: Optional[str] = None,
) -> "TheGraphBaseClient":
    """
    Get or create a singleton TheGraphBaseClient instance.
    
    PERFORMANCE: Reuses the same client across multiple protocols
    to avoid repeated Secret Manager calls and session setup.
    
    Args:
        subgraph_url: Subgraph URL (can be changed per-query)
        project_id: GCP project ID
        
    Returns:
        Shared TheGraphBaseClient instance
    """
    global _THEGRAPH_CLIENT_SINGLETON
    if _THEGRAPH_CLIENT_SINGLETON is None:
        _THEGRAPH_CLIENT_SINGLETON = TheGraphBaseClient(
            subgraph_url=subgraph_url,
            project_id=project_id,
        )
        logger.info("✅ Created TheGraph singleton client")
    return _THEGRAPH_CLIENT_SINGLETON


def get_cached_query_result(cache_key: str) -> Optional[Any]:
    """
    Get cached query result if still valid.
    
    Args:
        cache_key: Unique key for the query (e.g., "uniswap_v3_pools")
        
    Returns:
        Cached result or None if not cached/expired
    """
    if cache_key in _QUERY_RESULT_CACHE:
        result, timestamp = _QUERY_RESULT_CACHE[cache_key]
        if datetime.now(timezone.utc) - timestamp < _QUERY_CACHE_TTL:
            logger.debug(f"📋 Using cached query result for {cache_key}")
            return result
    return None


def set_cached_query_result(cache_key: str, result: Any):
    """
    Cache a query result.
    
    Args:
        cache_key: Unique key for the query
        result: Query result to cache
    """
    _QUERY_RESULT_CACHE[cache_key] = (result, datetime.now(timezone.utc))
    logger.debug(f"💾 Cached query result for {cache_key}")


def clear_query_result_cache():
    """Clear the query result cache."""
    global _QUERY_RESULT_CACHE
    _QUERY_RESULT_CACHE.clear()
    logger.info("🧹 Cleared The Graph query result cache")


def clear_thegraph_api_key_cache():
    """Clear the module-level API key cache."""
    global _THEGRAPH_API_KEY_CACHE, _THEGRAPH_API_KEY_TIMESTAMP
    _THEGRAPH_API_KEY_CACHE = None
    _THEGRAPH_API_KEY_TIMESTAMP = None
    logger.info("🧹 Cleared The Graph API key cache")


@dataclass
class TheGraphClientConfig:
    """Configuration for The Graph client."""
    
    # API endpoints
    gateway_base_url: str = "https://gateway.thegraph.com/api"
    studio_base_url: str = "https://api.studio.thegraph.com/query"
    
    # Default subgraph URLs (can be overridden)
    default_uniswap_v3_url: str = "https://api.studio.thegraph.com/query/48211/uniswap-v3-mainnet/version/latest"
    
    # Retry configuration
    max_retries: int = 3
    backoff_factor: float = 0.5
    status_forcelist: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    
    # Timeout
    timeout: int = 30
    
    # Caching
    api_key_cache_ttl: timedelta = field(default_factory=lambda: timedelta(hours=24))
    
    # Secret Manager
    secret_name: str = "THE_GRAPH_API_KEY"
    fallback_env_var: str = "THE_GRAPH_API_KEY"
    
    @classmethod
    def from_env(cls) -> "TheGraphClientConfig":
        """Create config from environment variables."""
        return cls(
            gateway_base_url=get_config("THEGRAPH_GATEWAY_URL", "https://gateway.thegraph.com/api"),
            studio_base_url=get_config("THEGRAPH_STUDIO_URL", "https://api.studio.thegraph.com/query"),
            default_uniswap_v3_url=get_config(
                "UNISWAP_V3_GRAPH_URL",
                "https://api.studio.thegraph.com/query/48211/uniswap-v3-mainnet/version/latest"
            ),
            max_retries=int(get_config("THEGRAPH_MAX_RETRIES", "3")),
            backoff_factor=float(get_config("THEGRAPH_BACKOFF_FACTOR", "0.5")),
            timeout=int(get_config("THEGRAPH_TIMEOUT", "30")),
            secret_name=get_config("THEGRAPH_SECRET_NAME", "THE_GRAPH_API_KEY"),
            fallback_env_var="THE_GRAPH_API_KEY",
        )


class TheGraphBaseClient:
    """
    Base client for The Graph API with centralized network management.
    
    Provides:
    - API key management (Secret Manager + caching)
    - HTTP session with retries
    - GraphQL query execution
    - Subgraph URL building
    
    Domain services compose with this for their specific queries.
    """
    
    def __init__(
        self,
        config: Optional[TheGraphClientConfig] = None,
        api_key: Optional[str] = None,
        subgraph_url: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        """
        Initialize The Graph base client.
        
        Args:
            config: Client configuration (defaults to env-based config)
            api_key: Optional API key (uses cached/Secret Manager if not provided)
            subgraph_url: Optional subgraph URL (uses default if not provided)
            project_id: GCP project ID for Secret Manager
        """
        self.config = config or TheGraphClientConfig.from_env()
        self.project_id = project_id or get_config("GCP_PROJECT_ID", "")
        
        # API key (lazy loaded)
        self._api_key = api_key
        
        # Subgraph URL
        self._subgraph_url = subgraph_url
        
        # HTTP session (lazy initialized)
        self._session: Optional[requests.Session] = None
        
        logger.debug(f"✅ TheGraphBaseClient created")
    
    @property
    def api_key(self) -> Optional[str]:
        """Get API key with caching."""
        global _THEGRAPH_API_KEY_CACHE, _THEGRAPH_API_KEY_TIMESTAMP
        
        # Return provided key if available
        if self._api_key:
            return self._api_key
        
        # Check cache validity
        if _THEGRAPH_API_KEY_CACHE and _THEGRAPH_API_KEY_TIMESTAMP:
            age = datetime.now(timezone.utc) - _THEGRAPH_API_KEY_TIMESTAMP
            if age < self.config.api_key_cache_ttl:
                logger.debug("✅ Using cached The Graph API key")
                return _THEGRAPH_API_KEY_CACHE
        
        # Fetch from Secret Manager
        try:
            api_key = get_secret_with_fallback(
                project_id=self.project_id,
                secret_name=self.config.secret_name,
                fallback_env_var=self.config.fallback_env_var,
            )
            
            if api_key:
                api_key = api_key.strip()
                _THEGRAPH_API_KEY_CACHE = api_key
                _THEGRAPH_API_KEY_TIMESTAMP = datetime.now(timezone.utc)
                logger.info(f"✅ Retrieved and cached The Graph API key (TTL: {self.config.api_key_cache_ttl})")
                return api_key
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to retrieve The Graph API key: {e}")
        
        return None  # API key is optional - falls back to Studio endpoints
    
    @property
    def subgraph_url(self) -> str:
        """Get the subgraph URL."""
        return self._subgraph_url or self.config.default_uniswap_v3_url
    
    @subgraph_url.setter
    def subgraph_url(self, url: str):
        """Set the subgraph URL."""
        self._subgraph_url = url
    
    @property
    def session(self) -> requests.Session:
        """Get or create HTTP session with retries."""
        if self._session is None:
            self._session = requests.Session()
            
            retry_strategy = Retry(
                total=self.config.max_retries,
                backoff_factor=self.config.backoff_factor,
                status_forcelist=self.config.status_forcelist,
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
            
            logger.debug(f"✅ Created HTTP session with {self.config.max_retries} retries")
        
        return self._session
    
    # =========================================================================
    # SUBGRAPH URL HELPERS
    # =========================================================================
    
    def build_gateway_url(self, subgraph_id: str) -> Optional[str]:
        """
        Build a Gateway URL (requires API key).
        
        Args:
            subgraph_id: The Graph subgraph ID
            
        Returns:
            Gateway URL or None if no API key
        """
        if not self.api_key:
            logger.warning("⚠️ No API key available for Gateway URL")
            return None
        
        return f"{self.config.gateway_base_url}/{self.api_key}/subgraphs/id/{subgraph_id}"
    
    def build_studio_url(self, account_id: str, subgraph_name: str, version: str = "version/latest") -> str:
        """
        Build a Studio URL (no API key needed, but rate-limited).
        
        Args:
            account_id: Studio account ID
            subgraph_name: Subgraph name
            version: Version string (default: "version/latest")
            
        Returns:
            Studio URL
        """
        return f"{self.config.studio_base_url}/{account_id}/{subgraph_name}/{version}"
    
    # =========================================================================
    # GRAPHQL EXECUTION
    # =========================================================================
    
    def execute_query(self, query: str, url: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query.
        
        Args:
            query: GraphQL query string
            url: Optional subgraph URL (uses default if not provided)
            
        Returns:
            Dictionary with 'data' and 'errors' keys
        """
        target_url = url or self.subgraph_url
        
        try:
            headers = {"Content-Type": "application/json"}
            
            response = self.session.post(
                target_url,
                json={"query": query},
                headers=headers,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            
            data = response.json()
            
            if "errors" in data:
                errors = data.get("errors", [])
                error_messages = [str(e.get("message", "")).lower() for e in errors]
                
                if any("removed" in msg or "deprecated" in msg or "endpoint" in msg for msg in error_messages):
                    logger.debug(f"⚠️ The Graph endpoint deprecated: {target_url}")
                else:
                    logger.error(f"❌ The Graph query errors: {errors}")
                
                return {"data": {}, "errors": errors}
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ The Graph request failed: {e}")
            return {"data": {}, "errors": [str(e)]}
        except Exception as e:
            logger.error(f"❌ Failed to execute GraphQL query: {e}")
            return {"data": {}, "errors": [str(e)]}
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    def cleanup(self):
        """Cleanup resources."""
        if self._session:
            self._session.close()
            self._session = None
        logger.debug("🧹 TheGraphBaseClient cleanup completed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


# Factory function
def create_thegraph_base_client(
    config: Optional[TheGraphClientConfig] = None,
    api_key: Optional[str] = None,
    subgraph_url: Optional[str] = None,
    project_id: Optional[str] = None,
) -> TheGraphBaseClient:
    """
    Create a TheGraphBaseClient instance.
    
    Args:
        config: Optional client configuration
        api_key: Optional API key
        subgraph_url: Optional subgraph URL
        project_id: Optional GCP project ID
        
    Returns:
        Configured TheGraphBaseClient
    """
    return TheGraphBaseClient(
        config=config,
        api_key=api_key,
        subgraph_url=subgraph_url,
        project_id=project_id,
    )

