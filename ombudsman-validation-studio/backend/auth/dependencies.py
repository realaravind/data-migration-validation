"""
Authentication Dependencies - FastAPI dependencies for authentication and authorization.

Provides dependency functions for:
- Getting current user from JWT token
- Requiring specific roles
- Requiring specific permissions
- API key authentication
"""

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timezone

from .models import User, UserInDB, UserRole, TokenData
from .security import verify_token
from .sqlite_repository import SQLiteAuthRepository

# Security scheme
security = HTTPBearer()

# Repository singleton (using SQLite)
auth_repo = SQLiteAuthRepository()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserInDB:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        Current user

    Raises:
        HTTPException 401: If token is invalid or user not found

    Usage:
        @app.get("/protected")
        async def protected_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.username}
    """
    token = credentials.credentials

    # Verify token
    token_data = verify_token(token, token_type="access")
    if token_data is None or token_data.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = auth_repo.get_user_by_id(token_data.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Check if user is locked
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is locked until {user.locked_until}"
        )

    return user


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    """
    Get current active user (alias for get_current_user).

    Usage:
        @app.get("/me")
        async def read_users_me(current_user: User = Depends(get_current_active_user)):
            return current_user
    """
    return current_user


def require_role(required_role: UserRole):
    """
    Require user to have a specific role.

    Args:
        required_role: Required role

    Returns:
        Dependency function

    Usage:
        @app.delete("/users/{user_id}")
        async def delete_user(
            user_id: str,
            current_user: User = Depends(require_role(UserRole.ADMIN))
        ):
            # Only admins can delete users
            pass
    """
    async def role_checker(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role"
            )
        return current_user

    return role_checker


def require_admin(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """
    Require user to be an admin.

    Usage:
        @app.post("/admin/settings")
        async def update_settings(
            settings: dict,
            current_user: User = Depends(require_admin)
        ):
            # Only admins can access this
            pass
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_user_or_admin(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """
    Require user to be at least a regular user (not just a viewer).

    Usage:
        @app.post("/pipelines/execute")
        async def execute_pipeline(
            pipeline: dict,
            current_user: User = Depends(require_user_or_admin)
        ):
            # Users and admins can execute pipelines, viewers cannot
            pass
    """
    if current_user.role not in [UserRole.USER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User or admin access required"
        )
    return current_user


def optional_authentication(
    authorization: Optional[str] = Header(None)
) -> Optional[UserInDB]:
    """
    Optional authentication - returns user if token is provided, None otherwise.

    Usage:
        @app.get("/public-or-private")
        async def endpoint(user: Optional[User] = Depends(optional_authentication)):
            if user:
                return {"message": f"Hello {user.username}"}
            else:
                return {"message": "Hello anonymous user"}
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")

    try:
        token_data = verify_token(token, token_type="access")
        if token_data is None or token_data.user_id is None:
            return None

        user = auth_repo.get_user_by_id(token_data.user_id)
        if user and user.is_active:
            return user

    except Exception:
        pass

    return None


async def get_current_user_or_api_key(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
) -> UserInDB:
    """
    Get current user from JWT token or API key.

    Supports two authentication methods:
    1. JWT Bearer token in Authorization header
    2. API key in X-API-Key header

    Usage:
        @app.get("/api/data")
        async def get_data(
            current_user: User = Depends(get_current_user_or_api_key)
        ):
            return {"data": "protected data"}
    """
    # Try JWT authentication first
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")

        try:
            token_data = verify_token(token, token_type="access")
            if token_data and token_data.user_id:
                user = auth_repo.get_user_by_id(token_data.user_id)
                if user and user.is_active:
                    return user
        except Exception:
            pass

    # Try API key authentication
    if x_api_key:
        # TODO: Implement API key verification
        # This would query the ApiKeys table and verify the key
        pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required (Bearer token or X-API-Key)",
        headers={"WWW-Authenticate": "Bearer"},
    )


def check_user_permission(user: UserInDB, resource: str, action: str) -> bool:
    """
    Check if user has permission to perform an action on a resource.

    Args:
        user: User to check
        resource: Resource name (e.g., "pipeline", "user", "project")
        action: Action name (e.g., "read", "write", "delete")

    Returns:
        True if user has permission, False otherwise

    Example:
        if check_user_permission(current_user, "pipeline", "delete"):
            # Allow deletion
            pass
    """
    # Admin has all permissions
    if user.role == UserRole.ADMIN:
        return True

    # Define role-based permissions
    permissions = {
        UserRole.USER: {
            "pipeline": ["read", "write", "execute"],
            "project": ["read", "write"],
            "metadata": ["read", "extract"],
            "mapping": ["read", "suggest"],
            "data": ["read", "generate"],
        },
        UserRole.VIEWER: {
            "pipeline": ["read"],
            "project": ["read"],
            "metadata": ["read"],
            "mapping": ["read"],
            "data": ["read"],
        }
    }

    role_permissions = permissions.get(user.role, {})
    resource_actions = role_permissions.get(resource, [])

    return action in resource_actions


class PermissionChecker:
    """Permission checker for specific resource and action"""

    def __init__(self, resource: str, action: str):
        self.resource = resource
        self.action = action

    def __call__(self, current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if not check_user_permission(current_user, self.resource, self.action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {self.action} on {self.resource}"
            )
        return current_user


# Convenience permission checkers
require_pipeline_write = PermissionChecker("pipeline", "write")
require_pipeline_delete = PermissionChecker("pipeline", "delete")
require_user_management = PermissionChecker("user", "manage")
