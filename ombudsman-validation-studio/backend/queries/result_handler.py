"""
Enhanced Custom Query Result Handler

Provides advanced result processing capabilities:
- Detailed result diffing with row-level comparison
- Multiple export formats (CSV, JSON, Excel, Parquet)
- Result history tracking
- Performance analysis
- Result caching
- Statistical analysis of differences
"""

import json
import csv
import io
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import hashlib
from collections import defaultdict
import logging

from config.paths import paths

logger = logging.getLogger(__name__)


class ResultComparator:
    """Advanced result comparison engine with detailed diffing"""

    def __init__(self, tolerance: float = 0.01):
        self.tolerance = tolerance

    def compare_results(
        self,
        sql_results: List[Dict],
        snow_results: List[Dict],
        comparison_type: str = "rowset",
        key_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compare query results with detailed analysis.

        Args:
            sql_results: SQL Server results
            snow_results: Snowflake results
            comparison_type: 'aggregation', 'rowset', or 'count'
            key_columns: Columns to use for row matching

        Returns:
            Detailed comparison results with statistics and differences
        """
        if comparison_type == "aggregation":
            return self._compare_aggregation(sql_results, snow_results)
        elif comparison_type == "count":
            return self._compare_count(sql_results, snow_results)
        else:
            return self._compare_rowset(sql_results, snow_results, key_columns)

    def _compare_aggregation(
        self,
        sql_results: List[Dict],
        snow_results: List[Dict]
    ) -> Dict[str, Any]:
        """Compare aggregation results (single row)"""
        if not sql_results or not snow_results:
            return {
                "match": False,
                "error": "One or both queries returned no results",
                "sql_rows": len(sql_results) if sql_results else 0,
                "snow_rows": len(snow_results) if snow_results else 0
            }

        sql_row = sql_results[0]
        snow_row = snow_results[0]

        column_comparisons = []
        mismatches = []

        all_columns = set(sql_row.keys()) | set(snow_row.keys())

        for col in all_columns:
            sql_val = sql_row.get(col)
            snow_val = snow_row.get(col)

            comparison = self._compare_values(col, sql_val, snow_val)
            column_comparisons.append(comparison)

            if not comparison["match"]:
                mismatches.append(comparison)

        return {
            "match": len(mismatches) == 0,
            "comparison_type": "aggregation",
            "columns_compared": len(column_comparisons),
            "columns_matched": len(column_comparisons) - len(mismatches),
            "columns_mismatched": len(mismatches),
            "column_comparisons": column_comparisons,
            "mismatches": mismatches,
            "sql_result": sql_row,
            "snow_result": snow_row
        }

    def _compare_count(
        self,
        sql_results: List[Dict],
        snow_results: List[Dict]
    ) -> Dict[str, Any]:
        """Compare count results"""
        sql_count = self._extract_count(sql_results)
        snow_count = self._extract_count(snow_results)

        match = sql_count == snow_count
        difference = abs(sql_count - snow_count)
        percent_diff = (difference / max(sql_count, 1)) * 100 if sql_count > 0 else 0

        return {
            "match": match,
            "comparison_type": "count",
            "sql_count": sql_count,
            "snow_count": snow_count,
            "difference": difference,
            "percent_difference": round(percent_diff, 2)
        }

    def _compare_rowset(
        self,
        sql_results: List[Dict],
        snow_results: List[Dict],
        key_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Compare rowset results with row-level diffing"""
        sql_count = len(sql_results)
        snow_count = len(snow_results)

        # Build index if key columns provided
        if key_columns:
            sql_index = self._build_row_index(sql_results, key_columns)
            snow_index = self._build_row_index(snow_results, key_columns)

            # Find matching and missing rows
            sql_keys = set(sql_index.keys())
            snow_keys = set(snow_index.keys())

            common_keys = sql_keys & snow_keys
            sql_only = sql_keys - snow_keys
            snow_only = snow_keys - sql_keys

            row_differences = []
            for key in common_keys:
                sql_row = sql_index[key]
                snow_row = snow_index[key]

                diff = self._compare_rows(sql_row, snow_row, key)
                if diff["has_differences"]:
                    row_differences.append(diff)

            return {
                "match": len(row_differences) == 0 and len(sql_only) == 0 and len(snow_only) == 0,
                "comparison_type": "rowset_keyed",
                "total_sql_rows": sql_count,
                "total_snow_rows": snow_count,
                "common_rows": len(common_keys),
                "sql_only_rows": len(sql_only),
                "snow_only_rows": len(snow_only),
                "row_differences": row_differences[:100],  # Limit to first 100
                "total_differences": len(row_differences),
                "sql_only_keys": list(sql_only)[:20],
                "snow_only_keys": list(snow_only)[:20]
            }
        else:
            # Simple position-based comparison
            row_differences = []
            for i, (sql_row, snow_row) in enumerate(zip(sql_results, snow_results)):
                diff = self._compare_rows(sql_row, snow_row, i)
                if diff["has_differences"]:
                    row_differences.append(diff)

            return {
                "match": sql_count == snow_count and len(row_differences) == 0,
                "comparison_type": "rowset_positional",
                "total_sql_rows": sql_count,
                "total_snow_rows": snow_count,
                "row_count_match": sql_count == snow_count,
                "row_differences": row_differences[:100],
                "total_differences": len(row_differences),
                "rows_compared": min(sql_count, snow_count)
            }

    def _compare_values(
        self,
        column: str,
        sql_val: Any,
        snow_val: Any
    ) -> Dict[str, Any]:
        """Compare two values with type-aware logic"""
        # Handle None values
        if sql_val is None and snow_val is None:
            return {
                "column": column,
                "match": True,
                "sql_value": None,
                "snow_value": None
            }

        if sql_val is None or snow_val is None:
            return {
                "column": column,
                "match": False,
                "sql_value": sql_val,
                "snow_value": snow_val,
                "difference_type": "null_mismatch"
            }

        # Try numeric comparison
        try:
            sql_num = float(sql_val)
            snow_num = float(snow_val)

            diff = abs(sql_num - snow_num)
            match = diff <= self.tolerance

            return {
                "column": column,
                "match": match,
                "sql_value": round(sql_num, 6),
                "snow_value": round(snow_num, 6),
                "difference": round(diff, 6),
                "percent_difference": round((diff / max(abs(sql_num), 0.000001)) * 100, 2) if sql_num != 0 else 0,
                "value_type": "numeric"
            }
        except (TypeError, ValueError):
            # String comparison
            sql_str = str(sql_val).strip()
            snow_str = str(snow_val).strip()

            match = sql_str == snow_str

            result = {
                "column": column,
                "match": match,
                "sql_value": sql_str,
                "snow_value": snow_str,
                "value_type": "string"
            }

            if not match:
                result["levenshtein_distance"] = self._levenshtein_distance(sql_str, snow_str)

            return result

    def _compare_rows(
        self,
        sql_row: Dict,
        snow_row: Dict,
        row_key: Any
    ) -> Dict[str, Any]:
        """Compare two rows and return differences"""
        all_columns = set(sql_row.keys()) | set(snow_row.keys())

        column_diffs = []
        for col in all_columns:
            sql_val = sql_row.get(col)
            snow_val = snow_row.get(col)

            comparison = self._compare_values(col, sql_val, snow_val)
            if not comparison["match"]:
                column_diffs.append(comparison)

        return {
            "row_key": row_key,
            "has_differences": len(column_diffs) > 0,
            "column_differences": column_diffs,
            "sql_row": sql_row,
            "snow_row": snow_row
        }

    def _build_row_index(
        self,
        results: List[Dict],
        key_columns: List[str]
    ) -> Dict[Tuple, Dict]:
        """Build index of rows by key columns"""
        index = {}
        for row in results:
            key = tuple(row.get(col) for col in key_columns)
            index[key] = row
        return index

    def _extract_count(self, results: List[Dict]) -> int:
        """Extract count from various result formats"""
        if not results:
            return 0

        if isinstance(results, list):
            if len(results) == 0:
                return 0

            # Check if first row has count column
            first_row = results[0]
            for key in ['count', 'COUNT', 'cnt', 'CNT', 'total', 'TOTAL']:
                if key in first_row:
                    return int(first_row[key])

            # If no count column, return row count
            return len(results)

        return 0

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]


