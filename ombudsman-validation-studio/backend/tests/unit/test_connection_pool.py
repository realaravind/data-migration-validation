"""
Unit tests for connection pooling functionality.

Tests ConnectionPool, PooledConnection, and ConnectionPoolManager classes.
"""

import pytest
import time
import threading
from datetime import datetime
from queue import Empty
import sys
import os

# Add ombudsman_core to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../ombudsman_core/src")))

from ombudsman.core.connection_pool import (
    PooledConnection,
    ConnectionPool,
    ConnectionPoolManager,
    pool_manager
)


class MockConnection:
    """Mock database connection for testing"""

    def __init__(self, should_fail=False):
        self.closed = False
        self.should_fail = should_fail

    def cursor(self):
        if self.should_fail:
            raise Exception("Mock cursor error")
        return MockCursor()

    def close(self):
        self.closed = True


class MockCursor:
    """Mock database cursor for testing"""

    def close(self):
        pass


@pytest.mark.unit
class TestPooledConnection:
    """Test PooledConnection wrapper class."""

    def test_pooled_connection_creation(self):
        """Test creating a pooled connection."""
        mock_conn = MockConnection()
        pooled = PooledConnection(mock_conn, "test_pool")

        assert pooled.connection == mock_conn
        assert pooled.pool_name == "test_pool"
        assert pooled.times_used == 0
        assert pooled.is_healthy is True
        assert isinstance(pooled.created_at, datetime)
        assert isinstance(pooled.last_used, datetime)

    def test_mark_used(self):
        """Test marking connection as used."""
        mock_conn = MockConnection()
        pooled = PooledConnection(mock_conn, "test_pool")

        initial_last_used = pooled.last_used
        time.sleep(0.01)

        pooled.mark_used()

        assert pooled.times_used == 1
        assert pooled.last_used > initial_last_used

        pooled.mark_used()
        assert pooled.times_used == 2

    def test_is_stale(self):
        """Test stale connection detection."""
        mock_conn = MockConnection()
        pooled = PooledConnection(mock_conn, "test_pool")

        # Fresh connection should not be stale
        assert pooled.is_stale(max_age_seconds=3600) is False

        # Set last_used to old time
        old_time = datetime.now()
        old_time = old_time.replace(year=old_time.year - 1)
        pooled.last_used = old_time

        # Should now be stale
        assert pooled.is_stale(max_age_seconds=3600) is True

    def test_age_seconds(self):
        """Test age calculation."""
        mock_conn = MockConnection()
        pooled = PooledConnection(mock_conn, "test_pool")

        time.sleep(0.1)
        age = pooled.age_seconds()

        assert age >= 0.1
        assert age < 1.0


