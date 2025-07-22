"""
Database Configuration
=====================

Redis connection and database configuration management.
Provides connection pools and async database clients.
"""

from typing import Optional
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
import asyncpg
from contextlib import asynccontextmanager

from .settings import get_settings
from .logging import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Database connection manager for Redis and PostgreSQL."""
    
    def __init__(self):
        self.settings = get_settings()
        self._redis_pool: Optional[ConnectionPool] = None
        self._postgres_pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self) -> None:
        """Initialize database connections."""
        await self._setup_redis()
        if self.settings.database_url:
            await self._setup_postgres()
        logger.info("Database connections initialized")
    
    async def close(self) -> None:
        """Close database connections."""
        if self._redis_pool:
            await self._redis_pool.disconnect()
            logger.info("Redis connection closed")
        
        if self._postgres_pool:
            await self._postgres_pool.close()
            logger.info("PostgreSQL connection closed")
    
    async def _setup_redis(self) -> None:
        """Setup Redis connection pool."""
        try:
            self._redis_pool = ConnectionPool.from_url(
                self.settings.redis_url,
                max_connections=self.settings.redis_max_connections,
                retry_on_timeout=True,
                decode_responses=True
            )
            
            # Test connection
            async with redis.Redis(connection_pool=self._redis_pool) as client:
                await client.ping()
            
            logger.info("Redis connection established", url=self.settings.redis_url)
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise
    
    async def _setup_postgres(self) -> None:
        """Setup PostgreSQL connection pool."""
        try:
            self._postgres_pool = await asyncpg.create_pool(
                self.settings.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("PostgreSQL connection established")
        except Exception as e:
            logger.error("Failed to connect to PostgreSQL", error=str(e))
            raise
    
    def get_redis_client(self) -> redis.Redis:
        """Get Redis client instance."""
        if not self._redis_pool:
            raise RuntimeError("Redis not initialized")
        return redis.Redis(connection_pool=self._redis_pool)
    
    @asynccontextmanager
    async def get_postgres_connection(self):
        """Get PostgreSQL connection context manager."""
        if not self._postgres_pool:
            raise RuntimeError("PostgreSQL not initialized")
        
        async with self._postgres_pool.acquire() as connection:
            yield connection


# Global database manager instance
db_manager = DatabaseManager()


async def get_redis_client() -> redis.Redis:
    """Get Redis client instance."""
    return db_manager.get_redis_client()


async def get_postgres_connection():
    """Get PostgreSQL connection context manager."""
    return db_manager.get_postgres_connection()


async def initialize_databases() -> None:
    """Initialize all database connections."""
    await db_manager.initialize()


async def close_databases() -> None:
    """Close all database connections."""
    await db_manager.close()


# Health check functions
async def check_redis_health() -> bool:
    """Check Redis connection health."""
    try:
        async with get_redis_client() as client:
            await client.ping()
        return True
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return False


async def check_postgres_health() -> bool:
    """Check PostgreSQL connection health."""
    if not db_manager.settings.database_url:
        return True  # Not configured, consider healthy
    
    try:
        async with get_postgres_connection() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error("PostgreSQL health check failed", error=str(e))
        return False


async def check_database_health() -> dict:
    """Check all database connections health."""
    return {
        "redis": await check_redis_health(),
        "postgres": await check_postgres_health()
    }