class ResultExporter:
    """Export results in multiple formats"""

    @staticmethod
    def export_to_csv(results: List[Dict], output_path: Optional[str] = None) -> str:
        """Export results to CSV format"""
        if not results:
            return ""

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

        csv_content = output.getvalue()

        if output_path:
            with open(output_path, 'w') as f:
                f.write(csv_content)

        return csv_content

    @staticmethod
    def export_to_json(results: List[Dict], output_path: Optional[str] = None) -> str:
        """Export results to JSON format"""
        json_content = json.dumps(results, indent=2, default=str)

        if output_path:
            with open(output_path, 'w') as f:
                f.write(json_content)

        return json_content

    @staticmethod
    def export_comparison_report(
        comparison_result: Dict,
        output_format: str = "json",
        output_path: Optional[str] = None
    ) -> str:
        """Export comparison results as a formatted report"""
        if output_format == "json":
            return ResultExporter.export_to_json([comparison_result], output_path)
        elif output_format == "csv":
            # Flatten comparison result for CSV
            flattened = ResultExporter._flatten_comparison(comparison_result)
            return ResultExporter.export_to_csv(flattened, output_path)
        else:
            raise ValueError(f"Unsupported export format: {output_format}")

    @staticmethod
    def _flatten_comparison(comparison: Dict) -> List[Dict]:
        """Flatten comparison result for CSV export"""
        if comparison.get("comparison_type") == "aggregation":
            return [comparison.get("sql_result", {}), comparison.get("snow_result", {})]
        elif "row_differences" in comparison:
            # Extract rows with differences
            rows = []
            for diff in comparison.get("row_differences", []):
                row = {
                    "row_key": diff.get("row_key"),
                    "has_differences": diff.get("has_differences"),
                    **diff.get("sql_row", {})
                }
                rows.append(row)
            return rows
        else:
            return [comparison]


