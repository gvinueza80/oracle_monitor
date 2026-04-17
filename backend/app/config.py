"""
Configuration management for Oracle Monitoring System
"""

import json
from typing import List, Optional

from pydantic_settings import BaseSettings


class OracleInstanceConfig(BaseSettings):
    """Configuration for a single Oracle instance"""
    name: str
    user: str
    password: str
    dsn: str
    ssl_enabled: bool = False
    pool_min: int = 2
    pool_max: int = 10
    timeout: int = 30


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "debug"

    # API Settings
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Database
    DATABASE_URL: str = "postgresql://oracle_monitor:dev_password@localhost:5432/oracle_monitor"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_TIMEOUT: int = 30

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_CACHE_TTL: int = 30  # seconds

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379"
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]

    # Oracle Monitoring Configuration
    ORACLE_INSTANCES: str = "[]"  # JSON string
    METRIC_COLLECTION_INTERVAL_CRITICAL: int = 10  # seconds (locks, sessions)
    METRIC_COLLECTION_INTERVAL_STANDARD: int = 30  # seconds (CPU, memory)
    METRIC_COLLECTION_INTERVAL_HISTORICAL: int = 300  # seconds (5 minutes)

    # Alert Configuration
    ALERT_RETENTION_DAYS: int = 365
    ALERT_SUPPRESSION_DEFAULT_MINUTES: int = 60
    ALERT_ESCALATION_ENABLED: bool = True

    # Notifications
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_ADDRESS: str = "oracle-monitor@example.com"

    SLACK_WEBHOOK_URL: Optional[str] = None
    SLACK_ALERT_CHANNEL: str = "#database-alerts"

    # Vault Configuration
    VAULT_ENABLED: bool = False
    VAULT_ADDR: Optional[str] = None
    VAULT_TOKEN: Optional[str] = None

    # Data Retention
    METRICS_RETENTION_DAYS: int = 90
    LOGS_RETENTION_DAYS: int = 365
    AUDIT_RETENTION_DAYS: int = 730

    # Performance
    MAX_QUERY_RESULT_SIZE: int = 10000
    SLOW_QUERY_THRESHOLD_MS: int = 5000

    class Config:
        env_file = ".env"
        case_sensitive = True

    def get_oracle_instances(self) -> List[OracleInstanceConfig]:
        """Parse Oracle instances from JSON string"""
        try:
            instances_data = json.loads(self.ORACLE_INSTANCES)
            return [OracleInstanceConfig(**inst) for inst in instances_data]
        except (json.JSONDecodeError, ValueError):
            return []

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"


# Global settings instance
settings = Settings()
