"""
SQL Server Authentication Repository - Complete implementation matching SQLite interface
"""

import os
import pyodbc
import uuid
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from .models import (
    UserCreate, UserUpdate, UserInDB, UserRole,
    RefreshTokenCreate, RefreshToken,
    AuditLogCreate, AuditLogEntry, EventType
)
from .security import hash_password


# SQL Server Connection Configuration - MUST be set via environment variables
DB_SERVER = os.getenv("AUTH_DB_SERVER")
DB_NAME = os.getenv("AUTH_DB_NAME")
DB_USER = os.getenv("AUTH_DB_USER")
DB_PASSWORD = os.getenv("AUTH_DB_PASSWORD")

# Validate required environment variables at module load
if not all([DB_SERVER, DB_NAME, DB_USER, DB_PASSWORD]):
    missing = []
    if not DB_SERVER: missing.append("AUTH_DB_SERVER")
    if not DB_NAME: missing.append("AUTH_DB_NAME")
    if not DB_USER: missing.append("AUTH_DB_USER")
    if not DB_PASSWORD: missing.append("AUTH_DB_PASSWORD")
    print(f"⚠️  WARNING: Missing authentication DB environment variables: {', '.join(missing)}")
    print("Authentication features will not work until these are configured in .env file")


class SQLServerAuthRepository:
    """SQL Server-based authentication repository matching SQLite interface"""

    def __init__(self):
        """Initialize SQL Server connection"""
        self.conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={DB_SERVER};"
            f"DATABASE={DB_NAME};"
            f"UID={DB_USER};"
            f"PWD={DB_PASSWORD};"
            f"TrustServerCertificate=yes;"
        )
        # Tables should already exist from our setup

    def _get_connection(self):
        """Get database connection"""
        return pyodbc.connect(self.conn_str)

    # ========================================================================
    # User Management
    # ========================================================================

    def create_user(self, user_create: UserCreate) -> UserInDB:
        """Create a new user"""
        # Check if username exists
        if self.get_user_by_username(user_create.username):
            raise ValueError(f"Username '{user_create.username}' already exists")

        # Check if email exists
        if self.get_user_by_email(user_create.email):
            raise ValueError(f"Email '{user_create.email}' already exists")

        conn = self._get_connection()
        cursor = conn.cursor()

        user_id = f"user_{uuid.uuid4().hex[:16]}"
        hashed_password = hash_password(user_create.password)
        now = datetime.now(timezone.utc)

        cursor.execute('''
            INSERT INTO users (
                user_id, username, email, hashed_password, full_name,
                role, is_active, is_verified, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            user_create.username,
            user_create.email,
            hashed_password,
            user_create.full_name,
            user_create.role.value if user_create.role else "user",
            1,  # is_active
            0,  # is_verified
            now,
            now
        ))

        conn.commit()
        conn.close()

        return self.get_user_by_id(user_id)

    def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_user(row)
        return None

    def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """Get user by username"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_user(row)
        return None

    def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_user(row)
        return None

    def update_user(self, user_id: str, user_update: UserUpdate) -> Optional[UserInDB]:
        """Update user information"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        conn = self._get_connection()
        cursor = conn.cursor()

        # Build update query dynamically
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

        updates.append("updated_at = ?")
        params.append(datetime.now(timezone.utc))

        params.append(user_id)

        query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
        cursor.execute(query, params)

        conn.commit()
        conn.close()

        return self.get_user_by_id(user_id)

    def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        rows_affected = cursor.rowcount

        conn.commit()
        conn.close()

        return rows_affected > 0

    def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None
    ) -> List[UserInDB]:
        """List users with filtering"""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM users WHERE 1=1"
        params = []

        if role is not None:
            query += " AND role = ?"
            params.append(role.value)

        if is_active is not None:
            query += " AND is_active = ?"
            params.append(1 if is_active else 0)

        query += f" ORDER BY created_at DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([skip, limit])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_user(row) for row in rows]

    def update_last_login(self, user_id: str):
        """Update user's last login timestamp"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users SET last_login = ? WHERE user_id = ?
        ''', (datetime.now(timezone.utc), user_id))

        conn.commit()
        conn.close()

    def increment_failed_login_attempts(self, user_id: str) -> int:
        """Increment failed login attempts and return new count"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users
            SET failed_login_attempts = ISNULL(failed_login_attempts, 0) + 1
            WHERE user_id = ?
        ''', (user_id,))

        cursor.execute('SELECT failed_login_attempts FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()

        conn.commit()
        conn.close()

        return row[0] if row else 0

    def reset_failed_login_attempts(self, user_id: str):
        """Reset failed login attempts to 0"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users SET failed_login_attempts = 0 WHERE user_id = ?
        ''', (user_id,))

        conn.commit()
        conn.close()

    def lock_user(self, user_id: str, lock_duration_minutes: int = 30):
        """Lock user account for specified duration"""
        conn = self._get_connection()
        cursor = conn.cursor()

        locked_until = datetime.now(timezone.utc) + timedelta(minutes=lock_duration_minutes)

        cursor.execute('''
            UPDATE users SET locked_until = ? WHERE user_id = ?
        ''', (locked_until, user_id))

        conn.commit()
        conn.close()

    def unlock_user(self, user_id: str):
        """Unlock user account"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users SET locked_until = NULL WHERE user_id = ?
        ''', (user_id,))

        conn.commit()
        conn.close()

    def update_password(self, user_id: str, new_password_hash: str):
        """Update user password"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users SET hashed_password = ?, updated_at = ?
            WHERE user_id = ?
        ''', (new_password_hash, datetime.now(timezone.utc), user_id))

        conn.commit()
        conn.close()

    # ========================================================================
    # Refresh Token Management
    # ========================================================================

    def create_refresh_token(self, token_create: RefreshTokenCreate) -> RefreshToken:
        """Create a refresh token"""
        conn = self._get_connection()
        cursor = conn.cursor()

        token_id = f"token_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)

        cursor.execute('''
            INSERT INTO refresh_tokens (
                token_id, user_id, refresh_token, expires_at,
                device_info, ip_address, created_at, is_revoked
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            token_id,
            token_create.user_id,
            token_create.refresh_token,
            token_create.expires_at,
            token_create.device_info,
            token_create.ip_address,
            now,
            0  # is_revoked
        ))

        conn.commit()
        conn.close()

        return self.get_refresh_token(token_create.refresh_token)

    def get_refresh_token(self, refresh_token: str) -> Optional[RefreshToken]:
        """Get refresh token by token string"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM refresh_tokens WHERE refresh_token = ?
        ''', (refresh_token,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_refresh_token(row)
        return None

    def revoke_refresh_token(self, refresh_token: str):
        """Revoke a refresh token"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE refresh_tokens SET is_revoked = 1 WHERE refresh_token = ?
        ''', (refresh_token,))

        conn.commit()
        conn.close()

    def revoke_all_user_tokens(self, user_id: str):
        """Revoke all refresh tokens for a user"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE refresh_tokens SET is_revoked = 1 WHERE user_id = ?
        ''', (user_id,))

        conn.commit()
        conn.close()

    def cleanup_expired_tokens(self) -> int:
        """Delete expired refresh tokens"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM refresh_tokens WHERE expires_at < ?
        ''', (datetime.now(timezone.utc),))

        rows_deleted = cursor.rowcount

        conn.commit()
        conn.close()

        return rows_deleted

    # ========================================================================
    # Audit Logging
    # ========================================================================

    def log_audit_event(self, audit_log: AuditLogCreate):
        """Log an audit event"""
        conn = self._get_connection()
        cursor = conn.cursor()

        log_id = f"log_{uuid.uuid4().hex[:16]}"

        cursor.execute('''
            INSERT INTO audit_logs (
                log_id, user_id, event_type, event_description,
                ip_address, user_agent, success, error_message, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            log_id,
            audit_log.user_id,
            audit_log.event_type.value if audit_log.event_type else None,
            audit_log.event_description,
            audit_log.ip_address,
            audit_log.user_agent,
            1 if audit_log.success else 0,
            audit_log.error_message,
            datetime.now(timezone.utc)
        ))

        conn.commit()
        conn.close()

    def get_audit_logs(
        self,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[str] = None,
        event_type: Optional[EventType] = None
    ) -> List[AuditLogEntry]:
        """Get audit logs with filtering"""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)

        query += f" ORDER BY created_at DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([skip, limit])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_audit_log(row) for row in rows]

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _row_to_user(self, row) -> UserInDB:
        """Convert database row to UserInDB model"""
        # Convert locked_until to timezone-aware if present
        locked_until = None
        if len(row) > 12 and row[12]:
            locked_until = row[12].replace(tzinfo=timezone.utc) if row[12].tzinfo is None else row[12]

        return UserInDB(
            user_id=row[0],
            username=row[1],
            email=row[2],
            hashed_password=row[3],
            full_name=row[4],
            role=UserRole(row[5]) if row[5] else UserRole.USER,
            is_active=bool(row[6]),
            created_at=row[7] if len(row) > 7 and row[7] else datetime.now(timezone.utc),
            updated_at=row[8] if len(row) > 8 and row[8] else datetime.now(timezone.utc),
            is_verified=bool(row[9]) if len(row) > 9 and row[9] is not None else False,
            last_login=row[10] if len(row) > 10 and row[10] else None,
            failed_login_attempts=row[11] if len(row) > 11 and row[11] is not None else 0,
            locked_until=locked_until
        )

    def _row_to_refresh_token(self, row) -> RefreshToken:
        """Convert database row to RefreshToken model"""
        return RefreshToken(
            token_id=row[0],
            user_id=row[1],
            refresh_token=row[2],
            expires_at=row[3],
            device_info=row[4],
            ip_address=row[5],
            created_at=row[6],
            is_revoked=bool(row[7])
        )

    def _row_to_audit_log(self, row) -> AuditLogEntry:
        """Convert database row to AuditLogEntry model"""
        return AuditLogEntry(
            log_id=row[0],
            user_id=row[1],
            event_type=EventType(row[2]) if row[2] else None,
            event_description=row[3],
            ip_address=row[4],
            user_agent=row[5],
            success=bool(row[6]),
            error_message=row[7],
            created_at=row[8]
        )