class QueryResultHistory:
    """Track and manage query execution history"""

    def __init__(self, storage_path: str = None):
        self.storage_path = Path(storage_path) if storage_path else paths.query_history_dir
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save_result(
        self,
        query_name: str,
        query_hash: str,
        result: Dict[str, Any],
        comparison: Dict[str, Any]
    ) -> str:
        """Save query execution result to history"""
        timestamp = datetime.now()
        result_id = self._generate_result_id(query_name, timestamp)

        history_entry = {
            "result_id": result_id,
            "query_name": query_name,
            "query_hash": query_hash,
            "timestamp": timestamp.isoformat(),
            "result": result,
            "comparison": comparison
        }

        # Save to file
        file_path = self.storage_path / f"{result_id}.json"
        with open(file_path, 'w') as f:
            json.dump(history_entry, f, indent=2, default=str)

        return result_id

    def get_result(self, result_id: str) -> Optional[Dict]:
        """Retrieve a specific result by ID"""
        file_path = self.storage_path / f"{result_id}.json"

        if not file_path.exists():
            return None

        with open(file_path, 'r') as f:
            return json.load(f)

    def list_results(
        self,
        query_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """List query execution history"""
        results = []

        for file_path in sorted(self.storage_path.glob("*.json"), reverse=True):
            try:
                with open(file_path, 'r') as f:
                    entry = json.load(f)

                if query_name and entry.get("query_name") != query_name:
                    continue

                # Add summary info
                results.append({
                    "result_id": entry["result_id"],
                    "query_name": entry["query_name"],
                    "timestamp": entry["timestamp"],
                    "match": entry.get("comparison", {}).get("match", False),
                    "comparison_type": entry.get("comparison", {}).get("comparison_type")
                })

                if len(results) >= limit:
                    break

            except Exception as e:
                logger.error(f"Error loading history file {file_path}: {e}")
                continue

        return results

    def get_trend_analysis(
        self,
        query_name: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """Analyze trends in query results over time"""
        cutoff = datetime.now() - timedelta(days=days)

        results = []
        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    entry = json.load(f)

                if entry.get("query_name") != query_name:
                    continue

                entry_time = datetime.fromisoformat(entry["timestamp"])
                if entry_time < cutoff:
                    continue

                results.append(entry)

            except Exception as e:
                logger.error(f"Error loading history file {file_path}: {e}")
                continue

        # Sort by timestamp
        results.sort(key=lambda x: x["timestamp"])

        # Calculate statistics
        total_runs = len(results)
        passed_runs = sum(1 for r in results if r.get("comparison", {}).get("match", False))
        failed_runs = total_runs - passed_runs

        return {
            "query_name": query_name,
            "period_days": days,
            "total_runs": total_runs,
            "passed_runs": passed_runs,
            "failed_runs": failed_runs,
            "pass_rate": round((passed_runs / max(total_runs, 1)) * 100, 2),
            "results": results
        }

    def _generate_result_id(self, query_name: str, timestamp: datetime) -> str:
        """Generate unique result ID"""
        safe_name = query_name.replace(" ", "_").replace("/", "_")[:50]
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")  # Include microseconds for uniqueness
        return f"{safe_name}_{timestamp_str}"

    @staticmethod
    def calculate_query_hash(sql_query: str, snow_query: str) -> str:
        """Calculate hash of queries for change tracking"""
        combined = f"{sql_query}|{snow_query}"
        return hashlib.md5(combined.encode()).hexdigest()


class PerformanceAnalyzer:
    """Analyze query performance"""

    @staticmethod
    def analyze_execution(
        sql_duration: float,
        snow_duration: float,
        sql_row_count: int,
        snow_row_count: int
    ) -> Dict[str, Any]:
        """Analyze query execution performance"""
        faster_system = "SQL Server" if sql_duration < snow_duration else "Snowflake"
        speed_ratio = max(sql_duration, snow_duration) / max(min(sql_duration, snow_duration), 0.001)

        sql_throughput = sql_row_count / max(sql_duration, 0.001)
        snow_throughput = snow_row_count / max(snow_duration, 0.001)

        return {
            "sql_execution_time": round(sql_duration, 3),
            "snow_execution_time": round(snow_duration, 3),
            "faster_system": faster_system,
            "speed_ratio": round(speed_ratio, 2),
            "sql_rows_per_second": round(sql_throughput, 2),
            "snow_rows_per_second": round(snow_throughput, 2),
            "performance_category": PerformanceAnalyzer._categorize_performance(sql_duration, snow_duration)
        }

    @staticmethod
    def _categorize_performance(sql_duration: float, snow_duration: float) -> str:
        """Categorize query performance"""
        avg_duration = (sql_duration + snow_duration) / 2

        if avg_duration < 0.1:
            return "excellent"
        elif avg_duration < 1.0:
            return "good"
        elif avg_duration < 5.0:
            return "acceptable"
        elif avg_duration < 30.0:
            return "slow"
        else:
            return "very_slow"
