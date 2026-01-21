"""
Security utilities for authentication and authorization.

Provides:
- Password hashing and verification (bcrypt)
- JWT token generation and validation
- Refresh token management
- API key generation and validation
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
import secrets
import hashlib
import os

from .models import TokenData, UserRole

# ============================================================================
# Configuration
# ============================================================================

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production-please")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # Access token valid for 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7  # Refresh token valid for 7 days

# Password hashing context with bcrypt configuration
# Set rounds to 12 for good security/performance balance
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
    bcrypt__ident="2b"
)


# ============================================================================
# Password Hashing
# ============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password

    Example:
        hashed = hash_password("my_secure_password")
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise

    Example:
        if verify_password(input_password, user.hashed_password):
            print("Password correct!")
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# JWT Token Generation
# ============================================================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token (user_id, username, role, etc.)
        expires_delta: Token expiration time (default: 30 minutes)

    Returns:
        Encoded JWT token

    Example:
        token = create_access_token(
            data={"sub": user.user_id, "username": user.username, "role": user.role}
        )
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Data to encode in the token (user_id)
        expires_delta: Token expiration time (default: 7 days)

    Returns:
        Encoded JWT refresh token

    Example:
        refresh_token = create_refresh_token(data={"sub": user.user_id})
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token to verify
        token_type: Expected token type ("access" or "refresh")

    Returns:
        TokenData if token is valid, None otherwise

    Example:
        token_data = verify_token(access_token, token_type="access")
        if token_data:
            print(f"User ID: {token_data.user_id}")
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Check token type
        if payload.get("type") != token_type:
            return None

        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        role_str: str = payload.get("role")
        scopes: list = payload.get("scopes", [])

        if user_id is None:
            return None

        # Convert role string to UserRole enum
        try:
            role = UserRole(role_str) if role_str else None
        except ValueError:
            role = None

        return TokenData(
            user_id=user_id,
            username=username,
            role=role,
            scopes=scopes
        )

    except JWTError:
        return None


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT token without verification (for debugging).

    Args:
        token: JWT token to decode

    Returns:
        Token payload dictionary or None

    Example:
        payload = decode_token(token)
        print(payload)
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ============================================================================
# API Key Generation
# ============================================================================

def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a secure API key.

    Returns:
        Tuple of (full_key, key_hash, key_prefix)
        - full_key: The complete API key to give to user (show only once!)
        - key_hash: Hash of the key to store in database
        - key_prefix: First 8 characters for identification

    Example:
        full_key, key_hash, key_prefix = generate_api_key()
        print(f"Your API key: {full_key}")
        print(f"Store in DB: {key_hash}")
        print(f"Prefix for display: {key_prefix}")
    """
    # Generate a secure random key
    full_key = f"ombs_{secrets.token_urlsafe(32)}"

    # Hash the key for storage
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    # Extract prefix for identification
    key_prefix = full_key[:13]  # "ombs_" + first 8 chars

    return full_key, key_hash, key_prefix


def verify_api_key(provided_key: str, stored_hash: str) -> bool:
    """
    Verify an API key against its stored hash.

    Args:
        provided_key: API key provided by client
        stored_hash: Hash stored in database

    Returns:
        True if key matches, False otherwise

    Example:
        if verify_api_key(request_key, user_api_key.key_hash):
            print("API key valid!")
    """
    provided_hash = hashlib.sha256(provided_key.encode()).hexdigest()
    return secrets.compare_digest(provided_hash, stored_hash)


# ============================================================================
# Token Utilities
# ============================================================================

def get_token_expiration_time(token: str) -> Optional[datetime]:
    """
    Get the expiration time of a token.

    Args:
        token: JWT token

    Returns:
        Expiration datetime or None

    Example:
        exp_time = get_token_expiration_time(access_token)
        print(f"Token expires at: {exp_time}")
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        return None
    except JWTError:
        return None


def is_token_expired(token: str) -> bool:
    """
    Check if a token is expired.

    Args:
        token: JWT token

    Returns:
        True if expired, False otherwise

    Example:
        if is_token_expired(token):
            print("Token has expired!")
    """
    exp_time = get_token_expiration_time(token)
    if exp_time is None:
        return True
    return datetime.now(timezone.utc) > exp_time


def get_password_strength_score(password: str) -> Dict[str, Any]:
    """
    Calculate password strength score.

    Args:
        password: Password to evaluate

    Returns:
        Dictionary with score and feedback

    Example:
        result = get_password_strength_score("MyP@ssw0rd123")
        print(f"Score: {result['score']}/5")
        print(f"Strength: {result['strength']}")
    """
    score = 0
    feedback = []

    # Length check
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Password should be at least 8 characters")

    if len(password) >= 12:
        score += 1

    # Character variety
    if any(c.isupper() for c in password):
        score += 1
    else:
        feedback.append("Add uppercase letters")

    if any(c.islower() for c in password):
        score += 1
    else:
        feedback.append("Add lowercase letters")

    if any(c.isdigit() for c in password):
        score += 1
    else:
        feedback.append("Add numbers")

    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        score += 1
        feedback.append("Great! Contains special characters")

    # Determine strength
    if score <= 2:
        strength = "weak"
    elif score <= 3:
        strength = "fair"
    elif score <= 4:
        strength = "good"
    else:
        strength = "strong"

    return {
        "score": score,
        "max_score": 5,
        "strength": strength,
        "feedback": feedback
    }


# ============================================================================
# Security Headers
# ============================================================================

def generate_csrf_token() -> str:
    """
    Generate a CSRF token.

    Returns:
        Secure random CSRF token

    Example:
        csrf_token = generate_csrf_token()
    """
    return secrets.token_urlsafe(32)


def verify_csrf_token(provided_token: str, stored_token: str) -> bool:
    """
    Verify a CSRF token.

    Args:
        provided_token: Token from request
        stored_token: Token from session

    Returns:
        True if tokens match, False otherwise
    """
    return secrets.compare_digest(provided_token, stored_token)
