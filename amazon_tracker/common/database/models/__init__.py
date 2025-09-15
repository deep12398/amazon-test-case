"""数据库模型"""

from .auth import APIKey, APIKeyStatus, Permission, PermissionScope, Role, UserRole
from .crawl import (
    CrawlerType,
    CrawlLog,
    CrawlSchedule,
    CrawlStatistics,
    CrawlTask,
    TaskPriority,
    TaskStatus,
)
from .product import (
    MarketplaceType,
    Product,
    ProductAlert,
    ProductPriceHistory,
    ProductRankHistory,
    ProductStatus,
    TrackingFrequency,
)
from .user import (
    SubscriptionPlan,
    SubscriptionStatus,
    Tenant,
    User,
    UserSession,
    UserStatus,
)

__all__ = [
    # 用户模型
    "User",
    "Tenant",
    "UserSession",
    "UserStatus",
    "SubscriptionPlan",
    "SubscriptionStatus",
    # 认证模型
    "APIKey",
    "Permission",
    "Role",
    "UserRole",
    "APIKeyStatus",
    "PermissionScope",
    # 产品模型
    "Product",
    "ProductPriceHistory",
    "ProductRankHistory",
    "ProductAlert",
    "ProductStatus",
    "TrackingFrequency",
    "MarketplaceType",
    # 爬虫模型
    "CrawlTask",
    "CrawlLog",
    "CrawlSchedule",
    "CrawlStatistics",
    "TaskStatus",
    "TaskPriority",
    "CrawlerType",
]
