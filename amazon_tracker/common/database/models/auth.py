"""认证和权限相关数据模型"""

import enum
import secrets
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..base import BaseModel


class APIKeyStatus(enum.Enum):
    """API Key状态枚举"""

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class PermissionScope(enum.Enum):
    """权限范围枚举"""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


# 角色权限关联表
role_permissions = Table(
    "role_permissions",
    BaseModel.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
    Index("ix_role_permissions_role", "role_id"),
    Index("ix_role_permissions_permission", "permission_id"),
)


class Permission(BaseModel):
    """权限表"""

    __tablename__ = "permissions"

    # 权限标识
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # 权限范围
    resource = Column(
        String(100), nullable=False
    )  # 资源类型：users, products, analytics等
    action = Column(String(50), nullable=False)  # 操作：read, write, delete, admin
    scope = Column(String(50), nullable=True)  # 作用域：tenant, global

    # 权限配置
    is_system = Column(Boolean, default=False)  # 是否为系统权限（不可删除）
    meta_data = Column(JSONB, default=dict)

    # 关系
    roles = relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )

    # 索引
    __table_args__ = (
        Index("ix_permission_resource_action", "resource", "action"),
        UniqueConstraint(
            "resource", "action", "scope", name="uq_permission_resource_action_scope"
        ),
    )

    def __repr__(self):
        return f"<Permission(name='{self.name}', resource='{self.resource}', action='{self.action}')>"


class Role(BaseModel):
    """角色表"""

    __tablename__ = "roles"

    # 角色信息
    name = Column(String(100), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # 租户关联（为空表示全局角色）
    tenant_id = Column(String(64), nullable=True, index=True)

    # 角色配置
    is_system = Column(Boolean, default=False)  # 是否为系统角色（不可删除）
    is_default = Column(Boolean, default=False)  # 是否为默认角色
    priority = Column(Integer, default=0)  # 优先级，数字越大优先级越高

    # 关系
    permissions = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )
    user_roles = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )

    # 索引
    __table_args__ = (
        Index("ix_role_tenant", "tenant_id"),
        UniqueConstraint("name", "tenant_id", name="uq_role_name_tenant"),
    )

    def __repr__(self):
        return f"<Role(name='{self.name}', tenant_id='{self.tenant_id}')>"


class UserRole(BaseModel):
    """用户角色关联表"""

    __tablename__ = "user_roles"

    # 关联信息
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)

    # 授权信息
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 授权者
    granted_at = Column(DateTime(timezone=True), default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # 角色过期时间

    # 状态
    is_active = Column(Boolean, default=True)

    # 关系
    user = relationship("User", foreign_keys=[user_id], back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")
    granted_by_user = relationship("User", foreign_keys=[granted_by])

    # 索引
    __table_args__ = (
        Index("ix_user_role_user_active", "user_id", "is_active"),
        Index("ix_user_role_expires", "expires_at"),
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )

    def is_expired(self) -> bool:
        """检查角色是否过期"""
        return self.expires_at is not None and self.expires_at <= datetime.utcnow()

    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"


class APIKey(BaseModel):
    """API Key表"""

    __tablename__ = "api_keys"

    # Key信息
    name = Column(String(255), nullable=False)
    key_id = Column(String(32), unique=True, nullable=False, index=True)  # 公开的Key ID
    key_hash = Column(String(255), nullable=False)  # Hash后的Key
    key_prefix = Column(String(8), nullable=False)  # Key前缀（用于识别）

    # 所有者信息
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 权限和限制
    scopes = Column(JSONB, default=list)  # 权限范围
    allowed_ips = Column(JSONB, default=list)  # 允许的IP地址
    rate_limit_per_minute = Column(Integer, default=60)  # 每分钟请求限制
    rate_limit_per_day = Column(Integer, default=10000)  # 每天请求限制

    # 状态和时间
    status = Column(String(20), default=APIKeyStatus.ACTIVE.value, index=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # 统计信息
    usage_count = Column(Integer, default=0)

    # 关系
    user = relationship("User", back_populates="api_keys")

    # 索引
    __table_args__ = (
        Index("ix_api_key_user_status", "user_id", "status"),
        Index("ix_api_key_expires", "expires_at"),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.key_id:
            self.key_id = secrets.token_urlsafe(24)
        if not self.key_prefix:
            self.key_prefix = f"ak_{secrets.token_urlsafe(4)}"[:8]

    def generate_key(self) -> str:
        """生成新的API Key"""
        key = f"{self.key_prefix}_{secrets.token_urlsafe(32)}"
        self.key_hash = self._hash_key(key)
        return key

    def verify_key(self, key: str) -> bool:
        """验证API Key"""
        return self.key_hash == self._hash_key(key)

    def _hash_key(self, key: str) -> str:
        """Hash API Key"""
        import hashlib

        return hashlib.sha256(key.encode()).hexdigest()

    def is_expired(self) -> bool:
        """检查Key是否过期"""
        return self.expires_at is not None and self.expires_at <= datetime.utcnow()

    def is_active(self) -> bool:
        """检查Key是否可用"""
        return self.status == APIKeyStatus.ACTIVE.value and not self.is_expired()

    def revoke(self):
        """撤销Key"""
        self.status = APIKeyStatus.REVOKED.value

    def increment_usage(self):
        """增加使用计数"""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()

    def __repr__(self):
        return f"<APIKey(name='{self.name}', key_id='{self.key_id}', user_id={self.user_id})>"
