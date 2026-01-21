"""
Enhanced Custom Query Results API

Advanced endpoints for managing, analyzing, and exporting query results.
"""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging

from .result_handler import (
    ResultComparator,
    ResultExporter,
    QueryResultHistory,
    PerformanceAnalyzer
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize components
result_history = QueryResultHistory()


class CompareResultsRequest(BaseModel):
    sql_results: List[Dict[str, Any]]
    snow_results: List[Dict[str, Any]]
    comparison_type: str = "rowset"  # aggregation, rowset, count
    tolerance: float = 0.01
    key_columns: Optional[List[str]] = None


class ExportRequest(BaseModel):
    results: List[Dict[str, Any]]
    format: str = "json"  # json, csv


class TrendAnalysisRequest(BaseModel):
    query_name: str
    days: int = 7


@router.post("/compare")
def compare_results(request: CompareResultsRequest):
    """
    Advanced result comparison with detailed diffing.

    Features:
    - Row-level comparison with key matching
    - Column-level difference analysis
    - Statistical difference metrics
    - Type-aware value comparison
    - Levenshtein distance for string differences
    """
    try:
        comparator = ResultComparator(tolerance=request.tolerance)

        comparison = comparator.compare_results(
            sql_results=request.sql_results,
            snow_results=request.snow_results,
            comparison_type=request.comparison_type,
            key_columns=request.key_columns
        )

        return {
            "status": "success",
            "comparison": comparison,
            "summary": {
                "match": comparison.get("match", False),
                "comparison_type": comparison.get("comparison_type"),
                "sql_rows": len(request.sql_results),
                "snow_rows": len(request.snow_results)
            }
        }

    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.post("/export")
def export_results(request: ExportRequest):
    """
    Export query results in various formats.

    Supported formats:
    - json: Structured JSON export
    - csv: Tabular CSV export
    """
    try:
        if request.format == "json":
            content = ResultExporter.export_to_json(request.results)
            media_type = "application/json"
            filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        elif request.format == "csv":
            content = ResultExporter.export_to_csv(request.results)
            media_type = "text/csv"
            filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")

        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/history")
def list_result_history(
    query_name: Optional[str] = None,
    limit: int = 100
):
    """
    List query execution history.

    Returns historical query executions with:
    - Execution timestamps
    - Pass/fail status
    - Comparison results
    """
    try:
        results = result_history.list_results(
            query_name=query_name,
            limit=limit
        )

        return {
            "status": "success",
            "count": len(results),
            "results": results
        }

    except Exception as e:
        logger.error(f"Failed to list history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list history: {str(e)}")


@router.get("/history/{result_id}")
def get_result_detail(result_id: str):
    """
    Get detailed results for a specific execution.

    Returns complete query execution details including:
    - Full result sets
    - Comparison analysis
    - Performance metrics
    """
    try:
        result = result_history.get_result(result_id)

        if not result:
            raise HTTPException(status_code=404, detail=f"Result not found: {result_id}")

        return {
            "status": "success",
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get result: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get result: {str(e)}")


@router.post("/history/save")
def save_query_result(
    query_name: str,
    sql_query: str,
    snow_query: str,
    result: Dict[str, Any],
    comparison: Dict[str, Any]
):
    """
    Save query execution result to history.

    Stores:
    - Query definition
    - Execution results
    - Comparison analysis
    - Timestamp and metadata
    """
    try:
        query_hash = QueryResultHistory.calculate_query_hash(sql_query, snow_query)

        result_id = result_history.save_result(
            query_name=query_name,
            query_hash=query_hash,
            result=result,
            comparison=comparison
        )

        return {
            "status": "success",
            "result_id": result_id,
            "message": f"Result saved with ID: {result_id}"
        }

    except Exception as e:
        logger.error(f"Failed to save result: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save result: {str(e)}")


@router.post("/analyze/trend")
def analyze_trend(request: TrendAnalysisRequest):
    """
    Analyze query result trends over time.

    Provides:
    - Pass/fail statistics
    - Trend analysis
    - Historical comparison
    - Performance trends
    """
    try:
        analysis = result_history.get_trend_analysis(
            query_name=request.query_name,
            days=request.days
        )

        return {
            "status": "success",
            "analysis": analysis
        }

    except Exception as e:
        logger.error(f"Trend analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trend analysis failed: {str(e)}")


@router.post("/analyze/performance")
def analyze_performance(
    sql_duration: float,
    snow_duration: float,
    sql_row_count: int,
    snow_row_count: int
):
    """
    Analyze query execution performance.

    Returns:
    - Execution time comparison
    - Throughput metrics
    - Performance categorization
    - Recommendations
    """
    try:
        analysis = PerformanceAnalyzer.analyze_execution(
            sql_duration=sql_duration,
            snow_duration=snow_duration,
            sql_row_count=sql_row_count,
            snow_row_count=snow_row_count
        )

        # Add recommendations
        recommendations = []
        if analysis["performance_category"] in ["slow", "very_slow"]:
            recommendations.append("Consider adding indexes on JOIN columns")
            recommendations.append("Review query execution plans")
            recommendations.append("Check for full table scans")

        if analysis["speed_ratio"] > 2:
            recommendations.append(f"{analysis['faster_system']} is significantly faster - investigate slower system")

        analysis["recommendations"] = recommendations

        return {
            "status": "success",
            "analysis": analysis
        }

    except Exception as e:
        logger.error(f"Performance analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Performance analysis failed: {str(e)}")


@router.get("/statistics/summary")
def get_statistics_summary(days: int = 7):
    """
    Get summary statistics for all query executions.

    Returns:
    - Total executions
    - Pass/fail rates
    - Most frequently run queries
    - Average execution times
    """
    try:
        # Get all results from last N days
        cutoff = datetime.now() - timedelta(days=days)

        all_results = result_history.list_results(limit=1000)

        # Filter by date
        recent_results = [
            r for r in all_results
            if datetime.fromisoformat(r["timestamp"]) >= cutoff
        ]

        # Calculate statistics
        total_runs = len(recent_results)
        passed = sum(1 for r in recent_results if r.get("match", False))
        failed = total_runs - passed

        # Count by query name
        query_counts = {}
        for r in recent_results:
            query_name = r.get("query_name", "Unknown")
            query_counts[query_name] = query_counts.get(query_name, 0) + 1

        # Top queries
        top_queries = sorted(
            query_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "status": "success",
            "period_days": days,
            "summary": {
                "total_executions": total_runs,
                "passed_executions": passed,
                "failed_executions": failed,
                "pass_rate": round((passed / max(total_runs, 1)) * 100, 2)
            },
            "top_queries": [
                {"query_name": name, "execution_count": count}
                for name, count in top_queries
            ]
        }

    except Exception as e:
        logger.error(f"Statistics summary failed: {e}")
        raise HTTPException(status_code=500, detail=f"Statistics summary failed: {str(e)}")


@router.delete("/history/{result_id}")
def delete_result(result_id: str):
    """Delete a result from history"""
    try:
        from pathlib import Path
        file_path = result_history.storage_path / f"{result_id}.json"

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Result not found: {result_id}")

        file_path.unlink()

        return {
            "status": "success",
            "message": f"Result {result_id} deleted"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@router.post("/batch-compare")
def batch_compare_queries(
    comparisons: List[CompareResultsRequest]
):
    """
    Compare multiple query results in batch.

    Useful for validating a full suite of queries at once.
    """
    try:
        results = []

        for i, comparison_request in enumerate(comparisons):
            try:
                comparator = ResultComparator(tolerance=comparison_request.tolerance)

                comparison = comparator.compare_results(
                    sql_results=comparison_request.sql_results,
                    snow_results=comparison_request.snow_results,
                    comparison_type=comparison_request.comparison_type,
                    key_columns=comparison_request.key_columns
                )

                results.append({
                    "index": i,
                    "status": "success",
                    "comparison": comparison
                })

            except Exception as e:
                results.append({
                    "index": i,
                    "status": "error",
                    "error": str(e)
                })

        # Summary statistics
        total = len(results)
        successful = sum(1 for r in results if r["status"] == "success")
        matched = sum(
            1 for r in results
            if r["status"] == "success" and r.get("comparison", {}).get("match", False)
        )

        return {
            "status": "success",
            "summary": {
                "total_comparisons": total,
                "successful_comparisons": successful,
                "matched_results": matched,
                "failed_comparisons": total - successful,
                "pass_rate": round((matched / max(total, 1)) * 100, 2)
            },
            "results": results
        }

    except Exception as e:
        logger.error(f"Batch comparison failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch comparison failed: {str(e)}")
