"""
SQL Server repository for authentication data.

Uses SQL Server database instead of SQLite for production deployments.
"""

import os
import sys
import pyodbc
from typing import Optional, List
from datetime import datetime, timezone
from .models import User, RefreshToken, ApiKey, UserRole


# SQL Server Connection Configuration - MUST be set via environment variables
DB_SERVER = os.getenv("AUTH_DB_SERVER")
DB_NAME = os.getenv("AUTH_DB_NAME")
DB_USER = os.getenv("AUTH_DB_USER")
DB_PASSWORD = os.getenv("AUTH_DB_PASSWORD")

# Validate required environment variables
if not all([DB_SERVER, DB_NAME, DB_USER, DB_PASSWORD]):
    missing = []
    if not DB_SERVER: missing.append("AUTH_DB_SERVER")
    if not DB_NAME: missing.append("AUTH_DB_NAME")
    if not DB_USER: missing.append("AUTH_DB_USER")
    if not DB_PASSWORD: missing.append("AUTH_DB_PASSWORD")
    print(f"❌ ERROR: Missing required environment variables: {', '.join(missing)}")
    print("Please configure authentication database connection in .env file")
    # Don't exit here - let the application start and fail gracefully on first connection attempt


def get_connection():
    """Get SQL Server database connection"""
    if not all([DB_SERVER, DB_NAME, DB_USER, DB_PASSWORD]):
        raise ValueError("Authentication database not configured. Please set AUTH_DB_SERVER, AUTH_DB_NAME, AUTH_DB_USER, and AUTH_DB_PASSWORD environment variables.")

    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
        f"TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)


# ============================================================================
# User Repository
# ============================================================================

def create_user(user: User) -> bool:
    """Create a new user"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO users (user_id, username, email, hashed_password, full_name, role, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user.user_id,
            user.username,
            user.email,
            user.hashed_password,
            user.full_name,
            user.role.value if user.role else "user",
            1 if user.is_active else 0,
            user.created_at,
            user.updated_at
        ))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating user: {e}")
        return False


def get_user_by_username(username: str) -> Optional[User]:
    """Get user by username"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return User(
                user_id=row[0],
                username=row[1],
                email=row[2],
                hashed_password=row[3],
                full_name=row[4],
                role=UserRole(row[5]) if row[5] else UserRole.USER,
                is_active=bool(row[6]),
                created_at=row[7],
                updated_at=row[8]
            )
        return None
    except Exception as e:
        print(f"Error getting user by username: {e}")
        return None


def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return User(
                user_id=row[0],
                username=row[1],
                email=row[2],
                hashed_password=row[3],
                full_name=row[4],
                role=UserRole(row[5]) if row[5] else UserRole.USER,
                is_active=bool(row[6]),
                created_at=row[7],
                updated_at=row[8]
            )
        return None
    except Exception as e:
        print(f"Error getting user by email: {e}")
        return None


def get_user_by_id(user_id: str) -> Optional[User]:
    """Get user by user_id"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return User(
                user_id=row[0],
                username=row[1],
                email=row[2],
                hashed_password=row[3],
                full_name=row[4],
                role=UserRole(row[5]) if row[5] else UserRole.USER,
                is_active=bool(row[6]),
                created_at=row[7],
                updated_at=row[8]
            )
        return None
    except Exception as e:
        print(f"Error getting user by id: {e}")
        return None


def update_user(user: User) -> bool:
    """Update user information"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users
            SET email = ?, hashed_password = ?, full_name = ?, role = ?,
                is_active = ?, updated_at = ?
            WHERE user_id = ?
        ''', (
            user.email,
            user.hashed_password,
            user.full_name,
            user.role.value if user.role else "user",
            1 if user.is_active else 0,
            datetime.now(timezone.utc),
            user.user_id
        ))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating user: {e}")
        return False


def delete_user(user_id: str) -> bool:
    """Delete a user"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False


def list_users() -> List[User]:
    """List all users"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()

        users = []
        for row in rows:
            users.append(User(
                user_id=row[0],
                username=row[1],
                email=row[2],
                hashed_password=row[3],
                full_name=row[4],
                role=UserRole(row[5]) if row[5] else UserRole.USER,
                is_active=bool(row[6]),
                created_at=row[7],
                updated_at=row[8]
            ))
        return users
    except Exception as e:
        print(f"Error listing users: {e}")
        return []


# ============================================================================
# Session Repository
# ============================================================================

def create_session(session: Session) -> bool:
    """Create a new session"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO sessions (session_id, user_id, refresh_token, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            session.session_id,
            session.user_id,
            session.refresh_token,
            session.created_at,
            session.expires_at
        ))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating session: {e}")
        return False


def get_session(session_id: str) -> Optional[Session]:
    """Get session by session_id"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return Session(
                session_id=row[0],
                user_id=row[1],
                refresh_token=row[2],
                created_at=row[3],
                expires_at=row[4]
            )
        return None
    except Exception as e:
        print(f"Error getting session: {e}")
        return None


def delete_session(session_id: str) -> bool:
    """Delete a session"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting session: {e}")
        return False


def delete_user_sessions(user_id: str) -> bool:
    """Delete all sessions for a user"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting user sessions: {e}")
        return False


# ============================================================================
# API Key Repository
# ============================================================================

def create_api_key(api_key: APIKey) -> bool:
    """Create a new API key"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO api_keys (key_id, user_id, key_name, key_hash, key_prefix,
                                  created_at, expires_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            api_key.key_id,
            api_key.user_id,
            api_key.key_name,
            api_key.key_hash,
            api_key.key_prefix,
            api_key.created_at,
            api_key.expires_at,
            1 if api_key.is_active else 0
        ))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating API key: {e}")
        return False


def get_api_key_by_prefix(key_prefix: str) -> Optional[APIKey]:
    """Get API key by prefix"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM api_keys WHERE key_prefix = ? AND is_active = 1', (key_prefix,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return APIKey(
                key_id=row[0],
                user_id=row[1],
                key_name=row[2],
                key_hash=row[3],
                key_prefix=row[4],
                created_at=row[5],
                expires_at=row[6],
                last_used_at=row[7],
                is_active=bool(row[8])
            )
        return None
    except Exception as e:
        print(f"Error getting API key: {e}")
        return None


def update_api_key_last_used(key_id: str) -> bool:
    """Update API key last used timestamp"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE api_keys
            SET last_used_at = ?
            WHERE key_id = ?
        ''', (datetime.now(timezone.utc), key_id))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating API key: {e}")
        return False


def delete_api_key(key_id: str) -> bool:
    """Delete an API key"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM api_keys WHERE key_id = ?', (key_id,))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting API key: {e}")
        return False


def list_user_api_keys(user_id: str) -> List[APIKey]:
    """List all API keys for a user"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM api_keys WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        rows = cursor.fetchall()
        conn.close()

        api_keys = []
        for row in rows:
            api_keys.append(APIKey(
                key_id=row[0],
                user_id=row[1],
                key_name=row[2],
                key_hash=row[3],
                key_prefix=row[4],
                created_at=row[5],
                expires_at=row[6],
                last_used_at=row[7],
                is_active=bool(row[8])
            ))
        return api_keys
    except Exception as e:
        print(f"Error listing API keys: {e}")
        return []
