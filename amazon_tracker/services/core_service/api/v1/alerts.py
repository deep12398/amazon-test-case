"""价格提醒系统API端点"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from sqlalchemy import desc
from sqlalchemy.orm import Session

from amazon_tracker.common.auth.jwt_auth import get_current_user
from amazon_tracker.common.auth.permissions import PermissionScope, require_permission
from amazon_tracker.common.database.connection import get_db_session
from amazon_tracker.common.database.models.product import (
    Product,
    ProductAlert,
)

from .schemas import AlertCreateRequest, AlertResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])
security = HTTPBearer()


@router.post("/", response_model=AlertResponse)
async def create_alert(
    request: AlertCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """创建价格提醒"""

    # 权限检查
    require_permission(current_user, PermissionScope.ALERT_CREATE)

    # 验证产品存在且属于当前租户
    product = (
        db.query(Product)
        .filter(
            Product.id == request.product_id,
            Product.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 验证提醒配置
    if (
        request.alert_type in ["price_drop", "price_target"]
        and not request.target_value
    ):
        raise HTTPException(
            status_code=400, detail="target_value is required for price alerts"
        )

    if request.alert_type == "rank_change" and not request.threshold_percentage:
        raise HTTPException(
            status_code=400,
            detail="threshold_percentage is required for rank change alerts",
        )

    # 检查是否已存在相同类型的提醒
    existing_alert = (
        db.query(ProductAlert)
        .filter(
            ProductAlert.product_id == request.product_id,
            ProductAlert.alert_type == request.alert_type,
            ProductAlert.is_active == True,
            ProductAlert.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if existing_alert:
        raise HTTPException(
            status_code=409,
            detail=f"Active alert of type '{request.alert_type}' already exists for this product",
        )

    # 创建提醒
    alert = ProductAlert(
        product_id=request.product_id,
        alert_type=request.alert_type,
        target_value=request.target_value,
        threshold_percentage=request.threshold_percentage,
        current_value=_get_current_value(product, request.alert_type),
        is_active=request.is_active,
        notification_methods=request.notification_methods,
        tenant_id=current_user["tenant_id"],
        created_by=current_user["user_id"],
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return AlertResponse.from_orm(alert)


@router.get("/", response_model=list[AlertResponse])
async def list_alerts(
    product_id: Optional[int] = Query(None),
    alert_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取价格提醒列表"""

    # 权限检查
    require_permission(current_user, PermissionScope.ALERT_READ)

    # 构建查询
    query = db.query(ProductAlert).filter(
        ProductAlert.tenant_id == current_user["tenant_id"],
        ProductAlert.is_deleted == False,
    )

    if product_id:
        query = query.filter(ProductAlert.product_id == product_id)

    if alert_type:
        query = query.filter(ProductAlert.alert_type == alert_type)

    if is_active is not None:
        query = query.filter(ProductAlert.is_active == is_active)

    alerts = (
        query.order_by(desc(ProductAlert.created_at)).offset(offset).limit(limit).all()
    )

    return [AlertResponse.from_orm(alert) for alert in alerts]


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取价格提醒详情"""

    # 权限检查
    require_permission(current_user, PermissionScope.ALERT_READ)

    alert = (
        db.query(ProductAlert)
        .filter(
            ProductAlert.id == alert_id,
            ProductAlert.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return AlertResponse.from_orm(alert)


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    request: AlertCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """更新价格提醒"""

    # 权限检查
    require_permission(current_user, PermissionScope.ALERT_UPDATE)

    alert = (
        db.query(ProductAlert)
        .filter(
            ProductAlert.id == alert_id,
            ProductAlert.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # 更新字段
    alert.alert_type = request.alert_type
    alert.target_value = request.target_value
    alert.threshold_percentage = request.threshold_percentage
    alert.is_active = request.is_active
    alert.notification_methods = request.notification_methods
    alert.updated_at = datetime.utcnow()

    # 更新当前值
    product = db.query(Product).filter(Product.id == alert.product_id).first()
    if product:
        alert.current_value = _get_current_value(product, request.alert_type)

    db.commit()
    db.refresh(alert)

    return AlertResponse.from_orm(alert)


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """删除价格提醒"""

    # 权限检查
    require_permission(current_user, PermissionScope.ALERT_DELETE)

    alert = (
        db.query(ProductAlert)
        .filter(
            ProductAlert.id == alert_id,
            ProductAlert.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # 软删除
    alert.is_deleted = True
    alert.is_active = False
    alert.updated_at = datetime.utcnow()

    db.commit()

    return {"message": "Alert deleted successfully"}


@router.post("/{alert_id}/toggle")
async def toggle_alert(
    alert_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """切换价格提醒状态"""

    # 权限检查
    require_permission(current_user, PermissionScope.ALERT_UPDATE)

    alert = (
        db.query(ProductAlert)
        .filter(
            ProductAlert.id == alert_id,
            ProductAlert.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_active = not alert.is_active
    alert.updated_at = datetime.utcnow()

    db.commit()

    return {
        "message": f"Alert {'activated' if alert.is_active else 'deactivated'} successfully",
        "is_active": alert.is_active,
    }


@router.post("/check-triggers")
async def check_alert_triggers(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """手动检查提醒触发条件"""

    # 权限检查
    require_permission(current_user, PermissionScope.ALERT_MANAGE)

    # 获取活跃提醒
    alerts = (
        db.query(ProductAlert)
        .join(Product)
        .filter(
            ProductAlert.tenant_id == current_user["tenant_id"],
            ProductAlert.is_active == True,
            ProductAlert.is_deleted == False,
            Product.is_deleted == False,
        )
        .all()
    )

    triggered_alerts = []

    for alert in alerts:
        product = alert.product

        # 检查触发条件
        is_triggered = False
        trigger_message = ""

        if alert.alert_type == "price_drop":
            if product.current_price and alert.target_value:
                if product.current_price <= alert.target_value:
                    is_triggered = True
                    trigger_message = f"Price dropped to ${product.current_price} (target: ${alert.target_value})"

        elif alert.alert_type == "price_target":
            if product.current_price and alert.target_value:
                if product.current_price >= alert.target_value:
                    is_triggered = True
                    trigger_message = f"Price reached target ${product.current_price} (target: ${alert.target_value})"

        elif alert.alert_type == "rank_change":
            if (
                alert.threshold_percentage
                and alert.current_value
                and product.current_rank
            ):
                change_percent = abs(
                    (product.current_rank - alert.current_value)
                    / alert.current_value
                    * 100
                )
                if change_percent >= alert.threshold_percentage:
                    is_triggered = True
                    direction = (
                        "improved"
                        if product.current_rank < alert.current_value
                        else "declined"
                    )
                    trigger_message = f"Rank {direction} by {change_percent:.1f}% (from {alert.current_value} to {product.current_rank})"

        elif alert.alert_type == "stock_alert":
            if product.availability:
                if (
                    "out of stock" in product.availability.lower()
                    or "unavailable" in product.availability.lower()
                ):
                    is_triggered = True
                    trigger_message = (
                        f"Product is now out of stock: {product.availability}"
                    )

        if is_triggered:
            # 更新提醒记录
            alert.last_triggered_at = datetime.utcnow()
            alert.trigger_count += 1
            alert.current_value = _get_current_value(product, alert.alert_type)

            triggered_alerts.append(
                {
                    "alert_id": alert.id,
                    "product_id": product.id,
                    "asin": product.asin,
                    "title": product.title,
                    "alert_type": alert.alert_type,
                    "message": trigger_message,
                }
            )

            # 发送通知（后台任务）
            background_tasks.add_task(
                _send_alert_notification, alert, product, trigger_message, current_user
            )

    db.commit()

    return {
        "checked_alerts": len(alerts),
        "triggered_alerts": len(triggered_alerts),
        "triggers": triggered_alerts,
    }


@router.get("/stats/summary")
async def get_alert_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取提醒统计信息"""

    # 权限检查
    require_permission(current_user, PermissionScope.ALERT_READ)

    # 基础统计
    total_alerts = (
        db.query(ProductAlert)
        .filter(
            ProductAlert.tenant_id == current_user["tenant_id"],
            ProductAlert.is_deleted == False,
        )
        .count()
    )

    active_alerts = (
        db.query(ProductAlert)
        .filter(
            ProductAlert.tenant_id == current_user["tenant_id"],
            ProductAlert.is_deleted == False,
            ProductAlert.is_active == True,
        )
        .count()
    )

    # 最近24小时触发的提醒
    recent_threshold = datetime.utcnow() - timedelta(hours=24)
    recent_triggers = (
        db.query(ProductAlert)
        .filter(
            ProductAlert.tenant_id == current_user["tenant_id"],
            ProductAlert.is_deleted == False,
            ProductAlert.last_triggered_at >= recent_threshold,
        )
        .count()
    )

    # 按类型统计
    alert_types = (
        db.query(ProductAlert.alert_type, db.func.count(ProductAlert.id))
        .filter(
            ProductAlert.tenant_id == current_user["tenant_id"],
            ProductAlert.is_deleted == False,
        )
        .group_by(ProductAlert.alert_type)
        .all()
    )

    by_type = {alert_type: count for alert_type, count in alert_types}

    return {
        "total_alerts": total_alerts,
        "active_alerts": active_alerts,
        "inactive_alerts": total_alerts - active_alerts,
        "recent_triggers_24h": recent_triggers,
        "by_type": by_type,
        "last_updated": datetime.utcnow(),
    }


