"""
Database Connection Pool Manager

Provides connection pooling for SQL Server and Snowflake connections:
- Configurable pool size
- Connection health monitoring
- Automatic stale connection cleanup
- Connection timeout handling
- Pool statistics and metrics
- Thread-safe operations
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from queue import Queue, Empty
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PooledConnection:
    """Wrapper for a pooled database connection with metadata"""

    def __init__(self, connection, pool_name: str):
        """
        Initialize pooled connection.

        Args:
            connection: Raw database connection
            pool_name: Name of the pool this connection belongs to
        """
        self.connection = connection
        self.pool_name = pool_name
        self.created_at = datetime.now()
        self.last_used = datetime.now()
        self.times_used = 0
        self.is_healthy = True

    def mark_used(self):
        """Mark connection as used and update timestamp"""
        self.last_used = datetime.now()
        self.times_used += 1

    def is_stale(self, max_age_seconds: int = 3600) -> bool:
        """
        Check if connection is stale.

        Args:
            max_age_seconds: Maximum age in seconds before considering stale

        Returns:
            True if connection is stale
        """
        age = (datetime.now() - self.last_used).total_seconds()
        return age > max_age_seconds

    def age_seconds(self) -> float:
        """Get connection age in seconds"""
        return (datetime.now() - self.created_at).total_seconds()


class ConnectionPool:
    """
    Connection pool for database connections.

    Features:
    - Minimum and maximum pool size
    - Connection reuse
    - Health checking
    - Stale connection cleanup
    - Connection timeout
    - Thread-safe operations
    """

    def __init__(
        self,
        name: str,
        connection_factory: Callable,
        min_size: int = 2,
        max_size: int = 10,
        max_age_seconds: int = 3600,
        health_check_interval: int = 300,
        connection_timeout: int = 30
    ):
        """
        Initialize connection pool.

        Args:
            name: Pool identifier
            connection_factory: Function that creates new connections
            min_size: Minimum number of connections to maintain
            max_size: Maximum number of connections allowed
            max_age_seconds: Maximum connection age before renewal
            health_check_interval: Seconds between health checks
            connection_timeout: Seconds to wait for available connection
        """
        self.name = name
        self.connection_factory = connection_factory
        self.min_size = min_size
        self.max_size = max_size
        self.max_age_seconds = max_age_seconds
        self.health_check_interval = health_check_interval
        self.connection_timeout = connection_timeout

        # Pool storage
        self._pool: Queue[PooledConnection] = Queue(maxsize=max_size)
        self._active_connections: Dict[int, PooledConnection] = {}
        self._lock = threading.RLock()

        # Statistics
        self._stats = {
            "created": 0,
            "reused": 0,
            "closed": 0,
            "errors": 0,
            "stale_cleaned": 0,
            "health_checks": 0
        }

        # Initialize minimum connections
        self._initialize_pool()

        # Start background cleanup thread
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name=f"{name}_cleanup"
        )
        self._cleanup_thread.start()

        logger.info(
            f"Connection pool '{name}' initialized: "
            f"min={min_size}, max={max_size}, max_age={max_age_seconds}s"
        )

    def _initialize_pool(self):
        """Create minimum number of connections"""
        for _ in range(self.min_size):
            try:
                conn = self._create_connection()
                self._pool.put(conn, block=False)
            except Exception as e:
                logger.error(f"Failed to initialize connection in pool '{self.name}': {e}")

    def _create_connection(self) -> PooledConnection:
        """
        Create a new pooled connection.

        Returns:
            PooledConnection: New pooled connection

        Raises:
            Exception: If connection creation fails
        """
        try:
            raw_conn = self.connection_factory()
            pooled_conn = PooledConnection(raw_conn, self.name)
            with self._lock:
                self._stats["created"] += 1
            logger.debug(f"Created new connection in pool '{self.name}'")
            return pooled_conn
        except Exception as e:
            with self._lock:
                self._stats["errors"] += 1
            logger.error(f"Failed to create connection in pool '{self.name}': {e}")
            raise

    def _is_connection_healthy(self, pooled_conn: PooledConnection) -> bool:
        """
        Check if connection is healthy.

        Args:
            pooled_conn: Pooled connection to check

        Returns:
            True if connection is healthy
        """
        try:
            # Simple health check: try to get a cursor
            cursor = pooled_conn.connection.cursor()
            cursor.close()
            return True
        except Exception as e:
            logger.warning(
                f"Connection health check failed in pool '{self.name}': {e}"
            )
            pooled_conn.is_healthy = False
            return False

    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool (context manager).

        Yields:
            Database connection

        Example:
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
        """
        pooled_conn = None
        try:
            pooled_conn = self._get()
            yield pooled_conn.connection
        finally:
            if pooled_conn:
                self._put(pooled_conn)

    def _get(self) -> PooledConnection:
        """
        Get a connection from the pool.

        Returns:
            PooledConnection: Connection from pool

        Raises:
            TimeoutError: If no connection available within timeout
        """
        start_time = time.time()

        while True:
            # Try to get existing connection from pool
            try:
                pooled_conn = self._pool.get(block=False)

                # Check if connection is healthy and not stale
                if pooled_conn.is_stale(self.max_age_seconds):
                    logger.debug(f"Closing stale connection in pool '{self.name}'")
                    self._close_connection(pooled_conn)
                    with self._lock:
                        self._stats["stale_cleaned"] += 1
                    continue

                if not self._is_connection_healthy(pooled_conn):
                    logger.debug(f"Closing unhealthy connection in pool '{self.name}'")
                    self._close_connection(pooled_conn)
                    continue

                # Connection is good, mark as used
                pooled_conn.mark_used()
                with self._lock:
                    self._stats["reused"] += 1
                    self._active_connections[id(pooled_conn)] = pooled_conn

                logger.debug(
                    f"Reusing connection from pool '{self.name}' "
                    f"(used {pooled_conn.times_used} times)"
                )
                return pooled_conn

            except Empty:
                # Pool is empty, check if we can create new connection
                with self._lock:
                    current_size = self._pool.qsize() + len(self._active_connections)

                if current_size < self.max_size:
                    # Create new connection
                    pooled_conn = self._create_connection()
                    pooled_conn.mark_used()
                    with self._lock:
                        self._active_connections[id(pooled_conn)] = pooled_conn
                    return pooled_conn

                # Pool is at max size, wait for a connection
                elapsed = time.time() - start_time
                if elapsed >= self.connection_timeout:
                    raise TimeoutError(
                        f"Timeout waiting for connection from pool '{self.name}' "
                        f"after {self.connection_timeout}s"
                    )

                # Wait a bit and try again
                time.sleep(0.1)

    def _put(self, pooled_conn: PooledConnection):
        """
        Return a connection to the pool.

        Args:
            pooled_conn: Connection to return
        """
        with self._lock:
            if id(pooled_conn) in self._active_connections:
                del self._active_connections[id(pooled_conn)]

        # Check if connection is still healthy
        if not pooled_conn.is_healthy or not self._is_connection_healthy(pooled_conn):
            logger.debug(f"Not returning unhealthy connection to pool '{self.name}'")
            self._close_connection(pooled_conn)
            return

        # Check if connection is stale
        if pooled_conn.is_stale(self.max_age_seconds):
            logger.debug(f"Not returning stale connection to pool '{self.name}'")
            self._close_connection(pooled_conn)
            with self._lock:
                self._stats["stale_cleaned"] += 1
            return

        # Return to pool
        try:
            self._pool.put(pooled_conn, block=False)
            logger.debug(f"Returned connection to pool '{self.name}'")
        except:
            # Pool is full, close the connection
            logger.debug(f"Pool '{self.name}' is full, closing connection")
            self._close_connection(pooled_conn)

    def _close_connection(self, pooled_conn: PooledConnection):
        """
        Close a pooled connection.

        Args:
            pooled_conn: Connection to close
        """
        try:
            pooled_conn.connection.close()
            with self._lock:
                self._stats["closed"] += 1
            logger.debug(f"Closed connection in pool '{self.name}'")
        except Exception as e:
            logger.warning(f"Error closing connection in pool '{self.name}': {e}")

    def _cleanup_loop(self):
        """Background thread for cleaning up stale connections"""
        while True:
            try:
                time.sleep(self.health_check_interval)
                self._cleanup_stale_connections()
                self._ensure_minimum_size()
            except Exception as e:
                logger.error(f"Error in cleanup loop for pool '{self.name}': {e}")

    def _cleanup_stale_connections(self):
        """Remove stale connections from pool"""
        to_remove = []

        # Check pooled connections
        temp_conns = []
        while not self._pool.empty():
            try:
                conn = self._pool.get(block=False)
                if conn.is_stale(self.max_age_seconds):
                    to_remove.append(conn)
                else:
                    temp_conns.append(conn)
            except Empty:
                break

        # Put back non-stale connections
        for conn in temp_conns:
            try:
                self._pool.put(conn, block=False)
            except:
                to_remove.append(conn)

        # Close stale connections
        for conn in to_remove:
            self._close_connection(conn)
            with self._lock:
                self._stats["stale_cleaned"] += 1

        if to_remove:
            logger.info(
                f"Cleaned up {len(to_remove)} stale connections from pool '{self.name}'"
            )

    def _ensure_minimum_size(self):
        """Ensure pool has minimum number of connections"""
        current_size = self._pool.qsize()
        if current_size < self.min_size:
            needed = self.min_size - current_size
            for _ in range(needed):
                try:
                    conn = self._create_connection()
                    self._pool.put(conn, block=False)
                except Exception as e:
                    logger.error(
                        f"Failed to create connection for min size in pool '{self.name}': {e}"
                    )
                    break

    def get_stats(self) -> Dict[str, Any]:
        """
        Get pool statistics.

        Returns:
            Dictionary with pool statistics
        """
        with self._lock:
            return {
                "name": self.name,
                "pool_size": self._pool.qsize(),
                "active_connections": len(self._active_connections),
                "total_capacity": self.max_size,
                "min_size": self.min_size,
                "statistics": self._stats.copy(),
                "utilization": len(self._active_connections) / self.max_size * 100
            }

    def close_all(self):
        """Close all connections in the pool"""
        # Close pooled connections
        while not self._pool.empty():
            try:
                conn = self._pool.get(block=False)
                self._close_connection(conn)
            except Empty:
                break

        # Close active connections
        with self._lock:
            for conn in list(self._active_connections.values()):
                self._close_connection(conn)
            self._active_connections.clear()

        logger.info(f"Closed all connections in pool '{self.name}'")


