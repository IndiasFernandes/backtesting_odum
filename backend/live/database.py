"""
asyncpg connection pool manager for live execution.

Purpose: Manage PostgreSQL connection pool for execution-critical database operations.
Service: Live service only (port 8001)

Dependencies:
    - asyncpg for async PostgreSQL operations
    - Environment variable: DATABASE_URL

Usage:
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetch('SELECT * FROM unified_orders')
"""
import asyncpg
import os
from typing import Optional
from urllib.parse import urlparse


_pool: Optional[asyncpg.Pool] = None


def _parse_database_url(database_url: str) -> dict:
    """Parse DATABASE_URL into asyncpg connection parameters."""
    parsed = urlparse(database_url)
    
    return {
        'database': parsed.path.lstrip('/') if parsed.path else 'execution_db',
        'user': parsed.username or 'user',
        'password': parsed.password or 'pass',
        'host': parsed.hostname or 'postgres',
        'port': parsed.port or 5432,
    }


async def get_pool() -> asyncpg.Pool:
    """Get or create asyncpg connection pool."""
    global _pool
    if _pool is None:
        await init_pool()
    return _pool


async def init_pool():
    """Initialize asyncpg connection pool."""
    global _pool
    
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://user:pass@postgres:5432/execution_db"
    )
    
    # Parse connection string for asyncpg
    conn_params = _parse_database_url(database_url)
    
    _pool = await asyncpg.create_pool(
        database=conn_params['database'],
        user=conn_params['user'],
        password=conn_params['password'],
        host=conn_params['host'],
        port=conn_params['port'],
        min_size=10,
        max_size=20,
        max_queries=50000,
        max_inactive_connection_lifetime=300.0,
        command_timeout=60
    )


async def close_pool():
    """Close connection pool gracefully."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

