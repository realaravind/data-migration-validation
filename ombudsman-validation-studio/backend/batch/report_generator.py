"""
Consolidated Report Generator for Batch Operations

Generates comprehensive reports from multiple pipeline executions including:
- Aggregate-level comparisons across all pipelines
- Detailed failure analysis
- Debugging SQL queries for each issue
- Cross-pipeline trends and patterns
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
from pathlib import Path

from config.paths import paths


class ConsolidatedReportGenerator:
    """Generate consolidated reports from batch execution results"""

    def __init__(self, results_dir: str = None):
        self.results_dir = Path(results_dir) if results_dir else paths.results_dir

    def _extract_table_name(self, result: Dict[str, Any]) -> str:
        """
        Extract table name from pipeline result.
        Handles both old and new pipeline_def structures.
        """
        pipeline_def = result.get("pipeline_def", {})

        # Try new structure first (pipeline_def.source.table)
        source = pipeline_def.get("source")
        if source and isinstance(source, dict):
            schema = source.get("schema", "")
            table = source.get("table", "unknown")
            return f"{schema}.{table}" if schema else table

        # Fallback to old structure (pipeline_def.pipeline.source.table)
        pipeline = pipeline_def.get("pipeline", {})
        source = pipeline.get("source", {})
        schema = source.get("schema", "")
        table = source.get("table", "unknown")
        return f"{schema}.{table}" if schema else table

    def _find_consolidated_run_id(self, job_id: str) -> Optional[str]:
        """
        Find the consolidated result file for a batch job and return its run_id.

        Args:
            job_id: Batch job ID

        Returns:
            The run_id from the consolidated result, or None if not found
        """
        # Look for files matching pattern batch_{job_id}_*.json
        pattern = f"batch_{job_id}_*.json"
        for file in self.results_dir.glob(pattern):
            try:
                with open(file) as f:
                    data = json.load(f)
                    run_id = data.get("run_id")
                    if run_id:
                        return run_id
            except Exception as e:
                print(f"Error loading consolidated result {file}: {e}")
                continue

        return None

    def generate_batch_report(self, job_id: str, run_ids: List[str]) -> Dict[str, Any]:
        """
        Generate a consolidated report for a batch job.

        Args:
            job_id: Batch job ID
            run_ids: List of pipeline run IDs to include in report

        Returns:
            Comprehensive report dictionary
        """
        # Collect all results
        all_results = []
        for run_id in run_ids:
            result = self._load_result(run_id)
            if result:
                all_results.append(result)

        if not all_results:
            return {
                "job_id": job_id,
                "error": "No results found for any pipeline runs",
                "run_ids": run_ids
            }

        # Find consolidated result file for this batch job
        consolidated_run_id = self._find_consolidated_run_id(job_id)

        # Detect system-level issues first
        system_alerts = self._detect_system_alerts(all_results)

        # Generate report sections
        report = {
            "job_id": job_id,
            "generated_at": datetime.now().isoformat(),
            "pipeline_count": len(all_results),
            "run_ids": run_ids,
            "consolidated_run_id": consolidated_run_id,  # Add consolidated run_id for comparison links

            # System alerts (permission issues, configuration problems)
            "system_alerts": system_alerts,

            # Executive summary
            "executive_summary": self._generate_executive_summary(all_results),

            # Aggregate metrics
            "aggregate_metrics": self._generate_aggregate_metrics(all_results),

            # Table-level summary
            "table_summary": self._generate_table_summary(all_results),

            # Failure analysis
            "failure_analysis": self._generate_failure_analysis(all_results),

            # Data quality scores
            "data_quality_scores": self._calculate_dq_scores(all_results),

            # Debugging queries
            "debugging_queries": self._generate_debugging_queries(all_results),

            # Detailed pipeline results
            "pipeline_details": self._generate_pipeline_details(all_results)
        }

        return report

    def _load_result(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Load a pipeline execution result from disk"""
        for file in self.results_dir.glob("*.json"):
            if run_id in file.name:
                try:
                    with open(file) as f:
                        return json.load(f)
                except Exception as e:
                    print(f"Error loading {file}: {e}")
                    return None
        return None

    def _generate_executive_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate high-level executive summary"""
        total_validations = 0
        passed_validations = 0
        failed_validations = 0
        error_validations = 0
        tables_validated = set()

        for result in results:
            steps = result.get("steps", result.get("results", []))

            # Extract table name from pipeline_def
            full_table = self._extract_table_name(result)
            tables_validated.add(full_table)

            for step in steps:
                total_validations += 1
                status = step.get("status", "").upper()

                if status in ("PASS", "PASSED"):
                    passed_validations += 1
                elif status in ("FAIL", "FAILED"):
                    failed_validations += 1
                elif status == "ERROR":
                    error_validations += 1

        pass_rate = (passed_validations / total_validations * 100) if total_validations > 0 else 0

        # Determine overall status: FAIL if any errors or failures, otherwise PASS
        if error_validations > 0 or failed_validations > 0:
            overall_status = "FAIL"
        else:
            overall_status = "PASS"

        return {
            "total_pipelines": len(results),
            "total_validations": total_validations,
            "passed": passed_validations,
            "failed": failed_validations + error_validations,  # Include errors in failed count for UI display
            "errors": error_validations,
            "pass_rate": round(pass_rate, 2),
            "tables_validated": len(tables_validated),
            "table_list": sorted(list(tables_validated)),
            "overall_status": overall_status
        }

    def _generate_aggregate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate aggregate data quality metrics across all pipelines"""
        metrics = {
            "row_count_totals": {"sql": 0, "snowflake": 0, "diff": 0},
            "orphaned_keys_total": 0,
            "null_count_total": 0,
            "duplicate_count_total": 0,
            "distribution_mismatches": 0,
            "schema_mismatches": 0
        }

        for result in results:
            steps = result.get("steps", result.get("results", []))

            for step in steps:
                details = step.get("details", {})
                step_name = step.get("step_name", step.get("name", ""))

                # Aggregate record counts
                if "record_count" in step_name.lower():
                    metrics["row_count_totals"]["sql"] += details.get("sql_count", 0)
                    metrics["row_count_totals"]["snowflake"] += details.get("snow_count", 0)

                # Aggregate orphaned keys
                if "conformance" in step_name.lower() or "foreign" in step_name.lower():
                    sql_orphans = details.get("sql_orphans", [])
                    snow_orphans = details.get("snow_orphans", [])
                    if isinstance(sql_orphans, list):
                        metrics["orphaned_keys_total"] += len(sql_orphans)
                    if isinstance(snow_orphans, list):
                        metrics["orphaned_keys_total"] += len(snow_orphans)

                # Aggregate nulls
                if "null" in step_name.lower():
                    metrics["null_count_total"] += details.get("null_count", 0)

                # Aggregate duplicates
                if "duplicate" in step_name.lower() or "uniqueness" in step_name.lower():
                    duplicates = details.get("duplicates", [])
                    if isinstance(duplicates, list):
                        metrics["duplicate_count_total"] += len(duplicates)

                # Count mismatches
                if "distribution" in step_name.lower():
                    if step.get("status") == "FAIL":
                        metrics["distribution_mismatches"] += 1

                if "schema" in step_name.lower():
                    if step.get("status") == "FAIL":
                        metrics["schema_mismatches"] += 1

        # Calculate diff
        metrics["row_count_totals"]["diff"] = abs(
            metrics["row_count_totals"]["sql"] - metrics["row_count_totals"]["snowflake"]
        )

        return metrics

    def _generate_table_summary(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate per-table validation summary"""
        table_data = defaultdict(lambda: {
            "table_name": "",
            "total_validations": 0,
            "passed": 0,
            "failed": 0,
            "critical_issues": [],
            "warnings": []
        })

        for result in results:
            # Extract table name from pipeline_def
            table = self._extract_table_name(result)

            steps = result.get("steps", result.get("results", []))

            for step in steps:
                table_data[table]["table_name"] = table
                table_data[table]["total_validations"] += 1

                status = step.get("status", "").upper()
                if status == "PASS":
                    table_data[table]["passed"] += 1
                elif status == "FAIL":
                    table_data[table]["failed"] += 1

                    # Categorize severity
                    severity = step.get("severity", "MEDIUM")
                    message = step.get("details", {}).get("message", step.get("message", "Validation failed"))

                    if severity in ["HIGH", "CRITICAL"]:
                        table_data[table]["critical_issues"].append({
                            "validation": step.get("step_name", step.get("name")),
                            "message": message
                        })
                    else:
                        table_data[table]["warnings"].append({
                            "validation": step.get("step_name", step.get("name")),
                            "message": message
                        })

        # Convert to list and add pass rates
        summary = []
        for table, data in table_data.items():
            data["pass_rate"] = round(
                (data["passed"] / data["total_validations"] * 100) if data["total_validations"] > 0 else 0,
                2
            )
            summary.append(data)

        # Sort by pass rate (worst first)
        summary.sort(key=lambda x: x["pass_rate"])

        return summary

    def _generate_failure_analysis(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze failures and group by type"""
        failure_categories = defaultdict(list)

        for result in results:
            pipeline_name = result.get("pipeline_name", "unknown")

            # Extract table name from pipeline_def
            pipeline_def = result.get("pipeline_def", {})
            pipeline = pipeline_def.get("pipeline", {})
            source = pipeline.get("source", {})
            schema = source.get("schema", "")
            table_name = source.get("table", "unknown")
            table = f"{schema}.{table_name}" if schema else table_name

            steps = result.get("steps", result.get("results", []))

            for step in steps:
                if step.get("status", "").upper() == "FAIL":
                    step_name = step.get("step_name", step.get("name", ""))
                    details = step.get("details", {})
                    message = details.get("message", step.get("message", ""))

                    # Categorize failure
                    category = self._categorize_failure(step_name, details)

                    failure_categories[category].append({
                        "table": table,
                        "pipeline": pipeline_name,
                        "validation": step_name,
                        "message": message,
                        "severity": step.get("severity", "MEDIUM"),
                        "details": self._extract_key_details(step_name, details)
                    })

        # Count and sort
        analysis = {}
        for category, failures in failure_categories.items():
            analysis[category] = {
                "count": len(failures),
                "failures": failures
            }

        return analysis

    def _detect_system_alerts(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect system-level issues that indicate configuration/permission problems"""
        alerts = []
        seen_issues = set()

        for result in results:
            pipeline_name = result.get("pipeline_name", "unknown")
            steps = result.get("steps", result.get("results", []))

            for step in steps:
                step_name = step.get("step_name", step.get("name", ""))
                details = step.get("details", {})

                # Detect Snowflake permission issues (0 columns while SQL has columns)
                if "schema" in step_name.lower() and "column" in step_name.lower():
                    sql_col_count = details.get("column_count_sql", 0)
                    snow_col_count = details.get("column_count_snow", 0)

                    if sql_col_count > 0 and snow_col_count == 0:
                        issue_key = "snowflake_no_metadata"
                        if issue_key not in seen_issues:
                            seen_issues.add(issue_key)
                            alerts.append({
                                "type": "PERMISSION_ERROR",
                                "severity": "CRITICAL",
                                "title": "Snowflake Metadata Access Issue",
                                "message": f"Snowflake returned 0 columns for tables that have {sql_col_count} columns in SQL Server. This typically indicates a permission issue - the Snowflake user may not have access to read table metadata.",
                                "recommendation": "Check that the Snowflake user has SELECT privileges on the tables and USAGE on the schema. Verify the table exists in the specified schema.",
                                "affected_pipeline": pipeline_name
                            })

                # Detect datatype validation with no Snowflake data
                if "datatype" in step_name.lower():
                    mismatches = details.get("mismatches", [])
                    if mismatches:
                        # Check if all mismatches have empty Snowflake datatype
                        all_empty_snow = all(
                            not m.get("snow_datatype") or m.get("snow_datatype") == "None"
                            for m in mismatches if isinstance(m, dict)
                        )
                        if all_empty_snow:
                            issue_key = "snowflake_no_datatypes"
                            if issue_key not in seen_issues:
                                seen_issues.add(issue_key)
                                alerts.append({
                                    "type": "PERMISSION_ERROR",
                                    "severity": "HIGH",
                                    "title": "Snowflake Datatype Information Unavailable",
                                    "message": "All datatype validations show empty Snowflake datatypes. This suggests the Snowflake user cannot read column metadata from INFORMATION_SCHEMA.",
                                    "recommendation": "Grant the Snowflake user SELECT on INFORMATION_SCHEMA views or ensure the tables exist in the specified database/schema.",
                                    "affected_pipeline": pipeline_name
                                })

        return alerts

    def _categorize_failure(self, step_name: str, details: Dict[str, Any]) -> str:
        """Categorize a failure based on validation type"""
        step_lower = step_name.lower()

        if "record_count" in step_lower or "row_count" in step_lower:
            return "row_count_mismatch"
        elif "foreign" in step_lower or "conformance" in step_lower:
            return "referential_integrity"
        elif "null" in step_lower:
            return "null_violations"
        elif "duplicate" in step_lower or "uniqueness" in step_lower:
            return "duplicate_records"
        elif "schema" in step_lower:
            return "schema_mismatch"
        elif "distribution" in step_lower:
            return "distribution_variance"
        elif "datatype" in step_lower or "data_type" in step_lower:
            return "datatype_mismatch"
        else:
            return "other"

    def _extract_key_details(self, step_name: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Extract most relevant details for reporting"""
        key_details = {}

        # Common fields
        for field in ["sql_count", "snow_count", "diff", "percentage_diff", "message"]:
            if field in details:
                key_details[field] = details[field]

        # Schema column comparison
        if "schema_column" in step_name.lower():
            for field in ["sql_columns", "snow_columns", "missing_in_sql", "missing_in_snow",
                         "column_count_sql", "column_count_snow"]:
                if field in details:
                    key_details[field] = details[field]

        # Schema datatype comparison
        elif "datatype" in step_name.lower() or "data_type" in step_name.lower():
            for field in ["mismatches", "mismatch_count"]:
                if field in details:
                    # Limit mismatches to first 10 for display
                    if field == "mismatches" and isinstance(details[field], list):
                        key_details[field] = details[field][:10]
                    else:
                        key_details[field] = details[field]

        # Schema nullability comparison
        elif "nullability" in step_name.lower():
            for field in ["mismatches", "mismatch_count"]:
                if field in details:
                    if field == "mismatches" and isinstance(details[field], list):
                        key_details[field] = details[field][:10]
                    else:
                        key_details[field] = details[field]

        # Foreign key / conformance
        elif "foreign" in step_name.lower() or "conformance" in step_name.lower():
            if "sql_orphans" in details and isinstance(details["sql_orphans"], list):
                key_details["sql_orphan_count"] = len(details["sql_orphans"])
                key_details["sql_orphan_sample"] = details["sql_orphans"][:5]
            if "snow_orphans" in details and isinstance(details["snow_orphans"], list):
                key_details["snow_orphan_count"] = len(details["snow_orphans"])
                key_details["snow_orphan_sample"] = details["snow_orphans"][:5]

        # Record counts
        elif "record_count" in step_name.lower():
            for field in ["sql_count", "snow_count", "diff", "percentage_diff"]:
                if field in details:
                    key_details[field] = details[field]

        # Statistics
        elif "statistic" in step_name.lower():
            for field in ["sql_stats", "snow_stats", "variance"]:
                if field in details:
                    key_details[field] = details[field]

        # Distribution
        elif "distribution" in step_name.lower():
            for field in ["sql_distribution", "snow_distribution", "mismatches"]:
                if field in details:
                    if isinstance(details[field], list) and len(details[field]) > 10:
                        key_details[field] = details[field][:10]
                    else:
                        key_details[field] = details[field]

        return key_details

    def _calculate_dq_scores(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate data quality scores for different dimensions"""
        dimensions = {
            "completeness": {"weight": 0.25, "score": 0},
            "accuracy": {"weight": 0.25, "score": 0},
            "consistency": {"weight": 0.25, "score": 0},
            "validity": {"weight": 0.25, "score": 0}
        }

        dimension_counts = {dim: {"pass": 0, "total": 0} for dim in dimensions}

        for result in results:
            steps = result.get("steps", result.get("results", []))

            for step in steps:
                step_name = step.get("step_name", step.get("name", "")).lower()
                status = step.get("status", "").upper()

                # Map validations to dimensions
                if "null" in step_name or "completeness" in step_name:
                    dimension_counts["completeness"]["total"] += 1
                    if status == "PASS":
                        dimension_counts["completeness"]["pass"] += 1

                elif "record_count" in step_name or "conformance" in step_name:
                    dimension_counts["accuracy"]["total"] += 1
                    if status == "PASS":
                        dimension_counts["accuracy"]["pass"] += 1

                elif "distribution" in step_name or "statistics" in step_name:
                    dimension_counts["consistency"]["total"] += 1
                    if status == "PASS":
                        dimension_counts["consistency"]["pass"] += 1

                elif "schema" in step_name or "datatype" in step_name or "domain" in step_name:
                    dimension_counts["validity"]["total"] += 1
                    if status == "PASS":
                        dimension_counts["validity"]["pass"] += 1

        # Calculate scores
        for dim, data in dimensions.items():
            counts = dimension_counts[dim]
            if counts["total"] > 0:
                score = (counts["pass"] / counts["total"]) * 100
                dimensions[dim]["score"] = round(score, 2)
                dimensions[dim]["validations"] = counts["total"]
            else:
                dimensions[dim]["score"] = None
                dimensions[dim]["validations"] = 0

        # Calculate overall score
        overall_score = sum(
            d["score"] * d["weight"]
            for d in dimensions.values()
            if d["score"] is not None
        )

        return {
            "overall_score": round(overall_score, 2),
            "dimensions": dimensions
        }

    def _generate_debugging_queries(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate debugging SQL queries for failures"""
        queries = []

        for result in results:
            # Extract source and target from pipeline_def
            pipeline_def = result.get("pipeline_def", {})

            # Try new structure first (direct source/target)
            source = pipeline_def.get("source")
            target = pipeline_def.get("target")

            # Fallback to old structure
            if not source:
                pipeline = pipeline_def.get("pipeline", {})
                source = pipeline.get("source", {})
                target = pipeline.get("target", {})
            elif not target:
                pipeline = pipeline_def.get("pipeline", {})
                target = pipeline.get("target", {})

            sql_table = f"{source.get('database', '')}.{source.get('schema', '')}.{source.get('table', '')}"
            snow_table = f"{target.get('database', '')}.{target.get('schema', '')}.{target.get('table', '')}"

            steps = result.get("steps", result.get("results", []))

            for step in steps:
                if step.get("status", "").upper() == "FAIL":
                    step_name = step.get("step_name", step.get("name", ""))
                    details = step.get("details", {})

                    # Generate appropriate debugging queries
                    debug_queries = self._create_debug_queries(step_name, details, sql_table, snow_table)

                    if debug_queries:
                        queries.append({
                            "table": source.get("table"),
                            "validation": step_name,
                            "issue": details.get("message", "Validation failed"),
                            "queries": debug_queries
                        })

        return queries

    def _create_debug_queries(
        self,
        step_name: str,
        details: Dict[str, Any],
        sql_table: str,
        snow_table: str
    ) -> List[Dict[str, str]]:
        """Create specific debugging queries based on validation type"""
        queries = []
        step_lower = step_name.lower()

        # Schema column queries
        if "schema_column" in step_lower:
            missing_in_snow = details.get("missing_in_snow", [])
            missing_in_sql = details.get("missing_in_sql", [])

            if missing_in_snow:
                queries.append({
                    "purpose": "Columns in SQL Server but missing in Snowflake",
                    "database": "SQL Server",
                    "query": f"""
-- These columns exist in SQL Server but not in Snowflake:
-- {', '.join(missing_in_snow)}

-- Check SQL Server schema
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = '{sql_table.split('.')[-2] if '.' in sql_table else 'dbo'}'
  AND TABLE_NAME = '{sql_table.split('.')[-1]}'
ORDER BY ORDINAL_POSITION;
"""
                })

            if missing_in_sql:
                queries.append({
                    "purpose": "Columns in Snowflake but missing in SQL Server",
                    "database": "Snowflake",
                    "query": f"""
-- These columns exist in Snowflake but not in SQL Server:
-- {', '.join(missing_in_sql)}

-- Check Snowflake schema
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = '{snow_table.split('.')[-2] if '.' in snow_table else 'PUBLIC'}'
  AND TABLE_NAME = '{snow_table.split('.')[-1]}'
ORDER BY ORDINAL_POSITION;
"""
                })

        # Schema datatype queries
        elif "datatype" in step_lower or "data_type" in step_lower:
            mismatches = details.get("mismatches", [])
            if mismatches:
                mismatch_list = [f"{m.get('column', 'unknown')}: SQL={m.get('sql_type', '?')} vs Snow={m.get('snow_type', '?')}"
                               for m in mismatches[:5]]
                queries.append({
                    "purpose": "Data type mismatches between SQL Server and Snowflake",
                    "database": "Both",
                    "query": f"""
-- Data type mismatches found:
-- {chr(10).join(['-- ' + m for m in mismatch_list])}

-- SQL Server data types
SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = '{sql_table.split('.')[-2] if '.' in sql_table else 'dbo'}'
  AND TABLE_NAME = '{sql_table.split('.')[-1]}'
ORDER BY ORDINAL_POSITION;

-- Snowflake data types
SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = '{snow_table.split('.')[-2] if '.' in snow_table else 'PUBLIC'}'
  AND TABLE_NAME = '{snow_table.split('.')[-1]}'
ORDER BY ORDINAL_POSITION;
"""
                })

        # Fact-dimension conformance queries
        elif "conformance" in step_lower or "fact_dim" in step_lower:
            message = details.get("message", "")
            queries.append({
                "purpose": "Investigate fact-dimension conformance issues",
                "database": "Both",
                "query": f"""
-- {message}

-- Find orphaned foreign keys (keys in fact table without matching dimension records)
-- Example for customer dimension:
SELECT f.dim_customer_key, COUNT(*) as occurrence_count
FROM {sql_table} f
LEFT JOIN DIM.DIM_CUSTOMER d ON f.dim_customer_key = d.customer_key
WHERE d.customer_key IS NULL
GROUP BY f.dim_customer_key
ORDER BY occurrence_count DESC
LIMIT 100;

-- Check dimension table for missing keys
SELECT COUNT(*) as total_dimension_records
FROM DIM.DIM_CUSTOMER;

-- Verify all fact foreign keys have dimension matches
SELECT
    COUNT(*) as total_facts,
    COUNT(DISTINCT dim_customer_key) as unique_customers,
    COUNT(DISTINCT dim_product_key) as unique_products,
    COUNT(DISTINCT dim_store_key) as unique_stores,
    COUNT(DISTINCT dim_date_key) as unique_dates
FROM {sql_table};
"""
            })

        # Record count queries
        elif "record_count" in step_lower:
            queries.append({
                "purpose": "Verify SQL Server row count",
                "database": "SQL Server",
                "query": f"SELECT COUNT(*) as row_count FROM {sql_table};"
            })
            queries.append({
                "purpose": "Verify Snowflake row count",
                "database": "Snowflake",
                "query": f"SELECT COUNT(*) as row_count FROM {snow_table};"
            })
            queries.append({
                "purpose": "Find records only in SQL Server",
                "database": "SQL Server",
                "query": f"""
-- Assuming primary key column exists
SELECT s.*
FROM {sql_table} s
LEFT JOIN {snow_table} t ON s.id = t.id
WHERE t.id IS NULL
LIMIT 100;
"""
            })
            queries.append({
                "purpose": "Find records only in Snowflake",
                "database": "Snowflake",
                "query": f"""
-- Assuming primary key column exists
SELECT t.*
FROM {snow_table} t
LEFT JOIN {sql_table} s ON t.id = s.id
WHERE s.id IS NULL
LIMIT 100;
"""
            })

        # Foreign key / conformance queries
        elif "foreign" in step_lower or "conformance" in step_lower:
            sql_orphans = details.get("sql_orphans", [])
            snow_orphans = details.get("snow_orphans", [])

            if sql_orphans:
                orphan_sample = sql_orphans[:10] if isinstance(sql_orphans, list) else []
                if orphan_sample:
                    queries.append({
                        "purpose": "Inspect orphaned records in SQL Server",
                        "database": "SQL Server",
                        "query": f"""
-- Check orphaned foreign key values
SELECT *
FROM {sql_table}
WHERE foreign_key_column IN ({','.join(map(str, orphan_sample))})
LIMIT 100;
"""
                    })

            if snow_orphans:
                orphan_sample = snow_orphans[:10] if isinstance(snow_orphans, list) else []
                if orphan_sample:
                    queries.append({
                        "purpose": "Inspect orphaned records in Snowflake",
                        "database": "Snowflake",
                        "query": f"""
-- Check orphaned foreign key values
SELECT *
FROM {snow_table}
WHERE foreign_key_column IN ({','.join(map(str, orphan_sample))})
LIMIT 100;
"""
                    })

        # Null validation queries
        elif "null" in step_lower:
            column = details.get("column", "column_name")
            queries.append({
                "purpose": f"Find NULL values in {column}",
                "database": "Both",
                "query": f"""
-- SQL Server
SELECT COUNT(*) as null_count
FROM {sql_table}
WHERE {column} IS NULL;

-- Snowflake
SELECT COUNT(*) as null_count
FROM {snow_table}
WHERE {column} IS NULL;
"""
            })

        # Duplicate queries
        elif "duplicate" in step_lower or "uniqueness" in step_lower:
            column = details.get("column", "column_name")
            queries.append({
                "purpose": f"Find duplicate values in {column}",
                "database": "Both",
                "query": f"""
-- SQL Server duplicates
SELECT {column}, COUNT(*) as occurrence_count
FROM {sql_table}
GROUP BY {column}
HAVING COUNT(*) > 1
ORDER BY occurrence_count DESC
LIMIT 100;

-- Snowflake duplicates
SELECT {column}, COUNT(*) as occurrence_count
FROM {snow_table}
GROUP BY {column}
HAVING COUNT(*) > 1
ORDER BY occurrence_count DESC
LIMIT 100;
"""
            })

        # Metric sum validations
        elif "metric_sum" in step_lower or "metric sum" in step_lower:
            queries.append({
                "purpose": "Compare sum aggregates between SQL Server and Snowflake",
                "database": "Both",
                "query": f"""
-- SQL Server metric sums
SELECT
    SUM(sales_amount) as total_sales,
    SUM(quantity) as total_quantity,
    SUM(cost_amount) as total_cost,
    SUM(discount_amount) as total_discount
FROM {sql_table};

-- Snowflake metric sums
SELECT
    SUM(sales_amount) as total_sales,
    SUM(quantity) as total_quantity,
    SUM(cost_amount) as total_cost,
    SUM(discount_amount) as total_discount
FROM {snow_table};
"""
            })

        # Metric average validations
        elif "metric_average" in step_lower or "average" in step_lower:
            queries.append({
                "purpose": "Compare average metrics between databases",
                "database": "Both",
                "query": f"""
-- SQL Server averages
SELECT
    AVG(sales_amount) as avg_sales,
    AVG(quantity) as avg_quantity,
    AVG(unit_price) as avg_price
FROM {sql_table};

-- Snowflake averages
SELECT
    AVG(sales_amount) as avg_sales,
    AVG(quantity) as avg_quantity,
    AVG(unit_price) as avg_price
FROM {snow_table};
"""
            })

        # Statistics validations
        elif "statistic" in step_lower:
            queries.append({
                "purpose": "Compare statistical measures between databases",
                "database": "Both",
                "query": f"""
-- SQL Server statistics
SELECT
    COUNT(*) as row_count,
    AVG(sales_amount) as avg_sales,
    MIN(sales_amount) as min_sales,
    MAX(sales_amount) as max_sales,
    STDEV(sales_amount) as std_dev_sales
FROM {sql_table};

-- Snowflake statistics
SELECT
    COUNT(*) as row_count,
    AVG(sales_amount) as avg_sales,
    MIN(sales_amount) as min_sales,
    MAX(sales_amount) as max_sales,
    STDDEV(sales_amount) as std_dev_sales
FROM {snow_table};
"""
            })

        # Outlier detection
        elif "outlier" in step_lower:
            queries.append({
                "purpose": "Find potential outliers in numeric columns",
                "database": "Both",
                "query": f"""
-- SQL Server outliers (values beyond 3 standard deviations)
WITH stats AS (
    SELECT
        AVG(sales_amount) as mean_val,
        STDEV(sales_amount) as std_val
    FROM {sql_table}
)
SELECT *
FROM {sql_table}, stats
WHERE ABS(sales_amount - mean_val) > 3 * std_val
LIMIT 100;

-- Snowflake outliers
WITH stats AS (
    SELECT
        AVG(sales_amount) as mean_val,
        STDDEV(sales_amount) as std_val
    FROM {snow_table}
)
SELECT *
FROM {snow_table}, stats
WHERE ABS(sales_amount - mean_val) > 3 * std_val
LIMIT 100;
"""
            })

        return queries

    def _generate_pipeline_details(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate detailed breakdown for each pipeline"""
        details = []

        for result in results:
            # Extract table name from pipeline_def
            table = self._extract_table_name(result)

            steps = result.get("steps", result.get("results", []))

            pass_count = sum(1 for s in steps if s.get("status", "").upper() == "PASS")
            fail_count = sum(1 for s in steps if s.get("status", "").upper() == "FAIL")

            pipeline_detail = {
                "pipeline_name": result.get("pipeline_name", "unknown"),
                "run_id": result.get("run_id"),
                "table": table,
                "execution_time": result.get("execution_time"),
                "total_validations": len(steps),
                "passed": pass_count,
                "failed": fail_count,
                "pass_count": pass_count,  # Frontend expects this
                "fail_count": fail_count,  # Frontend expects this
                "status": result.get("status", "completed" if fail_count == 0 else "failed"),  # Frontend expects this
                "duration_ms": result.get("duration_ms", result.get("execution_time_ms", 0)),  # Frontend expects this
                "validations": []
            }

            for step in steps:
                validation = {
                    "name": step.get("step_name", step.get("name")),
                    "status": step.get("status"),
                    "severity": step.get("severity", "NONE"),
                    "message": step.get("details", {}).get("message", step.get("message", ""))
                }

                # Include FULL details object for frontend rendering
                details_dict = step.get("details", {})
                if details_dict and isinstance(details_dict, dict):
                    # Include complete details for proper frontend rendering
                    validation["details"] = details_dict

                    # Also include key_metrics for backward compatibility
                    validation["key_metrics"] = self._extract_key_details(
                        step.get("name", ""),
                        details_dict
                    )
                else:
                    validation["details"] = {}
                    validation["key_metrics"] = {}

                pipeline_detail["validations"].append(validation)

            details.append(pipeline_detail)

        return details


# Global instance
report_generator = ConsolidatedReportGenerator()
