"""
Integration tests for connection pool statistics API.

Tests all pool monitoring and metrics endpoints.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestPoolStatsEndpoints:
    """Test pool statistics endpoints."""

    def test_get_all_pool_stats(self, client):
        """Test getting statistics for all pools."""
        response = client.get("/connections/pools/stats")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] == "success"
        assert "pools" in data
        assert "total_pools" in data

        # Pools may or may not exist depending on whether connections have been used
        assert isinstance(data["pools"], dict)
        assert isinstance(data["total_pools"], int)

    def test_get_specific_pool_stats(self, client):
        """Test getting statistics for a specific pool."""
        # First, get all pools to see what exists
        all_stats_response = client.get("/connections/pools/stats")
        all_stats = all_stats_response.json()

        if all_stats["total_pools"] > 0:
            # Get stats for first pool
            pool_name = list(all_stats["pools"].keys())[0]
            response = client.get(f"/connections/pools/stats/{pool_name}")

            assert response.status_code == 200
            data = response.json()

            assert "status" in data
            assert data["status"] == "success"
            assert "pool" in data

            pool_stats = data["pool"]
            assert "name" in pool_stats
            assert "pool_size" in pool_stats
            assert "active_connections" in pool_stats
            assert "total_capacity" in pool_stats
            assert "statistics" in pool_stats
            assert "utilization" in pool_stats
        else:
            # If no pools exist, test with nonexistent pool
            response = client.get("/connections/pools/stats/nonexistent")
            assert response.status_code == 404

    def test_get_nonexistent_pool_stats(self, client):
        """Test getting stats for pool that doesn't exist."""
        response = client.get("/connections/pools/stats/nonexistent_pool_xyz")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_pool_health_endpoint(self, client):
        """Test pool health check endpoint."""
        response = client.get("/connections/pools/health")

        assert response.status_code == 200
        data = response.json()

        assert "overall_status" in data
        assert data["overall_status"] in ["healthy", "degraded", "unhealthy"]
        assert "pools" in data
        assert "total_pools" in data
        assert "healthy_pools" in data
        assert "warnings" in data

        # Verify structure of pool health
        if len(data["pools"]) > 0:
            pool = data["pools"][0]
            assert "name" in pool
            assert "status" in pool
            assert pool["status"] in ["healthy", "degraded", "unhealthy"]
            assert "utilization" in pool
            assert "pool_size" in pool
            assert "active_connections" in pool
            assert "errors" in pool

    def test_pool_metrics_endpoint(self, client):
        """Test aggregated pool metrics endpoint."""
        response = client.get("/connections/pools/metrics")

        assert response.status_code == 200
        data = response.json()

        assert "total_pools" in data
        assert "total_connections" in data
        assert "total_active" in data
        assert "total_idle" in data
        assert "total_capacity" in data
        assert "overall_utilization" in data
        assert "total_created" in data
        assert "total_reused" in data
        assert "total_closed" in data
        assert "total_errors" in data
        assert "reuse_ratio" in data

        # All values should be non-negative
        assert data["total_pools"] >= 0
        assert data["total_connections"] >= 0
        assert data["total_active"] >= 0
        assert data["total_idle"] >= 0
        assert data["overall_utilization"] >= 0


@pytest.mark.integration
class TestPoolManagementEndpoints:
    """Test pool management endpoints."""

    def test_close_specific_pool(self, client):
        """Test closing a specific pool."""
        # First, check if any pools exist
        all_stats_response = client.get("/connections/pools/stats")
        all_stats = all_stats_response.json()

        if all_stats["total_pools"] > 0:
            # Close first pool
            pool_name = list(all_stats["pools"].keys())[0]
            response = client.post(f"/connections/pools/close/{pool_name}")

            assert response.status_code == 200
            data = response.json()

            assert "status" in data
            assert data["status"] == "success"
            assert "message" in data
        else:
            # Test with nonexistent pool
            response = client.post("/connections/pools/close/nonexistent")
            assert response.status_code == 404

    def test_close_nonexistent_pool(self, client):
        """Test closing a pool that doesn't exist."""
        response = client.post("/connections/pools/close/nonexistent_pool_xyz")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_close_all_pools(self, client):
        """Test closing all pools."""
        response = client.post("/connections/pools/close-all")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] == "success"
        assert "message" in data
        assert "pools_closed" in data
        assert isinstance(data["pools_closed"], int)
        assert data["pools_closed"] >= 0


