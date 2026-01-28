"""
Bug Report Service

Generates bug reports from batch execution results, analyzing failures and errors
to create actionable bug entries for Azure DevOps or downloadable reports.
"""

import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

from .models import (
    Bug, BugReport, BugReportSummary, BugSeverity, BugStatus,
    ValidationCategory, GenerateBugReportRequest
)
from config.paths import paths


class BugReportService:
    """Service for generating bug reports from batch execution results"""

    def __init__(self, results_dir: str = None, reports_dir: str = None):
        self.results_dir = Path(results_dir) if results_dir else paths.results_dir
        self.reports_dir = Path(reports_dir) if reports_dir else paths.data_dir / "bug_reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_bug_report(
        self,
        request: GenerateBugReportRequest,
        project_id: str,
        project_name: str,
        user: Optional[str] = None
    ) -> BugReport:
        """
        Generate a bug report from batch execution results.

        Args:
            request: Bug report generation request
            project_id: Project ID
            project_name: Project name
            user: User who generated the report

        Returns:
            BugReport: Generated bug report

        Raises:
            FileNotFoundError: If batch result file not found
            ValueError: If batch results are invalid
        """
        # Find batch result file
        batch_results = self._load_batch_results(request.batch_job_id)

        if not batch_results:
            raise FileNotFoundError(f"No results found for batch job {request.batch_job_id}")

        # Extract job metadata
        batch_job_name = batch_results.get("batch_job_name", f"Batch Job {request.batch_job_id}")

        # Generate report ID
        report_id = f"bug_report_{uuid.uuid4().hex[:12]}"

        # Parse failures and generate bugs
        bugs = self._extract_bugs_from_results(
            batch_results,
            request.batch_job_id,
            request.severity_threshold,
            request.include_sample_data,
            request.max_samples_per_bug
        )

        # Generate summary
        summary = self._generate_summary(bugs)

        # Group bugs if requested
        grouped_bugs = None
        if request.group_by:
            grouped_bugs = self._group_bugs(bugs, request.group_by)

        # Create bug report
        report = BugReport(
            report_id=report_id,
            batch_job_id=request.batch_job_id,
            batch_job_name=batch_job_name,
            project_id=project_id,
            project_name=project_name,
            title=request.title or f"Bug Report: {batch_job_name}",
            description=request.description,
            generated_by=user,
            bugs=bugs,
            summary=summary,
            group_by=request.group_by,
            grouped_bugs=grouped_bugs,
            include_sample_data=request.include_sample_data,
            max_samples_per_bug=request.max_samples_per_bug
        )

        # Save report
        self._save_report(report)

        return report

    def _load_batch_results(self, batch_job_id: str) -> Optional[Dict[str, Any]]:
        """
        Load batch execution results from file.

        Args:
            batch_job_id: Batch job ID

        Returns:
            Batch results dictionary or None if not found
        """
        # Look for files matching pattern batch_{job_id}_*.json
        pattern = f"batch_{batch_job_id}_*.json"

        for file in self.results_dir.glob(pattern):
            try:
                with open(file) as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading batch result {file}: {e}")
                continue

        return None

    def _extract_bugs_from_results(
        self,
        batch_results: Dict[str, Any],
        batch_job_id: str,
        severity_threshold: Optional[BugSeverity],
        include_sample_data: bool,
        max_samples: int
    ) -> List[Bug]:
        """
        Extract bugs from batch execution results.

        Args:
            batch_results: Batch results dictionary
            batch_job_id: Batch job ID
            severity_threshold: Minimum severity to include
            include_sample_data: Whether to include sample data
            max_samples: Maximum number of samples per bug

        Returns:
            List of Bug objects
        """
        bugs = []
        results = batch_results.get("results", [])

        for result in results:
            # Only process failed or error results
            status = result.get("status", "")
            if status not in ["FAIL", "ERROR", "FAILED"]:
                continue

            # Determine severity
            severity = self._determine_severity(result)

            # Skip if below threshold
            if severity_threshold and self._is_below_threshold(severity, severity_threshold):
                continue

            # Determine category
            category = self._determine_category(result)

            # Extract detailed information
            details = result.get("details", {})

            # Create bug
            bug = Bug(
                bug_id=f"bug_{uuid.uuid4().hex[:8]}",
                title=self._generate_bug_title(result),
                description=self._generate_bug_description(result, details),
                severity=severity,
                category=category,
                batch_job_id=batch_job_id,
                run_id=batch_results.get("run_id"),
                step_name=result.get("name", "unknown"),
                validation_type=self._extract_validation_type(result),
                table_name=self._extract_table_name(result, batch_results),
                error_message=details.get("error") or details.get("message"),
                sample_data=self._extract_sample_data(details, include_sample_data, max_samples),
                tags=self._generate_tags(result, category)
            )

            bugs.append(bug)

        return bugs

    def _determine_severity(self, result: Dict[str, Any]) -> BugSeverity:
        """
        Determine bug severity based on validation result.

        Args:
            result: Validation result

        Returns:
            BugSeverity
        """
        severity_str = result.get("severity", "MEDIUM").upper()
        status = result.get("status", "").upper()
        details = result.get("details", {})

        # Error status is always HIGH or CRITICAL
        if status == "ERROR":
            # Check if it's a critical error (schema, data corruption, etc.)
            error = str(details.get("error", "")).lower()
            if any(keyword in error for keyword in ["corrupt", "crash", "schema", "integrity"]):
                return BugSeverity.CRITICAL
            return BugSeverity.HIGH

        # Map severity string
        severity_map = {
            "CRITICAL": BugSeverity.CRITICAL,
            "HIGH": BugSeverity.HIGH,
            "MEDIUM": BugSeverity.MEDIUM,
            "LOW": BugSeverity.LOW,
            "INFO": BugSeverity.INFO
        }

        return severity_map.get(severity_str, BugSeverity.MEDIUM)

    def _is_below_threshold(self, severity: BugSeverity, threshold: BugSeverity) -> bool:
        """Check if severity is below threshold."""
        severity_order = [
            BugSeverity.INFO,
            BugSeverity.LOW,
            BugSeverity.MEDIUM,
            BugSeverity.HIGH,
            BugSeverity.CRITICAL
        ]
        return severity_order.index(severity) < severity_order.index(threshold)

    def _determine_category(self, result: Dict[str, Any]) -> ValidationCategory:
        """
        Determine validation category from result.

        Args:
            result: Validation result

        Returns:
            ValidationCategory
        """
        name = result.get("name", "").lower()
        validation_type = self._extract_validation_type(result)

        # Map validation types to categories
        if any(keyword in validation_type for keyword in ["schema", "column", "datatype", "nullability"]):
            return ValidationCategory.SCHEMA
        elif any(keyword in validation_type for keyword in ["null", "uniqueness", "domain", "outlier", "distribution", "regex", "statistic"]):
            return ValidationCategory.DATA_QUALITY
        elif any(keyword in validation_type for keyword in ["foreign", "fk", "referential"]):
            return ValidationCategory.REFERENTIAL_INTEGRITY
        elif any(keyword in validation_type for keyword in ["dimension", "dim", "scd", "surrogate", "business_key"]):
            return ValidationCategory.DIMENSION
        elif any(keyword in validation_type for keyword in ["fact", "conformance", "late_arriving"]):
            return ValidationCategory.FACT
        elif any(keyword in validation_type for keyword in ["metric", "sum", "average", "ratio"]):
            return ValidationCategory.METRIC
        elif any(keyword in validation_type for keyword in ["timeseries", "ts_", "continuity", "period"]):
            return ValidationCategory.TIMESERIES
        else:
            return ValidationCategory.CUSTOM

    def _extract_validation_type(self, result: Dict[str, Any]) -> str:
        """Extract validation type from result."""
        name = result.get("name", "")
        details = result.get("details", {})

        # Try to extract from config
        config = details.get("config", {})
        if isinstance(config, dict):
            for key in ["validation_type", "type", "validator"]:
                if key in config:
                    return str(config[key])

        return name

    def _extract_table_name(self, result: Dict[str, Any], batch_results: Dict[str, Any]) -> Optional[str]:
        """Extract table name from result or batch metadata."""
        # Try from result details
        details = result.get("details", {})
        if "table" in details:
            return str(details["table"])

        # Try from batch results
        tables = batch_results.get("tables_validated", [])
        if tables:
            return tables[0] if isinstance(tables, list) else str(tables)

        return None

    def _generate_bug_title(self, result: Dict[str, Any]) -> str:
        """Generate a concise bug title from result."""
        name = result.get("name", "Validation Failure")
        status = result.get("status", "FAIL")

        # Clean up name
        title = name.replace("_", " ").title()

        return f"{status}: {title}"

    def _generate_bug_description(self, result: Dict[str, Any], details: Dict[str, Any]) -> str:
        """Generate detailed bug description."""
        lines = []

        # Validation name
        lines.append(f"**Validation:** {result.get('name', 'Unknown')}")

        # Error message
        error = details.get("error") or details.get("message")
        if error:
            lines.append(f"**Error:** {error}")

        # Configuration
        config = details.get("config")
        if config and isinstance(config, dict):
            lines.append("\n**Configuration:**")
            for key, value in config.items():
                if isinstance(value, (str, int, float, bool)):
                    lines.append(f"- {key}: {value}")

        # Expected vs Actual
        if "expected" in details:
            lines.append(f"\n**Expected:** {details['expected']}")
        if "actual" in details:
            lines.append(f"**Actual:** {details['actual']}")

        # Additional context
        if "context" in details:
            lines.append(f"\n**Context:** {details['context']}")

        return "\n".join(lines)

    def _extract_sample_data(
        self,
        details: Dict[str, Any],
        include_sample: bool,
        max_samples: int
    ) -> Optional[List[Dict[str, Any]]]:
        """Extract sample data from validation details."""
        if not include_sample:
            return None

        # Look for sample data in various fields
        for key in ["sample_data", "samples", "failed_rows", "mismatches"]:
            if key in details:
                data = details[key]
                if isinstance(data, list):
                    return data[:max_samples]

        return None

    def _generate_tags(self, result: Dict[str, Any], category: ValidationCategory) -> List[str]:
        """Generate tags for bug."""
        tags = [category.value]

        # Add severity tag
        severity = result.get("severity", "medium")
        tags.append(f"severity-{severity.lower()}")

        # Add status tag
        status = result.get("status", "failed")
        tags.append(status.lower())

        return tags

    def _generate_summary(self, bugs: List[Bug]) -> BugReportSummary:
        """Generate summary statistics from bugs."""
        summary = BugReportSummary(total_bugs=len(bugs))

        for bug in bugs:
            # Count by severity
            if bug.severity == BugSeverity.CRITICAL:
                summary.critical_count += 1
            elif bug.severity == BugSeverity.HIGH:
                summary.high_count += 1
            elif bug.severity == BugSeverity.MEDIUM:
                summary.medium_count += 1
            elif bug.severity == BugSeverity.LOW:
                summary.low_count += 1
            elif bug.severity == BugSeverity.INFO:
                summary.info_count += 1

            # Count by category
            if bug.category == ValidationCategory.SCHEMA:
                summary.schema_failures += 1
            elif bug.category == ValidationCategory.DATA_QUALITY:
                summary.data_quality_failures += 1
            elif bug.category == ValidationCategory.REFERENTIAL_INTEGRITY:
                summary.referential_integrity_failures += 1
            elif bug.category == ValidationCategory.DIMENSION:
                summary.dimension_failures += 1
            elif bug.category == ValidationCategory.FACT:
                summary.fact_failures += 1
            elif bug.category == ValidationCategory.METRIC:
                summary.metric_failures += 1
            elif bug.category == ValidationCategory.TIMESERIES:
                summary.timeseries_failures += 1
            elif bug.category == ValidationCategory.CUSTOM:
                summary.custom_failures += 1

            # Count by status
            if bug.status == BugStatus.PENDING_REVIEW:
                summary.pending_review += 1
            elif bug.status == BugStatus.APPROVED:
                summary.approved += 1
            elif bug.status == BugStatus.REJECTED:
                summary.rejected += 1
            elif bug.status == BugStatus.CREATED_IN_AZURE:
                summary.created_in_azure += 1
            elif bug.status == BugStatus.FAILED_TO_CREATE:
                summary.failed_to_create += 1

        return summary

    def _group_bugs(self, bugs: List[Bug], group_by: str) -> Dict[str, List[Bug]]:
        """Group bugs by specified criterion."""
        grouped = defaultdict(list)

        for bug in bugs:
            if group_by == "severity":
                key = bug.severity.value
            elif group_by == "category":
                key = bug.category.value
            elif group_by == "table":
                key = bug.table_name or "unknown"
            elif group_by == "step":
                key = bug.step_name
            else:
                key = "all"

            grouped[key].append(bug)

        return dict(grouped)

    def _save_report(self, report: BugReport) -> None:
        """Save bug report to file."""
        report_file = self.reports_dir / f"{report.report_id}.json"

        with open(report_file, 'w') as f:
            json.dump(report.dict(), f, indent=2, default=str)

    def load_report(self, report_id: str) -> Optional[BugReport]:
        """Load saved bug report."""
        report_file = self.reports_dir / f"{report_id}.json"

        if not report_file.exists():
            return None

        with open(report_file) as f:
            data = json.load(f)
            return BugReport(**data)

    def update_bug_statuses(
        self,
        report_id: str,
        approved_bug_ids: List[str],
        rejected_bug_ids: List[str]
    ) -> BugReport:
        """
        Update bug statuses (approve/reject).

        Args:
            report_id: Bug report ID
            approved_bug_ids: List of bug IDs to approve
            rejected_bug_ids: List of bug IDs to reject

        Returns:
            Updated BugReport

        Raises:
            FileNotFoundError: If report not found
        """
        report = self.load_report(report_id)
        if not report:
            raise FileNotFoundError(f"Bug report {report_id} not found")

        # Update bug statuses
        for bug in report.bugs:
            if bug.bug_id in approved_bug_ids:
                bug.status = BugStatus.APPROVED
                bug.reviewed_at = datetime.utcnow()
            elif bug.bug_id in rejected_bug_ids:
                bug.status = BugStatus.REJECTED
                bug.reviewed_at = datetime.utcnow()

        # Update summary
        report.summary = self._generate_summary(report.bugs)
        report.approved_count = len(approved_bug_ids)

        # Save updated report
        self._save_report(report)

        return report

    def list_reports(self, project_id: Optional[str] = None, limit: int = 50) -> List[BugReport]:
        """List bug reports, optionally filtered by project."""
        reports = []

        for report_file in sorted(self.reports_dir.glob("bug_report_*.json"), reverse=True)[:limit]:
            try:
                report = self.load_report(report_file.stem)
                if report and (not project_id or report.project_id == project_id):
                    reports.append(report)
            except Exception as e:
                print(f"Error loading report {report_file}: {e}")
                continue

        return reports