def _get_current_value(product: Product, alert_type: str) -> Optional[float]:
    """获取当前值用于提醒比较"""
    if alert_type in ["price_drop", "price_target"]:
        return product.current_price
    elif alert_type == "rank_change":
        return float(product.current_rank) if product.current_rank else None
    return None


async def _send_alert_notification(
    alert: ProductAlert, product: Product, message: str, user: dict
):
    """发送提醒通知（后台任务）"""
    try:
        # 这里可以集成各种通知方式

        if "email" in alert.notification_methods:
            # 发送邮件通知
            await _send_email_notification(alert, product, message, user)

        if "webhook" in alert.notification_methods:
            # 发送Webhook通知
            await _send_webhook_notification(alert, product, message, user)

        if "in_app" in alert.notification_methods:
            # 创建应用内通知
            await _create_in_app_notification(alert, product, message, user)

    except Exception as e:
        # 记录通知发送失败
        print(f"Failed to send notification for alert {alert.id}: {e}")


async def _send_email_notification(
    alert: ProductAlert, product: Product, message: str, user: dict
):
    """发送邮件通知"""
    # TODO: 集成邮件服务
    print(f"Email notification: {message}")


async def _send_webhook_notification(
    alert: ProductAlert, product: Product, message: str, user: dict
):
    """发送Webhook通知"""
    # TODO: 集成Webhook服务
    print(f"Webhook notification: {message}")


async def _create_in_app_notification(
    alert: ProductAlert, product: Product, message: str, user: dict
):
    """创建应用内通知"""
    # TODO: 创建应用内通知记录
    print(f"In-app notification: {message}")