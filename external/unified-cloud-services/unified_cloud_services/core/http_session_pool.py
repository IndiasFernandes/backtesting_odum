"""
HTTP Session Pool - Reusable requests.Session instances.

Avoids creating new HTTP connections for each API call.
Provides connection pooling for all services.

Moved from instruments-service to eliminate duplication.
Used by: instruments-service, market-tick-data-handler, and other services.
"""

import logging
from threading import Lock
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Module-level pool of HTTP sessions: {base_url: requests.Session}
_SESSION_POOL: dict[str, requests.Session] = {}
_POOL_LOCK = Lock()


def get_http_session(
    base_url: str | None = None,
    retry_strategy: Retry | None = None,
) -> requests.Session:
    """
    Get an HTTP session from the pool, or create a new one if not exists.

    Reuses existing sessions to avoid creating new HTTP connections.

    Args:
        base_url: Base URL for the session (used as cache key). If None, creates a generic session.
        retry_strategy: Optional retry strategy for the session

    Returns:
        requests.Session instance
    """
    # Use base_url as cache key, or "default" if None
    cache_key = base_url or "default"

    # Check pool first (thread-safe)
    with _POOL_LOCK:
        if cache_key in _SESSION_POOL:
            session = _SESSION_POOL[cache_key]
            logger.debug(f"✅ Reusing HTTP session for {cache_key}")
            return session

    # Create new session
    session = requests.Session()

    # Setup retry strategy if provided
    if retry_strategy:
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
    else:
        # Default retry strategy
        default_retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=default_retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

    # Add to pool (thread-safe)
    with _POOL_LOCK:
        _SESSION_POOL[cache_key] = session

    logger.debug(f"✅ Created and cached HTTP session for {cache_key}")
    return session


def clear_pool():
    """Clear the HTTP session pool."""
    with _POOL_LOCK:
        _SESSION_POOL.clear()
        logger.debug("Cleared HTTP session pool")
