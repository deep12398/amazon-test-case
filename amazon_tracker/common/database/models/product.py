"""产品相关数据模型"""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..base import BaseModel, TenantMixin


class ProductStatus(enum.Enum):
    """产品状态枚举"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"
    MONITORING = "monitoring"
    ERROR = "error"


class TrackingFrequency(enum.Enum):
    """追踪频率枚举"""

    HOURLY = "hourly"
    EVERY_6_HOURS = "every_6_hours"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class MarketplaceType(enum.Enum):
    """市场类型枚举"""

    AMAZON_US = "amazon_us"
    AMAZON_UK = "amazon_uk"
    AMAZON_DE = "amazon_de"
    AMAZON_FR = "amazon_fr"
    AMAZON_JP = "amazon_jp"
    AMAZON_CA = "amazon_ca"
    AMAZON_AU = "amazon_au"
    AMAZON_IN = "amazon_in"


class Product(BaseModel, TenantMixin):
    """产品表"""

    __tablename__ = "products"

    # 基本信息
    asin = Column(String(20), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    brand = Column(String(200), nullable=True)
    category = Column(String(200), nullable=True)

    # 市场信息
    marketplace = Column(
        SQLEnum(MarketplaceType), default=MarketplaceType.AMAZON_US, nullable=False
    )
    product_url = Column(Text, nullable=False)
    image_url = Column(Text, nullable=True)

    # 追踪设置
    status = Column(
        SQLEnum(ProductStatus), default=ProductStatus.ACTIVE, nullable=False
    )
    tracking_frequency = Column(
        SQLEnum(TrackingFrequency), default=TrackingFrequency.DAILY, nullable=False
    )
    is_competitor = Column(Boolean, default=False, nullable=False)  # 是否是竞品

    # 当前数据快照
    current_price = Column(Numeric(10, 2), nullable=True)
    buy_box_price = Column(Numeric(10, 2), nullable=True)  # Buy Box价格
    current_rank = Column(Integer, nullable=True)  # Best Seller Rank
    current_rating = Column(Numeric(3, 2), nullable=True)
    current_review_count = Column(Integer, nullable=True, default=0)
    current_availability = Column(String(50), nullable=True)

    # 元数据
    product_data = Column(JSONB, default=dict)  # 完整产品数据
    bullet_points = Column(JSONB, default=list)  # 产品特征点
    description = Column(Text, nullable=True)  # 产品描述
    last_scraped_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)

    # 用户设置
    price_alert_threshold = Column(Numeric(10, 2), nullable=True)  # 价格预警阈值
    rank_alert_threshold = Column(Integer, nullable=True)  # 排名预警阈值
    notes = Column(Text, nullable=True)
    tags = Column(JSONB, default=list)  # 标签

    # 关系
    price_history = relationship(
        "ProductPriceHistory", back_populates="product", cascade="all, delete-orphan"
    )
    rank_history = relationship(
        "ProductRankHistory", back_populates="product", cascade="all, delete-orphan"
    )
    crawl_tasks = relationship(
        "CrawlTask", back_populates="product", cascade="all, delete-orphan"
    )

    # 索引和约束
    __table_args__ = (
        UniqueConstraint(
            "asin",
            "marketplace",
            "tenant_id",
            name="uq_product_asin_marketplace_tenant",
        ),
        Index("ix_product_tenant_status", "tenant_id", "status"),
        Index("ix_product_marketplace_asin", "marketplace", "asin"),
        Index("ix_product_last_scraped", "last_scraped_at"),
        Index("ix_product_tracking_frequency", "tracking_frequency"),
        Index("ix_product_is_competitor", "tenant_id", "is_competitor"),
    )

    @property
    def needs_update(self) -> bool:
        """检查是否需要更新数据"""
        if not self.last_scraped_at:
            return True

        frequency_map = {
            TrackingFrequency.HOURLY: 1,
            TrackingFrequency.EVERY_6_HOURS: 6,
            TrackingFrequency.DAILY: 24,
            TrackingFrequency.WEEKLY: 24 * 7,
            TrackingFrequency.MONTHLY: 24 * 30,
        }

        hours_since_update = (
            datetime.utcnow() - self.last_scraped_at
        ).total_seconds() / 3600
        return hours_since_update >= frequency_map.get(self.tracking_frequency, 24)

    def update_current_data(self, data: dict[str, Any]):
        """更新当前数据快照"""
        self.current_price = data.get("price")
        self.current_rank = data.get("rank")
        self.current_rating = data.get("rating")
        self.current_review_count = data.get("review_count", 0)
        self.current_availability = data.get("availability")
        self.product_data = data
        self.last_scraped_at = datetime.utcnow()
        self.error_count = 0
        self.last_error = None

    def record_error(self, error_message: str):
        """记录错误"""
        self.last_error = error_message
        self.error_count += 1

        # 如果错误次数过多，暂停追踪
        if self.error_count >= 5:
            self.status = ProductStatus.ERROR

    def __repr__(self):
        return f"<Product(asin='{self.asin}', title='{self.title[:50]}...', tenant_id='{self.tenant_id}')>"


class ProductPriceHistory(BaseModel):
    """产品价格历史"""

    __tablename__ = "product_price_history"

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)

    # 价格信息
    price = Column(Numeric(10, 2), nullable=True)
    list_price = Column(Numeric(10, 2), nullable=True)  # 原价
    buy_box_price = Column(Numeric(10, 2), nullable=True)  # Buy Box价格
    discount_percent = Column(Numeric(5, 2), nullable=True)
    currency = Column(String(3), default="USD", nullable=False)

    # 时间戳
    recorded_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    # 关系
    product = relationship("Product", back_populates="price_history")

    # 索引
    __table_args__ = (
        Index("ix_price_history_product_recorded", "product_id", "recorded_at"),
        Index("ix_price_history_recorded_at", "recorded_at"),
    )

    def __repr__(self):
        return f"<ProductPriceHistory(product_id={self.product_id}, price={self.price}, recorded_at={self.recorded_at})>"


class ProductRankHistory(BaseModel):
    """产品排名历史"""

    __tablename__ = "product_rank_history"

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)

    # 排名信息
    rank = Column(Integer, nullable=True)
    category = Column(String(200), nullable=True)
    subcategory = Column(String(200), nullable=True)

    # 评价信息
    rating = Column(Numeric(3, 2), nullable=True)
    review_count = Column(Integer, nullable=True, default=0)

    # 时间戳
    recorded_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    # 关系
    product = relationship("Product", back_populates="rank_history")

    # 索引
    __table_args__ = (
        Index("ix_rank_history_product_recorded", "product_id", "recorded_at"),
        Index("ix_rank_history_recorded_at", "recorded_at"),
    )

    def __repr__(self):
        return f"<ProductRankHistory(product_id={self.product_id}, rank={self.rank}, recorded_at={self.recorded_at})>"


class ProductAlert(BaseModel, TenantMixin):
    """产品预警"""

    __tablename__ = "product_alerts"

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_by = Column(Integer, nullable=True)  # 创建者ID

    # 预警类型和条件
    alert_type = Column(
        String(50), nullable=False
    )  # price_drop, price_target, rank_change, stock_alert等
    target_value = Column(Numeric(10, 2), nullable=True)  # 目标价格或排名
    threshold_percentage = Column(Numeric(5, 2), nullable=True)  # 百分比阈值
    current_value = Column(Numeric(10, 2), nullable=True)  # 当前值

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    # 触发历史
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    trigger_count = Column(Integer, default=0, nullable=False)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)

    # 通知设置
    notification_methods = Column(JSONB, default=list)  # 通知方式列表

    # 关系
    product = relationship("Product")
    user = relationship("User", foreign_keys=[user_id])

    # 索引
    __table_args__ = (
        Index("ix_alert_product_user", "product_id", "user_id"),
        Index("ix_alert_tenant_active", "tenant_id", "is_active"),
        Index("ix_alert_type", "alert_type"),
        Index("ix_alert_active_deleted", "is_active", "is_deleted"),
    )

    def __repr__(self):
        return f"<ProductAlert(product_id={self.product_id}, alert_type='{self.alert_type}', is_active={self.is_active})>"


