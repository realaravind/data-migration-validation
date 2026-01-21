"""
Audit Logger Service

Main service for logging audit events throughout the application.
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any
from .models import AuditLogCreate, AuditLevel, AuditCategory
from .storage import AuditLogStorage


class AuditLogger:
    """
    Centralized audit logging service.

    Usage:
        logger = AuditLogger()
        logger.log_authentication("user123", "login_success")
        logger.log_data_change("pipeline", "pipeline_abc", "create", user_id="user123")
    """

    _instance = None
    _storage = None

    def __new__(cls):
        """Singleton pattern to ensure single instance"""
        if cls._instance is None:
            cls._instance = super(AuditLogger, cls).__new__(cls)
            cls._storage = AuditLogStorage()
        return cls._instance

    def log(
        self,
        category: AuditCategory,
        action: str,
        level: AuditLevel = AuditLevel.INFO,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """
        Log an audit event.

        Args:
            category: Category of the event
            action: Action description
            level: Severity level
            user_id: User ID
            username: Username
            ip_address: Client IP address
            user_agent: Client user agent
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional details
            request_id: Request ID for correlation
            session_id: Session ID
            duration_ms: Operation duration in milliseconds
            status_code: HTTP status code
            error_message: Error message if applicable
        """
        log_entry = AuditLogCreate(
            timestamp=datetime.utcnow(),
            level=level,
            category=category,
            action=action,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            request_id=request_id,
            session_id=session_id,
            duration_ms=duration_ms,
            status_code=status_code,
            error_message=error_message
        )

        try:
            self._storage.add_log(log_entry)
        except Exception as e:
            # Don't let audit logging failures break the application
            print(f"Failed to write audit log: {e}")

    # Convenience methods for common audit events

    def log_authentication(
        self,
        user_id: str,
        action: str,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log authentication events (login, logout, token refresh)"""
        level = AuditLevel.INFO if success else AuditLevel.WARNING
        self.log(
            category=AuditCategory.AUTHENTICATION,
            action=action,
            level=level,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            details=details
        )

    def log_authorization(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        allowed: bool,
        username: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log authorization checks"""
        level = AuditLevel.INFO if allowed else AuditLevel.WARNING
        self.log(
            category=AuditCategory.AUTHORIZATION,
            action=action,
            level=level,
            user_id=user_id,
            username=username,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details
        )

    def log_api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: int,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log API requests"""
        level = AuditLevel.INFO
        if status_code >= 500:
            level = AuditLevel.ERROR
        elif status_code >= 400:
            level = AuditLevel.WARNING

        self.log(
            category=AuditCategory.API_REQUEST,
            action=f"{method} {path}",
            level=level,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            duration_ms=duration_ms,
            status_code=status_code,
            details=details
        )

    def log_data_change(
        self,
        resource_type: str,
        resource_id: str,
        operation: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log data modification events"""
        full_details = details or {}
        if before:
            full_details["before"] = before
        if after:
            full_details["after"] = after

        self.log(
            category=AuditCategory.DATA_CHANGE,
            action=f"{operation}_{resource_type}",
            level=AuditLevel.INFO,
            user_id=user_id,
            username=username,
            resource_type=resource_type,
            resource_id=resource_id,
            details=full_details
        )

    def log_validation_execution(
        self,
        pipeline_id: str,
        run_id: str,
        status: str,
        duration_ms: Optional[int] = None,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log validation pipeline execution"""
        level = AuditLevel.INFO
        if status == "failed":
            level = AuditLevel.ERROR
        elif status == "warning":
            level = AuditLevel.WARNING

        self.log(
            category=AuditCategory.VALIDATION,
            action=f"pipeline_execution_{status}",
            level=level,
            user_id=user_id,
            username=username,
            resource_type="pipeline",
            resource_id=pipeline_id,
            duration_ms=duration_ms,
            details={**(details or {}), "run_id": run_id}
        )

    def log_configuration_change(
        self,
        config_type: str,
        config_id: str,
        operation: str,
        user_id: str,
        username: Optional[str] = None,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None
    ):
        """Log configuration changes"""
        self.log(
            category=AuditCategory.CONFIGURATION,
            action=f"{operation}_{config_type}",
            level=AuditLevel.INFO,
            user_id=user_id,
            username=username,
            resource_type=config_type,
            resource_id=config_id,
            details={"before": before, "after": after}
        )

    def log_database_operation(
        self,
        database: str,
        operation: str,
        table: Optional[str] = None,
        user_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log database operations"""
        self.log(
            category=AuditCategory.DATABASE,
            action=f"{operation}_{database}",
            level=AuditLevel.DEBUG,
            user_id=user_id,
            resource_type="database",
            resource_id=table or database,
            duration_ms=duration_ms,
            details=details
        )

    def log_file_operation(
        self,
        operation: str,
        file_path: str,
        file_type: Optional[str] = None,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log file operations (upload, download, delete)"""
        self.log(
            category=AuditCategory.FILE_OPERATION,
            action=f"{operation}_file",
            level=AuditLevel.INFO,
            user_id=user_id,
            username=username,
            resource_type=file_type or "file",
            resource_id=file_path,
            details=details
        )

    def log_export(
        self,
        export_type: str,
        format: str,
        record_count: int,
        user_id: str,
        username: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log data exports"""
        self.log(
            category=AuditCategory.EXPORT,
            action=f"export_{export_type}",
            level=AuditLevel.INFO,
            user_id=user_id,
            username=username,
            resource_type="export",
            details={
                **(details or {}),
                "format": format,
                "record_count": record_count
            }
        )

    def log_error(
        self,
        error_message: str,
        action: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log system errors"""
        self.log(
            category=AuditCategory.SYSTEM,
            action=action,
            level=AuditLevel.ERROR,
            user_id=user_id,
            error_message=error_message,
            details=details
        )

    def log_system_event(
        self,
        action: str,
        level: AuditLevel = AuditLevel.INFO,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log general system events"""
        self.log(
            category=AuditCategory.SYSTEM,
            action=action,
            level=level,
            details=details
        )


# Global audit logger instance
audit_logger = AuditLogger()
