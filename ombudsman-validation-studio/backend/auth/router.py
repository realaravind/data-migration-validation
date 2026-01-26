"""
Authentication API Router - FastAPI endpoints for authentication and user management.

Endpoints:
- POST /auth/register - Register new user
- POST /auth/login - Login and get tokens
- POST /auth/refresh - Refresh access token
- POST /auth/logout - Logout and revoke tokens
- GET /auth/me - Get current user info
- PUT /auth/me - Update current user info
- PUT /auth/me/password - Change password
- GET /auth/users - List users (admin only)
- GET /auth/users/{user_id} - Get user by ID (admin only)
- DELETE /auth/users/{user_id} - Delete user (admin only)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from .models import (
    UserCreate, UserUpdate, UserPublic, UserPasswordChange,
    LoginRequest, LoginResponse,
    RefreshTokenRequest, Token,
    UserListResponse,
    SuccessResponse,
    UserRole, EventType
)
from .security import (
    verify_password, hash_password,
    create_access_token, create_refresh_token, verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
)
from .models import RefreshTokenCreate, AuditLogCreate
from .dependencies import (
    get_current_user, require_admin, get_current_active_user, auth_repo
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# auth_repo is imported from dependencies.py which uses the configured backend


# ============================================================================
# Helper Functions
# ============================================================================

def get_client_ip(request: Request) -> Optional[str]:
    """Get client IP address from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> Optional[str]:
    """Get user agent from request"""
    return request.headers.get("User-Agent")


# ============================================================================
# Public Endpoints (No Authentication Required)
# ============================================================================

@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(user_create: UserCreate, request: Request):
    """
    Register a new user.

    Args:
        user_create: User registration data

    Returns:
        Created user (without password)

    Raises:
        400: If username or email already exists
        422: If validation fails
    """
    try:
        # Create user
        user = auth_repo.create_user(user_create)

        # Log the registration
        auth_repo.log_audit_event(AuditLogCreate(
            user_id=user.user_id,
            event_type=EventType.USER_REGISTER,
            event_description=f"User {user.username} registered successfully",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            success=True
        ))

        # Return public user info (without password)
        return UserPublic(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            last_login=user.last_login
        )

    except ValueError as e:
        auth_repo.log_audit_event(AuditLogCreate(
            event_type=EventType.USER_REGISTER,
            event_description=f"Registration failed: {str(e)}",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            success=False,
            error_message=str(e)
        ))

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=LoginResponse)
async def login(login_request: LoginRequest, request: Request):
    """
    Login and get access and refresh tokens.

    Args:
        login_request: Username/email and password

    Returns:
        Access token, refresh token, and user info

    Raises:
        401: If credentials are invalid
        403: If account is locked
    """
    # Get user by username or email
    user = auth_repo.get_user_by_username(login_request.username)
    if not user:
        user = auth_repo.get_user_by_email(login_request.username)

    # Check if user exists
    if not user:
        auth_repo.log_audit_event(AuditLogCreate(
            event_type=EventType.FAILED_LOGIN,
            event_description=f"Login failed: user '{login_request.username}' not found",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            success=False
        ))

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is locked until {user.locked_until}"
        )

    # Verify password
    if not verify_password(login_request.password, user.hashed_password):
        # Increment failed login attempts
        failed_attempts = auth_repo.increment_failed_login_attempts(user.user_id)

        # Lock account after 5 failed attempts
        if failed_attempts >= 5:
            auth_repo.lock_user(user.user_id, lock_duration_minutes=30)

            auth_repo.log_audit_event(AuditLogCreate(
                user_id=user.user_id,
                event_type=EventType.ACCOUNT_LOCKED,
                event_description=f"Account locked after {failed_attempts} failed login attempts",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                success=True
            ))

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account locked due to too many failed login attempts"
            )

        auth_repo.log_audit_event(AuditLogCreate(
            user_id=user.user_id,
            event_type=EventType.FAILED_LOGIN,
            event_description=f"Failed login attempt ({failed_attempts}/5)",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            success=False
        ))

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Reset failed login attempts on successful login
    auth_repo.reset_failed_login_attempts(user.user_id)

    # Update last login
    auth_repo.update_last_login(user.user_id)

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.user_id,
            "username": user.username,
            "role": user.role.value
        },
        expires_delta=access_token_expires
    )

    # Create refresh token
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_refresh_token(
        data={"sub": user.user_id},
        expires_delta=refresh_token_expires
    )

    # Store refresh token in database
    auth_repo.create_refresh_token(RefreshTokenCreate(
        user_id=user.user_id,
        refresh_token=refresh_token,
        expires_at=datetime.now(timezone.utc) + refresh_token_expires,
        device_info=get_user_agent(request),
        ip_address=get_client_ip(request)
    ))

    # Log successful login
    auth_repo.log_audit_event(AuditLogCreate(
        user_id=user.user_id,
        event_type=EventType.USER_LOGIN,
        event_description="User logged in successfully",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        success=True
    ))

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
        user=UserPublic(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            last_login=datetime.now()
        )
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_request: RefreshTokenRequest, request: Request):
    """
    Refresh access token using refresh token.

    Args:
        refresh_request: Refresh token

    Returns:
        New access token and refresh token

    Raises:
        401: If refresh token is invalid or expired
    """
    # Verify refresh token
    token_data = verify_token(refresh_request.refresh_token, token_type="refresh")
    if not token_data or not token_data.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Check if refresh token exists and is not revoked
    stored_token = auth_repo.get_refresh_token(refresh_request.refresh_token)
    if not stored_token or stored_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked"
        )

    # Check if refresh token is expired
    if stored_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired"
        )

    # Get user
    user = auth_repo.get_user_by_id(token_data.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Create new access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.user_id,
            "username": user.username,
            "role": user.role.value
        },
        expires_delta=access_token_expires
    )

    # Create new refresh token
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    new_refresh_token = create_refresh_token(
        data={"sub": user.user_id},
        expires_delta=refresh_token_expires
    )

    # Revoke old refresh token
    auth_repo.revoke_refresh_token(refresh_request.refresh_token)

    # Store new refresh token
    auth_repo.create_refresh_token(RefreshTokenCreate(
        user_id=user.user_id,
        refresh_token=new_refresh_token,
        expires_at=datetime.now(timezone.utc) + refresh_token_expires,
        device_info=get_user_agent(request),
        ip_address=get_client_ip(request)
    ))

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


