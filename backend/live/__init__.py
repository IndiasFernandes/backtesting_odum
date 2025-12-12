"""
Live execution module.

Purpose: Live trading execution system components.
Service: Live service only (port 8001)

Components:
    - models: SQLAlchemy models for database schema
    - database: asyncpg connection pool manager
    - adapters: External venue adapters (Deribit, IB, etc.)
"""

