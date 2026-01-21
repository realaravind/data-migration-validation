"""
Unit Tests for Enhanced Query Result Handler

Tests:
- ResultComparator: Advanced result comparison
- ResultExporter: Multi-format export
- QueryResultHistory: Result tracking
- PerformanceAnalyzer: Performance analysis
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from queries.result_handler import (
    ResultComparator,
    ResultExporter,
    QueryResultHistory,
    PerformanceAnalyzer
)


@pytest.mark.unit
class TestResultComparator:
    """Test advanced result comparison"""

    def test_compare_aggregation_match(self):
        """Test aggregation comparison with matching results"""
        comparator = ResultComparator(tolerance=0.01)

        sql_results = [{"total": 1000.00, "average": 25.50}]
        snow_results = [{"total": 1000.00, "average": 25.50}]

        result = comparator.compare_results(
            sql_results,
            snow_results,
            comparison_type="aggregation"
        )

        assert result["match"] is True
        assert result["comparison_type"] == "aggregation"
        assert result["columns_mismatched"] == 0

    def test_compare_aggregation_mismatch(self):
        """Test aggregation comparison with mismatched results"""
        comparator = ResultComparator(tolerance=0.01)

        sql_results = [{"total": 1000.00, "average": 25.50}]
        snow_results = [{"total": 1050.00, "average": 25.50}]

        result = comparator.compare_results(
            sql_results,
            snow_results,
            comparison_type="aggregation"
        )

        assert result["match"] is False
        assert len(result["mismatches"]) == 1
        assert result["mismatches"][0]["column"] == "total"

    def test_compare_count(self):
        """Test count comparison"""
        comparator = ResultComparator()

        sql_results = [{"count": 500}]
        snow_results = [{"count": 500}]

        result = comparator.compare_results(
            sql_results,
            snow_results,
            comparison_type="count"
        )

        assert result["match"] is True
        assert result["sql_count"] == 500
        assert result["snow_count"] == 500

    def test_compare_count_mismatch(self):
        """Test count comparison with mismatch"""
        comparator = ResultComparator()

        sql_results = [{"count": 500}]
        snow_results = [{"count": 520}]

        result = comparator.compare_results(
            sql_results,
            snow_results,
            comparison_type="count"
        )

        assert result["match"] is False
        assert result["difference"] == 20
        assert result["percent_difference"] > 0

    def test_compare_rowset_positional(self):
        """Test rowset comparison without key columns"""
        comparator = ResultComparator(tolerance=0.01)

        sql_results = [
            {"id": 1, "value": 100},
            {"id": 2, "value": 200}
        ]
        snow_results = [
            {"id": 1, "value": 100},
            {"id": 2, "value": 200}
        ]

        result = comparator.compare_results(
            sql_results,
            snow_results,
            comparison_type="rowset"
        )

        assert result["match"] is True
        assert result["comparison_type"] == "rowset_positional"
        assert result["rows_compared"] == 2

    def test_compare_rowset_with_keys(self):
        """Test rowset comparison with key columns"""
        comparator = ResultComparator()

        sql_results = [
            {"id": 1, "name": "Alice", "value": 100},
            {"id": 2, "name": "Bob", "value": 200}
        ]
        snow_results = [
            {"id": 2, "name": "Bob", "value": 200},
            {"id": 1, "name": "Alice", "value": 100}
        ]

        result = comparator.compare_results(
            sql_results,
            snow_results,
            comparison_type="rowset",
            key_columns=["id"]
        )

        assert result["match"] is True
        assert result["comparison_type"] == "rowset_keyed"
        assert result["common_rows"] == 2

    def test_compare_rowset_missing_rows(self):
        """Test rowset comparison with missing rows"""
        comparator = ResultComparator()

        sql_results = [
            {"id": 1, "value": 100},
            {"id": 2, "value": 200},
            {"id": 3, "value": 300}
        ]
        snow_results = [
            {"id": 1, "value": 100},
            {"id": 2, "value": 200}
        ]

        result = comparator.compare_results(
            sql_results,
            snow_results,
            comparison_type="rowset",
            key_columns=["id"]
        )

        assert result["match"] is False
        assert result["sql_only_rows"] == 1
        assert (3,) in result["sql_only_keys"]

    def test_numeric_tolerance(self):
        """Test numeric value comparison with tolerance"""
        comparator = ResultComparator(tolerance=0.1)

        sql_results = [{"value": 100.05}]
        snow_results = [{"value": 100.10}]

        result = comparator.compare_results(
            sql_results,
            snow_results,
            comparison_type="aggregation"
        )

        assert result["match"] is True  # Within tolerance

    def test_string_comparison(self):
        """Test string value comparison"""
        comparator = ResultComparator()

        sql_results = [{"name": "Alice"}]
        snow_results = [{"name": "alice"}]

        result = comparator.compare_results(
            sql_results,
            snow_results,
            comparison_type="aggregation"
        )

        assert result["match"] is False
        assert result["mismatches"][0]["value_type"] == "string"

    def test_null_handling(self):
        """Test NULL value handling"""
        comparator = ResultComparator()

        sql_results = [{"value": None}]
        snow_results = [{"value": None}]

        result = comparator.compare_results(
            sql_results,
            snow_results,
            comparison_type="aggregation"
        )

        assert result["match"] is True

    def test_levenshtein_distance(self):
        """Test Levenshtein distance calculation"""
        comparator = ResultComparator()

        distance = comparator._levenshtein_distance("kitten", "sitting")
        assert distance == 3

        distance = comparator._levenshtein_distance("hello", "hello")
        assert distance == 0


@pytest.mark.unit
class TestResultExporter:
    """Test result export functionality"""

    def test_export_to_json(self):
        """Test JSON export"""
        results = [
            {"id": 1, "name": "Alice", "value": 100},
            {"id": 2, "name": "Bob", "value": 200}
        ]

        json_str = ResultExporter.export_to_json(results)

        assert json_str is not None
        parsed = json.loads(json_str)
        assert len(parsed) == 2
        assert parsed[0]["name"] == "Alice"

    def test_export_to_csv(self):
        """Test CSV export"""
        results = [
            {"id": 1, "name": "Alice", "value": 100},
            {"id": 2, "name": "Bob", "value": 200}
        ]

        csv_str = ResultExporter.export_to_csv(results)

        assert csv_str is not None
        lines = csv_str.strip().split('\n')
        assert len(lines) == 3  # Header + 2 rows
        assert "Alice" in csv_str

    def test_export_to_file(self):
        """Test export to file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_results.json"

            results = [{"id": 1, "value": 100}]
            ResultExporter.export_to_json(results, str(output_path))

            assert output_path.exists()

            with open(output_path, 'r') as f:
                data = json.load(f)
                assert len(data) == 1
                assert data[0]["value"] == 100

    def test_export_empty_results(self):
        """Test exporting empty results"""
        results = []

        json_str = ResultExporter.export_to_json(results)
        assert json_str == "[]"

        csv_str = ResultExporter.export_to_csv(results)
        assert csv_str == ""