@pytest.mark.unit
class TestConnectionPool:
    """Test ConnectionPool class."""

    def test_pool_creation(self):
        """Test creating a connection pool."""
        pool = ConnectionPool(
            name="test_pool",
            connection_factory=lambda: MockConnection(),
            min_size=2,
            max_size=5
        )

        assert pool.name == "test_pool"
        assert pool.min_size == 2
        assert pool.max_size == 5

        # Should have created min_size connections
        stats = pool.get_stats()
        assert stats["pool_size"] >= 2
        assert stats["pool_size"] <= pool.min_size

        # Cleanup
        pool.close_all()

    def test_get_connection(self):
        """Test getting connection from pool."""
        pool = ConnectionPool(
            name="test_pool",
            connection_factory=lambda: MockConnection(),
            min_size=1,
            max_size=5
        )

        # Get connection
        with pool.get_connection() as conn:
            assert conn is not None
            assert isinstance(conn, MockConnection)

        # Connection should be returned to pool
        stats = pool.get_stats()
        assert stats["active_connections"] == 0

        # Cleanup
        pool.close_all()

    def test_connection_reuse(self):
        """Test that connections are reused."""
        pool = ConnectionPool(
            name="test_pool",
            connection_factory=lambda: MockConnection(),
            min_size=1,
            max_size=5
        )

        # Get and return connection multiple times
        for i in range(5):
            with pool.get_connection() as conn:
                pass

        stats = pool.get_stats()
        # Should have reused connections
        assert stats["statistics"]["reused"] > 0

        # Cleanup
        pool.close_all()

    def test_multiple_concurrent_connections(self):
        """Test getting multiple connections concurrently."""
        pool = ConnectionPool(
            name="test_pool",
            connection_factory=lambda: MockConnection(),
            min_size=2,
            max_size=5
        )

        connections = []

        # Get multiple connections
        for _ in range(3):
            pooled = pool._get()
            connections.append(pooled)

        stats = pool.get_stats()
        assert stats["active_connections"] == 3

        # Return connections
        for conn in connections:
            pool._put(conn)

        stats = pool.get_stats()
        assert stats["active_connections"] == 0

        # Cleanup
        pool.close_all()

    def test_max_size_limit(self):
        """Test that pool respects max_size."""
        pool = ConnectionPool(
            name="test_pool",
            connection_factory=lambda: MockConnection(),
            min_size=1,
            max_size=3,
            connection_timeout=1  # 1 second timeout
        )

        connections = []

        # Get max_size connections
        for _ in range(3):
            conn = pool._get()
            connections.append(conn)

        # Trying to get another should timeout
        with pytest.raises(TimeoutError):
            pool._get()

        # Return one connection
        pool._put(connections[0])

        # Now should be able to get another
        conn = pool._get()
        assert conn is not None

        # Cleanup
        for c in connections[1:]:
            pool._put(c)
        pool._put(conn)
        pool.close_all()

    def test_health_check(self):
        """Test connection health checking."""
        pool = ConnectionPool(
            name="test_pool",
            connection_factory=lambda: MockConnection(),
            min_size=1,
            max_size=5
        )

        # Get a connection
        pooled = pool._get()

        # Should be healthy
        assert pool._is_connection_healthy(pooled) is True

        # Mark as unhealthy
        pooled.connection.should_fail = True

        # Should detect unhealthy connection
        assert pool._is_connection_healthy(pooled) is False

        # Cleanup
        pool.close_all()

    def test_stale_connection_cleanup(self):
        """Test that stale connections are cleaned up."""
        pool = ConnectionPool(
            name="test_pool",
            connection_factory=lambda: MockConnection(),
            min_size=1,
            max_size=5,
            max_age_seconds=1  # 1 second max age
        )

        # Get connection
        pooled = pool._get()

        # Make it stale
        old_time = datetime.now()
        old_time = old_time.replace(year=old_time.year - 1)
        pooled.last_used = old_time

        # Try to return it - should be closed instead
        initial_stats = pool.get_stats()
        pool._put(pooled)

        # Connection should have been closed (not returned to pool)
        stats = pool.get_stats()
        assert stats["statistics"]["stale_cleaned"] > initial_stats["statistics"]["stale_cleaned"]

        # Cleanup
        pool.close_all()

    def test_pool_statistics(self):
        """Test pool statistics collection."""
        pool = ConnectionPool(
            name="test_pool",
            connection_factory=lambda: MockConnection(),
            min_size=2,
            max_size=5
        )

        stats = pool.get_stats()

        assert "name" in stats
        assert "pool_size" in stats
        assert "active_connections" in stats
        assert "total_capacity" in stats
        assert "statistics" in stats
        assert "utilization" in stats

        assert stats["name"] == "test_pool"
        assert stats["total_capacity"] == 5
        assert stats["min_size"] == 2

        # Cleanup
        pool.close_all()

    def test_close_all(self):
        """Test closing all connections in pool."""
        pool = ConnectionPool(
            name="test_pool",
            connection_factory=lambda: MockConnection(),
            min_size=2,
            max_size=5
        )

        # Get some connections
        conn1 = pool._get()
        conn2 = pool._get()

        # Close all
        pool.close_all()

        stats = pool.get_stats()
        assert stats["pool_size"] == 0
        assert stats["active_connections"] == 0


