"""
Configuration Models

Pydantic models for type-safe configuration management.
"""

from pydantic import BaseModel, Field, validator, SecretStr
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class ConfigSource(str, Enum):
    """Configuration source types"""
    ENV = "environment"
    FILE = "file"
    AWS_SECRETS = "aws_secrets_manager"
    AZURE_KEYVAULT = "azure_keyvault"
    HASHICORP_VAULT = "hashicorp_vault"
    ENCRYPTED_FILE = "encrypted_file"


class DatabaseConfig(BaseModel):
    """Database connection configuration"""
    host: str = Field(..., description="Database host")
    port: int = Field(..., description="Database port")
    database: str = Field(..., description="Database name")
    username: str = Field(..., description="Database username")
    password: SecretStr = Field(..., description="Database password")
    driver: Optional[str] = Field(None, description="Database driver")
    pool_size: int = Field(5, description="Connection pool size")
    max_overflow: int = Field(10, description="Max pool overflow")
    pool_timeout: int = Field(30, description="Pool timeout in seconds")
    pool_recycle: int = Field(3600, description="Pool recycle time in seconds")
    echo: bool = Field(False, description="Enable SQL echo logging")
    ssl_enabled: bool = Field(False, description="Enable SSL")
    ssl_ca_cert: Optional[str] = Field(None, description="SSL CA certificate path")

    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v

    @validator('pool_size')
    def validate_pool_size(cls, v):
        if v < 1:
            raise ValueError('Pool size must be at least 1')
        return v

    def get_connection_string(self, mask_password: bool = True) -> str:
        """Generate connection string"""
        password = "****" if mask_password else self.password.get_secret_value()
        driver_str = f"+{self.driver}" if self.driver else ""
        return f"postgresql{driver_str}://{self.username}:{password}@{self.host}:{self.port}/{self.database}"

    class Config:
        json_encoders = {
            SecretStr: lambda v: v.get_secret_value() if v else None
        }


class SecretConfig(BaseModel):
    """Secret management configuration"""
    provider: ConfigSource = Field(ConfigSource.ENV, description="Secret provider type")
    aws_region: Optional[str] = Field(None, description="AWS region for Secrets Manager")
    aws_secret_name: Optional[str] = Field(None, description="AWS secret name")
    azure_vault_url: Optional[str] = Field(None, description="Azure Key Vault URL")
    vault_url: Optional[str] = Field(None, description="HashiCorp Vault URL")
    vault_token: Optional[SecretStr] = Field(None, description="Vault authentication token")
    vault_path: Optional[str] = Field(None, description="Vault secret path")
    encryption_key: Optional[SecretStr] = Field(None, description="Encryption key for file-based secrets")
    cache_ttl: int = Field(300, description="Secret cache TTL in seconds")
    auto_rotate: bool = Field(False, description="Enable automatic secret rotation")
    rotation_days: int = Field(90, description="Days between automatic rotations")


class JWTConfig(BaseModel):
    """JWT authentication configuration"""
    secret_key: SecretStr = Field(..., description="JWT secret key")
    algorithm: str = Field("HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(30, description="Access token expiration")
    refresh_token_expire_days: int = Field(7, description="Refresh token expiration")

    @validator('algorithm')
    def validate_algorithm(cls, v):
        allowed = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if v not in allowed:
            raise ValueError(f"Algorithm must be one of {allowed}")
        return v


class CORSConfig(BaseModel):
    """CORS configuration"""
    allow_origins: List[str] = Field(["*"], description="Allowed origins")
    allow_credentials: bool = Field(True, description="Allow credentials")
    allow_methods: List[str] = Field(["*"], description="Allowed methods")
    allow_headers: List[str] = Field(["*"], description="Allowed headers")
    expose_headers: List[str] = Field([], description="Exposed headers")
    max_age: int = Field(600, description="Preflight cache max age")


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field("INFO", description="Log level")
    format: str = Field("%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")
    handlers: List[str] = Field(["console"], description="Log handlers")
    log_file: Optional[str] = Field(None, description="Log file path")
    max_bytes: int = Field(10485760, description="Max log file size (10MB)")
    backup_count: int = Field(5, description="Number of backup files")
    json_logs: bool = Field(False, description="Use JSON log format")

    @validator('level')
    def validate_level(cls, v):
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v.upper()


class ApplicationConfig(BaseModel):
    """Main application configuration"""
    app_name: str = Field("Ombudsman Validation Studio", description="Application name")
    app_version: str = Field("2.0.0", description="Application version")
    environment: str = Field("development", description="Environment (development, staging, production)")
    debug: bool = Field(False, description="Debug mode")
    host: str = Field("0.0.0.0", description="API host")
    port: int = Field(8000, description="API port")
    reload: bool = Field(False, description="Auto-reload on code changes")
    workers: int = Field(1, description="Number of worker processes")

    # Database configurations
    sql_server: Optional[DatabaseConfig] = Field(None, description="SQL Server configuration")
    snowflake: Optional[DatabaseConfig] = Field(None, description="Snowflake configuration")
    postgres: Optional[DatabaseConfig] = Field(None, description="PostgreSQL configuration (for app data)")

    # Security
    jwt: Optional[JWTConfig] = Field(None, description="JWT configuration")
    cors: CORSConfig = Field(default_factory=CORSConfig, description="CORS configuration")
    secrets: SecretConfig = Field(default_factory=SecretConfig, description="Secrets management")

    # Logging
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging configuration")

    # Features
    enable_auth: bool = Field(True, description="Enable authentication")
    enable_websockets: bool = Field(True, description="Enable WebSocket support")
    enable_metrics: bool = Field(True, description="Enable metrics collection")
    enable_cache: bool = Field(True, description="Enable caching")

    # Limits
    max_upload_size_mb: int = Field(100, description="Max file upload size in MB")
    rate_limit_per_minute: int = Field(60, description="API rate limit per minute")
    max_concurrent_pipelines: int = Field(10, description="Max concurrent pipeline executions")

    # Storage
    data_dir: str = Field("/data", description="Data storage directory")
    temp_dir: str = Field("/tmp", description="Temporary files directory")
    backup_dir: Optional[str] = Field(None, description="Backup directory")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="Config creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Config update time")
    config_version: str = Field("1.0", description="Configuration schema version")

    @validator('environment')
    def validate_environment(cls, v):
        allowed = ["development", "staging", "production"]
        if v.lower() not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v.lower()

    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v

    @validator('workers')
    def validate_workers(cls, v):
        if v < 1:
            raise ValueError('Workers must be at least 1')
        return v

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"

    class Config:
        json_encoders = {
            SecretStr: lambda v: "***REDACTED***",
            datetime: lambda v: v.isoformat()
        }


class ConfigMetadata(BaseModel):
    """Configuration metadata for tracking"""
    source: ConfigSource
    loaded_at: datetime = Field(default_factory=datetime.now)
    file_path: Optional[str] = None
    environment: Optional[str] = None
    version: str = "1.0"
    is_encrypted: bool = False
    checksum: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConfigHistory(BaseModel):
    """Configuration change history"""
    timestamp: datetime = Field(default_factory=datetime.now)
    changed_by: Optional[str] = None
    changes: Dict[str, Any]
    reason: Optional[str] = None
    previous_checksum: Optional[str] = None
    new_checksum: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
