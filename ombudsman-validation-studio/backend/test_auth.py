#!/usr/bin/env python3
"""
Auth Test Script - Debug authentication issues
Run from backend directory: python3 test_auth.py
"""

import os
import sys
import traceback

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_auth():
    print("=" * 60)
    print("AUTH DEBUGGING SCRIPT")
    print("=" * 60)

    # Step 1: Check environment
    print("\n[1] ENVIRONMENT CHECK")
    print("-" * 40)
    auth_backend = os.getenv("AUTH_BACKEND", "sqlite")
    print(f"AUTH_BACKEND: {auth_backend}")
    print(f"Working directory: {os.getcwd()}")

    # Step 2: Try to import and initialize auth repo
    print("\n[2] IMPORTING AUTH MODULE")
    print("-" * 40)
    try:
        if auth_backend.lower() == "sqlserver":
            print("Using SQL Server backend...")
            from auth.sqlserver_auth_repository import SQLServerAuthRepository
            repo = SQLServerAuthRepository()
        else:
            print("Using SQLite backend...")
            from auth.sqlite_repository import SQLiteAuthRepository
            repo = SQLiteAuthRepository()
        print("SUCCESS: Auth repository initialized")
    except Exception as e:
        print(f"ERROR: Failed to initialize auth repository")
        print(f"Exception: {e}")
        traceback.print_exc()
        return False

    # Step 3: Test database connection by listing users
    print("\n[3] TESTING DATABASE CONNECTION")
    print("-" * 40)
    try:
        users = repo.list_users(limit=10)
        print(f"SUCCESS: Found {len(users)} users in database")
        for user in users:
            print(f"  - {user.username} ({user.email}) - Role: {user.role.value}")
    except Exception as e:
        print(f"ERROR: Failed to list users")
        print(f"Exception: {e}")
        traceback.print_exc()

        # Try to create tables
        print("\n[3b] ATTEMPTING TO CREATE TABLES")
        print("-" * 40)
        try:
            if auth_backend.lower() == "sqlserver":
                from auth.setup_sql_server_auth import setup_tables
                setup_tables()
                print("SUCCESS: Tables created")
            else:
                # SQLite creates tables automatically
                print("SQLite should create tables automatically...")
        except Exception as e2:
            print(f"ERROR: Failed to create tables: {e2}")
            traceback.print_exc()
            return False

    # Step 4: Create test user if none exist
    print("\n[4] CHECKING/CREATING TEST USER")
    print("-" * 40)
    try:
        from auth.models import UserCreate, UserRole

        # Check if admin exists
        admin_user = repo.get_user_by_username("admin")
        if admin_user:
            print(f"Admin user exists: {admin_user.username}")
        else:
            print("Creating admin user...")
            user_create = UserCreate(
                username="admin",
                email="admin@localhost",
                password="admin123",
                role=UserRole.ADMIN
            )
            new_user = repo.create_user(user_create)
            print(f"SUCCESS: Created user '{new_user.username}'")
    except ValueError as e:
        print(f"User already exists or validation error: {e}")
    except Exception as e:
        print(f"ERROR: Failed to create user")
        print(f"Exception: {e}")
        traceback.print_exc()

    # Step 5: Test login
    print("\n[5] TESTING LOGIN")
    print("-" * 40)
    try:
        from auth.security import verify_password

        user = repo.get_user_by_username("admin")
        if user:
            print(f"Found user: {user.username}")
            print(f"Hashed password exists: {bool(user.hashed_password)}")
            print(f"User is active: {user.is_active}")

            # Test password verification
            test_password = "admin123"
            is_valid = verify_password(test_password, user.hashed_password)
            print(f"Password 'admin123' valid: {is_valid}")

            if is_valid:
                print("\nSUCCESS: Login test passed!")
                print("You should be able to login with:")
                print("  Username: admin")
                print("  Password: admin123")
            else:
                print("\nWARNING: Password verification failed")
                print("The stored password hash may not match 'admin123'")
        else:
            print("ERROR: Admin user not found")
    except Exception as e:
        print(f"ERROR: Login test failed")
        print(f"Exception: {e}")
        traceback.print_exc()

    # Step 6: Test full login flow
    print("\n[6] TESTING FULL LOGIN FLOW")
    print("-" * 40)
    try:
        from auth.security import create_access_token, create_refresh_token
        from datetime import timedelta

        user = repo.get_user_by_username("admin")
        if user:
            # Create tokens
            access_token = create_access_token(
                data={"sub": user.user_id, "username": user.username, "role": user.role.value},
                expires_delta=timedelta(minutes=30)
            )
            print(f"Access token created: {access_token[:50]}...")

            refresh_token = create_refresh_token(
                data={"sub": user.user_id},
                expires_delta=timedelta(days=7)
            )
            print(f"Refresh token created: {refresh_token[:50]}...")

            print("\nSUCCESS: Token generation works!")
    except Exception as e:
        print(f"ERROR: Token generation failed")
        print(f"Exception: {e}")
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    return True


if __name__ == "__main__":
    # Set up environment
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)

    # Run tests
    success = test_auth()
    sys.exit(0 if success else 1)
