"""权限检查和装饰器"""

from typing import Union

from fastapi import Depends, HTTPException, status

from .jwt_auth import JWTBearer, get_current_user
from .models import AuthUser, TokenData


class PermissionChecker:
    """权限检查器"""

    def __init__(self, required_permissions: list[str], require_all: bool = True):
        """
        初始化权限检查器

        Args:
            required_permissions: 需要的权限列表
            require_all: 是否需要所有权限（True）还是任意一个权限（False）
        """
        self.required_permissions = required_permissions
        self.require_all = require_all

    def check_permissions(self, user: AuthUser) -> bool:
        """检查用户是否有权限"""
        if user.is_super_admin:
            return True

        user_permissions = set(user.permissions)
        required_permissions = set(self.required_permissions)

        if self.require_all:
            return required_permissions.issubset(user_permissions)
        else:
            return bool(required_permissions.intersection(user_permissions))

    def __call__(self, token_data: TokenData = Depends(JWTBearer())) -> AuthUser:
        """作为FastAPI依赖使用"""
        user = get_current_user(token_data)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        if not self.check_permissions(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )

        return user


class RoleChecker:
    """角色检查器"""

    def __init__(self, required_roles: list[str], require_all: bool = False):
        """
        初始化角色检查器

        Args:
            required_roles: 需要的角色列表
            require_all: 是否需要所有角色（True）还是任意一个角色（False）
        """
        self.required_roles = required_roles
        self.require_all = require_all

    def check_roles(self, user: AuthUser) -> bool:
        """检查用户是否有角色"""
        if user.is_super_admin:
            return True

        user_roles = set(user.roles)
        required_roles = set(self.required_roles)

        if self.require_all:
            return required_roles.issubset(user_roles)
        else:
            return bool(required_roles.intersection(user_roles))

    def __call__(self, token_data: TokenData = Depends(JWTBearer())) -> AuthUser:
        """作为FastAPI依赖使用"""
        user = get_current_user(token_data)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        if not self.check_roles(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role privileges",
            )

        return user


class TenantChecker:
    """租户检查器 - 确保用户只能访问自己租户的数据"""

    def __init__(self, allow_super_admin: bool = True):
        """
        初始化租户检查器

        Args:
            allow_super_admin: 是否允许超级管理员跨租户访问
        """
        self.allow_super_admin = allow_super_admin

    def check_tenant_access(self, user: AuthUser, target_tenant_id: str) -> bool:
        """检查用户是否可以访问目标租户的数据"""
        if self.allow_super_admin and user.is_super_admin:
            return True

        return user.tenant_id == target_tenant_id

    def __call__(self, token_data: TokenData = Depends(JWTBearer())) -> AuthUser:
        """作为FastAPI依赖使用"""
        user = get_current_user(token_data)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        return user


def require_permission(
    permissions: Union[str, list[str]], require_all: bool = True
) -> PermissionChecker:
    """
    权限要求装饰器工厂

    Args:
        permissions: 权限名称或权限列表
        require_all: 是否需要所有权限

    Returns:
        PermissionChecker实例

    Usage:
        @app.get("/admin/users")
        async def get_users(user: AuthUser = Depends(require_permission("users.read"))):
            pass
    """
    if isinstance(permissions, str):
        permissions = [permissions]

    return PermissionChecker(permissions, require_all)


def require_role(
    roles: Union[str, list[str]], require_all: bool = False
) -> RoleChecker:
    """
    角色要求装饰器工厂

    Args:
        roles: 角色名称或角色列表
        require_all: 是否需要所有角色

    Returns:
        RoleChecker实例

    Usage:
        @app.get("/admin/dashboard")
        async def admin_dashboard(user: AuthUser = Depends(require_role("admin"))):
            pass
    """
    if isinstance(roles, str):
        roles = [roles]

    return RoleChecker(roles, require_all)


def require_tenant_access() -> TenantChecker:
    """
    租户访问要求装饰器

    Returns:
        TenantChecker实例

    Usage:
        @app.get("/tenant/{tenant_id}/products")
        async def get_products(
            tenant_id: str,
            user: AuthUser = Depends(require_tenant_access())
        ):
            # 需要手动检查租户访问权限
            if not TenantChecker().check_tenant_access(user, tenant_id):
                raise HTTPException(403, "Access denied")
            pass
    """
    return TenantChecker()


def require_super_admin() -> RoleChecker:
    """
    超级管理员要求装饰器

    Returns:
        RoleChecker实例
    """

    def super_admin_checker(token_data: TokenData = Depends(JWTBearer())) -> AuthUser:
        user = get_current_user(token_data)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        if not user.is_super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Super admin privileges required",
            )

        return user

    return super_admin_checker


# 常用权限常量
class PermissionScope:
    """权限作用域常量定义"""

    # 爬虫权限
    CRAWLER_READ = "crawler.read"
    CRAWLER_CREATE = "crawler.create"
    CRAWLER_MANAGE = "crawler.manage"

    # 产品权限
    PRODUCTS_READ = "products.read"
    PRODUCTS_WRITE = "products.write"
    PRODUCTS_DELETE = "products.delete"

    # 用户权限
    USERS_READ = "users.read"
    USERS_WRITE = "users.write"
    USERS_ADMIN = "users.admin"

    # 提醒权限
    ALERT_CREATE = "alert.create"
    ALERT_READ = "alert.read"
    ALERT_UPDATE = "alert.update"
    ALERT_DELETE = "alert.delete"
    ALERT_MANAGE = "alert.manage"


class Permissions:
    """权限常量定义"""

    # 用户管理
    USERS_READ = "users.read"
    USERS_WRITE = "users.write"
    USERS_DELETE = "users.delete"
    USERS_ADMIN = "users.admin"

    # 产品管理
    PRODUCTS_READ = "products.read"
    PRODUCTS_WRITE = "products.write"
    PRODUCTS_DELETE = "products.delete"
    PRODUCTS_ADMIN = "products.admin"

    # 分析和报告
    ANALYTICS_READ = "analytics.read"
    ANALYTICS_EXPORT = "analytics.export"

    # 系统管理
    SYSTEM_ADMIN = "system.admin"
    SYSTEM_SETTINGS = "system.settings"

    # API Key管理
    API_KEYS_READ = "api_keys.read"
    API_KEYS_WRITE = "api_keys.write"
    API_KEYS_DELETE = "api_keys.delete"

    # 租户管理
    TENANT_READ = "tenant.read"
    TENANT_WRITE = "tenant.write"
    TENANT_ADMIN = "tenant.admin"


# 常用角色常量
class Roles:
    """角色常量定义"""

    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    USER = "user"
    VIEWER = "viewer"
    API_USER = "api_user"
