"""
Tardis Base Client - Centralized Network Management

Provides core HTTP client functionality for Tardis API interactions.
Domain services (instruments-service, market-tick-data-handler) compose with this
for their specific API endpoints.

Features:
- Session reuse with connection pooling
- Retry strategy with exponential backoff
- Module-level API key caching
- Warmup and health checks
- Centralized error handling and logging

Architecture:
- unified-cloud-services: TardisBaseClient (network layer)
- instruments-service: Uses for /v1/exchanges/{exchange} endpoints
- market-tick-data-handler: Uses for /v1/{exchange}/{data_type}/... CSV endpoints
"""

import logging
import asyncio
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
import aiohttp
from aiohttp import ClientTimeout, TCPConnector
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from unified_cloud_services import get_secret_with_fallback, get_config

logger = logging.getLogger(__name__)

# Module-level API key cache (shared across all instances)
_TARDIS_API_KEY_CACHE: Optional[str] = None
_TARDIS_API_KEY_TIMESTAMP: Optional[datetime] = None
_TARDIS_API_KEY_TTL = timedelta(hours=24)

# Module-level instrument cache (shared across all instances and days)
# Caches full instrument lists per exchange - they don't change often
# Format: {exchange: (instruments_list, timestamp)}
_INSTRUMENTS_CACHE: Dict[str, Tuple[Any, datetime]] = {}
_INSTRUMENTS_CACHE_TTL = timedelta(hours=12)  # Refresh every 12 hours


def clear_tardis_api_key_cache():
    """Clear the module-level API key cache."""
    global _TARDIS_API_KEY_CACHE, _TARDIS_API_KEY_TIMESTAMP
    _TARDIS_API_KEY_CACHE = None
    _TARDIS_API_KEY_TIMESTAMP = None
    logger.info("🧹 Cleared Tardis API key cache")


def get_cached_instruments(exchange: str) -> Optional[Any]:
    """
    Get cached instruments for an exchange if still valid.
    
    PERFORMANCE: Avoids repeated Tardis API calls for instrument lists.
    Instrument lists don't change frequently (new instruments are rare),
    so caching saves ~1-2s per exchange.
    
    Args:
        exchange: Tardis exchange identifier
        
    Returns:
        Cached instruments list or None if not cached/expired
    """
    if exchange in _INSTRUMENTS_CACHE:
        instruments, timestamp = _INSTRUMENTS_CACHE[exchange]
        if datetime.now(timezone.utc) - timestamp < _INSTRUMENTS_CACHE_TTL:
            logger.debug(f"📋 Using cached instruments for {exchange}")
            return instruments
        else:
            logger.debug(f"⏰ Instrument cache expired for {exchange}")
    return None


def set_cached_instruments(exchange: str, instruments: Any):
    """
    Cache instruments for an exchange.
    
    Args:
        exchange: Tardis exchange identifier
        instruments: Instruments list to cache
    """
    _INSTRUMENTS_CACHE[exchange] = (instruments, datetime.now(timezone.utc))
    logger.debug(f"💾 Cached {len(instruments) if instruments else 0} instruments for {exchange}")


def clear_instruments_cache(exchange: Optional[str] = None):
    """
    Clear instruments cache.
    
    Args:
        exchange: If provided, clear only this exchange. Otherwise clear all.
    """
    global _INSTRUMENTS_CACHE
    if exchange:
        if exchange in _INSTRUMENTS_CACHE:
            del _INSTRUMENTS_CACHE[exchange]
            logger.info(f"🧹 Cleared instruments cache for {exchange}")
    else:
        _INSTRUMENTS_CACHE.clear()
        logger.info("🧹 Cleared all instruments cache")


