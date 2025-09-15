"""JWT认证实现"""

import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from uuid import uuid4

# 加载环境变量
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(project_root / ".env.local")
load_dotenv(project_root / ".env")

from jose import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..database.base import get_db_session as get_direct_db_session
from ..database.models import Tenant, User, UserSession
from .models import AuthUser, TokenData


class JWTAuth:
    """JWT认证管理器"""

    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET_KEY", self._generate_secret_key())
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )
        self.refresh_token_expire_days = int(
            os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
        )

    def _generate_secret_key(self) -> str:
        """生成JWT密钥"""
        return secrets.token_urlsafe(64)

    def create_access_token(
        self, user: User, session_id: str, expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建访问令牌"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )

        # 获取用户角色和权限
        roles, permissions = self._get_user_permissions(user)

        # JWT payload
        to_encode = {
            "sub": str(user.id),  # subject (user_id)
            "email": user.email,
            "username": user.username,
            "tenant_id": user.tenant_id,
            "is_super_admin": user.is_super_admin,
            "roles": roles,
            "permissions": permissions,
            "session_id": session_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid4()),  # JWT ID
            "type": "access",
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(
        self, user: User, session_id: str, expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建刷新令牌"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        to_encode = {
            "sub": str(user.id),
            "session_id": session_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid4()),
            "type": "refresh",
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[TokenData]:
        """验证并解析JWT令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            user_id: int = int(payload.get("sub"))
            if user_id is None:
                return None

            token_data = TokenData(
                user_id=user_id,
                email=payload.get("email"),
                username=payload.get("username"),
                tenant_id=payload.get("tenant_id"),
                is_super_admin=payload.get("is_super_admin", False),
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                session_id=payload.get("session_id"),
                exp=datetime.fromtimestamp(payload.get("exp")),
                iat=datetime.fromtimestamp(payload.get("iat")),
                jti=payload.get("jti"),
            )

            return token_data

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """使用刷新令牌获取新的访问令牌"""
        try:
            payload = jwt.decode(
                refresh_token, self.secret_key, algorithms=[self.algorithm]
            )

            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                )

            user_id = int(payload.get("sub"))
            session_id = payload.get("session_id")

            # 验证会话是否还有效
            db = get_direct_db_session()
            try:
                session = (
                    db.query(UserSession)
                    .filter(
                        UserSession.session_id == session_id,
                        UserSession.is_active == True,
                        UserSession.refresh_token == refresh_token,
                    )
                    .first()
                )

                if not session or session.is_expired():
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Session expired or invalid",
                    )

                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User not found",
                    )

                # 创建新的访问令牌
                new_access_token = self.create_access_token(user, session_id)

                # 更新会话活动时间
                session.last_activity_at = datetime.utcnow()
                db.commit()

                return new_access_token

            finally:
                db.close()

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired",
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

    def invalidate_token(self, jti: str):
        """使JWT令牌失效（通过将JTI加入黑名单）"""
        # TODO: 实现JWT黑名单机制，可以使用Redis存储
        pass

    def _get_user_permissions(self, user: User) -> tuple[list[str], list[str]]:
        """获取用户角色和权限"""
        db = get_direct_db_session()
        try:
            # 获取用户活跃的角色
            from ..database.models import Role, UserRole

            user_roles = (
                db.query(UserRole)
                .filter(UserRole.user_id == user.id, UserRole.is_active == True)
                .all()
            )

            roles = []
            permissions = set()

            for user_role in user_roles:
                if user_role.is_expired():
                    continue

                role = db.query(Role).filter(Role.id == user_role.role_id).first()
                if role:
                    roles.append(role.name)

                    # 获取角色的权限
                    for permission in role.permissions:
                        permissions.add(permission.name)

            return roles, list(permissions)

        finally:
            db.close()


# 全局JWT认证实例
jwt_auth = JWTAuth()


# 便捷函数
def create_access_token(
    user: User, session_id: str, expires_delta: Optional[timedelta] = None
) -> str:
    """创建访问令牌"""
    return jwt_auth.create_access_token(user, session_id, expires_delta)


def verify_token(token: str) -> Optional[TokenData]:
    """验证JWT令牌"""
    return jwt_auth.verify_token(token)


def get_current_user(token_data: TokenData) -> Optional[AuthUser]:
    """根据令牌数据获取当前用户信息"""
    db = get_direct_db_session()
    try:
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if not user:
            return None

        tenant = db.query(Tenant).filter(Tenant.tenant_id == user.tenant_id).first()

        return AuthUser(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            tenant_id=user.tenant_id,
            is_super_admin=user.is_super_admin,
            is_email_verified=user.is_email_verified,
            status=user.status.value,
            roles=token_data.roles,
            permissions=token_data.permissions,
            last_login_at=user.last_login_at,
            preferences=user.preferences or {},
        )

    finally:
        db.close()


# 创建一个简单的JWT认证依赖函数
def jwt_bearer_dependency(authorization: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> TokenData:
    """JWT Bearer认证依赖函数"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )

    if authorization.scheme != "Bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme"
        )

    token_data = verify_token(authorization.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or expired token"
        )

    return token_data


def JWTBearer(auto_error: bool = True):
    """JWT Bearer认证依赖工厂函数"""
    return jwt_bearer_dependency
