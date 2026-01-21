"""
Audit Log Data Models

Defines the schema and Pydantic models for audit logs.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class AuditLevel(str, Enum):
    """Audit log severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditCategory(str, Enum):
    """Categories of audit events"""
    AUTHENTICATION = "authentication"  # Login, logout, token refresh
    AUTHORIZATION = "authorization"    # Permission checks, access denied
    API_REQUEST = "api_request"        # API calls
    DATA_CHANGE = "data_change"        # Create, update, delete operations
    VALIDATION = "validation"          # Pipeline execution
    CONFIGURATION = "configuration"    # Config changes
    SYSTEM = "system"                  # System events, errors
    DATABASE = "database"              # Database operations
    FILE_OPERATION = "file_operation"  # File uploads, downloads
    EXPORT = "export"                  # Data exports


class AuditLogBase(BaseModel):
    """Base audit log model"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: AuditLevel = AuditLevel.INFO
    category: AuditCategory
    action: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    duration_ms: Optional[int] = None
    status_code: Optional[int] = None
    error_message: Optional[str] = None


class AuditLogCreate(AuditLogBase):
    """Model for creating audit logs"""
    pass


class AuditLog(AuditLogBase):
    """Full audit log model with ID"""
    id: str

    class Config:
        from_attributes = True


class AuditLogFilter(BaseModel):
    """Filters for querying audit logs"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    level: Optional[AuditLevel] = None
    category: Optional[AuditCategory] = None
    user_id: Optional[str] = None
    username: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    search: Optional[str] = None  # Search in action, details, error_message
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)
    sort_by: str = Field(default="timestamp")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class AuditLogSummary(BaseModel):
    """Summary statistics for audit logs"""
    total_logs: int
    by_level: Dict[str, int]
    by_category: Dict[str, int]
    by_user: Dict[str, int]
    recent_errors: List[AuditLog]
    most_active_users: List[Dict[str, Any]]
    most_common_actions: List[Dict[str, Any]]


class AuditLogExport(BaseModel):
    """Export configuration for audit logs"""
    format: str = Field(default="csv", pattern="^(csv|json|excel)$")
    filters: AuditLogFilter
    include_details: bool = True
