"""
SQLite Authentication Repository - Database operations for user management using SQLite.

Provides CRUD operations for:
- Users
- Refresh tokens
- Audit logs

This is a drop-in replacement for the SQL Server repository using SQLite3.
"""

import sqlite3
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import uuid
from pathlib import Path

from .models import (
    User, UserInDB, UserCreate, UserUpdate,
    RefreshToken, RefreshTokenCreate,
    AuditLogEntry, AuditLogCreate,
    UserRole, EventType
)
from .security import hash_password
from config.paths import paths

logger = logging.getLogger(__name__)

# Database file path - use centralized config
DB_DIR = str(paths.auth_dir)
DB_FILE = os.path.join(DB_DIR, "ombudsman_auth.db")


class SQLiteAuthRepository:
    """Repository for authentication and user management operations using SQLite"""

    def __init__(self):
        """Initialize repository and create database/tables if needed"""
        self.db_path = DB_FILE
        self._ensure_database_exists()
        self._create_tables()

    def _ensure_database_exists(self):
        """Ensure database directory and file exist"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(DB_DIR, exist_ok=True)
            logger.info(f"Database directory ensured at: {DB_DIR}")
        except Exception as e:
            logger.error(f"Failed to create database directory: {e}")
            raise

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn

    def _create_tables(self):
        """Create database tables if they don't exist"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    hashed_password TEXT NOT NULL,
                    full_name TEXT,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    is_verified INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_login TEXT,
                    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                    locked_until TEXT
                )
            """)

            # Refresh tokens table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    token_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    refresh_token TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    revoked_at TEXT,
                    is_revoked INTEGER NOT NULL DEFAULT 0,
                    device_info TEXT,
                    ip_address TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)

            # Audit log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    event_type TEXT NOT NULL,
                    event_description TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    success INTEGER NOT NULL,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token ON refresh_tokens(refresh_token)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_event_type ON audit_log(event_type)")

            conn.commit()
            logger.info("Database tables created/verified successfully")

        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
        finally:
            conn.close()

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

        # Current timestamp
        now = datetime.now(timezone.utc).isoformat()

        # Insert user
        query = """
        INSERT INTO users (
            user_id, username, email, hashed_password, full_name, role,
            is_active, is_verified, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 1, 0, ?, ?)
        """

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (
                user_id,
                user_create.username.lower(),
                user_create.email.lower(),
                hashed_password,
                user_create.full_name,
                user_create.role.value,
                now,
                now
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
        query = "SELECT * FROM users WHERE user_id = ?"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_user(row)

        finally:
            conn.close()

    def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """Get user by username"""
        query = "SELECT * FROM users WHERE username = ?"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (username.lower(),))
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_user(row)

        finally:
            conn.close()

    def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email"""
        query = "SELECT * FROM users WHERE email = ?"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (email.lower(),))
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_user(row)

        finally:
            conn.close()

    def update_user(self, user_id: str, user_update: UserUpdate) -> Optional[UserInDB]:
        """Update user information"""
        updates = []
        params = []

        if user_update.email is not None:
            updates.append("email = ?")
            params.append(user_update.email.lower())

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

        updates.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(user_id)

        query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()

            return self.get_user_by_id(user_id)

        finally:
            conn.close()

    def delete_user(self, user_id: str) -> bool:
        """Delete user (and cascade delete tokens, audit logs)"""
        query = "DELETE FROM users WHERE user_id = ?"

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
        query = "SELECT * FROM users WHERE 1=1"
        params = []

        if role is not None:
            query += " AND role = ?"
            params.append(role.value)

        if is_active is not None:
            query += " AND is_active = ?"
            params.append(1 if is_active else 0)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_user(row) for row in rows]

        finally:
            conn.close()

    def update_last_login(self, user_id: str):
        """Update user's last login timestamp"""
        query = "UPDATE users SET last_login = ? WHERE user_id = ?"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (datetime.now(timezone.utc).isoformat(), user_id))
            conn.commit()

        finally:
            conn.close()

    def increment_failed_login_attempts(self, user_id: str) -> int:
        """Increment failed login attempts and return new count"""
        query = """
        UPDATE users
        SET failed_login_attempts = failed_login_attempts + 1
        WHERE user_id = ?
        """

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            conn.commit()

            # Get new count
            cursor.execute("SELECT failed_login_attempts FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return row[0] if row else 0

        finally:
            conn.close()

    def reset_failed_login_attempts(self, user_id: str):
        """Reset failed login attempts to 0"""
        query = "UPDATE users SET failed_login_attempts = 0 WHERE user_id = ?"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            conn.commit()

        finally:
            conn.close()

    def lock_user(self, user_id: str, lock_duration_minutes: int = 30):
        """Lock user account"""
        locked_until = (datetime.now(timezone.utc) + timedelta(minutes=lock_duration_minutes)).isoformat()

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET locked_until = ?, updated_at = ? WHERE user_id = ?",
                (locked_until, datetime.now(timezone.utc).isoformat(), user_id)
            )
            conn.commit()

            # Log the event
            self.log_audit_event(AuditLogCreate(
                user_id=user_id,
                event_type=EventType.ACCOUNT_LOCKED,
                event_description="Account locked due to too many failed login attempts",
                success=True
            ))

        finally:
            conn.close()

    def unlock_user(self, user_id: str):
        """Unlock user account"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE users
                   SET locked_until = NULL, failed_login_attempts = 0, updated_at = ?
                   WHERE user_id = ?""",
                (datetime.now(timezone.utc).isoformat(), user_id)
            )
            conn.commit()

            # Log the event
            self.log_audit_event(AuditLogCreate(
                user_id=user_id,
                event_type=EventType.ACCOUNT_UNLOCKED,
                event_description="Account unlocked by administrator",
                success=True
            ))

        finally:
            conn.close()

    def update_password(self, user_id: str, new_password_hash: str):
        """Update user password"""
        query = "UPDATE users SET hashed_password = ?, updated_at = ? WHERE user_id = ?"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (new_password_hash, datetime.now(timezone.utc).isoformat(), user_id))
            conn.commit()

        finally:
            conn.close()

    # ========================================================================
    # Refresh Token Operations
    # ========================================================================

    def create_refresh_token(self, token_create: RefreshTokenCreate) -> RefreshToken:
        """Create a refresh token"""
        query = """
        INSERT INTO refresh_tokens (
            user_id, refresh_token, expires_at, device_info, ip_address, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """

        now = datetime.now(timezone.utc).isoformat()

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (
                token_create.user_id,
                token_create.refresh_token,
                token_create.expires_at.isoformat(),
                token_create.device_info,
                token_create.ip_address,
                now
            ))
            conn.commit()

            # Get the created token
            cursor.execute("SELECT * FROM refresh_tokens WHERE refresh_token = ?", (token_create.refresh_token,))
            row = cursor.fetchone()

            return self._row_to_refresh_token(row)

        finally:
            conn.close()

    def get_refresh_token(self, refresh_token: str) -> Optional[RefreshToken]:
        """Get refresh token by token value"""
        query = "SELECT * FROM refresh_tokens WHERE refresh_token = ?"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (refresh_token,))
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_refresh_token(row)

        finally:
            conn.close()

    def revoke_refresh_token(self, refresh_token: str):
        """Revoke a refresh token"""
        query = """
        UPDATE refresh_tokens
        SET is_revoked = 1, revoked_at = ?
        WHERE refresh_token = ?
        """

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (datetime.now(timezone.utc).isoformat(), refresh_token))
            conn.commit()

        finally:
            conn.close()

    def revoke_all_user_tokens(self, user_id: str):
        """Revoke all refresh tokens for a user"""
        query = """
        UPDATE refresh_tokens
        SET is_revoked = 1, revoked_at = ?
        WHERE user_id = ? AND is_revoked = 0
        """

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (datetime.now(timezone.utc).isoformat(), user_id))
            conn.commit()

        finally:
            conn.close()

    def cleanup_expired_tokens(self) -> int:
        """Clean up expired and old revoked tokens"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            now = datetime.now(timezone.utc).isoformat()
            thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

            # Delete expired tokens
            cursor.execute("DELETE FROM refresh_tokens WHERE expires_at < ?", (now,))
            count1 = cursor.rowcount

            # Delete revoked tokens older than 30 days
            cursor.execute(
                "DELETE FROM refresh_tokens WHERE is_revoked = 1 AND revoked_at < ?",
                (thirty_days_ago,)
            )
            count2 = cursor.rowcount

            conn.commit()
            return count1 + count2

        finally:
            conn.close()

    # ========================================================================
    # Audit Log Operations
    # ========================================================================

    def log_audit_event(self, audit_log: AuditLogCreate):
        """Log an audit event"""
        query = """
        INSERT INTO audit_log (
            user_id, event_type, event_description, ip_address, user_agent, success, error_message, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
                audit_log.error_message,
                datetime.now(timezone.utc).isoformat()
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
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []

        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)

        if event_type is not None:
            query += " AND event_type = ?"
            params.append(event_type.value)

        if start_date is not None:
            query += " AND created_at >= ?"
            params.append(start_date.isoformat())

        if end_date is not None:
            query += " AND created_at <= ?"
            params.append(end_date.isoformat())

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_audit_log(row) for row in rows]

        finally:
            conn.close()

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _row_to_user(self, row) -> UserInDB:
        """Convert database row to UserInDB model"""
        return UserInDB(
            user_id=row["user_id"],
            username=row["username"],
            email=row["email"],
            hashed_password=row["hashed_password"],
            full_name=row["full_name"],
            role=UserRole(row["role"]),
            is_active=bool(row["is_active"]),
            is_verified=bool(row["is_verified"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_login=datetime.fromisoformat(row["last_login"]) if row["last_login"] else None,
            failed_login_attempts=row["failed_login_attempts"],
            locked_until=datetime.fromisoformat(row["locked_until"]) if row["locked_until"] else None
        )

    def _row_to_refresh_token(self, row) -> RefreshToken:
        """Convert database row to RefreshToken model"""
        return RefreshToken(
            token_id=str(row["token_id"]),  # Convert int to string for Pydantic validation
            user_id=row["user_id"],
            refresh_token=row["refresh_token"],
            expires_at=datetime.fromisoformat(row["expires_at"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            revoked_at=datetime.fromisoformat(row["revoked_at"]) if row["revoked_at"] else None,
            is_revoked=bool(row["is_revoked"]),
            device_info=row["device_info"],
            ip_address=row["ip_address"]
        )

    def _row_to_audit_log(self, row) -> AuditLogEntry:
        """Convert database row to AuditLogEntry model"""
        return AuditLogEntry(
            log_id=row["log_id"],
            user_id=row["user_id"],
            event_type=EventType(row["event_type"]),
            event_description=row["event_description"],
            ip_address=row["ip_address"],
            user_agent=row["user_agent"],
            success=bool(row["success"]),
            error_message=row["error_message"],
            created_at=datetime.fromisoformat(row["created_at"])
        )
