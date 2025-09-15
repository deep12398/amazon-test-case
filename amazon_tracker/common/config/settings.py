"""应用程序配置设置"""

from functools import lru_cache
from typing import Optional

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    # 降级处理，如果pydantic_settings不可用
    from pydantic import BaseSettings, Field

    SettingsConfigDict = None


class Settings(BaseSettings):
    """应用程序设置"""

    if SettingsConfigDict:
        model_config = SettingsConfigDict(
            env_file=".env.local", env_ignore_empty=True, extra="ignore"
        )
    else:

        class Config:
            env_file = ".env.local"
            extra = "ignore"

    # ===== 基础配置 =====
    APP_NAME: str = "Amazon产品追踪分析系统"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # ===== 数据库配置 =====
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/amazon_tracker",
        description="数据库连接URL",
    )

    # ===== Redis配置 =====
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0", description="Redis连接URL"
    )

    # ===== 认证配置 =====
    JWT_SECRET: str = Field(
        default="your-super-secret-jwt-key-here", description="JWT密钥"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    JWT_REFRESH_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12

    # ===== API配置 =====
    API_V1_PREFIX: str = "/api/v1"
    API_RATE_LIMIT: str = "100/hour"
    API_BURST_LIMIT: str = "20/minute"
    CORS_ORIGINS: str = "http://localhost:3000,https://yourdomain.com"

    # ===== 外部API配置 =====
    OPENAI_API_KEY: Optional[str] = None
    APIFY_API_TOKEN: Optional[str] = None

    # ===== AWS配置 =====
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    SQS_QUEUE_URL: Optional[str] = None
    SQS_DLQ_URL: Optional[str] = None

    # ===== Supabase配置 =====
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None

    # ===== Celery配置 =====
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1", description="Celery消息队列URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/1", description="Celery结果后端URL"
    )
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_TIMEZONE: str = "UTC"

    # ===== APISIX网关配置 =====
    APISIX_ADMIN_KEY: Optional[str] = None
    APISIX_PROXY_URL: str = "http://localhost:9080"
    APISIX_ADMIN_URL: str = "http://localhost:9180"
    ETCD_HOST: str = "localhost"
    ETCD_PORT: int = 2379

    # ===== 监控配置 =====
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    OPENTELEMETRY_ENDPOINT: str = "http://localhost:4317"
    PROMETHEUS_PORT: int = 9090
    GRAFANA_PORT: int = 3000

    # ===== 外部API限制 =====
    APIFY_TIMEOUT: int = 300
    APIFY_MAX_RETRIES: int = 3
    OPENAI_TIMEOUT: int = 60
    OPENAI_MAX_TOKENS: int = 4000
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ===== 邮件配置 =====
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: Optional[str] = None
    NOTIFICATION_EMAIL: Optional[str] = None

    # ===== 应用程序设置 =====
    MAX_PRODUCTS_PER_TENANT: int = 1000
    MAX_CONCURRENT_CRAWLS: int = 5
    DATA_RETENTION_DAYS: int = 365
    CACHE_TTL_SECONDS: int = 3600

    # ===== 开发设置 =====
    RELOAD: bool = False
    WORKERS: int = 4

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS允许的源列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    """获取配置设置单例"""
    return Settings()
