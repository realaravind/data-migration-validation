"""Alert service for capturing errors and providing fix suggestions."""

import re
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertCategory(str, Enum):
    CONNECTION = "connection"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    SYSTEM = "system"


@dataclass
class FixSuggestion:
    """A suggested fix for an error."""
    title: str
    description: str
    steps: List[str]
    code_snippet: Optional[str] = None
    doc_link: Optional[str] = None


@dataclass
class Alert:
    """An alert with error details and fix suggestions."""
    id: str
    timestamp: str
    severity: AlertSeverity
    category: AlertCategory
    title: str
    message: str
    source: str
    details: Optional[Dict[str, Any]] = None
    suggestions: List[FixSuggestion] = field(default_factory=list)
    read: bool = False
    action_url: Optional[str] = None  # URL for quick action (e.g., re-auth)
    action_label: Optional[str] = None  # Label for the action button

    def to_dict(self) -> Dict:
        data = asdict(self)
        data['severity'] = self.severity.value
        data['category'] = self.category.value
        return data


# Error patterns and their fix suggestions
ERROR_PATTERNS = [
    # Snowflake permission errors
    {
        "pattern": r"(Insufficient privileges|Access Denied|INVALID_GRANT|Object .* does not exist or not authorized)",
        "category": AlertCategory.PERMISSION,
        "title": "Snowflake Permission Error",
        "suggestions": [
            FixSuggestion(
                title="Grant Required Permissions",
                description="Your Snowflake role lacks necessary permissions to access the requested resources.",
                steps=[
                    "Connect to Snowflake with an ACCOUNTADMIN role",
                    "Grant USAGE on the required database: GRANT USAGE ON DATABASE <db_name> TO ROLE <your_role>;",
                    "Grant USAGE on schemas: GRANT USAGE ON ALL SCHEMAS IN DATABASE <db_name> TO ROLE <your_role>;",
                    "Grant SELECT on tables: GRANT SELECT ON ALL TABLES IN DATABASE <db_name> TO ROLE <your_role>;",
                    "Or use ACCOUNTADMIN role in your environment config: SNOWFLAKE_ROLE=ACCOUNTADMIN"
                ],
                code_snippet="""-- Run in Snowflake as ACCOUNTADMIN
GRANT USAGE ON DATABASE your_db TO ROLE your_role;
GRANT USAGE ON ALL SCHEMAS IN DATABASE your_db TO ROLE your_role;
GRANT SELECT ON ALL TABLES IN DATABASE your_db TO ROLE your_role;

-- For full visibility across all databases:
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE your_role;""",
                doc_link="https://docs.snowflake.com/en/user-guide/security-access-control-privileges"
            )
        ]
    },
    # Snowflake OAuth errors
    {
        "pattern": r"(Invalid OAuth access token|OAuth token expired|invalid_grant|token-request failed|400.*token-request|Failed to get OAuth token)",
        "category": AlertCategory.AUTHENTICATION,
        "title": "Snowflake OAuth Token Expired",
        "action_url": "/oauth/snowflake/authorize",
        "action_label": "Re-authenticate with Snowflake",
        "suggestions": [
            FixSuggestion(
                title="One-Click Re-authentication",
                description="Your Snowflake OAuth refresh token has expired. Click the button above or use the link below to re-authenticate.",
                steps=[
                    "Click 'Re-authenticate with Snowflake' button",
                    "Sign in to Snowflake when prompted",
                    "Authorize the application",
                    "The token will be automatically saved"
                ],
                doc_link="https://docs.snowflake.com/en/user-guide/oauth-custom"
            )
        ]
    },
    # Snowflake connection errors
    {
        "pattern": r"(Failed to connect to Snowflake|snowflake.*connection.*failed|Could not connect to Snowflake)",
        "category": AlertCategory.CONNECTION,
        "title": "Snowflake Connection Failed",
        "suggestions": [
            FixSuggestion(
                title="Check Snowflake Connection Settings",
                description="Unable to establish connection to Snowflake.",
                steps=[
                    "Verify SNOWFLAKE_ACCOUNT is correct (format: <account>.<region> or <orgname>-<account_name>)",
                    "Check SNOWFLAKE_USER is a valid username",
                    "Verify authentication method (password, OAuth, or token)",
                    "Ensure network allows outbound HTTPS to Snowflake",
                    "Check if MFA is required - use OAuth for MFA-enabled accounts"
                ],
                doc_link="https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-connect"
            )
        ]
    },
    # SQL Server connection errors
    {
        "pattern": r"(Cannot open database|Login failed for user|SQL Server.*connection|TCP Provider.*error|ODBC Driver.*error)",
        "category": AlertCategory.CONNECTION,
        "title": "SQL Server Connection Failed",
        "suggestions": [
            FixSuggestion(
                title="Check SQL Server Connection",
                description="Unable to connect to SQL Server database.",
                steps=[
                    "Verify MSSQL_HOST and MSSQL_PORT are correct",
                    "Check MSSQL_USER and MSSQL_PASSWORD credentials",
                    "Ensure MSSQL_DATABASE exists and user has access",
                    "Verify SQL Server allows remote connections",
                    "Check firewall rules allow connection on the specified port",
                    "Ensure ODBC Driver 18 for SQL Server is installed"
                ],
                code_snippet="""# Test connection from command line:
sqlcmd -S <host>,<port> -U <user> -P <password> -d <database> -Q "SELECT 1"

# Or with Python:
python -c "import pyodbc; pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=<host>,<port>;DATABASE=<database>;UID=<user>;PWD=<password>;TrustServerCertificate=yes')" """
            )
        ]
    },
    # SQL Server permission errors
    {
        "pattern": r"(SELECT permission denied|permission was denied|not have permission|access is denied.*sql)",
        "category": AlertCategory.PERMISSION,
        "title": "SQL Server Permission Error",
        "suggestions": [
            FixSuggestion(
                title="Grant SQL Server Permissions",
                description="Your SQL Server user lacks required permissions.",
                steps=[
                    "Connect to SQL Server as sa or admin user",
                    "Grant SELECT permission on required tables",
                    "Or assign db_datareader role for read access to all tables"
                ],
                code_snippet="""-- Grant read access to specific database
USE [your_database];
EXEC sp_addrolemember 'db_datareader', 'your_user';

-- Or grant SELECT on specific schema
GRANT SELECT ON SCHEMA::dbo TO your_user;"""
            )
        ]
    },
    # Configuration errors
    {
        "pattern": r"(Environment variable .* not set|Missing required config|configuration error|Invalid configuration)",
        "category": AlertCategory.CONFIGURATION,
        "title": "Configuration Error",
        "suggestions": [
            FixSuggestion(
                title="Check Environment Configuration",
                description="Required configuration is missing or invalid.",
                steps=[
                    "Review your ombudsman.env file",
                    "Ensure all required environment variables are set",
                    "Run ./start-ombudsman.sh edit-secrets to update configuration",
                    "Restart the backend after changes"
                ]
            )
        ]
    },
    # LLM/AI errors
    {
        "pattern": r"(Ollama.*connection|OpenAI.*error|API key.*invalid|LLM.*failed|insufficient_quota)",
        "category": AlertCategory.CONFIGURATION,
        "title": "LLM Provider Error",
        "suggestions": [
            FixSuggestion(
                title="Check LLM Configuration",
                description="Error connecting to or using the LLM provider.",
                steps=[
                    "Verify LLM_PROVIDER is set correctly (ollama, openai, azure_openai, anthropic)",
                    "For Ollama: ensure Ollama is running (ollama serve)",
                    "For OpenAI: verify OPENAI_API_KEY is valid and has credits",
                    "For Azure OpenAI: check endpoint, key, and deployment name",
                    "Check network connectivity to the LLM provider"
                ]
            )
        ]
    }
]


