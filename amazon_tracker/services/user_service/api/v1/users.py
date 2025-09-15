"""用户管理API路由"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_
from sqlalchemy.orm import Session
from amazon_tracker.common.auth.jwt_auth import JWTBearer
from amazon_tracker.common.auth.models import (
    APIKeyInfo,
    APIKeyRequest,
    APIKeyResponse,
    AuthUser,
    TenantInfo,
    UserProfile,
)
from amazon_tracker.common.auth.permissions import (
    Permissions,
    require_permission,
)
from amazon_tracker.common.database.base import get_db_session
from amazon_tracker.common.database.models import (
    APIKey,
    Role,
    User,
    UserRole,
    UserStatus,
)

router = APIRouter()


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    authorization: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db_session)
):
    """获取当前用户档案"""
    # 验证JWT token
    from amazon_tracker.common.auth.jwt_auth import verify_token, get_current_user

    if not authorization or authorization.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid authentication")

    token_data = verify_token(authorization.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")

    current_user = get_current_user(token_data)
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")

    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    tenant = user.tenant
    tenant_info = TenantInfo(
        tenant_id=tenant.tenant_id,
        name=tenant.name,
        domain=tenant.domain,
        subscription_plan=tenant.subscription_plan.value,
        subscription_status=tenant.subscription_status.value,
        trial_ends_at=tenant.trial_ends_at,
        max_users=tenant.max_users,
        max_products=tenant.max_products,
        max_api_calls_per_day=tenant.max_api_calls_per_day,
        timezone=tenant.timezone,
    )

    profile = UserProfile(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_email_verified=user.is_email_verified,
        status=user.status.value,
        tenant=tenant_info,
        preferences=user.preferences or {},
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )

    return profile


@router.put("/me")
async def update_current_user_profile(
    updates: dict,
    current_user: AuthUser = Depends(JWTBearer()),
    db: Session = Depends(get_db_session),
):
    """更新当前用户档案"""

    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 允许更新的字段
    allowed_fields = {"full_name", "username", "avatar_url", "preferences"}

    for field, value in updates.items():
        if field in allowed_fields:
            setattr(user, field, value)

    db.commit()

    return {"message": "档案更新成功"}


@router.get("/", response_model=list[dict])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None, description="搜索邮箱或姓名"),
    status_filter: Optional[UserStatus] = Query(None, description="按状态筛选"),
    current_user: AuthUser = Depends(require_permission(Permissions.USERS_READ)),
    db: Session = Depends(get_db_session),
):
    """获取用户列表"""

    query = db.query(User).filter(User.tenant_id == current_user.tenant_id)

    # 搜索过滤
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                User.email.ilike(search_term),
                User.full_name.ilike(search_term),
                User.username.ilike(search_term),
            )
        )

    # 状态过滤
    if status_filter:
        query = query.filter(User.status == status_filter)

    total = query.count()
    users = query.offset(skip).limit(limit).all()

    result = []
    for user in users:
        user_data = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "status": user.status.value,
            "is_email_verified": user.is_email_verified,
            "is_super_admin": user.is_super_admin,
            "last_login_at": user.last_login_at,
            "created_at": user.created_at,
        }
        result.append(user_data)

    return {"users": result, "total": total, "skip": skip, "limit": limit}


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    current_user: AuthUser = Depends(require_permission(Permissions.USERS_READ)),
    db: Session = Depends(get_db_session),
):
    """获取指定用户信息"""

    user = (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == current_user.tenant_id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "status": user.status.value,
        "is_email_verified": user.is_email_verified,
        "is_super_admin": user.is_super_admin,
        "last_login_at": user.last_login_at,
        "login_count": user.login_count,
        "preferences": user.preferences,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


@router.put("/{user_id}/status")
async def update_user_status(
    user_id: int,
    new_status: UserStatus,
    current_user: AuthUser = Depends(require_permission(Permissions.USERS_WRITE)),
    db: Session = Depends(get_db_session),
):
    """更新用户状态"""

    user = (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == current_user.tenant_id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 防止用户禁用自己
    if user.id == current_user.id and new_status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="不能禁用自己的账户"
        )

    user.status = new_status
    db.commit()

    return {"message": f"用户状态已更新为 {new_status.value}"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: AuthUser = Depends(require_permission(Permissions.USERS_DELETE)),
    db: Session = Depends(get_db_session),
):
    """删除用户（软删除）"""

    user = (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == current_user.tenant_id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 防止用户删除自己
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除自己的账户"
        )

    user.is_deleted = True
    user.status = UserStatus.INACTIVE
    db.commit()

    return {"message": "用户已删除"}


@router.get("/me/api-keys", response_model=list[APIKeyInfo])
async def list_user_api_keys(
    current_user: AuthUser = Depends(JWTBearer()), db: Session = Depends(get_db_session)
):
    """获取当前用户的API Key列表"""

    api_keys = (
        db.query(APIKey)
        .filter(APIKey.user_id == current_user.id, APIKey.is_deleted == False)
        .order_by(APIKey.created_at.desc())
        .all()
    )

    return api_keys


@router.post("/me/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyRequest,
    current_user: AuthUser = Depends(JWTBearer()),
    db: Session = Depends(get_db_session),
):
    """创建API Key"""

    # 检查用户是否有权限创建API Key
    if Permissions.API_KEYS_WRITE not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="没有权限创建API Key"
        )

    # 检查是否超过限制
    existing_count = (
        db.query(APIKey)
        .filter(
            APIKey.user_id == current_user.id,
            APIKey.is_deleted == False,
            APIKey.status == "active",
        )
        .count()
    )

    if existing_count >= 10:  # 每个用户最多10个API Key
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="API Key数量已达上限"
        )

    # 创建API Key
    api_key = APIKey(
        name=request.name,
        user_id=current_user.id,
        scopes=request.scopes,
        allowed_ips=request.allowed_ips,
        rate_limit_per_minute=request.rate_limit_per_minute,
        rate_limit_per_day=request.rate_limit_per_day,
    )

    if request.expires_in_days:
        from datetime import timedelta

        api_key.expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)

    # 生成Key
    key = api_key.generate_key()

    db.add(api_key)
    db.commit()

    return APIKeyResponse(
        key_id=api_key.key_id,
        name=api_key.name,
        key=key,  # 只在创建时返回
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        rate_limit_per_minute=api_key.rate_limit_per_minute,
        rate_limit_per_day=api_key.rate_limit_per_day,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.delete("/me/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: AuthUser = Depends(JWTBearer()),
    db: Session = Depends(get_db_session),
):
    """撤销API Key"""

    api_key = (
        db.query(APIKey)
        .filter(
            APIKey.key_id == key_id,
            APIKey.user_id == current_user.id,
            APIKey.is_deleted == False,
        )
        .first()
    )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API Key不存在"
        )

    api_key.revoke()
    db.commit()

    return {"message": "API Key已撤销"}


@router.get("/{user_id}/roles")
async def get_user_roles(
    user_id: int,
    current_user: AuthUser = Depends(require_permission(Permissions.USERS_READ)),
    db: Session = Depends(get_db_session),
):
    """获取用户角色列表"""

    user = (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == current_user.tenant_id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    user_roles = (
        db.query(UserRole)
        .filter(UserRole.user_id == user_id, UserRole.is_active == True)
        .all()
    )

    roles = []
    for user_role in user_roles:
        if not user_role.is_expired():
            role = db.query(Role).filter(Role.id == user_role.role_id).first()
            if role:
                roles.append(
                    {
                        "id": role.id,
                        "name": role.name,
                        "display_name": role.display_name,
                        "granted_at": user_role.granted_at,
                        "expires_at": user_role.expires_at,
                    }
                )

    return roles
