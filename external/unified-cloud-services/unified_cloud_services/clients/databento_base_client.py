"""
Databento Base Client - Centralized Network Management

Provides core client functionality for Databento API interactions.
Domain services (instruments-service, market-tick-data-handler) compose with this
for their specific API endpoints.

Features:
- Module-level API key caching
- Session persistence and health tracking
- Rate limiting with semaphore
- Retry configuration with backoff
- Warmup and health checks
- Centralized logging

Architecture:
- unified-cloud-services: DatabentoBaseClient (network layer)
- instruments-service: Uses for metadata.list_datasets() and timeseries.get_range()
- market-tick-data-handler: Uses for historical data downloads (OHLCV, trades)
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

from unified_cloud_services import get_secret_with_fallback, get_config

logger = logging.getLogger(__name__)

# Check if databento is available
try:
    import databento as db
    DATABENTO_AVAILABLE = True
except ImportError:
    DATABENTO_AVAILABLE = False
    db = None
    logger.warning("databento package not available. Install with: pip install databento")

# Module-level API key cache (shared across all instances)
_DATABENTO_API_KEY_CACHE: Optional[str] = None
_DATABENTO_API_KEY_TIMESTAMP: Optional[datetime] = None
_DATABENTO_API_KEY_TTL = timedelta(hours=24)

# Module-level client cache for connection pooling
_DATABENTO_CLIENT_CACHE: Optional[Any] = None


def clear_databento_api_key_cache():
    """Clear the module-level API key cache."""
    global _DATABENTO_API_KEY_CACHE, _DATABENTO_API_KEY_TIMESTAMP
    _DATABENTO_API_KEY_CACHE = None
    _DATABENTO_API_KEY_TIMESTAMP = None
    logger.info("🧹 Cleared Databento API key cache")


def clear_databento_client_cache():
    """Clear the module-level client cache."""
    global _DATABENTO_CLIENT_CACHE
    _DATABENTO_CLIENT_CACHE = None
    logger.info("🧹 Cleared Databento client cache")


@dataclass
class DatabentoClientConfig:
    """Configuration for Databento client."""
    
    # Retry configuration
    max_retries: int = 15
    backoff_factor: float = 0.25
    
    # Rate limiting
    max_concurrent_requests: int = 10
    rate_limit_delay: float = 0.2
    
    # Session persistence
    keep_session_alive: bool = True
    reset_on_failure_only: bool = True
    health_check_enabled: bool = True
    max_session_duration_hours: int = 4
    failure_threshold: int = 3
    success_reset_failures: bool = True
    
    # Caching
    api_key_cache_ttl: timedelta = field(default_factory=lambda: timedelta(hours=24))
    reuse_client: bool = True  # Use module-level client caching
    
    # Secret Manager
    secret_name: str = "databento-api-key"
    fallback_env_var: str = "DATABENTO_API_KEY"
    
    @classmethod
    def from_env(cls) -> "DatabentoClientConfig":
        """Create config from environment variables."""
        return cls(
            max_retries=int(get_config("DATABENTO_RETRY_ATTEMPTS", "15")),
            backoff_factor=float(get_config("DATABENTO_BACKOFF_FACTOR", "0.25")),
            max_concurrent_requests=int(get_config("DATABENTO_MAX_CONCURRENT_REQUESTS", "10")),
            rate_limit_delay=float(get_config("DATABENTO_RATE_LIMIT_DELAY", "0.2")),
            keep_session_alive=get_config("DATABENTO_KEEP_SESSION_ALIVE", "true").lower() == "true",
            reset_on_failure_only=get_config("DATABENTO_RESET_ON_FAILURE_ONLY", "true").lower() == "true",
            health_check_enabled=get_config("DATABENTO_SESSION_HEALTH_CHECK_ENABLED", "true").lower() == "true",
            max_session_duration_hours=int(get_config("DATABENTO_MAX_SESSION_DURATION_HOURS", "4")),
            failure_threshold=int(get_config("DATABENTO_SESSION_FAILURE_THRESHOLD", "3")),
            success_reset_failures=get_config("DATABENTO_SESSION_SUCCESS_RESET_FAILURES", "true").lower() == "true",
            reuse_client=get_config("DATABENTO_REUSE_CLIENT", "true").lower() == "true",
            secret_name=get_config("DATABENTO_SECRET_NAME", "databento-api-key"),
            fallback_env_var="DATABENTO_API_KEY",
        )


class DatabentoBaseClient:
    """
    Base Databento client with centralized network management.
    
    Provides:
    - API key management (Secret Manager + caching)
    - Client management (sync, with module-level caching option)
    - Rate limiting with semaphore
    - Session health tracking
    - Warmup and health checks
    - Centralized logging
    
    Domain services compose with this for their specific endpoints.
    """
    
    def __init__(
        self,
        config: Optional[DatabentoClientConfig] = None,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        """
        Initialize Databento base client.
        
        Args:
            config: Client configuration (defaults to env-based config)
            api_key: Optional API key (uses cached/Secret Manager if not provided)
            project_id: GCP project ID for Secret Manager
        """
        if not DATABENTO_AVAILABLE:
            raise ImportError(
                "databento package not available. Install with: pip install databento"
            )
        
        self.config = config or DatabentoClientConfig.from_env()
        self.project_id = project_id or get_config("GCP_PROJECT_ID")
        
        # API key (lazy loaded)
        self._api_key = api_key
        
        # Client instance
        self._client: Optional[Any] = None
        
        # Session health tracking
        self._initialized = False
        self._healthy = True
        self._session_start_time: Optional[datetime] = None
        self._failure_count: int = 0
        self._last_success_time: Optional[datetime] = None
        
        # Rate limiting semaphore (lazy initialized)
        self._semaphore: Optional[asyncio.Semaphore] = None
        
        logger.debug(f"✅ DatabentoBaseClient created: max_concurrent={self.config.max_concurrent_requests}")
    
    @property
    def api_key(self) -> str:
        """Get API key with caching."""
        global _DATABENTO_API_KEY_CACHE, _DATABENTO_API_KEY_TIMESTAMP
        
        # Return provided key if available
        if self._api_key:
            return self._api_key
        
        # Check cache validity
        if _DATABENTO_API_KEY_CACHE and _DATABENTO_API_KEY_TIMESTAMP:
            age = datetime.now(timezone.utc) - _DATABENTO_API_KEY_TIMESTAMP
            if age < self.config.api_key_cache_ttl:
                logger.debug("✅ Using cached Databento API key")
                return _DATABENTO_API_KEY_CACHE
        
        # Fetch from Secret Manager
        try:
            api_key = get_secret_with_fallback(
                project_id=self.project_id,
                secret_name=self.config.secret_name,
                fallback_env_var=self.config.fallback_env_var,
            )
            
            if api_key:
                _DATABENTO_API_KEY_CACHE = api_key
                _DATABENTO_API_KEY_TIMESTAMP = datetime.now(timezone.utc)
                logger.info(f"✅ Retrieved and cached Databento API key (TTL: {self.config.api_key_cache_ttl})")
                return api_key
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to retrieve Databento API key: {e}")
        
        raise ValueError(
            "Databento API key required. Set DATABENTO_SECRET_NAME (Secret Manager), "
            "DATABENTO_API_KEY env var (fallback), or pass api_key parameter."
        )
    
    @property
    def client(self) -> Any:
        """Get or create Databento Historical client with caching."""
        global _DATABENTO_CLIENT_CACHE
        
        # Use cached client if enabled and available
        if self.config.reuse_client and _DATABENTO_CLIENT_CACHE is not None:
            if self._client is None:
                self._client = _DATABENTO_CLIENT_CACHE
                logger.debug("✅ Reusing module-level Databento client (connection pooling)")
            return self._client
        
        # Create new client
        if self._client is None:
            self._client = db.Historical(self.api_key)
            
            # Cache for reuse
            if self.config.reuse_client:
                _DATABENTO_CLIENT_CACHE = self._client
                logger.info("✅ Created and cached Databento Historical client")
            else:
                logger.info("✅ Created Databento Historical client (no caching)")
        
        return self._client
    
    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================
    
    def initialize_session(self, auto_warmup: bool = True) -> None:
        """
        Initialize session for operations.
        
        Sets up:
        - Client (with optional caching)
        - Rate limiting semaphore
        - Session health tracking
        - Auto-warmup (by default)
        
        Args:
            auto_warmup: If True, warmup connection after initialization (default: True)
        """
        if self._initialized:
            logger.debug("✅ Databento session already initialized")
            return
        
        # Force client initialization
        _ = self.client
        
        # Initialize semaphore for rate limiting
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        
        # Initialize session health tracking
        self._session_start_time = datetime.now(timezone.utc)
        self._failure_count = 0
        self._last_success_time = datetime.now(timezone.utc)
        self._healthy = True
        
        self._initialized = True
        
        logger.info(
            f"✅ DatabentoBaseClient session initialized: "
            f"max_concurrent={self.config.max_concurrent_requests}, "
            f"retries={self.config.max_retries}"
        )
        
        if self.config.keep_session_alive:
            logger.info(
                f"🔄 Session persistence enabled: "
                f"max_duration={self.config.max_session_duration_hours}h, "
                f"failure_threshold={self.config.failure_threshold}"
            )
        
        # Auto-warmup connection after initialization
        if auto_warmup:
            self.warmup()
    
    async def initialize_session_async(self) -> None:
        """Async version of initialize_session."""
        self.initialize_session()
    
    # =========================================================================
    # HEALTH TRACKING
    # =========================================================================
    
    def is_healthy(self) -> bool:
        """
        Check if session is still healthy and within configured limits.
        
        Returns:
            bool: True if session is healthy, False otherwise
        """
        if not self._initialized or not self._healthy:
            return False
        
        if not self.config.health_check_enabled:
            return True
        
        # Check session duration
        if self._session_start_time:
            session_age = datetime.now(timezone.utc) - self._session_start_time
            max_duration = timedelta(hours=self.config.max_session_duration_hours)
            if session_age > max_duration:
                logger.warning(
                    f"⚠️ Databento session exceeded max duration: "
                    f"{session_age} > {max_duration}"
                )
                return False
        
        # Check failure count
        if self._failure_count >= self.config.failure_threshold:
            logger.warning(
                f"⚠️ Databento session failure threshold reached: "
                f"{self._failure_count} >= {self.config.failure_threshold}"
            )
            return False
        
        return True
    
    def record_success(self) -> None:
        """Record a successful API call."""
        self._last_success_time = datetime.now(timezone.utc)
        if self.config.success_reset_failures:
            self._failure_count = 0
    
    def record_failure(self) -> None:
        """Record a failed API call."""
        self._failure_count += 1
        if self._failure_count >= self.config.failure_threshold:
            self._healthy = False
            logger.warning(
                f"⚠️ Databento session marked unhealthy after {self._failure_count} failures"
            )
    
    async def reset_if_needed(self) -> bool:
        """
        Reset session if unhealthy.
        
        Returns:
            bool: True if session was reset, False if kept alive
        """
        if not self.config.reset_on_failure_only or not self.is_healthy():
            logger.info("🔄 Resetting Databento session due to health check failure")
            
            # Reset session
            self._client = None
            self._initialized = False
            
            # Clear module cache if using it
            if self.config.reuse_client:
                global _DATABENTO_CLIENT_CACHE
                _DATABENTO_CLIENT_CACHE = None
            
            # Reinitialize
            self.initialize_session()
            return True
        
        return False
    
    # =========================================================================
    # WARMUP
    # =========================================================================
    
    def warmup(self) -> bool:
        """
        Warmup connection by making a lightweight metadata request.
        
        Validates API key and establishes initial connection.
        
        Returns:
            bool: True if warmup successful
        """
        if not self._initialized:
            self.initialize_session()
        
        try:
            # Test connection with metadata request (no data cost)
            datasets = self.client.metadata.list_datasets()
            
            logger.info(
                f"✅ DatabentoBaseClient warmup successful: "
                f"API key valid, {len(datasets) if datasets else 0} datasets available"
            )
            self.record_success()
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ DatabentoBaseClient warmup failed: {e}")
            self.record_failure()
            return False
    
    async def warmup_async(self) -> bool:
        """Async version of warmup (runs sync call in executor)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.warmup)
    
    # =========================================================================
    # RATE LIMITING
    # =========================================================================
    
    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Get rate limiting semaphore."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        return self._semaphore
    
    async def rate_limited(self):
        """
        Context manager for rate-limited operations.
        
        Usage:
            async with client.rate_limited():
                result = await some_api_call()
        """
        return self.semaphore
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        self._client = None
        self._initialized = False
        self._healthy = False
        
        # Don't clear module cache by default (other instances may use it)
        
        logger.info("🧹 DatabentoBaseClient cleanup completed")
    
    def cleanup_with_cache_clear(self) -> None:
        """Cleanup resources and clear module caches."""
        self.cleanup()
        clear_databento_client_cache()
        clear_databento_api_key_cache()
    
    # =========================================================================
    # CONTEXT MANAGERS
    # =========================================================================
    
    def __enter__(self):
        """Sync context manager entry."""
        self.initialize_session()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.cleanup()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize_session_async()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.cleanup()


# Factory function for convenience
def create_databento_base_client(
    config: Optional[DatabentoClientConfig] = None,
    api_key: Optional[str] = None,
    project_id: Optional[str] = None,
) -> DatabentoBaseClient:
    """
    Create a DatabentoBaseClient instance.
    
    Args:
        config: Optional client configuration
        api_key: Optional API key
        project_id: Optional GCP project ID
        
    Returns:
        Configured DatabentoBaseClient
    """
    return DatabentoBaseClient(config=config, api_key=api_key, project_id=project_id)