class AlertService:
    """Service for managing alerts and providing fix suggestions."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._alerts: List[Alert] = []
        self._alert_id_counter = 0
        self._max_alerts = 100  # Keep last 100 alerts
        self._initialized = True

    def _generate_id(self) -> str:
        self._alert_id_counter += 1
        return f"alert_{self._alert_id_counter}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    def _match_error_pattern(self, error_message: str) -> Optional[Dict]:
        """Match error message against known patterns."""
        for pattern_config in ERROR_PATTERNS:
            if re.search(pattern_config["pattern"], error_message, re.IGNORECASE):
                return pattern_config
        return None

    def add_alert(
        self,
        message: str,
        source: str,
        severity: AlertSeverity = AlertSeverity.ERROR,
        category: Optional[AlertCategory] = None,
        title: Optional[str] = None,
        details: Optional[Dict] = None,
        dedupe_minutes: int = 5,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None
    ) -> Optional[Alert]:
        """Add a new alert with automatic fix suggestions.

        Args:
            dedupe_minutes: Don't add duplicate alerts from same source within this time window.
                           Set to 0 to disable deduplication.
            action_url: Optional URL for quick action button (e.g., re-auth link)
            action_label: Optional label for the action button
        """
        # Deduplication: check if we already have a recent alert from this source
        if dedupe_minutes > 0:
            from datetime import timedelta
            now = datetime.utcnow()
            for existing in self._alerts:
                if existing.source == source:
                    existing_time = datetime.fromisoformat(existing.timestamp.rstrip('Z'))
                    if (now - existing_time) < timedelta(minutes=dedupe_minutes):
                        logger.debug(f"Skipping duplicate alert from {source} (within {dedupe_minutes}m window)")
                        return None

        # Try to match against known patterns
        pattern_match = self._match_error_pattern(message)

        # Use provided action_url/action_label or fall back to pattern match
        final_action_url = action_url
        final_action_label = action_label

        if pattern_match:
            category = category or pattern_match["category"]
            title = title or pattern_match["title"]
            suggestions = pattern_match.get("suggestions", [])
            if not final_action_url:
                final_action_url = pattern_match.get("action_url")
            if not final_action_label:
                final_action_label = pattern_match.get("action_label")
        else:
            category = category or AlertCategory.SYSTEM
            title = title or "System Error"
            suggestions = []

        alert = Alert(
            id=self._generate_id(),
            timestamp=datetime.utcnow().isoformat() + "Z",
            severity=severity,
            category=category,
            title=title,
            message=message,
            source=source,
            details=details,
            suggestions=suggestions,
            action_url=final_action_url,
            action_label=final_action_label
        )

        self._alerts.insert(0, alert)  # Add to front (newest first)

        # Trim old alerts
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[:self._max_alerts]

        logger.info(f"Alert added: [{severity.value}] {title} - {message[:100]}")
        return alert

    def add_error(self, error: Exception, source: str, details: Optional[Dict] = None) -> Alert:
        """Convenience method to add an alert from an exception."""
        return self.add_alert(
            message=str(error),
            source=source,
            severity=AlertSeverity.ERROR,
            details=details
        )

    def get_alerts(
        self,
        unread_only: bool = False,
        severity: Optional[AlertSeverity] = None,
        category: Optional[AlertCategory] = None,
        limit: int = 50
    ) -> List[Alert]:
        """Get alerts with optional filtering."""
        alerts = self._alerts

        if unread_only:
            alerts = [a for a in alerts if not a.read]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        if category:
            alerts = [a for a in alerts if a.category == category]

        return alerts[:limit]

    def get_unread_count(self) -> int:
        """Get count of unread alerts."""
        return len([a for a in self._alerts if not a.read])

    def mark_read(self, alert_id: str) -> bool:
        """Mark an alert as read."""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.read = True
                return True
        return False

    def mark_all_read(self) -> int:
        """Mark all alerts as read. Returns count marked."""
        count = 0
        for alert in self._alerts:
            if not alert.read:
                alert.read = True
                count += 1
        return count

    def clear_alerts(self) -> int:
        """Clear all alerts. Returns count cleared."""
        count = len(self._alerts)
        self._alerts = []
        return count

    def delete_alert(self, alert_id: str) -> bool:
        """Delete a specific alert."""
        for i, alert in enumerate(self._alerts):
            if alert.id == alert_id:
                self._alerts.pop(i)
                return True
        return False


# Global singleton instance
alert_service = AlertService()
