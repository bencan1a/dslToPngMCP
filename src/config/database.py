"""
Database Configuration
=====================

Redis connection and database configuration management.
Provides connection pools and async database clients.
"""

from typing import Optional, Dict, Any, AsyncGenerator, TypeVar, Generic
import redis.asyncio as redis  # type: ignore[import-untyped]
from redis.asyncio import ConnectionPool  # type: ignore[import-untyped]
import asyncpg  # type: ignore[import-untyped]
from contextlib import asynccontextmanager

from .settings import get_settings
from .logging import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Database connection manager for Redis and PostgreSQL."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._redis_pool: Optional[ConnectionPool] = None  # type: ignore[type-arg]
        self._postgres_pool: Optional[asyncpg.Pool] = None  # type: ignore[type-arg]

    async def initialize(self) -> None:
        """Initialize database connections."""
        await self._setup_redis()
        if self.settings.database_url:
            await self._setup_postgres()
        logger.info("Database connections initialized")

    async def close(self) -> None:
        """Close database connections."""
        if self._redis_pool:  # type: ignore[misc]
            await self._redis_pool.disconnect()  # type: ignore[attr-defined]
            logger.info("Redis connection closed")

        if self._postgres_pool:  # type: ignore[misc]
            await self._postgres_pool.close()  # type: ignore[attr-defined]
            logger.info("PostgreSQL connection closed")

    async def _setup_redis(self) -> None:
        """Setup Redis connection pool."""
        try:
            self._redis_pool = ConnectionPool.from_url(  # type: ignore[attr-defined]
                self.settings.redis_url,
                max_connections=self.settings.redis_max_connections,
                retry_on_timeout=True,
                decode_responses=True,
            )

            # Test connection
            async with redis.Redis(connection_pool=self._redis_pool) as client:  # type: ignore[attr-defined]
                await client.ping()  # type: ignore[attr-defined]

            logger.info("Redis connection established", url=self.settings.redis_url)
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise

    async def _setup_postgres(self) -> None:
        """Setup PostgreSQL connection pool."""
        try:
            self._postgres_pool = await asyncpg.create_pool(  # type: ignore[attr-defined]
                self.settings.database_url, min_size=1, max_size=10, command_timeout=60
            )
            logger.info("PostgreSQL connection established")
        except Exception as e:
            logger.error("Failed to connect to PostgreSQL", error=str(e))
            raise

    def get_redis_client(self) -> redis.Redis:  # type: ignore[type-arg]
        """Get Redis client instance."""
        if not self._redis_pool:  # type: ignore[misc]
            raise RuntimeError("Redis not initialized")
        return redis.Redis(connection_pool=self._redis_pool)  # type: ignore[attr-defined]

    @asynccontextmanager
    async def get_postgres_connection(self) -> AsyncGenerator[Any, None]:  # type: ignore[misc]
        """Get PostgreSQL connection context manager."""
        if not self._postgres_pool:  # type: ignore[misc]
            raise RuntimeError("PostgreSQL not initialized")

        async with self._postgres_pool.acquire() as connection:  # type: ignore[attr-defined]
            yield connection


# Global database manager instance
db_manager = DatabaseManager()


# Type variable for Redis client
T = TypeVar("T", bound=redis.Redis)  # type: ignore[type-arg]