@pytest.mark.unit
class TestConnectionPoolManager:
    """Test ConnectionPoolManager singleton."""

    def test_singleton_pattern(self):
        """Test that ConnectionPoolManager is a singleton."""
        manager1 = ConnectionPoolManager()
        manager2 = ConnectionPoolManager()

        assert manager1 is manager2

    def test_get_or_create_pool(self):
        """Test getting or creating pools."""
        manager = ConnectionPoolManager()

        # Create first pool
        pool1 = manager.get_or_create_pool(
            name="test_pool_1",
            connection_factory=lambda: MockConnection(),
            min_size=1,
            max_size=5
        )

        assert pool1.name == "test_pool_1"

        # Get same pool again
        pool2 = manager.get_or_create_pool(
            name="test_pool_1",
            connection_factory=lambda: MockConnection()
        )

        # Should be the same instance
        assert pool1 is pool2

        # Create different pool
        pool3 = manager.get_or_create_pool(
            name="test_pool_2",
            connection_factory=lambda: MockConnection()
        )

        assert pool3.name == "test_pool_2"
        assert pool3 is not pool1

        # Cleanup
        manager.close_all_pools()

    def test_get_pool(self):
        """Test getting existing pool."""
        manager = ConnectionPoolManager()

        # Create pool
        pool = manager.get_or_create_pool(
            name="test_pool",
            connection_factory=lambda: MockConnection()
        )

        # Get pool
        retrieved = manager.get_pool("test_pool")
        assert retrieved is pool

        # Get non-existent pool
        none_pool = manager.get_pool("nonexistent")
        assert none_pool is None

        # Cleanup
        manager.close_all_pools()

    def test_get_all_stats(self):
        """Test getting statistics for all pools."""
        manager = ConnectionPoolManager()

        # Create multiple pools
        pool1 = manager.get_or_create_pool(
            name="pool_1",
            connection_factory=lambda: MockConnection()
        )

        pool2 = manager.get_or_create_pool(
            name="pool_2",
            connection_factory=lambda: MockConnection()
        )

        # Get all stats
        all_stats = manager.get_all_stats()

        assert "pool_1" in all_stats
        assert "pool_2" in all_stats
        assert all_stats["pool_1"]["name"] == "pool_1"
        assert all_stats["pool_2"]["name"] == "pool_2"

        # Cleanup
        manager.close_all_pools()

    def test_close_all_pools(self):
        """Test closing all pools."""
        manager = ConnectionPoolManager()

        # Create pools
        pool1 = manager.get_or_create_pool("pool_1", lambda: MockConnection())
        pool2 = manager.get_or_create_pool("pool_2", lambda: MockConnection())

        # Close all
        manager.close_all_pools()

        # Pools should be cleared
        all_stats = manager.get_all_stats()
        assert len(all_stats) == 0


@pytest.mark.unit
class TestThreadSafety:
    """Test thread safety of connection pool."""

    def test_concurrent_get_connections(self):
        """Test getting connections from multiple threads."""
        pool = ConnectionPool(
            name="test_pool",
            connection_factory=lambda: MockConnection(),
            min_size=2,
            max_size=10
        )

        results = []
        errors = []

        def get_and_use_connection():
            try:
                with pool.get_connection() as conn:
                    time.sleep(0.01)  # Simulate work
                    results.append(conn)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=get_and_use_connection)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All threads should have succeeded
        assert len(errors) == 0
        assert len(results) == 20

        # Pool should be healthy
        stats = pool.get_stats()
        assert stats["active_connections"] == 0

        # Cleanup
        pool.close_all()


@pytest.mark.unit
class TestGlobalPoolManager:
    """Test the global pool_manager instance."""

    def test_global_pool_manager(self):
        """Test using the global pool_manager."""
        # Should be able to access global instance
        assert pool_manager is not None
        assert isinstance(pool_manager, ConnectionPoolManager)

        # Create pool using global instance
        pool = pool_manager.get_or_create_pool(
            name="global_test_pool",
            connection_factory=lambda: MockConnection()
        )

        assert pool.name == "global_test_pool"

        # Cleanup
        pool_manager.close_all_pools()
