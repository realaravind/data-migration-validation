"""
Audit Log Storage

Handles persistence of audit logs to JSON files.
In production, this could be replaced with a proper database.
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from config.paths import paths
from .models import AuditLog, AuditLogCreate, AuditLogFilter, AuditLogSummary


class AuditLogStorage:
    """
    Stores audit logs in JSON files organized by date.
    Each day gets its own file for efficient querying and rotation.
    """

    def __init__(self, storage_dir: str = None):
        """
        Initialize audit log storage.

        Args:
            storage_dir: Directory to store audit logs
        """
        if storage_dir is None:
            storage_dir = str(paths.audit_logs_dir)

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_file(self, date: datetime) -> Path:
        """Get the log file path for a specific date"""
        return self.storage_dir / f"audit_{date.strftime('%Y%m%d')}.jsonl"

    def add_log(self, log: AuditLogCreate) -> AuditLog:
        """
        Add a new audit log entry.

        Args:
            log: Audit log data to store

        Returns:
            AuditLog: The stored log with generated ID
        """
        # Generate unique ID
        log_id = str(uuid.uuid4())

        # Create full log entry
        log_dict = log.model_dump()
        log_dict["id"] = log_id

        # Convert datetime to ISO format
        if isinstance(log_dict.get("timestamp"), datetime):
            log_dict["timestamp"] = log_dict["timestamp"].isoformat()

        # Get appropriate log file
        log_file = self._get_log_file(log.timestamp)

        # Append to log file (JSONL format)
        with open(log_file, "a") as f:
            f.write(json.dumps(log_dict) + "\n")

        return AuditLog(**log_dict)

    def query_logs(self, filters: AuditLogFilter) -> List[AuditLog]:
        """
        Query audit logs with filters.

        Args:
            filters: Filter criteria

        Returns:
            List of matching audit logs
        """
        logs = []

        # Determine date range to scan
        start_date = filters.start_date or datetime.utcnow() - timedelta(days=30)
        end_date = filters.end_date or datetime.utcnow()

        # Scan all relevant log files
        current_date = start_date
        while current_date <= end_date:
            log_file = self._get_log_file(current_date)

            if log_file.exists():
                with open(log_file, "r") as f:
                    for line in f:
                        try:
                            log_dict = json.loads(line.strip())
                            log = AuditLog(**log_dict)

                            # Apply filters
                            if self._matches_filters(log, filters):
                                logs.append(log)
                        except Exception as e:
                            print(f"Error parsing log line: {e}")

            current_date += timedelta(days=1)

        # Sort logs
        reverse = filters.sort_order == "desc"
        logs.sort(
            key=lambda x: getattr(x, filters.sort_by, x.timestamp),
            reverse=reverse
        )

        # Apply pagination
        start_idx = filters.offset
        end_idx = filters.offset + filters.limit
        return logs[start_idx:end_idx]

    def _matches_filters(self, log: AuditLog, filters: AuditLogFilter) -> bool:
        """Check if a log entry matches the filter criteria"""
        # Level filter
        if filters.level and log.level != filters.level:
            return False

        # Category filter
        if filters.category and log.category != filters.category:
            return False

        # User filters
        if filters.user_id and log.user_id != filters.user_id:
            return False
        if filters.username and log.username != filters.username:
            return False

        # Action filter
        if filters.action and filters.action.lower() not in log.action.lower():
            return False

        # Resource filters
        if filters.resource_type and log.resource_type != filters.resource_type:
            return False
        if filters.resource_id and log.resource_id != filters.resource_id:
            return False

        # IP address filter
        if filters.ip_address and log.ip_address != filters.ip_address:
            return False

        # Search filter (search in action, details, error_message)
        if filters.search:
            search_lower = filters.search.lower()
            search_fields = [
                log.action.lower() if log.action else "",
                str(log.details).lower() if log.details else "",
                log.error_message.lower() if log.error_message else ""
            ]
            if not any(search_lower in field for field in search_fields):
                return False

        return True

    def get_summary(self, filters: AuditLogFilter) -> AuditLogSummary:
        """
        Get summary statistics for audit logs.

        Args:
            filters: Filter criteria

        Returns:
            AuditLogSummary with statistics
        """
        # Get all matching logs
        logs = self.query_logs(AuditLogFilter(
            start_date=filters.start_date,
            end_date=filters.end_date,
            limit=10000  # Get more logs for summary
        ))

        # Count by level
        by_level = {}
        for log in logs:
            by_level[log.level] = by_level.get(log.level, 0) + 1

        # Count by category
        by_category = {}
        for log in logs:
            by_category[log.category] = by_category.get(log.category, 0) + 1

        # Count by user
        by_user = {}
        for log in logs:
            if log.username:
                by_user[log.username] = by_user.get(log.username, 0) + 1

        # Recent errors
        recent_errors = [
            log for log in logs
            if log.level in [AuditLevel.ERROR, AuditLevel.CRITICAL]
        ][:10]

        # Most active users
        most_active_users = [
            {"username": username, "count": count}
            for username, count in sorted(
                by_user.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        ]

        # Most common actions
        action_counts = {}
        for log in logs:
            action_counts[log.action] = action_counts.get(log.action, 0) + 1

        most_common_actions = [
            {"action": action, "count": count}
            for action, count in sorted(
                action_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        ]

        return AuditLogSummary(
            total_logs=len(logs),
            by_level=by_level,
            by_category=by_category,
            by_user=by_user,
            recent_errors=recent_errors,
            most_active_users=most_active_users,
            most_common_actions=most_common_actions
        )

    def cleanup_old_logs(self, days_to_keep: int = 90):
        """
        Delete audit logs older than specified days.

        Args:
            days_to_keep: Number of days to retain logs
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        for log_file in self.storage_dir.glob("audit_*.jsonl"):
            # Extract date from filename
            try:
                date_str = log_file.stem.replace("audit_", "")
                file_date = datetime.strptime(date_str, "%Y%m%d")

                if file_date < cutoff_date:
                    log_file.unlink()
                    print(f"Deleted old audit log: {log_file}")
            except Exception as e:
                print(f"Error processing {log_file}: {e}")

    def export_logs(self, filters: AuditLogFilter, format: str = "json") -> str:
        """
        Export audit logs to specified format.

        Args:
            filters: Filter criteria
            format: Export format (json, csv)

        Returns:
            Exported data as string
        """
        logs = self.query_logs(filters)

        if format == "json":
            return json.dumps(
                [log.model_dump() for log in logs],
                default=str,
                indent=2
            )
        elif format == "csv":
            import csv
            import io

            output = io.StringIO()
            if not logs:
                return output.getvalue()

            # Get all fields
            fieldnames = list(logs[0].model_dump().keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)

            writer.writeheader()
            for log in logs:
                row = log.model_dump()
                # Convert complex types to strings
                for key, value in row.items():
                    if isinstance(value, (dict, list)):
                        row[key] = json.dumps(value)
                writer.writerow(row)

            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")
