"""租户模型"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from amazon_tracker.common.database.base import Base

if TYPE_CHECKING:
    from .product import Product
    from .user import User


class Tenant(Base):
    """租户表

    存储多租户系统中的租户信息
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="租户ID"
    )

    name: Mapped[str] = Column(String(255), nullable=False, comment="租户名称")

    subdomain: Mapped[str] = Column(
        String(100), unique=True, nullable=True, comment="子域名"
    )

    api_key: Mapped[str] = Column(
        String(255), unique=True, nullable=True, comment="API密钥"
    )

    plan_type: Mapped[str] = Column(
        String(50),
        nullable=False,
        default="basic",
        comment="套餐类型: basic, premium, enterprise",
    )

    max_products: Mapped[int] = Column(
        Integer, nullable=False, default=100, comment="最大产品数量"
    )

    max_users: Mapped[int] = Column(
        Integer, nullable=False, default=5, comment="最大用户数量"
    )

    status: Mapped[str] = Column(
        String(50),
        nullable=False,
        default="active",
        comment="状态: active, suspended, cancelled",
    )

    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="创建时间",
    )

    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )

    # 关系定义
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="tenant", cascade="all, delete-orphan"
    )

    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="tenant", cascade="all, delete-orphan"
    )

    # 索引定义
    __table_args__ = (
        Index("idx_tenants_subdomain", "subdomain"),
        Index("idx_tenants_api_key", "api_key"),
        Index("idx_tenants_status", "status"),
        Index("idx_tenants_plan_type", "plan_type"),
        Index("idx_tenants_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name='{self.name}', plan='{self.plan_type}')>"
