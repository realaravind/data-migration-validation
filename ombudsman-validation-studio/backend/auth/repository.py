"""
Authentication Repository - Database operations for user management.

Provides CRUD operations for:
- Users
- Refresh tokens
- API keys
- Audit logs
"""

import pyodbc
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List
import uuid
import json

from .models import (
    User, UserInDB, UserCreate, UserUpdate,
    RefreshToken, RefreshTokenCreate,
    ApiKey, ApiKeyCreate,
    AuditLogEntry, AuditLogCreate,
    UserRole, EventType
)
from .security import hash_password

logger = logging.getLogger(__name__)


class AuthRepository:
    """Repository for authentication and user management operations"""

    def __init__(self):
        """Initialize repository with database connection"""
        self.conn_str = os.getenv("SQLSERVER_CONN_STR")
        if not self.conn_str:
            logger.warning("SQLSERVER_CONN_STR not set, auth features may not work")

    def _get_connection(self) -> pyodbc.Connection:
        """Get database connection"""
        if not self.conn_str:
            raise ValueError("Database connection string not configured")
        return pyodbc.connect(self.conn_str)

    # ========================================================================
    # User Operations
    # ========================================================================

    def create_user(self, user_create: UserCreate) -> UserInDB:
        """
        Create a new user.

        Args:
            user_create: User creation data

        Returns:
            Created user with hashed password

        Raises:
            ValueError: If username or email already exists
        """
        # Check if username exists
        if self.get_user_by_username(user_create.username):
            raise ValueError(f"Username '{user_create.username}' already exists")

        # Check if email exists
        if self.get_user_by_email(user_create.email):
            raise ValueError(f"Email '{user_create.email}' already exists")

        # Generate user ID
        user_id = f"user_{uuid.uuid4()}"

        # Hash password
        hashed_password = hash_password(user_create.password)

        # Insert user
        query = """
        INSERT INTO Users (
            user_id, username, email, hashed_password, full_name, role, is_active, is_verified
        )
        VALUES (?, ?, ?, ?, ?, ?, 1, 0)
        """

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (
                user_id,
                user_create.username,
                user_create.email,
                hashed_password,
                user_create.full_name,
                user_create.role.value
            ))
            conn.commit()

            # Log the event
            self.log_audit_event(AuditLogCreate(
                user_id=user_id,
                event_type=EventType.USER_REGISTER,
                event_description=f"User {user_create.username} registered",
                success=True
            ))

            return self.get_user_by_id(user_id)

        finally:
            conn.close()

    def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID"""
        query = "SELECT * FROM Users WHERE user_id = ?"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_user(row, cursor.description)

        finally:
            conn.close()

    def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """Get user by username"""
        query = "SELECT * FROM Users WHERE username = ?"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (username.lower(),))
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_user(row, cursor.description)

        finally:
            conn.close()

    def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email"""
        query = "SELECT * FROM Users WHERE email = ?"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (email.lower(),))
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_user(row, cursor.description)

        finally:
            conn.close()

    def update_user(self, user_id: str, user_update: UserUpdate) -> Optional[UserInDB]:
        """Update user information"""
        updates = []
        params = []

        if user_update.email is not None:
            updates.append("email = ?")
            params.append(user_update.email)

        if user_update.full_name is not None:
            updates.append("full_name = ?")
            params.append(user_update.full_name)

        if user_update.role is not None:
            updates.append("role = ?")
            params.append(user_update.role.value)

        if user_update.is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if user_update.is_active else 0)

        if user_update.is_verified is not None:
            updates.append("is_verified = ?")
            params.append(1 if user_update.is_verified else 0)

        if not updates:
            return self.get_user_by_id(user_id)

        updates.append("updated_at = GETDATE()")
        params.append(user_id)

        query = f"UPDATE Users SET {', '.join(updates)} WHERE user_id = ?"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()

            return self.get_user_by_id(user_id)

        finally:
            conn.close()

    def delete_user(self, user_id: str) -> bool:
        """Delete user (and cascade delete tokens, api keys, audit logs)"""
        query = "DELETE FROM Users WHERE user_id = ?"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            conn.commit()

            return cursor.rowcount > 0

        finally:
            conn.close()

    def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None
    ) -> List[UserInDB]:
        """List users with optional filtering"""
        query = "SELECT * FROM Users WHERE 1=1"
        params = []

        if role is not None:
            query += " AND role = ?"
            params.append(role.value)

        if is_active is not None:
            query += " AND is_active = ?"
            params.append(1 if is_active else 0)

        query += " ORDER BY created_at DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([skip, limit])

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_user(row, cursor.description) for row in rows]

        finally:
            conn.close()

    def update_last_login(self, user_id: str):
        """Update user's last login timestamp"""
        query = "UPDATE Users SET last_login = GETDATE() WHERE user_id = ?"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            conn.commit()

        finally:
            conn.close()

    def increment_failed_login_attempts(self, user_id: str) -> int:
        """Increment failed login attempts and return new count"""
        query = """
        UPDATE Users
        SET failed_login_attempts = failed_login_attempts + 1
        WHERE user_id = ?
        """

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            conn.commit()

            # Get new count
            cursor.execute("SELECT failed_login_attempts FROM Users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return row[0] if row else 0

        finally:
            conn.close()

    def reset_failed_login_attempts(self, user_id: str):
        """Reset failed login attempts to 0"""
        query = "UPDATE Users SET failed_login_attempts = 0 WHERE user_id = ?"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            conn.commit()

        finally:
            conn.close()

    def lock_user(self, user_id: str, lock_duration_minutes: int = 30):
        """Lock user account"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("EXEC sp_LockUser ?, ?", (user_id, lock_duration_minutes))
            conn.commit()

        finally:
            conn.close()

    def unlock_user(self, user_id: str):
        """Unlock user account"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("EXEC sp_UnlockUser ?", (user_id,))
            conn.commit()

        finally:
            conn.close()

    # ========================================================================
    # Refresh Token Operations
    # ========================================================================

    def create_refresh_token(self, token_create: RefreshTokenCreate) -> RefreshToken:
        """Create a refresh token"""
        query = """
        INSERT INTO RefreshTokens (
            user_id, refresh_token, expires_at, device_info, ip_address
        )
        VALUES (?, ?, ?, ?, ?)
        """

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (
                token_create.user_id,
                token_create.refresh_token,
                token_create.expires_at,
                token_create.device_info,
                token_create.ip_address
            ))
            conn.commit()

            # Get the created token
            cursor.execute("SELECT * FROM RefreshTokens WHERE refresh_token = ?", (token_create.refresh_token,))
            row = cursor.fetchone()

            return self._row_to_refresh_token(row, cursor.description)

        finally:
            conn.close()

    def get_refresh_token(self, refresh_token: str) -> Optional[RefreshToken]:
        """Get refresh token by token value"""
        query = "SELECT * FROM RefreshTokens WHERE refresh_token = ?"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (refresh_token,))
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_refresh_token(row, cursor.description)

        finally:
            conn.close()

    def revoke_refresh_token(self, refresh_token: str):
        """Revoke a refresh token"""
        query = """
        UPDATE RefreshTokens
        SET is_revoked = 1, revoked_at = GETDATE()
        WHERE refresh_token = ?
        """

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (refresh_token,))
            conn.commit()

        finally:
            conn.close()

    def revoke_all_user_tokens(self, user_id: str):
        """Revoke all refresh tokens for a user"""
        query = """
        UPDATE RefreshTokens
        SET is_revoked = 1, revoked_at = GETDATE()
        WHERE user_id = ? AND is_revoked = 0
        """

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            conn.commit()

        finally:
            conn.close()

    def cleanup_expired_tokens(self) -> int:
        """Clean up expired and old revoked tokens"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("EXEC sp_CleanupExpiredTokens")
            result = cursor.fetchone()
            conn.commit()

            return result[0] if result else 0

        finally:
            conn.close()

    # ========================================================================
    # Audit Log Operations
    # ========================================================================

    def log_audit_event(self, audit_log: AuditLogCreate):
        """Log an audit event"""
        query = """
        INSERT INTO AuditLog (
            user_id, event_type, event_description, ip_address, user_agent, success, error_message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (
                audit_log.user_id,
                audit_log.event_type.value,
                audit_log.event_description,
                audit_log.ip_address,
                audit_log.user_agent,
                1 if audit_log.success else 0,
                audit_log.error_message
            ))
            conn.commit()

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            # Don't fail the main operation if audit logging fails

        finally:
            conn.close()

    def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """Get audit logs with optional filtering"""
        query = "SELECT * FROM AuditLog WHERE 1=1"
        params = []

        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)

        if event_type is not None:
            query += " AND event_type = ?"
            params.append(event_type.value)

        if start_date is not None:
            query += " AND created_at >= ?"
            params.append(start_date)

        if end_date is not None:
            query += " AND created_at <= ?"
            params.append(end_date)

        query += " ORDER BY created_at DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([skip, limit])

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_audit_log(row, cursor.description) for row in rows]

        finally:
            conn.close()

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _row_to_user(self, row, description) -> UserInDB:
        """Convert database row to UserInDB model"""
        columns = [column[0].lower() for column in description]
        data = dict(zip(columns, row))

        return UserInDB(
            user_id=data["user_id"],
            username=data["username"],
            email=data["email"],
            hashed_password=data["hashed_password"],
            full_name=data.get("full_name"),
            role=UserRole(data["role"]),
            is_active=bool(data["is_active"]),
            is_verified=bool(data["is_verified"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            last_login=data.get("last_login"),
            failed_login_attempts=data["failed_login_attempts"],
            locked_until=data.get("locked_until")
        )

    def _row_to_refresh_token(self, row, description) -> RefreshToken:
        """Convert database row to RefreshToken model"""
        columns = [column[0].lower() for column in description]
        data = dict(zip(columns, row))

        return RefreshToken(
            token_id=data["token_id"],
            user_id=data["user_id"],
            refresh_token=data["refresh_token"],
            expires_at=data["expires_at"],
            created_at=data["created_at"],
            revoked_at=data.get("revoked_at"),
            is_revoked=bool(data["is_revoked"]),
            device_info=data.get("device_info"),
            ip_address=data.get("ip_address")
        )

    def _row_to_audit_log(self, row, description) -> AuditLogEntry:
        """Convert database row to AuditLogEntry model"""
        columns = [column[0].lower() for column in description]
        data = dict(zip(columns, row))

        return AuditLogEntry(
            log_id=data["log_id"],
            user_id=data.get("user_id"),
            event_type=EventType(data["event_type"]),
            event_description=data.get("event_description"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            success=bool(data["success"]),
            error_message=data.get("error_message"),
            created_at=data["created_at"]
        )
