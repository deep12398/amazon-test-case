"""租户管理API路由"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from amazon_tracker.common.auth.jwt_auth import JWTBearer
from amazon_tracker.common.auth.models import AuthUser, TenantInfo
from amazon_tracker.common.auth.permissions import (
    Permissions,
    require_permission,
    require_super_admin,
)
from amazon_tracker.common.database.base import get_db_session
from amazon_tracker.common.database.models import (
    SubscriptionPlan,
    SubscriptionStatus,
    Tenant,
    User,
)

router = APIRouter()


@router.get("/me", response_model=TenantInfo)
async def get_current_tenant(
    current_user: AuthUser = Depends(JWTBearer()), db: Session = Depends(get_db_session)
):
    """获取当前租户信息"""

    tenant = db.query(Tenant).filter(Tenant.tenant_id == current_user.tenant_id).first()

    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在")

    return TenantInfo(
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


@router.put("/me")
async def update_current_tenant(
    updates: dict,
    current_user: AuthUser = Depends(require_permission(Permissions.TENANT_WRITE)),
    db: Session = Depends(get_db_session),
):
    """更新当前租户信息"""

    tenant = db.query(Tenant).filter(Tenant.tenant_id == current_user.tenant_id).first()

    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在")

    # 允许更新的字段
    allowed_fields = {"name", "domain", "timezone", "settings"}

    for field, value in updates.items():
        if field in allowed_fields:
            setattr(tenant, field, value)

    db.commit()

    return {"message": "租户信息更新成功"}


@router.get("/me/usage")
async def get_tenant_usage(
    current_user: AuthUser = Depends(require_permission(Permissions.TENANT_READ)),
    db: Session = Depends(get_db_session),
):
    """获取租户使用情况统计"""

    tenant = db.query(Tenant).filter(Tenant.tenant_id == current_user.tenant_id).first()

    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在")

    # 用户数量统计
    user_count = (
        db.query(User)
        .filter(User.tenant_id == current_user.tenant_id, User.is_deleted == False)
        .count()
    )

    active_user_count = (
        db.query(User)
        .filter(
            User.tenant_id == current_user.tenant_id,
            User.is_deleted == False,
            User.status == "active",
        )
        .count()
    )

    # TODO: 添加产品数量、API调用次数等统计

    return {
        "tenant_info": {
            "name": tenant.name,
            "subscription_plan": tenant.subscription_plan.value,
            "subscription_status": tenant.subscription_status.value,
            "trial_ends_at": tenant.trial_ends_at,
            "subscription_ends_at": tenant.subscription_ends_at,
        },
        "limits": {
            "max_users": tenant.max_users,
            "max_products": tenant.max_products,
            "max_api_calls_per_day": tenant.max_api_calls_per_day,
        },
        "current_usage": {
            "user_count": user_count,
            "active_user_count": active_user_count,
            "product_count": 0,  # TODO: 从产品服务获取
            "api_calls_today": 0,  # TODO: 从监控系统获取
        },
        "usage_percentage": {
            "users": (user_count / tenant.max_users) * 100
            if tenant.max_users > 0
            else 0,
            "products": 0,  # TODO: 计算
            "api_calls": 0,  # TODO: 计算
        },
        "is_trial_active": tenant.is_trial_active,
    }


@router.post("/me/upgrade")
async def upgrade_subscription(
    plan: SubscriptionPlan,
    current_user: AuthUser = Depends(require_permission(Permissions.TENANT_ADMIN)),
    db: Session = Depends(get_db_session),
):
    """升级订阅计划"""

    tenant = db.query(Tenant).filter(Tenant.tenant_id == current_user.tenant_id).first()

    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在")

    # 检查升级逻辑
    plan_hierarchy = {
        SubscriptionPlan.FREE_TRIAL: 0,
        SubscriptionPlan.BASIC: 1,
        SubscriptionPlan.PROFESSIONAL: 2,
        SubscriptionPlan.ENTERPRISE: 3,
    }

    current_level = plan_hierarchy.get(tenant.subscription_plan, 0)
    target_level = plan_hierarchy.get(plan, 0)

    if target_level <= current_level:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="只能升级到更高级的计划"
        )

    # 更新订阅计划
    tenant.subscription_plan = plan
    tenant.subscription_status = SubscriptionStatus.ACTIVE

    # 根据计划设置限制
    plan_limits = {
        SubscriptionPlan.BASIC: {
            "max_users": 20,
            "max_products": 500,
            "max_api_calls_per_day": 50000,
        },
        SubscriptionPlan.PROFESSIONAL: {
            "max_users": 100,
            "max_products": 2000,
            "max_api_calls_per_day": 200000,
        },
        SubscriptionPlan.ENTERPRISE: {
            "max_users": 1000,
            "max_products": 10000,
            "max_api_calls_per_day": 1000000,
        },
    }

    limits = plan_limits.get(plan, {})
    for key, value in limits.items():
        setattr(tenant, key, value)

    # TODO: 集成支付系统处理订阅费用

    db.commit()

    return {"message": f"订阅已升级到 {plan.value}", "new_limits": limits}


# ===== 超级管理员功能 =====


@router.get("/", response_model=list[dict])
async def list_all_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    plan_filter: Optional[SubscriptionPlan] = Query(None),
    status_filter: Optional[SubscriptionStatus] = Query(None),
    current_user: AuthUser = Depends(require_super_admin()),
    db: Session = Depends(get_db_session),
):
    """获取所有租户列表（超级管理员）"""

    query = db.query(Tenant).filter(Tenant.is_deleted == False)

    # 搜索过滤
    if search:
        search_term = f"%{search}%"
        query = query.filter(Tenant.name.ilike(search_term))

    # 计划过滤
    if plan_filter:
        query = query.filter(Tenant.subscription_plan == plan_filter)

    # 状态过滤
    if status_filter:
        query = query.filter(Tenant.subscription_status == status_filter)

    total = query.count()
    tenants = query.offset(skip).limit(limit).all()

    result = []
    for tenant in tenants:
        # 统计租户用户数
        user_count = (
            db.query(User)
            .filter(User.tenant_id == tenant.tenant_id, User.is_deleted == False)
            .count()
        )

        tenant_data = {
            "id": tenant.id,
            "tenant_id": tenant.tenant_id,
            "name": tenant.name,
            "domain": tenant.domain,
            "subscription_plan": tenant.subscription_plan.value,
            "subscription_status": tenant.subscription_status.value,
            "user_count": user_count,
            "max_users": tenant.max_users,
            "trial_ends_at": tenant.trial_ends_at,
            "created_at": tenant.created_at,
        }
        result.append(tenant_data)

    return {"tenants": result, "total": total, "skip": skip, "limit": limit}


@router.get("/{tenant_id}")
async def get_tenant_details(
    tenant_id: str,
    current_user: AuthUser = Depends(require_super_admin()),
    db: Session = Depends(get_db_session),
):
    """获取租户详细信息（超级管理员）"""

    tenant = (
        db.query(Tenant)
        .filter(Tenant.tenant_id == tenant_id, Tenant.is_deleted == False)
        .first()
    )

    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在")

    # 获取租户统计信息
    total_users = (
        db.query(User)
        .filter(User.tenant_id == tenant_id, User.is_deleted == False)
        .count()
    )

    active_users = (
        db.query(User)
        .filter(
            User.tenant_id == tenant_id,
            User.is_deleted == False,
            User.status == "active",
        )
        .count()
    )

    return {
        "tenant": {
            "id": tenant.id,
            "tenant_id": tenant.tenant_id,
            "name": tenant.name,
            "domain": tenant.domain,
            "subscription_plan": tenant.subscription_plan.value,
            "subscription_status": tenant.subscription_status.value,
            "trial_ends_at": tenant.trial_ends_at,
            "subscription_ends_at": tenant.subscription_ends_at,
            "max_users": tenant.max_users,
            "max_products": tenant.max_products,
            "max_api_calls_per_day": tenant.max_api_calls_per_day,
            "timezone": tenant.timezone,
            "settings": tenant.settings,
            "created_at": tenant.created_at,
            "updated_at": tenant.updated_at,
        },
        "statistics": {
            "total_users": total_users,
            "active_users": active_users,
            "user_utilization": (total_users / tenant.max_users) * 100
            if tenant.max_users > 0
            else 0,
        },
    }


@router.put("/{tenant_id}/subscription")
async def update_tenant_subscription(
    tenant_id: str,
    updates: dict,
    current_user: AuthUser = Depends(require_super_admin()),
    db: Session = Depends(get_db_session),
):
    """更新租户订阅信息（超级管理员）"""

    tenant = (
        db.query(Tenant)
        .filter(Tenant.tenant_id == tenant_id, Tenant.is_deleted == False)
        .first()
    )

    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在")

    # 允许更新的订阅字段
    allowed_fields = {
        "subscription_plan",
        "subscription_status",
        "subscription_ends_at",
        "max_users",
        "max_products",
        "max_api_calls_per_day",
    }

    for field, value in updates.items():
        if field in allowed_fields:
            if field == "subscription_plan" and isinstance(value, str):
                value = SubscriptionPlan(value)
            elif field == "subscription_status" and isinstance(value, str):
                value = SubscriptionStatus(value)

            setattr(tenant, field, value)

    db.commit()

    return {"message": "租户订阅信息更新成功"}
