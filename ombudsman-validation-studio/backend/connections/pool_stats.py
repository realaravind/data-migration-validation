"""
Connection Pool Statistics and Monitoring API.

Provides endpoints for monitoring connection pool health, statistics, and metrics.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import sys
import os

# Add ombudsman_core to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../ombudsman_core/src")))

from ombudsman.core.connection_pool import pool_manager

router = APIRouter(prefix="/pools", tags=["Connection Pools"])


@router.get("/stats", response_model=Dict[str, Any])
async def get_all_pool_stats():
    """
    Get statistics for all connection pools.

    Returns:
        Dictionary mapping pool name to statistics:
        - name: Pool name
        - pool_size: Number of idle connections
        - active_connections: Number of connections in use
        - total_capacity: Maximum pool size
        - min_size: Minimum pool size
        - statistics: Usage statistics (created, reused, closed, errors, etc.)
        - utilization: Percentage of pool in use

    Example:
        {
            "sqlserver": {
                "name": "sqlserver",
                "pool_size": 3,
                "active_connections": 2,
                "total_capacity": 10,
                "min_size": 2,
                "statistics": {
                    "created": 5,
                    "reused": 127,
                    "closed": 0,
                    "errors": 0,
                    "stale_cleaned": 0,
                    "health_checks": 0
                },
                "utilization": 20.0
            },
            "snowflake": {...}
        }
    """
    try:
        stats = pool_manager.get_all_stats()
        return {
            "status": "success",
            "pools": stats,
            "total_pools": len(stats)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve pool statistics: {str(e)}"
        )


@router.get("/stats/{pool_name}", response_model=Dict[str, Any])
async def get_pool_stats(pool_name: str):
    """
    Get statistics for a specific connection pool.

    Args:
        pool_name: Name of the pool (e.g., "sqlserver", "snowflake")

    Returns:
        Pool statistics dictionary

    Raises:
        404: If pool not found
    """
    try:
        pool = pool_manager.get_pool(pool_name)
        if pool is None:
            raise HTTPException(
                status_code=404,
                detail=f"Pool '{pool_name}' not found"
            )

        stats = pool.get_stats()
        return {
            "status": "success",
            "pool": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve pool statistics: {str(e)}"
        )


@router.get("/health", response_model=Dict[str, Any])
async def get_pool_health():
    """
    Get health status of all connection pools.

    Returns:
        Health summary with overall status and individual pool health:
        - overall_status: "healthy", "degraded", or "unhealthy"
        - pools: List of pool health summaries
        - total_pools: Number of pools
        - healthy_pools: Number of healthy pools
        - warnings: List of warnings

    A pool is considered:
    - Healthy: Utilization < 80%, no recent errors
    - Degraded: Utilization 80-95%, or some errors
    - Unhealthy: Utilization > 95%, or many errors
    """
    try:
        all_stats = pool_manager.get_all_stats()

        pool_health = []
        healthy_count = 0
        warnings = []

        for pool_name, stats in all_stats.items():
            utilization = stats.get("utilization", 0)
            errors = stats.get("statistics", {}).get("errors", 0)
            pool_size = stats.get("pool_size", 0)
            min_size = stats.get("min_size", 0)

            # Determine health status
            if utilization > 95 or errors > 10:
                health = "unhealthy"
                warnings.append(f"Pool '{pool_name}' is unhealthy (utilization: {utilization:.1f}%, errors: {errors})")
            elif utilization > 80 or errors > 0:
                health = "degraded"
                warnings.append(f"Pool '{pool_name}' is degraded (utilization: {utilization:.1f}%, errors: {errors})")
            else:
                health = "healthy"
                healthy_count += 1

            # Check if pool is below minimum size
            if pool_size < min_size:
                warnings.append(f"Pool '{pool_name}' below minimum size ({pool_size} < {min_size})")

            pool_health.append({
                "name": pool_name,
                "status": health,
                "utilization": utilization,
                "pool_size": pool_size,
                "active_connections": stats.get("active_connections", 0),
                "errors": errors
            })

        # Determine overall status
        if healthy_count == len(all_stats):
            overall_status = "healthy"
        elif healthy_count > 0:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

        return {
            "overall_status": overall_status,
            "pools": pool_health,
            "total_pools": len(all_stats),
            "healthy_pools": healthy_count,
            "warnings": warnings
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve pool health: {str(e)}"
        )


@router.post("/close/{pool_name}")
async def close_pool(pool_name: str):
    """
    Close all connections in a specific pool.

    Args:
        pool_name: Name of the pool to close

    Returns:
        Success message

    Raises:
        404: If pool not found
    """
    try:
        pool = pool_manager.get_pool(pool_name)
        if pool is None:
            raise HTTPException(
                status_code=404,
                detail=f"Pool '{pool_name}' not found"
            )

        pool.close_all()

        return {
            "status": "success",
            "message": f"All connections in pool '{pool_name}' have been closed"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to close pool: {str(e)}"
        )


@router.post("/close-all")
async def close_all_pools():
    """
    Close all connections in all pools.

    Returns:
        Success message with count of pools closed
    """
    try:
        all_stats = pool_manager.get_all_stats()
        pool_count = len(all_stats)

        pool_manager.close_all_pools()

        return {
            "status": "success",
            "message": f"All connections in {pool_count} pools have been closed",
            "pools_closed": pool_count
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to close pools: {str(e)}"
        )


@router.get("/metrics", response_model=Dict[str, Any])
async def get_pool_metrics():
    """
    Get aggregated metrics across all pools.

    Returns:
        Aggregated metrics:
        - total_pools: Number of pools
        - total_connections: Total connections (idle + active)
        - total_active: Total active connections
        - total_idle: Total idle connections
        - total_capacity: Total maximum capacity
        - overall_utilization: Average utilization percentage
        - total_created: Total connections created
        - total_reused: Total connection reuses
        - total_closed: Total connections closed
        - total_errors: Total errors
        - reuse_ratio: Ratio of reused to created connections
    """
    try:
        all_stats = pool_manager.get_all_stats()

        total_pools = len(all_stats)
        total_active = 0
        total_idle = 0
        total_capacity = 0
        total_created = 0
        total_reused = 0
        total_closed = 0
        total_errors = 0
        total_utilization = 0

        for stats in all_stats.values():
            total_active += stats.get("active_connections", 0)
            total_idle += stats.get("pool_size", 0)
            total_capacity += stats.get("total_capacity", 0)
            total_utilization += stats.get("utilization", 0)

            statistics = stats.get("statistics", {})
            total_created += statistics.get("created", 0)
            total_reused += statistics.get("reused", 0)
            total_closed += statistics.get("closed", 0)
            total_errors += statistics.get("errors", 0)

        avg_utilization = total_utilization / total_pools if total_pools > 0 else 0
        reuse_ratio = total_reused / total_created if total_created > 0 else 0

        return {
            "total_pools": total_pools,
            "total_connections": total_active + total_idle,
            "total_active": total_active,
            "total_idle": total_idle,
            "total_capacity": total_capacity,
            "overall_utilization": avg_utilization,
            "total_created": total_created,
            "total_reused": total_reused,
            "total_closed": total_closed,
            "total_errors": total_errors,
            "reuse_ratio": reuse_ratio * 100  # As percentage
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve pool metrics: {str(e)}"
        )
