"""
Authentication Module

Provides complete authentication and authorization system:
- User registration and login
- JWT token generation and validation
- Password hashing with bcrypt
- Role-based access control (admin, user, viewer)
- Refresh token management
- Audit logging
- API key authentication
"""

from .router import router
from .models import (
    User, UserCreate, UserUpdate, UserPublic,
    UserRole, Token, LoginRequest, LoginResponse
)
from .security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, verify_token
)
from .dependencies import (
    get_current_user, get_current_active_user,
    require_admin, require_role, require_user_or_admin,
    optional_authentication, check_user_permission
)
from .repository import AuthRepository

__all__ = [
    # Router
    "router",

    # Models
    "User",
    "UserCreate",
    "UserUpdate",
    "UserPublic",
    "UserRole",
    "Token",
    "LoginRequest",
    "LoginResponse",

    # Security
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "verify_token",

    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "require_admin",
    "require_role",
    "require_user_or_admin",
    "optional_authentication",
    "check_user_permission",

    # Repository
    "AuthRepository",
]