@dataclass
class TardisClientConfig:
    """Configuration for Tardis client."""
    
    # API endpoints
    api_base_url: str = "https://api.tardis.dev/v1"
    datasets_base_url: str = "https://datasets.tardis.dev/v1"
    
    # Connection pooling
    connection_pool_size: int = 16
    max_connections: int = 100
    
    # Timeouts
    connect_timeout: int = 30
    read_timeout: int = 300  # 5 minutes for large CSV downloads
    
    # Retry configuration
    max_retries: int = 3
    backoff_factor: float = 1.0
    retry_status_codes: Tuple[int, ...] = (429, 500, 502, 503, 504)
    
    # Caching
    api_key_cache_ttl: timedelta = field(default_factory=lambda: timedelta(hours=24))
    
    # Secret Manager
    secret_name: str = "tardis-api-key"
    fallback_env_var: str = "TARDIS_API_KEY"
    
    @classmethod
    def from_env(cls) -> "TardisClientConfig":
        """Create config from environment variables."""
        return cls(
            api_base_url=get_config("TARDIS_API_BASE_URL", "https://api.tardis.dev/v1"),
            datasets_base_url=get_config("TARDIS_BASE_URL", "https://datasets.tardis.dev/v1"),
            connection_pool_size=int(get_config("TARDIS_CONNECTION_POOL_SIZE", "16")),
            max_connections=int(get_config("TARDIS_MAX_CONNECTIONS", "100")),
            connect_timeout=int(get_config("TARDIS_CONNECT_TIMEOUT", "30")),
            read_timeout=int(get_config("TARDIS_READ_TIMEOUT", "300")),
            max_retries=int(get_config("TARDIS_MAX_RETRIES", "3")),
            backoff_factor=float(get_config("TARDIS_BACKOFF_FACTOR", "1.0")),
            secret_name=get_config("TARDIS_SECRET_NAME", "tardis-api-key"),
            fallback_env_var="TARDIS_API_KEY",
        )


