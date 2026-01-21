-- Authentication and User Management Schema
-- Database: SQL Server
-- Created: 2025-12-03

-- ============================================================================
-- TABLE: Users
-- Stores user accounts with authentication details
-- ============================================================================

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Users' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    CREATE TABLE Users (
        user_id VARCHAR(100) PRIMARY KEY,
        username NVARCHAR(100) NOT NULL UNIQUE,
        email NVARCHAR(255) NOT NULL UNIQUE,
        hashed_password NVARCHAR(255) NOT NULL,
        full_name NVARCHAR(255),
        role VARCHAR(50) NOT NULL DEFAULT 'user',
        is_active BIT NOT NULL DEFAULT 1,
        is_verified BIT NOT NULL DEFAULT 0,
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        last_login DATETIME2,
        failed_login_attempts INT NOT NULL DEFAULT 0,
        locked_until DATETIME2,

        -- Indexes
        INDEX idx_users_username (username),
        INDEX idx_users_email (email),
        INDEX idx_users_role (role),
        INDEX idx_users_is_active (is_active),

        -- Constraints
        CONSTRAINT chk_users_role CHECK (role IN ('admin', 'user', 'viewer', 'api_key')),
        CONSTRAINT chk_users_email_format CHECK (email LIKE '%_@__%.__%')
    );

    PRINT 'Table Users created successfully';
END
ELSE
BEGIN
    PRINT 'Table Users already exists';
END
GO

-- ============================================================================
-- TABLE: RefreshTokens
-- Stores refresh tokens for JWT authentication
-- ============================================================================

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'RefreshTokens' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    CREATE TABLE RefreshTokens (
        token_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        user_id VARCHAR(100) NOT NULL,
        refresh_token NVARCHAR(500) NOT NULL UNIQUE,
        expires_at DATETIME2 NOT NULL,
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        revoked_at DATETIME2,
        is_revoked BIT NOT NULL DEFAULT 0,
        device_info NVARCHAR(500),
        ip_address VARCHAR(50),

        -- Foreign key
        CONSTRAINT fk_refresh_tokens_user FOREIGN KEY (user_id)
            REFERENCES Users(user_id) ON DELETE CASCADE,

        -- Indexes
        INDEX idx_refresh_tokens_user (user_id),
        INDEX idx_refresh_tokens_token (refresh_token),
        INDEX idx_refresh_tokens_expires (expires_at)
    );

    PRINT 'Table RefreshTokens created successfully';
END
ELSE
BEGIN
    PRINT 'Table RefreshTokens already exists';
END
GO

-- ============================================================================
-- TABLE: AuditLog
-- Tracks user authentication and security events
-- ============================================================================

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'AuditLog' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    CREATE TABLE AuditLog (
        log_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        user_id VARCHAR(100),
        event_type VARCHAR(100) NOT NULL,
        event_description NVARCHAR(MAX),
        ip_address VARCHAR(50),
        user_agent NVARCHAR(500),
        success BIT NOT NULL,
        error_message NVARCHAR(MAX),
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),

        -- Foreign key (nullable for failed login attempts)
        CONSTRAINT fk_audit_log_user FOREIGN KEY (user_id)
            REFERENCES Users(user_id) ON DELETE SET NULL,

        -- Indexes
        INDEX idx_audit_log_user (user_id),
        INDEX idx_audit_log_event_type (event_type),
        INDEX idx_audit_log_created_at (created_at),
        INDEX idx_audit_log_success (success)
    );

    PRINT 'Table AuditLog created successfully';
END
ELSE
BEGIN
    PRINT 'Table AuditLog already exists';
END
GO

-- ============================================================================
-- TABLE: ApiKeys
-- Stores API keys for programmatic access
-- ============================================================================

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ApiKeys' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    CREATE TABLE ApiKeys (
        key_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        user_id VARCHAR(100) NOT NULL,
        key_name NVARCHAR(255) NOT NULL,
        api_key_hash NVARCHAR(255) NOT NULL UNIQUE,
        api_key_prefix VARCHAR(20) NOT NULL,
        is_active BIT NOT NULL DEFAULT 1,
        expires_at DATETIME2,
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        last_used_at DATETIME2,
        permissions NVARCHAR(MAX),  -- JSON array of permissions

        -- Foreign key
        CONSTRAINT fk_api_keys_user FOREIGN KEY (user_id)
            REFERENCES Users(user_id) ON DELETE CASCADE,

        -- Indexes
        INDEX idx_api_keys_user (user_id),
        INDEX idx_api_keys_prefix (api_key_prefix),
        INDEX idx_api_keys_is_active (is_active)
    );

    PRINT 'Table ApiKeys created successfully';
END
ELSE
BEGIN
    PRINT 'Table ApiKeys already exists';
END
GO

-- ============================================================================
-- VIEW: ActiveUsers
-- Shows currently active users with recent activity
-- ============================================================================

IF EXISTS (SELECT * FROM sys.views WHERE name = 'ActiveUsers' AND schema_id = SCHEMA_ID('dbo'))
    DROP VIEW ActiveUsers;
GO