class RedisClientWrapper(Generic[T]):
    """
    Redis client wrapper that supports both direct usage and context manager usage.

    This class wraps a Redis client and provides both direct method access
    and async context manager support. This allows for backward compatibility
    with code that uses the Redis client directly, while also supporting
    proper resource management with async context managers.
    """

    def __init__(self, client: T) -> None:
        """Initialize with a Redis client."""
        self._client: T = client

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the wrapped Redis client."""
        return getattr(self._client, name)  # type: ignore

    async def __aenter__(self) -> T:
        """Enter async context manager."""
        return self._client

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        await self._client.aclose()  # type: ignore[attr-defined]


def get_redis_client() -> redis.Redis:  # type: ignore[type-arg]
    """
    Get Redis client instance.

    Returns:
        Redis client
    """
    # Get the Redis client from the database manager
    return db_manager.get_redis_client()  # type: ignore[misc]


@asynccontextmanager
async def get_redis_client_context() -> AsyncGenerator[redis.Redis, None]:  # type: ignore[type-arg]
    """
    Get Redis client instance as an async context manager.

    This ensures the Redis client is properly initialized with the current event loop
    and properly closed when done. For Celery workers, creates fresh clients to avoid
    event loop binding issues.

    Returns:
        AsyncGenerator yielding a Redis client
    """
    import asyncio
    import threading
    import os
    import sys

    # 🔍 EVENT LOOP DIAGNOSTIC: Log current event loop context
    try:
        current_loop = asyncio.get_running_loop()
        logger.info(
            "🔍 REDIS CLIENT CONTEXT: Current event loop info",
            current_loop_id=id(current_loop),
            current_loop_running=current_loop.is_running(),
            current_loop_closed=current_loop.is_closed(),
            thread_id=threading.current_thread().ident,
            process_id=os.getpid(),
            thread_name=threading.current_thread().name,
        )
    except RuntimeError as e:
        logger.error(
            "🚨 REDIS CLIENT CONTEXT: No running event loop when getting Redis client",
            error=str(e),
            thread_id=threading.current_thread().ident,
            process_id=os.getpid(),
        )
        raise

    # 🔧 CELERY WORKER DETECTION: Check if we're in a Celery worker context
    is_celery_worker = threading.current_thread().name == "MainThread" and (
        "ForkPoolWorker" in str(os.environ.get("CELERY_CURRENT_TASK", ""))
        or "render_dsl_to_png" in str(os.environ.get("CELERY_CURRENT_TASK", ""))
        or any("celery" in arg.lower() for arg in sys.argv)
    )

    logger.info(
        "🔍 CELERY WORKER DETECTION: Checking worker context",
        is_celery_worker=is_celery_worker,
        thread_name=threading.current_thread().name,
        celery_task_env=os.environ.get("CELERY_CURRENT_TASK", "none"),
        argv_contains_celery=any("celery" in arg.lower() for arg in sys.argv),
    )

    if is_celery_worker:
        # 🔧 CELERY WORKER: Create fresh Redis client for current event loop
        settings = get_settings()
        logger.info(
            "🔧 CELERY WORKER: Creating fresh Redis client for current event loop",
            redis_url=(
                settings.redis_url[:50] + "..."
                if len(settings.redis_url) > 50
                else settings.redis_url
            ),
            current_loop_id=id(current_loop),
        )

        # Create fresh Redis client bound to current event loop
        client = redis.Redis.from_url(  # type: ignore[attr-defined]
            settings.redis_url,
            max_connections=10,  # Smaller pool for worker tasks
            retry_on_timeout=True,
            decode_responses=True,
        )

        logger.info(
            "✅ CELERY WORKER: Fresh Redis client created successfully",
            client_id=id(client),
            client_type=type(client).__name__,
            has_connection_pool=hasattr(client, "connection_pool"),
        )
    else:
        # 🔧 NORMAL CONTEXT: Use global database manager client
        logger.info(
            "🔧 NORMAL CONTEXT: Using global database manager Redis client",
            current_loop_id=id(current_loop),
        )

        client = db_manager.get_redis_client()  # type: ignore[misc]

        # 🔍 DIAGNOSTIC: Log global client information
        pool = getattr(client, "connection_pool", None) if client else None  # type: ignore
        logger.info(
            "🔍 GLOBAL CLIENT: Retrieved Redis client from database manager",
            client_type=type(client).__name__ if client else "None",
            client_id=id(client) if client else "None",  # type: ignore
            pool_type=type(pool).__name__ if pool else "None",
            pool_id=id(pool) if pool else "None",  # type: ignore
        )

    try:
        # 🔍 CLIENT VALIDATION: Test client before yielding
        logger.info(
            "🔍 CLIENT VALIDATION: About to test Redis client connectivity",
            client_id=id(client),  # type: ignore
            is_celery_worker=is_celery_worker,
        )

        # Test the connection to ensure it works with current event loop
        await client.ping()  # type: ignore[attr-defined]

        logger.info(
            "✅ CLIENT VALIDATION: Redis client ping successful",
            client_id=id(client),  # type: ignore
            is_celery_worker=is_celery_worker,
        )

        # Yield the client for use in the async with block
        yield client

    except Exception as client_error:
        logger.error(
            "🚨 CLIENT ERROR: Redis client operation failed",
            client_id=id(client),  # type: ignore
            is_celery_worker=is_celery_worker,
            error_type=type(client_error).__name__,
            error_message=str(client_error),
        )
        raise
    finally:
        # 🔧 CLEANUP: Proper client cleanup with connection leak prevention
        logger.info(
            "🔧 CLEANUP: Starting Redis client cleanup",
            client_id=id(client),  # type: ignore
            is_celery_worker=is_celery_worker,
        )

        try:
            await client.aclose()  # type: ignore[attr-defined]
            logger.info(
                "✅ CLEANUP: Redis client closed successfully",
                client_id=id(client),  # type: ignore
                is_celery_worker=is_celery_worker,
            )
        except Exception as cleanup_error:
            logger.warning(
                "⚠️ CLEANUP WARNING: Redis client cleanup error (non-fatal)",
                client_id=id(client),  # type: ignore
                is_celery_worker=is_celery_worker,
                cleanup_error=str(cleanup_error),
            )


async def get_postgres_connection() -> Any:  # type: ignore[misc]
    """Get PostgreSQL connection context manager."""
    return db_manager.get_postgres_connection()  # type: ignore[misc]


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
        # Use context manager version for proper resource management
        async with get_redis_client_context() as client:
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
        async with await get_postgres_connection() as conn:  # type: ignore[misc]
            await conn.execute("SELECT 1")  # type: ignore[attr-defined]
        return True
    except Exception as e:
        logger.error("PostgreSQL health check failed", error=str(e))
        return False


async def check_database_health() -> Dict[str, bool]:
    """Check all database connections health."""
    return {"redis": await check_redis_health(), "postgres": await check_postgres_health()}