class ConnectionPoolManager:
    """
    Manages multiple connection pools.

    Singleton pattern to ensure one pool per database type.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._pools = {}
        return cls._instance

    def get_or_create_pool(
        self,
        name: str,
        connection_factory: Callable,
        **pool_kwargs
    ) -> ConnectionPool:
        """
        Get existing pool or create new one.

        Args:
            name: Pool name
            connection_factory: Function to create connections
            **pool_kwargs: Additional pool configuration

        Returns:
            ConnectionPool: The connection pool
        """
        if name not in self._pools:
            with self._lock:
                if name not in self._pools:
                    self._pools[name] = ConnectionPool(
                        name,
                        connection_factory,
                        **pool_kwargs
                    )
        return self._pools[name]

    def get_pool(self, name: str) -> Optional[ConnectionPool]:
        """
        Get existing pool by name.

        Args:
            name: Pool name

        Returns:
            ConnectionPool or None if not found
        """
        return self._pools.get(name)

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all pools.

        Returns:
            Dictionary mapping pool name to statistics
        """
        return {name: pool.get_stats() for name, pool in self._pools.items()}

    def close_all_pools(self):
        """Close all connection pools"""
        for pool in self._pools.values():
            pool.close_all()
        self._pools.clear()
        logger.info("Closed all connection pools")


# Global pool manager instance
pool_manager = ConnectionPoolManager()