CREATE VIEW ActiveUsers AS
SELECT
    u.user_id,
    u.username,
    u.email,
    u.full_name,
    u.role,
    u.created_at,
    u.last_login,
    COUNT(DISTINCT rt.token_id) as active_sessions,
    COUNT(DISTINCT ak.key_id) as active_api_keys
FROM Users u
LEFT JOIN RefreshTokens rt ON u.user_id = rt.user_id
    AND rt.is_revoked = 0
    AND rt.expires_at > GETDATE()
LEFT JOIN ApiKeys ak ON u.user_id = ak.user_id
    AND ak.is_active = 1
WHERE u.is_active = 1
GROUP BY
    u.user_id, u.username, u.email, u.full_name,
    u.role, u.created_at, u.last_login;
GO

PRINT 'View ActiveUsers created successfully';
GO

-- ============================================================================
-- STORED PROCEDURE: sp_CleanupExpiredTokens
-- Removes expired refresh tokens and revoked tokens older than 30 days
-- ============================================================================

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_CleanupExpiredTokens' AND schema_id = SCHEMA_ID('dbo'))
    DROP PROCEDURE sp_CleanupExpiredTokens;
GO

CREATE PROCEDURE sp_CleanupExpiredTokens
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @DeletedCount INT;

    -- Delete expired tokens
    DELETE FROM RefreshTokens
    WHERE expires_at < GETDATE();

    SET @DeletedCount = @@ROWCOUNT;

    -- Delete revoked tokens older than 30 days
    DELETE FROM RefreshTokens
    WHERE is_revoked = 1
    AND revoked_at < DATEADD(DAY, -30, GETDATE());

    SET @DeletedCount = @DeletedCount + @@ROWCOUNT;

    RETURN @DeletedCount;
END
GO

PRINT 'Stored procedure sp_CleanupExpiredTokens created successfully';
GO

-- ============================================================================
-- STORED PROCEDURE: sp_LockUser
-- Locks a user account after too many failed login attempts
-- ============================================================================

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_LockUser' AND schema_id = SCHEMA_ID('dbo'))
    DROP PROCEDURE sp_LockUser;
GO

CREATE PROCEDURE sp_LockUser
    @user_id VARCHAR(100),
    @lock_duration_minutes INT = 30
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE Users
    SET
        locked_until = DATEADD(MINUTE, @lock_duration_minutes, GETDATE()),
        updated_at = GETDATE()
    WHERE user_id = @user_id;

    -- Log the event
    INSERT INTO AuditLog (user_id, event_type, event_description, success)
    VALUES (@user_id, 'account_locked', 'Account locked due to too many failed login attempts', 1);
END
GO

PRINT 'Stored procedure sp_LockUser created successfully';
GO

-- ============================================================================
-- STORED PROCEDURE: sp_UnlockUser
-- Unlocks a user account
-- ============================================================================

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_UnlockUser' AND schema_id = SCHEMA_ID('dbo'))
    DROP PROCEDURE sp_UnlockUser;
GO

CREATE PROCEDURE sp_UnlockUser
    @user_id VARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE Users
    SET
        locked_until = NULL,
        failed_login_attempts = 0,
        updated_at = GETDATE()
    WHERE user_id = @user_id;

    -- Log the event
    INSERT INTO AuditLog (user_id, event_type, event_description, success)
    VALUES (@user_id, 'account_unlocked', 'Account unlocked by administrator', 1);
END
GO

PRINT 'Stored procedure sp_UnlockUser created successfully';
GO

-- ============================================================================
-- Default Admin User (for initial setup)
-- Username: admin
-- Password: admin123 (CHANGE THIS IMMEDIATELY AFTER FIRST LOGIN!)
-- ============================================================================

-- Note: This is a placeholder. The actual password hash will be generated by the application
-- using bcrypt. This is just to show the structure.

IF NOT EXISTS (SELECT * FROM Users WHERE username = 'admin')
BEGIN
    INSERT INTO Users (
        user_id,
        username,
        email,
        hashed_password,
        full_name,
        role,
        is_active,
        is_verified
    )
    VALUES (
        'user_' + CAST(NEWID() AS VARCHAR(36)),
        'admin',
        'admin@ombudsman.local',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7MJQZYMr6a',  -- bcrypt hash of 'admin123'
        'System Administrator',
        'admin',
        1,
        1
    );

    PRINT 'Default admin user created. Please change password after first login!';
END
ELSE
BEGIN
    PRINT 'Admin user already exists';
END
GO

-- ============================================================================
-- Sample Audit Log Events
-- ============================================================================

PRINT '';
PRINT 'Sample audit log event types:';
PRINT '  - user_login';
PRINT '  - user_logout';
PRINT '  - user_register';
PRINT '  - password_change';
PRINT '  - password_reset';
PRINT '  - account_locked';
PRINT '  - account_unlocked';
PRINT '  - api_key_created';
PRINT '  - api_key_revoked';
PRINT '  - permission_changed';
PRINT '';

PRINT 'Authentication schema setup completed successfully!';
PRINT 'Tables: Users, RefreshTokens, AuditLog, ApiKeys';
PRINT 'Views: ActiveUsers';
PRINT 'Procedures: sp_CleanupExpiredTokens, sp_LockUser, sp_UnlockUser';
GO
