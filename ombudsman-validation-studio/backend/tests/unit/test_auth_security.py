"""
Unit tests for authentication security utilities.

Tests password hashing, JWT token generation/validation, and API key generation.
"""

import pytest
from datetime import datetime, timedelta, timezone
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from auth.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, verify_token,
    generate_api_key, verify_api_key,
    get_password_strength_score,
    is_token_expired, get_token_expiration_time
)
from auth.models import UserRole


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "MySecurePassword123"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 50  # Bcrypt hashes are long
        assert hashed.startswith("$2b$")  # Bcrypt identifier

    def test_verify_password_correct(self):
        """Test verifying correct password"""
        password = "MySecurePassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password"""
        password = "MySecurePassword123"
        wrong_password = "WrongPassword123"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes (salt)"""
        password = "MySecurePassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


@pytest.mark.unit
class TestJWTTokens:
    """Test JWT token generation and validation"""

    def test_create_access_token(self):
        """Test creating access token"""
        data = {
            "sub": "user_123",
            "username": "testuser",
            "role": "user"
        }

        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are long

    def test_create_refresh_token(self):
        """Test creating refresh token"""
        data = {"sub": "user_123"}

        token = create_refresh_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 100

    def test_verify_access_token(self):
        """Test verifying access token"""
        data = {
            "sub": "user_123",
            "username": "testuser",
            "role": UserRole.USER.value
        }

        token = create_access_token(data)
        token_data = verify_token(token, token_type="access")

        assert token_data is not None
        assert token_data.user_id == "user_123"
        assert token_data.username == "testuser"
        assert token_data.role == UserRole.USER

    def test_verify_refresh_token(self):
        """Test verifying refresh token"""
        data = {"sub": "user_123"}

        token = create_refresh_token(data)
        token_data = verify_token(token, token_type="refresh")

        assert token_data is not None
        assert token_data.user_id == "user_123"

    def test_verify_wrong_token_type(self):
        """Test that verifying token with wrong type fails"""
        data = {"sub": "user_123"}

        access_token = create_access_token(data)
        # Try to verify access token as refresh token
        token_data = verify_token(access_token, token_type="refresh")

        assert token_data is None

    def test_verify_invalid_token(self):
        """Test verifying invalid token"""
        invalid_token = "invalid.jwt.token"

        token_data = verify_token(invalid_token, token_type="access")

        assert token_data is None

    def test_token_expiration(self):
        """Test that tokens have expiration"""
        data = {"sub": "user_123"}

        token = create_access_token(data)
        exp_time = get_token_expiration_time(token)

        assert exp_time is not None
        assert exp_time > datetime.now(timezone.utc)

    def test_expired_token(self):
        """Test expired token detection"""
        data = {"sub": "user_123"}

        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        assert is_token_expired(token) is True

    def test_custom_expiration(self):
        """Test creating token with custom expiration"""
        data = {"sub": "user_123"}

        # Create token that expires in 1 hour
        token = create_access_token(data, expires_delta=timedelta(hours=1))
        exp_time = get_token_expiration_time(token)

        assert exp_time is not None
        # Check expiration is roughly 1 hour from now
        time_until_exp = (exp_time - datetime.now(timezone.utc)).total_seconds()
        assert 3500 < time_until_exp < 3700  # ~1 hour (3600 seconds)


@pytest.mark.unit
class TestAPIKeys:
    """Test API key generation and verification"""

    def test_generate_api_key(self):
        """Test generating API key"""
        full_key, key_hash, key_prefix = generate_api_key()

        assert full_key is not None
        assert full_key.startswith("ombs_")
        assert len(full_key) > 40

        assert key_hash is not None
        assert len(key_hash) == 64  # SHA-256 hash is 64 hex characters

        assert key_prefix is not None
        assert key_prefix == full_key[:13]  # "ombs_" + first 8 chars

    def test_verify_api_key_correct(self):
        """Test verifying correct API key"""
        full_key, key_hash, _ = generate_api_key()

        assert verify_api_key(full_key, key_hash) is True

    def test_verify_api_key_incorrect(self):
        """Test verifying incorrect API key"""
        full_key, key_hash, _ = generate_api_key()
        wrong_key, _, _ = generate_api_key()

        assert verify_api_key(wrong_key, key_hash) is False

    def test_api_keys_are_unique(self):
        """Test that generated API keys are unique"""
        key1, _, _ = generate_api_key()
        key2, _, _ = generate_api_key()

        assert key1 != key2


@pytest.mark.unit
class TestPasswordStrength:
    """Test password strength scoring"""

    def test_weak_password(self):
        """Test weak password scoring"""
        result = get_password_strength_score("abc")

        assert result["strength"] == "weak"
        assert result["score"] <= 2
        assert len(result["feedback"]) > 0

    def test_fair_password(self):
        """Test fair password scoring"""
        result = get_password_strength_score("Password")

        assert result["strength"] in ["weak", "fair"]
        assert len(result["feedback"]) > 0

    def test_good_password(self):
        """Test good password scoring"""
        result = get_password_strength_score("Password123")

        assert result["strength"] in ["fair", "good"]
        assert result["score"] >= 3

    def test_strong_password(self):
        """Test strong password scoring"""
        result = get_password_strength_score("MyP@ssw0rd123!")

        assert result["strength"] in ["good", "strong"]
        assert result["score"] >= 4

    def test_password_feedback(self):
        """Test password feedback messages"""
        result = get_password_strength_score("short")

        assert "feedback" in result
        assert isinstance(result["feedback"], list)

    def test_long_password_bonus(self):
        """Test that longer passwords get higher scores"""
        short_result = get_password_strength_score("Pass1234")
        long_result = get_password_strength_score("MyLongPassword1234")

        # Long password should have higher or equal score
        assert long_result["score"] >= short_result["score"]


@pytest.mark.unit
class TestTokenUtilities:
    """Test token utility functions"""

    def test_get_token_expiration_time(self):
        """Test getting token expiration time"""
        data = {"sub": "user_123"}
        token = create_access_token(data)

        exp_time = get_token_expiration_time(token)

        assert exp_time is not None
        assert isinstance(exp_time, datetime)
        assert exp_time > datetime.now(timezone.utc)

    def test_get_expiration_invalid_token(self):
        """Test getting expiration of invalid token"""
        invalid_token = "invalid.token.here"

        exp_time = get_token_expiration_time(invalid_token)

        assert exp_time is None

    def test_is_token_expired_valid(self):
        """Test checking if valid token is expired"""
        data = {"sub": "user_123"}
        token = create_access_token(data, expires_delta=timedelta(hours=1))

        assert is_token_expired(token) is False

    def test_is_token_expired_expired(self):
        """Test checking if expired token is expired"""
        data = {"sub": "user_123"}
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        assert is_token_expired(token) is True

    def test_is_token_expired_invalid(self):
        """Test checking expiration of invalid token"""
        invalid_token = "invalid.token.here"

        # Invalid token should be considered expired
        assert is_token_expired(invalid_token) is True