@pytest.mark.unit
class TestQueryResultHistory:
    """Test result history tracking"""

    def test_save_and_retrieve_result(self):
        """Test saving and retrieving results"""
        with tempfile.TemporaryDirectory() as tmpdir:
            history = QueryResultHistory(storage_path=tmpdir)

            result = {
                "sql_rows": 100,
                "snow_rows": 100,
                "match": True
            }

            comparison = {
                "match": True,
                "comparison_type": "aggregation"
            }

            result_id = history.save_result(
                query_name="Test Query",
                query_hash="abc123",
                result=result,
                comparison=comparison
            )

            assert result_id is not None

            # Retrieve result
            retrieved = history.get_result(result_id)
            assert retrieved is not None
            assert retrieved["query_name"] == "Test Query"
            assert retrieved["result"]["match"] is True

    def test_list_results(self):
        """Test listing results"""
        with tempfile.TemporaryDirectory() as tmpdir:
            history = QueryResultHistory(storage_path=tmpdir)

            # Save multiple results
            for i in range(5):
                history.save_result(
                    query_name=f"Query {i}",
                    query_hash=f"hash{i}",
                    result={"data": i},
                    comparison={"match": i % 2 == 0}
                )

            results = history.list_results(limit=10)
            assert len(results) == 5

    def test_filter_by_query_name(self):
        """Test filtering results by query name"""
        with tempfile.TemporaryDirectory() as tmpdir:
            history = QueryResultHistory(storage_path=tmpdir)

            history.save_result("Query A", "hash1", {}, {"match": True})
            history.save_result("Query B", "hash2", {}, {"match": False})
            history.save_result("Query A", "hash3", {}, {"match": True})

            results = history.list_results(query_name="Query A")
            assert len(results) == 2

    def test_trend_analysis(self):
        """Test trend analysis over time"""
        with tempfile.TemporaryDirectory() as tmpdir:
            history = QueryResultHistory(storage_path=tmpdir)

            # Save results for the same query
            for i in range(10):
                history.save_result(
                    query_name="Daily Query",
                    query_hash="hash",
                    result={},
                    comparison={"match": i % 3 == 0}  # 4 pass, 6 fail
                )

            trend = history.get_trend_analysis("Daily Query", days=7)

            assert trend["total_runs"] == 10
            assert trend["passed_runs"] == 4
            assert trend["failed_runs"] == 6
            assert trend["pass_rate"] == 40.0

    def test_query_hash_calculation(self):
        """Test query hash generation"""
        hash1 = QueryResultHistory.calculate_query_hash("SELECT 1", "SELECT 1")
        hash2 = QueryResultHistory.calculate_query_hash("SELECT 1", "SELECT 1")
        hash3 = QueryResultHistory.calculate_query_hash("SELECT 2", "SELECT 2")

        assert hash1 == hash2
        assert hash1 != hash3


