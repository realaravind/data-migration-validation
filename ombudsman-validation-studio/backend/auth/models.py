"""
Authentication Models - Pydantic models for user management and authentication.

Provides type-safe models for:
- User registration and authentication
- JWT tokens and refresh tokens
- User roles and permissions
- Audit logging
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User role types"""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    API_KEY = "api_key"


class EventType(str, Enum):
    """Audit log event types"""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTER = "user_register"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    PERMISSION_CHANGED = "permission_changed"
    FAILED_LOGIN = "failed_login"


# ============================================================================
# User Models
# ============================================================================

class UserBase(BaseModel):
    """Base user model with common fields"""
    username: str = Field(..., min_length=3, max_length=100, description="Unique username")
    email: EmailStr = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, max_length=255, description="User's full name")
    role: UserRole = Field(default=UserRole.USER, description="User role")

    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v.lower()


class UserCreate(UserBase):
    """Model for user registration"""
    password: str = Field(..., min_length=8, max_length=100, description="User password")

    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    """Model for updating user information"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserPasswordChange(BaseModel):
    """Model for password change"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")

    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class User(UserBase):
    """Complete user model (as stored in database)"""
    user_id: str
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserInDB(User):
    """User model including hashed password (for internal use only)"""
    hashed_password: str


class UserPublic(UserBase):
    """Public user model (safe to return in API responses)"""
    user_id: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Authentication Models
# ============================================================================

class Token(BaseModel):
    """JWT access token response"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="Refresh token for getting new access tokens")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")


class TokenData(BaseModel):
    """Data extracted from JWT token"""
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[UserRole] = None
    scopes: List[str] = Field(default_factory=list)


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token"""
    refresh_token: str = Field(..., description="Refresh token")


class LoginRequest(BaseModel):
    """User login request"""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class LoginResponse(BaseModel):
    """User login response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


# ============================================================================
# Refresh Token Models
# ============================================================================

class RefreshToken(BaseModel):
    """Refresh token model"""
    token_id: str
    user_id: str
    refresh_token: str
    expires_at: datetime
    created_at: datetime
    revoked_at: Optional[datetime] = None
    is_revoked: bool = False
    device_info: Optional[str] = None
    ip_address: Optional[str] = None

    class Config:
        from_attributes = True


class RefreshTokenCreate(BaseModel):
    """Create refresh token"""
    user_id: str
    refresh_token: str
    expires_at: datetime
    device_info: Optional[str] = None
    ip_address: Optional[str] = None


# ============================================================================
# API Key Models
# ============================================================================

class ApiKeyCreate(BaseModel):
    """Create API key"""
    key_name: str = Field(..., min_length=3, max_length=255, description="API key name")
    expires_at: Optional[datetime] = Field(None, description="Expiration date (optional)")
    permissions: Optional[List[str]] = Field(default_factory=list, description="API key permissions")


class ApiKey(BaseModel):
    """API key model"""
    key_id: int
    user_id: str
    key_name: str
    api_key_prefix: str
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime
    last_used_at: Optional[datetime]
    permissions: Optional[List[str]]

    class Config:
        from_attributes = True


class ApiKeyResponse(ApiKey):
    """API key response (includes the full key only on creation)"""
    api_key: Optional[str] = Field(None, description="Full API key (only returned on creation)")


# ============================================================================
# Audit Log Models
# ============================================================================

class AuditLogEntry(BaseModel):
    """Audit log entry"""
    log_id: int
    user_id: Optional[str]
    event_type: EventType
    event_description: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    success: bool
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogCreate(BaseModel):
    """Create audit log entry"""
    user_id: Optional[str] = None
    event_type: EventType
    event_description: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


# ============================================================================
# Response Models
# ============================================================================

class UserListResponse(BaseModel):
    """Response for user list"""
    users: List[UserPublic]
    total: int
    page: int
    page_size: int


class AuditLogResponse(BaseModel):
    """Response for audit log"""
    logs: List[AuditLogEntry]
    total: int
    page: int
    page_size: int


class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    error: str
    detail: Optional[str] = None
