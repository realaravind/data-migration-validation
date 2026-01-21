# Authentication & Authorization Guide

## Overview

The Ombudsman Validation Studio includes a **production-ready authentication system** with:
- JWT-based authentication (access & refresh tokens)
- Role-based access control (RBAC)
- Bcrypt password hashing
- Account security (brute force protection, account locking)
- Comprehensive audit logging
- API key support for programmatic access

## Quick Start

### 1. Setup Database

Run the authentication schema to create required tables:

```bash
# Connect to your SQL Server database
sqlcmd -S your-server -d your-database -i backend/auth/schema.sql
```

This creates:
- `Users` - User accounts
- `RefreshTokens` - Token storage
- `AuditLog` - Security events
- `ApiKeys` - API keys

###2. Configure Environment

Set JWT secret key in `.env`:

```env
JWT_SECRET_KEY=your-secret-key-change-in-production
SQLSERVER_CONN_STR=your-connection-string
```

### 3. Start the API

```bash
cd ombudsman-validation-studio/backend
uvicorn main:app --reload
```

## User Roles

| Role | Permissions | Use Case |
|------|------------|----------|
| **admin** | Full access to all resources | System administrators |
| **user** | Execute pipelines, manage projects | Data engineers |
| **viewer** | Read-only access | Stakeholders, auditors |
| **api_key** | Programmatic access | Automated systems |

## API Endpoints

### Public Endpoints (No Auth Required)

#### Register User
```bash
POST /auth/register
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123",
  "full_name": "John Doe",
  "role": "user"
}
```

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit

#### Login
```bash
POST /auth/login
Content-Type: application/json

{
  "username": "john_doe",
  "password": "SecurePass123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "user_id": "user_123...",
    "username": "john_doe",
    "email": "john@example.com",
    "role": "user",
    ...
  }
}
```

#### Refresh Token
```bash
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "your_refresh_token"
}
```

### Protected Endpoints (Auth Required)

#### Get Current User
```bash
GET /auth/me
Authorization: Bearer {access_token}
```

#### Update Current User
```bash
PUT /auth/me
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "email": "newemail@example.com",
  "full_name": "John Smith"
}
```

#### Change Password
```bash
PUT /auth/me/password
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "current_password": "OldPass123",
  "new_password": "NewPass123"
}
```

#### Logout
```bash
POST /auth/logout
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "refresh_token": "your_refresh_token"
}
```

### Admin Endpoints (Admin Only)

#### List Users
```bash
GET /auth/users?role=user&is_active=true&page=1&limit=100
Authorization: Bearer {admin_access_token}
```

#### Get User by ID
```bash
GET /auth/users/{user_id}
Authorization: Bearer {admin_access_token}
```

#### Delete User
```bash
DELETE /auth/users/{user_id}
Authorization: Bearer {admin_access_token}
```

## Using Authentication in Code

### Python Client Example

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Register
response = requests.post(f"{BASE_URL}/auth/register", json={
    "username": "api_user",
    "email": "api@example.com",
    "password": "SecurePass123",
    "role": "user"
})
print(f"Registered: {response.json()}")

# 2. Login
response = requests.post(f"{BASE_URL}/auth/login", json={
    "username": "api_user",
    "password": "SecurePass123"
})
tokens = response.json()
access_token = tokens["access_token"]
refresh_token = tokens["refresh_token"]

# 3. Use protected endpoint
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
print(f"Current user: {response.json()}")

# 4. Execute pipeline (requires auth)
response = requests.post(
    f"{BASE_URL}/pipelines/execute",
    headers=headers,
    json={
        "pipeline_yaml": pipeline_yaml_content,
        "pipeline_name": "my_pipeline"
    }
)
print(f"Pipeline started: {response.json()}")

# 5. Refresh token when expired
response = requests.post(f"{BASE_URL}/auth/refresh", json={
    "refresh_token": refresh_token
})
new_tokens = response.json()
access_token = new_tokens["access_token"]
```

### FastAPI Dependency Usage

```python
from fastapi import APIRouter, Depends
from auth.dependencies import (
    get_current_user,
    require_admin,
    require_user_or_admin,
    optional_authentication
)
from auth.models import UserInDB

router = APIRouter()

# Protected endpoint (any authenticated user)
@router.get("/protected")
async def protected_endpoint(current_user: UserInDB = Depends(get_current_user)):
    return {"message": f"Hello {current_user.username}"}

# Admin only
@router.delete("/admin/resource/{id}")
async def delete_resource(id: str, current_user: UserInDB = Depends(require_admin)):
    # Only admins can access this
    return {"deleted": id}

# User or Admin (not viewer)
@router.post("/data/process")
async def process_data(data: dict, current_user: UserInDB = Depends(require_user_or_admin)):
    # Viewers cannot access this
    return {"processed": True}

# Optional authentication
@router.get("/public-or-private")
async def mixed_endpoint(current_user: Optional[UserInDB] = Depends(optional_authentication)):
    if current_user:
        return {"message": f"Hello {current_user.username}"}
    else:
        return {"message": "Hello guest"}