@pytest.mark.unit
class TestPerformanceAnalyzer:
    """Test performance analysis"""

    def test_basic_performance_analysis(self):
        """Test basic performance metrics"""
        analysis = PerformanceAnalyzer.analyze_execution(
            sql_duration=1.5,
            snow_duration=1.0,
            sql_row_count=1000,
            snow_row_count=1000
        )

        assert analysis["sql_execution_time"] == 1.5
        assert analysis["snow_execution_time"] == 1.0
        assert analysis["faster_system"] == "Snowflake"
        assert analysis["speed_ratio"] > 1

    def test_throughput_calculation(self):
        """Test rows per second calculation"""
        analysis = PerformanceAnalyzer.analyze_execution(
            sql_duration=2.0,
            snow_duration=1.0,
            sql_row_count=1000,
            snow_row_count=2000
        )

        assert analysis["sql_rows_per_second"] == 500.0
        assert analysis["snow_rows_per_second"] == 2000.0

    def test_performance_categorization(self):
        """Test performance category assignment"""
        # Excellent performance
        analysis = PerformanceAnalyzer.analyze_execution(
            sql_duration=0.05,
            snow_duration=0.05,
            sql_row_count=100,
            snow_row_count=100
        )
        assert analysis["performance_category"] == "excellent"

        # Good performance
        analysis = PerformanceAnalyzer.analyze_execution(
            sql_duration=0.5,
            snow_duration=0.5,
            sql_row_count=100,
            snow_row_count=100
        )
        assert analysis["performance_category"] == "good"

        # Slow performance
        analysis = PerformanceAnalyzer.analyze_execution(
            sql_duration=10.0,
            snow_duration=10.0,
            sql_row_count=100,
            snow_row_count=100
        )
        assert analysis["performance_category"] == "slow"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