# ============================================================================
# Protected Endpoints (Authentication Required)
# ============================================================================

@router.get("/me", response_model=UserPublic)
async def get_current_user_info(current_user = Depends(get_current_active_user)):
    """
    Get current user information.

    Returns:
        Current user info
    """
    return UserPublic(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.put("/me", response_model=UserPublic)
async def update_current_user(
    user_update: UserUpdate,
    current_user = Depends(get_current_active_user)
):
    """
    Update current user information.

    Args:
        user_update: User update data

    Returns:
        Updated user info

    Note: Regular users cannot change their role or active status
    """
    # Don't allow users to change their own role or active status
    if current_user.role != UserRole.ADMIN:
        user_update.role = None
        user_update.is_active = None
        user_update.is_verified = None

    updated_user = auth_repo.update_user(current_user.user_id, user_update)

    return UserPublic(
        user_id=updated_user.user_id,
        username=updated_user.username,
        email=updated_user.email,
        full_name=updated_user.full_name,
        role=updated_user.role,
        is_active=updated_user.is_active,
        is_verified=updated_user.is_verified,
        created_at=updated_user.created_at,
        last_login=updated_user.last_login
    )


@router.put("/me/password", response_model=SuccessResponse)
async def change_password(
    password_change: UserPasswordChange,
    current_user = Depends(get_current_active_user),
    request: Request = None
):
    """
    Change current user's password.

    Args:
        password_change: Current and new password

    Returns:
        Success message
    """
    # Verify current password
    if not verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Hash new password
    new_hashed_password = hash_password(password_change.new_password)

    # Update password in database
    auth_repo.update_password(current_user.user_id, new_hashed_password)

    # Log password change
    auth_repo.log_audit_event(AuditLogCreate(
        user_id=current_user.user_id,
        event_type=EventType.PASSWORD_CHANGE,
        event_description="Password changed successfully",
        ip_address=get_client_ip(request) if request else None,
        user_agent=get_user_agent(request) if request else None,
        success=True
    ))

    return SuccessResponse(
        success=True,
        message="Password changed successfully"
    )


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    refresh_request: RefreshTokenRequest,
    current_user = Depends(get_current_active_user),
    request: Request = None
):
    """
    Logout and revoke refresh token.

    Args:
        refresh_request: Refresh token to revoke

    Returns:
        Success message
    """
    # Revoke the refresh token
    auth_repo.revoke_refresh_token(refresh_request.refresh_token)

    # Log logout
    auth_repo.log_audit_event(AuditLogCreate(
        user_id=current_user.user_id,
        event_type=EventType.USER_LOGOUT,
        event_description="User logged out",
        ip_address=get_client_ip(request) if request else None,
        user_agent=get_user_agent(request) if request else None,
        success=True
    ))

    return SuccessResponse(
        success=True,
        message="Logged out successfully"
    )


# ============================================================================
# Admin Endpoints (Admin Role Required)
# ============================================================================

@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    current_user = Depends(require_admin)
):
    """
    List all users (admin only).

    Args:
        skip: Number of users to skip
        limit: Maximum number of users to return
        role: Filter by role
        is_active: Filter by active status

    Returns:
        List of users
    """
    users = auth_repo.list_users(skip=skip, limit=limit, role=role, is_active=is_active)

    return UserListResponse(
        users=[UserPublic(
            user_id=u.user_id,
            username=u.username,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            is_verified=u.is_verified,
            created_at=u.created_at,
            last_login=u.last_login
        ) for u in users],
        total=len(users),
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit
    )


@router.get("/users/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: str,
    current_user = Depends(require_admin)
):
    """
    Get user by ID (admin only).

    Args:
        user_id: User ID

    Returns:
        User info
    """
    user = auth_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserPublic(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.delete("/users/{user_id}", response_model=SuccessResponse)
async def delete_user(
    user_id: str,
    current_user = Depends(require_admin)
):
    """
    Delete user (admin only).

    Args:
        user_id: User ID to delete

    Returns:
        Success message
    """
    # Don't allow deleting yourself
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    success = auth_repo.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return SuccessResponse(
        success=True,
        message=f"User {user_id} deleted successfully"
    )
