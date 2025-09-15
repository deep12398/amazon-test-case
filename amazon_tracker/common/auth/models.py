"""认证相关数据模型和Pydantic Schema"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TokenData(BaseModel):
    """JWT Token数据结构"""

    user_id: int
    tenant_id: str
    email: str
    username: Optional[str] = None
    is_super_admin: bool = False
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    session_id: str
    exp: datetime
    iat: datetime
    jti: str  # JWT ID


class AuthUser(BaseModel):
    """认证用户信息"""

    id: int
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    tenant_id: str
    is_super_admin: bool = False
    is_email_verified: bool = False
    status: str
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    last_login_at: Optional[datetime] = None
    preferences: dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """登录请求"""

    email: EmailStr
    password: str
    device_type: Optional[str] = "web"
    remember_me: bool = False


class LoginResponse(BaseModel):
    """登录响应"""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # 秒
    user: AuthUser


class RegisterRequest(BaseModel):
    """注册请求"""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    company_name: Optional[str] = Field(None, max_length=255)  # 用于创建租户


class RegisterResponse(BaseModel):
    """注册响应"""

    message: str
    user_id: int
    tenant_id: str
    verification_required: bool = True


class PasswordResetRequest(BaseModel):
    """密码重置请求"""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """密码重置确认"""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class RefreshTokenRequest(BaseModel):
    """刷新Token请求"""

    refresh_token: str


class APIKeyRequest(BaseModel):
    """API Key创建请求"""

    name: str = Field(..., max_length=255)
    scopes: list[str] = Field(default_factory=list)
    allowed_ips: list[str] = Field(default_factory=list)
    rate_limit_per_minute: int = Field(60, ge=1, le=1000)
    rate_limit_per_day: int = Field(10000, ge=1, le=1000000)
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)


class APIKeyResponse(BaseModel):
    """API Key响应"""

    key_id: str
    name: str
    key: str  # 仅在创建时返回
    key_prefix: str
    scopes: list[str]
    rate_limit_per_minute: int
    rate_limit_per_day: int
    expires_at: Optional[datetime]
    created_at: datetime


class APIKeyInfo(BaseModel):
    """API Key信息（不包含Key本身）"""

    key_id: str
    name: str
    key_prefix: str
    scopes: list[str]
    status: str
    rate_limit_per_minute: int
    rate_limit_per_day: int
    usage_count: int
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class SessionInfo(BaseModel):
    """会话信息"""

    session_id: UUID
    device_type: Optional[str]
    ip_address: Optional[str]
    location: Optional[str]
    is_active: bool
    last_activity_at: datetime
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """用户档案"""

    id: int
    email: str
    username: Optional[str]
    full_name: Optional[str]
    avatar_url: Optional[str]
    is_email_verified: bool
    status: str
    tenant: "TenantInfo"
    preferences: dict[str, Any]
    last_login_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class TenantInfo(BaseModel):
    """租户信息"""

    tenant_id: str
    name: str
    domain: Optional[str]
    subscription_plan: str
    subscription_status: str
    trial_ends_at: Optional[datetime]
    max_users: int
    max_products: int
    max_api_calls_per_day: int
    timezone: str

    class Config:
        from_attributes = True
