"""用户相关数据模型"""

import enum
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..base import BaseModel


class UserStatus(enum.Enum):
    """用户状态枚举"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class SubscriptionPlan(enum.Enum):
    """订阅计划枚举"""

    FREE_TRIAL = "free_trial"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(enum.Enum):
    """订阅状态枚举"""

    TRIAL = "trial"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"


class Tenant(BaseModel):
    """租户表 - 多租户支持"""

    __tablename__ = "tenants"

    tenant_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(100), unique=True, nullable=True)

    subscription_plan = Column(
        SQLEnum(SubscriptionPlan), default=SubscriptionPlan.FREE_TRIAL
    )
    subscription_status = Column(
        SQLEnum(SubscriptionStatus), default=SubscriptionStatus.TRIAL
    )
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    subscription_ends_at = Column(DateTime(timezone=True), nullable=True)

    max_users = Column(Integer, default=5)
    max_products = Column(Integer, default=100)
    max_api_calls_per_day = Column(Integer, default=1000)

    settings = Column(JSONB, default=dict)
    timezone = Column(String(50), default="UTC")

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.tenant_id:
            self.tenant_id = f"tenant_{secrets.token_urlsafe(16)}"
        if not self.trial_ends_at:
            self.trial_ends_at = datetime.utcnow() + timedelta(days=14)

    @property
    def is_trial_active(self) -> bool:
        return (
            self.subscription_status == SubscriptionStatus.TRIAL
            and self.trial_ends_at
            and self.trial_ends_at > datetime.utcnow()
        )

    def __repr__(self):
        return (
            f"<Tenant(id={self.id}, tenant_id='{self.tenant_id}', name='{self.name}')>"
        )


class User(BaseModel):
    """用户表"""

    __tablename__ = "users"

    email = Column(String(320), nullable=False, index=True)
    username = Column(String(50), nullable=True, index=True)
    full_name = Column(String(255), nullable=True)

    password_hash = Column(String(255), nullable=False)
    salt = Column(String(32), nullable=False)

    status = Column(SQLEnum(UserStatus), default=UserStatus.PENDING_VERIFICATION)
    is_email_verified = Column(Boolean, default=False)
    is_super_admin = Column(Boolean, default=False)

    tenant_id = Column(
        String(64), ForeignKey("tenants.tenant_id"), nullable=False, index=True
    )

    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    login_count = Column(Integer, default=0)

    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), default=func.now())

    email_verification_token = Column(String(255), nullable=True, index=True)
    email_verification_expires_at = Column(DateTime(timezone=True), nullable=True)
    password_reset_token = Column(String(255), nullable=True, index=True)
    password_reset_expires_at = Column(DateTime(timezone=True), nullable=True)

    preferences = Column(JSONB, default=dict)
    avatar_url = Column(String(512), nullable=True)

    tenant = relationship("Tenant", back_populates="users")
    sessions = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    user_roles = relationship(
        "UserRole",
        foreign_keys="UserRole.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    api_keys = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("email", "tenant_id", name="uq_user_email_tenant"),
        UniqueConstraint("username", "tenant_id", name="uq_user_username_tenant"),
        Index("ix_user_tenant_status", "tenant_id", "status"),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.salt:
            self.salt = secrets.token_urlsafe(24)

    def set_password(self, password: str):
        salt = secrets.token_urlsafe(24)
        self.salt = salt
        self.password_hash = self._hash_password(password, salt)
        self.password_changed_at = datetime.utcnow()

    def verify_password(self, password: str) -> bool:
        return self.password_hash == self._hash_password(password, self.salt)

    def _hash_password(self, password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
        ).hex()

    def generate_email_verification_token(self) -> str:
        token = secrets.token_urlsafe(32)
        self.email_verification_token = token
        self.email_verification_expires_at = datetime.utcnow() + timedelta(hours=24)
        return token

    def is_locked(self) -> bool:
        return self.locked_until is not None and self.locked_until > datetime.utcnow()

    def unlock_account(self):
        pass

    def __repr__(self):
        return (
            f"<User(id={self.id}, email='{self.email}', tenant_id='{self.tenant_id}')>"
        )


class UserSession(BaseModel):
    """用户会话表"""

    __tablename__ = "user_sessions"

    session_id = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    device_type = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    location = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), default=func.now())

    jwt_jti = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=True, index=True)

    user = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("ix_session_user_active", "user_id", "is_active"),
        Index("ix_session_expires", "expires_at"),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(hours=24)

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    def invalidate(self):
        self.is_active = False

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, session_id='{self.session_id}')>"