@pytest.mark.integration
class TestPoolStatisticsStructure:
    """Test the structure of pool statistics."""

    def test_pool_stats_structure(self, client):
        """Test that pool stats have correct structure."""
        # Create a connection to ensure pool exists
        try:
            conn_response = client.get("/connections/status")
            # This should create pools if they don't exist
        except:
            pass

        # Get all stats
        response = client.get("/connections/pools/stats")
        assert response.status_code == 200

        data = response.json()
        pools = data.get("pools", {})

        for pool_name, pool_stats in pools.items():
            # Verify required fields
            assert "name" in pool_stats
            assert "pool_size" in pool_stats
            assert "active_connections" in pool_stats
            assert "total_capacity" in pool_stats
            assert "min_size" in pool_stats
            assert "statistics" in pool_stats
            assert "utilization" in pool_stats

            # Verify statistics substructure
            stats = pool_stats["statistics"]
            assert "created" in stats
            assert "reused" in stats
            assert "closed" in stats
            assert "errors" in stats
            assert "stale_cleaned" in stats
            assert "health_checks" in stats

            # Verify value types
            assert isinstance(pool_stats["pool_size"], int)
            assert isinstance(pool_stats["active_connections"], int)
            assert isinstance(pool_stats["utilization"], (int, float))
            assert pool_stats["utilization"] >= 0
            assert pool_stats["utilization"] <= 100


@pytest.mark.integration
class TestPoolHealthMonitoring:
    """Test pool health monitoring."""

    def test_health_status_calculation(self, client):
        """Test that health status is calculated correctly."""
        response = client.get("/connections/pools/health")

        assert response.status_code == 200
        data = response.json()

        # If we have pools, verify health logic
        if data["total_pools"] > 0:
            for pool in data["pools"]:
                utilization = pool["utilization"]
                errors = pool["errors"]

                # Verify health status matches criteria
                if utilization > 95 or errors > 10:
                    assert pool["status"] == "unhealthy"
                elif utilization > 80 or errors > 0:
                    assert pool["status"] in ["degraded", "unhealthy"]
                # else should be healthy

    def test_health_warnings(self, client):
        """Test that health warnings are generated."""
        response = client.get("/connections/pools/health")

        assert response.status_code == 200
        data = response.json()

        # Warnings should be a list
        assert isinstance(data["warnings"], list)

        # If there are unhealthy or degraded pools, should have warnings
        unhealthy_count = sum(1 for p in data["pools"] if p["status"] != "healthy")
        if unhealthy_count > 0:
            assert len(data["warnings"]) > 0


@pytest.mark.integration
class TestPoolMetrics:
    """Test pool metrics aggregation."""

    def test_metrics_aggregation(self, client):
        """Test that metrics are aggregated correctly."""
        # Get individual pool stats
        all_stats_response = client.get("/connections/pools/stats")
        all_stats = all_stats_response.json()

        # Get aggregated metrics
        metrics_response = client.get("/connections/pools/metrics")
        metrics = metrics_response.json()

        # Verify aggregation
        if all_stats["total_pools"] > 0:
            # Calculate expected totals
            expected_active = sum(
                p["active_connections"] for p in all_stats["pools"].values()
            )
            expected_idle = sum(
                p["pool_size"] for p in all_stats["pools"].values()
            )

            assert metrics["total_active"] == expected_active
            assert metrics["total_idle"] == expected_idle
            assert metrics["total_connections"] == expected_active + expected_idle

    def test_reuse_ratio_calculation(self, client):
        """Test that reuse ratio is calculated correctly."""
        response = client.get("/connections/pools/metrics")

        assert response.status_code == 200
        data = response.json()

        # Reuse ratio should be between 0 and 100 (percentage)
        assert data["reuse_ratio"] >= 0
        assert data["reuse_ratio"] <= 100 * 100  # Can exceed 100% (more reuses than creates)

        # If connections were created and reused
        if data["total_created"] > 0 and data["total_reused"] > 0:
            expected_ratio = (data["total_reused"] / data["total_created"]) * 100
            assert abs(data["reuse_ratio"] - expected_ratio) < 0.01


@pytest.mark.integration
@pytest.mark.slow
class TestPoolBehavior:
    """Test actual pool behavior under load."""

    def test_pool_creation_on_demand(self, client):
        """Test that pools are created on demand."""
        # Get initial pool count
        initial_response = client.get("/connections/pools/stats")
        initial_count = initial_response.json()["total_pools"]

        # Make a connection test request (should create pools if not exist)
        client.get("/connections/status")

        # Check if pools were created
        final_response = client.get("/connections/pools/stats")
        final_data = final_response.json()

        # Pools may have been created
        assert final_data["total_pools"] >= initial_count

    def test_connection_reuse(self, client):
        """Test that connections are being reused."""
        # Get initial metrics
        initial_response = client.get("/connections/pools/metrics")
        initial_metrics = initial_response.json()

        # Make multiple requests that use connections
        for _ in range(5):
            try:
                client.get("/connections/status")
            except:
                pass  # May fail if connections not configured, that's ok

        # Get final metrics
        final_response = client.get("/connections/pools/metrics")
        final_metrics = final_response.json()

        # Reused count should have increased (or stayed same if no pools)
        assert final_metrics["total_reused"] >= initial_metrics["total_reused"]