```

## Security Features

### 1. Brute Force Protection
- Failed login attempts tracked
- Account locked after 5 failed attempts
- 30-minute lockout period
- Automatic unlock after timeout

### 2. Password Security
- Bcrypt hashing (industry standard)
- Per-password salt (automatic)
- Configurable work factor
- Password strength validation

### 3. Token Security
- Short-lived access tokens (30 minutes)
- Long-lived refresh tokens (7 days)
- Token revocation on logout
- Automatic cleanup of expired tokens

### 4. Audit Logging
All security events logged:
- User login/logout
- Registration
- Password changes
- Failed login attempts
- Account locking/unlocking
- Permission changes

Query audit logs:
```sql
SELECT TOP 100 *
FROM AuditLog
WHERE user_id = 'user_123'
ORDER BY created_at DESC
```

## Protected Endpoints

The following endpoints now require authentication:

### Pipeline Endpoints
- ✅ `POST /pipelines/execute` - User or Admin
- ✅ `DELETE /pipelines/{run_id}` - User or Admin
- ✅ `POST /pipelines/custom/save` - User or Admin
- ✅ `DELETE /pipelines/custom/project/{project_id}/{pipeline_name}` - User or Admin
- ℹ️ `GET /pipelines/status/{run_id}` - Optional auth
- ℹ️ `GET /pipelines/list` - Optional auth

### Project Endpoints
- ✅ `POST /projects/create` - User or Admin
- ✅ `POST /projects/{project_id}/save` - User or Admin
- ✅ `DELETE /projects/{project_id}` - User or Admin
- ℹ️ `GET /projects/list` - Optional auth

## Testing Authentication

### Unit Tests (28 tests)
```bash
cd ombudsman-validation-studio/backend
pytest tests/unit/test_auth_security.py -v
```

Tests cover:
- Password hashing and verification
- JWT token generation and validation
- API key generation
- Password strength scoring
- Token utilities

### Integration Tests (50+ tests)
```bash
pytest tests/integration/test_auth_api.py -v
```

Tests cover:
- User registration
- Login/logout
- Token refresh
- Protected endpoints
- Admin endpoints
- Role-based access control

## Common Use Cases

### 1. Single User Session
```python
# Login once, use access token until expires
tokens = login(username, password)
access_token = tokens["access_token"]

# Use for all requests
headers = {"Authorization": f"Bearer {access_token}"}
```

### 2. Long-Running Application
```python
def get_valid_token():
    if is_token_expired(access_token):
        # Refresh the token
        new_tokens = refresh_token(refresh_token)
        access_token = new_tokens["access_token"]
        refresh_token = new_tokens["refresh_token"]
    return access_token

# Use in requests
headers = {"Authorization": f"Bearer {get_valid_token()}"}
```

### 3. Multiple Devices
Each login creates a new refresh token. User can be logged in on multiple devices simultaneously. Logout from one device doesn't affect others.

## Troubleshooting

### "401 Unauthorized"
- Token expired: Use refresh token to get new access token
- Invalid token: Re-login to get new tokens
- No token: Include `Authorization: Bearer {token}` header

### "403 Forbidden"
- Insufficient permissions: Check user role
- Account locked: Wait 30 minutes or contact admin
- Account inactive: Contact admin to reactivate

### "Account locked"
- Too many failed login attempts
- Wait 30 minutes for automatic unlock
- Admin can manually unlock: `EXEC sp_UnlockUser @user_id='user_123'`

## Best Practices

1. **Store tokens securely**
   - Never commit tokens to version control
   - Use secure storage (environment variables, secrets manager)
   - Don't log tokens

2. **Handle token expiration**
   - Implement automatic token refresh
   - Handle 401 errors gracefully
   - Re-authenticate when refresh fails

3. **Use appropriate roles**
   - Assign minimum necessary permissions
   - Regular users for data engineers
   - Viewers for stakeholders
   - Admin only for system administrators

4. **Monitor audit logs**
   - Review failed login attempts
   - Check for unusual activity
   - Monitor account lockouts

5. **Rotate secrets regularly**
   - Change JWT_SECRET_KEY periodically
   - Update database passwords
   - Revoke unused API keys

## API Summary

| Endpoint | Method | Auth | Role | Description |
|----------|--------|------|------|-------------|
| `/auth/register` | POST | No | - | Register new user |
| `/auth/login` | POST | No | - | Login and get tokens |
| `/auth/refresh` | POST | No | - | Refresh access token |
| `/auth/me` | GET | Yes | Any | Get current user |
| `/auth/me` | PUT | Yes | Any | Update current user |
| `/auth/me/password` | PUT | Yes | Any | Change password |
| `/auth/logout` | POST | Yes | Any | Logout and revoke token |
| `/auth/users` | GET | Yes | Admin | List all users |
| `/auth/users/{id}` | GET | Yes | Admin | Get user by ID |
| `/auth/users/{id}` | DELETE | Yes | Admin | Delete user |

## Next Steps

1. **Set up database**: Run `auth/schema.sql`
2. **Configure environment**: Set `JWT_SECRET_KEY`
3. **Create admin user**: Register with `role: "admin"`
4. **Test authentication**: Try login and protected endpoints
5. **Integrate with frontend**: Implement token storage and refresh
6. **Monitor**: Review audit logs regularly

For questions or issues, check the audit logs or test with the provided examples.