class TardisBaseClient:
    """
    Base Tardis client with centralized network management.
    
    Provides:
    - API key management (Secret Manager + caching)
    - Session management (sync and async)
    - Connection pooling and retries
    - Warmup and health checks
    - Centralized logging
    
    Domain services compose with this for their specific endpoints.
    """
    
    def __init__(
        self,
        config: Optional[TardisClientConfig] = None,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        """
        Initialize Tardis base client.
        
        Args:
            config: Client configuration (defaults to env-based config)
            api_key: Optional API key (uses cached/Secret Manager if not provided)
            project_id: GCP project ID for Secret Manager
        """
        self.config = config or TardisClientConfig.from_env()
        self.project_id = project_id or get_config("GCP_PROJECT_ID")
        
        # API key (lazy loaded)
        self._api_key = api_key
        
        # Sync session (for instruments-service style requests)
        self._sync_session: Optional[requests.Session] = None
        
        # Async session (for market-tick-data-handler style downloads)
        self._async_session: Optional[aiohttp.ClientSession] = None
        
        self._initialized = False
        self._healthy = True
        
        logger.debug(f"✅ TardisBaseClient created: pool_size={self.config.connection_pool_size}")
    
    @property
    def api_key(self) -> str:
        """Get API key with caching."""
        global _TARDIS_API_KEY_CACHE, _TARDIS_API_KEY_TIMESTAMP
        
        # Return provided key if available
        if self._api_key:
            return self._api_key
        
        # Check cache validity
        if _TARDIS_API_KEY_CACHE and _TARDIS_API_KEY_TIMESTAMP:
            age = datetime.now(timezone.utc) - _TARDIS_API_KEY_TIMESTAMP
            if age < self.config.api_key_cache_ttl:
                logger.debug("✅ Using cached Tardis API key")
                return _TARDIS_API_KEY_CACHE
        
        # Fetch from Secret Manager
        try:
            api_key = get_secret_with_fallback(
                project_id=self.project_id,
                secret_name=self.config.secret_name,
                fallback_env_var=self.config.fallback_env_var,
            )
            
            if api_key:
                _TARDIS_API_KEY_CACHE = api_key
                _TARDIS_API_KEY_TIMESTAMP = datetime.now(timezone.utc)
                logger.info(f"✅ Retrieved and cached Tardis API key (TTL: {self.config.api_key_cache_ttl})")
                return api_key
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to retrieve Tardis API key: {e}")
        
        raise ValueError(
            "Tardis API key required. Set TARDIS_SECRET_NAME (Secret Manager), "
            "TARDIS_API_KEY env var (fallback), or pass api_key parameter."
        )
    
    @property
    def headers(self) -> Dict[str, str]:
        """
        Get standard headers for Tardis API requests.
        
        NOTE: Content-Type is intentionally omitted because:
        - Tardis datasets endpoint returns 302 redirect to pre-signed S3 URLs
        - S3 pre-signed URLs include expected headers in signature calculation
        - Sending Content-Type: application/json breaks S3 signature validation
        - GET requests don't need Content-Type anyway
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "unified-trading-system/1.0",
        }
    
    @property
    def json_headers(self) -> Dict[str, str]:
        """Get headers for JSON API requests (POST/PUT)."""
        return {
            **self.headers,
            "Content-Type": "application/json",
        }
    
    # =========================================================================
    # SYNC SESSION (for instruments-service style requests)
    # =========================================================================
    
    def get_sync_session(self, auto_warmup: bool = True) -> requests.Session:
        """
        Get or create sync HTTP session with retries.
        
        Args:
            auto_warmup: If True, warmup connection pool on first creation (default: True)
            
        Returns:
            Configured requests.Session with connection pooling
        """
        if self._sync_session is None:
            self._sync_session = requests.Session()
            
            # Configure retry strategy
            retry_strategy = Retry(
                total=self.config.max_retries,
                backoff_factor=self.config.backoff_factor,
                status_forcelist=list(self.config.retry_status_codes),
            )
            adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=self.config.connection_pool_size,
                pool_maxsize=self.config.max_connections,
            )
            self._sync_session.mount("https://", adapter)
            self._sync_session.headers.update(self.headers)
            
            logger.info(
                f"✅ TardisBaseClient sync session initialized: "
                f"pool_size={self.config.connection_pool_size}, retries={self.config.max_retries}"
            )
            
            # Auto-warmup connection pool on first creation
            if auto_warmup:
                self.sync_warmup()
        
        return self._sync_session
    
    def sync_get(
        self,
        url: str,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> requests.Response:
        """
        Make a sync GET request with retries and logging.
        
        Args:
            url: Request URL
            timeout: Request timeout (defaults to config)
            **kwargs: Additional requests.get kwargs
            
        Returns:
            Response object
        """
        session = self.get_sync_session()
        timeout = timeout or self.config.read_timeout
        
        logger.debug(f"📥 Tardis sync GET: {url}")
        
        try:
            response = session.get(url, timeout=timeout, **kwargs)
            
            if response.status_code == 200:
                logger.debug(f"✅ Tardis sync GET success: {url}")
            elif response.status_code == 404:
                logger.warning(f"⚠️ Tardis 404 - Not found: {url}")
            else:
                # Read response body for error details
                try:
                    error_body = response.text
                    # Truncate long responses
                    error_preview = error_body[:500] if len(error_body) > 500 else error_body
                except Exception:
                    error_preview = "(unable to read response body)"
                
                logger.warning(f"⚠️ Tardis HTTP {response.status_code}: {url}")
                logger.warning(f"   Response: {error_preview}")
                
                # Log specific guidance for common errors
                if response.status_code == 403:
                    logger.warning(f"   💡 HTTP 403 = Forbidden. Possible causes:")
                    logger.warning(f"      - API key doesn't have access to this data")
                    logger.warning(f"      - Historical data requires paid subscription")
                    logger.warning(f"      - Exchange/date combo not in your plan")
                elif response.status_code == 429:
                    logger.warning(f"   💡 HTTP 429 = Rate limited. Wait and retry.")
                elif response.status_code == 401:
                    logger.warning(f"   💡 HTTP 401 = Unauthorized. Check API key.")
            
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Tardis sync GET failed: {url}")
            logger.error(f"   Error: {type(e).__name__}: {e}")
            raise
    
    # =========================================================================
    # ASYNC SESSION (for market-tick-data-handler style downloads)
    # =========================================================================
    
    async def initialize_async_session(self, auto_warmup: bool = True) -> None:
        """
        Initialize async HTTP session with connection pooling.
        
        Args:
            auto_warmup: If True, warmup connection pool after creation (default: True)
        """
        if self._async_session and not self._async_session.closed:
            logger.debug("✅ Async session already initialized")
            return
        
        connector = TCPConnector(
            limit=self.config.max_connections,
            limit_per_host=self.config.connection_pool_size,
            ttl_dns_cache=300,
            force_close=False,
        )
        
        timeout = ClientTimeout(
            connect=self.config.connect_timeout,
            total=self.config.read_timeout,
        )
        
        self._async_session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers,
        )
        
        self._initialized = True
        self._healthy = True
        
        logger.info(
            f"✅ TardisBaseClient async session initialized: "
            f"pool_size={self.config.connection_pool_size}, max_connections={self.config.max_connections}"
        )
        
        # Auto-warmup connection pool after creation
        if auto_warmup:
            await self.warmup()
    
    async def get_async_session(self) -> aiohttp.ClientSession:
        """Get or create async HTTP session."""
        await self.initialize_async_session()
        return self._async_session
    
    async def async_get(
        self,
        url: str,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """
        Make an async GET request with logging.
        
        Args:
            url: Request URL
            **kwargs: Additional aiohttp kwargs
            
        Returns:
            Response object (caller must handle context manager)
        """
        session = await self.get_async_session()
        
        logger.debug(f"📥 Tardis async GET: {url}")
        
        return await session.get(url, **kwargs)
    
    async def async_get_bytes(
        self,
        url: str,
        **kwargs,
    ) -> Tuple[int, bytes]:
        """
        Make an async GET request and return status + bytes.
        
        Args:
            url: Request URL
            **kwargs: Additional aiohttp kwargs
            
        Returns:
            Tuple of (status_code, response_bytes)
        """
        session = await self.get_async_session()
        
        logger.debug(f"📥 Tardis async GET (bytes): {url}")
        
        try:
            async with session.get(url, **kwargs) as response:
                status = response.status
                
                if status == 200:
                    data = await response.read()
                    logger.debug(f"✅ Tardis async GET success: {len(data)} bytes from {url}")
                    return status, data
                elif status == 404:
                    logger.warning(f"⚠️ Tardis 404 - Not found: {url}")
                    return status, b""
                else:
                    # Read response body for error details
                    try:
                        error_body = await response.text()
                        # Truncate long responses
                        error_preview = error_body[:500] if len(error_body) > 500 else error_body
                    except Exception:
                        error_preview = "(unable to read response body)"
                    
                    logger.warning(f"⚠️ Tardis HTTP {status}: {url}")
                    logger.warning(f"   Response: {error_preview}")
                    
                    # Log specific guidance for common errors
                    if status == 403:
                        logger.warning(f"   💡 HTTP 403 = Forbidden. Possible causes:")
                        logger.warning(f"      - API key doesn't have access to this data")
                        logger.warning(f"      - Historical data requires paid subscription")
                        logger.warning(f"      - Exchange/date combo not in your plan")
                    elif status == 429:
                        logger.warning(f"   💡 HTTP 429 = Rate limited. Wait and retry.")
                    elif status == 401:
                        logger.warning(f"   💡 HTTP 401 = Unauthorized. Check API key.")
                    
                    return status, b""
                    
        except aiohttp.ClientError as e:
            logger.error(f"❌ Tardis async GET failed: {url}")
            logger.error(f"   Error: {type(e).__name__}: {e}")
            raise
    
    # =========================================================================
    # WARMUP AND HEALTH
    # =========================================================================
    
    async def warmup(self) -> bool:
        """
        Warmup connection pools by pinging BOTH api and datasets endpoints.
        
        IMPORTANT: api.tardis.dev and datasets.tardis.dev are different hosts!
        We need to warmup both for connection pooling to work correctly.
        
        Returns:
            True if warmup successful
        """
        await self.initialize_async_session()
        
        warmup_results = []
        
        # Warmup 1: API endpoint (for instrument listings)
        try:
            api_warmup_url = f"{self.config.api_base_url}/exchanges"
            async with self._async_session.get(
                api_warmup_url,
                timeout=ClientTimeout(total=10),
            ) as response:
                warmup_results.append(("api.tardis.dev", response.status == 200))
                logger.debug(f"✅ API warmup: {response.status}")
        except Exception as e:
            warmup_results.append(("api.tardis.dev", False))
            logger.debug(f"⚠️ API warmup failed: {e}")
        
        # Warmup 2: Datasets endpoint (for CSV downloads) - HEAD request to avoid data transfer
        try:
            # Use a known endpoint pattern - just check connectivity
            datasets_warmup_url = f"{self.config.datasets_base_url}"
            async with self._async_session.head(
                datasets_warmup_url,
                timeout=ClientTimeout(total=10),
                allow_redirects=True,
            ) as response:
                # 403/404 are fine - we just want to establish TCP connection + DNS
                warmup_results.append(("datasets.tardis.dev", response.status in [200, 403, 404, 405]))
                logger.debug(f"✅ Datasets warmup: {response.status}")
        except Exception as e:
            warmup_results.append(("datasets.tardis.dev", False))
            logger.debug(f"⚠️ Datasets warmup failed: {e}")
        
        # Log results
        all_success = all(success for _, success in warmup_results)
        if all_success:
            logger.info("✅ TardisBaseClient warmup successful (api + datasets)")
            self._healthy = True
        else:
            failed = [host for host, success in warmup_results if not success]
            logger.warning(f"⚠️ TardisBaseClient partial warmup: failed for {failed}")
        
        return True  # Don't block on warmup failure
    
    def sync_warmup(self) -> bool:
        """
        Sync warmup for connection pools (both api and datasets).
        
        Returns:
            True if warmup successful
        """
        warmup_results = []
        
        try:
            session = self.get_sync_session(auto_warmup=False)  # Avoid recursion
            
            # Warmup 1: API endpoint
            try:
                api_url = f"{self.config.api_base_url}/exchanges"
                response = session.get(api_url, timeout=10)
                warmup_results.append(("api.tardis.dev", response.status_code == 200))
            except Exception as e:
                warmup_results.append(("api.tardis.dev", False))
                logger.debug(f"⚠️ API warmup failed: {e}")
            
            # Warmup 2: Datasets endpoint (HEAD request)
            try:
                datasets_url = f"{self.config.datasets_base_url}"
                response = session.head(datasets_url, timeout=10, allow_redirects=True)
                warmup_results.append(("datasets.tardis.dev", response.status_code in [200, 403, 404, 405]))
            except Exception as e:
                warmup_results.append(("datasets.tardis.dev", False))
                logger.debug(f"⚠️ Datasets warmup failed: {e}")
            
            all_success = all(success for _, success in warmup_results)
            if all_success:
                logger.info("✅ TardisBaseClient sync warmup successful (api + datasets)")
                self._healthy = True
            else:
                failed = [host for host, success in warmup_results if not success]
                logger.warning(f"⚠️ TardisBaseClient partial sync warmup: failed for {failed}")
            
            return True
                
        except Exception as e:
            logger.warning(f"⚠️ TardisBaseClient sync warmup failed: {e}")
            return True
    
    def is_healthy(self) -> bool:
        """Check if client is healthy."""
        return self._healthy
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    def close_sync_session(self) -> None:
        """Close sync session."""
        if self._sync_session:
            self._sync_session.close()
            self._sync_session = None
            logger.debug("✅ TardisBaseClient sync session closed")
    
    async def close_async_session(self) -> None:
        """Close async session."""
        if self._async_session and not self._async_session.closed:
            await self._async_session.close()
            self._async_session = None
            self._initialized = False
            logger.debug("✅ TardisBaseClient async session closed")
    
    def cleanup(self) -> None:
        """Cleanup all resources (sync)."""
        self.close_sync_session()
        logger.info("🧹 TardisBaseClient cleanup completed")
    
    async def cleanup_async(self) -> None:
        """Cleanup all resources (async)."""
        await self.close_async_session()
        logger.info("🧹 TardisBaseClient async cleanup completed")
    
    # =========================================================================
    # CONTEXT MANAGERS
    # =========================================================================
    
    def __enter__(self):
        """Sync context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.cleanup()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize_async_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup_async()


# Factory function for convenience
def create_tardis_base_client(
    config: Optional[TardisClientConfig] = None,
    api_key: Optional[str] = None,
    project_id: Optional[str] = None,
) -> TardisBaseClient:
    """
    Create a TardisBaseClient instance.
    
    Args:
        config: Optional client configuration
        api_key: Optional API key
        project_id: Optional GCP project ID
        
    Returns:
        Configured TardisBaseClient
    """
    return TardisBaseClient(config=config, api_key=api_key, project_id=project_id)

