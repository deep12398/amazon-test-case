"""监控和健康检查API端点"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPBearer
from prometheus_client import generate_latest

from amazon_tracker.common.auth.jwt_auth import get_current_user
from amazon_tracker.common.auth.permissions import PermissionScope, require_permission
from amazon_tracker.common.monitoring.health_check import get_health_status
from amazon_tracker.common.monitoring.metrics import crawler_metrics

router = APIRouter(prefix="/monitoring", tags=["monitoring"])
security = HTTPBearer()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """健康检查端点（公开访问）"""
    try:
        health_status = await get_health_status()

        # 根据整体状态设置HTTP状态码
        status_code = 200
        if health_status["status"] == "degraded":
            status_code = 200  # 降级但仍可用
        elif health_status["status"] == "unhealthy":
            status_code = 503  # 服务不可用

        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e), "timestamp": None, "checks": {}}


@router.get("/metrics", response_class=PlainTextResponse)
async def get_metrics():
    """Prometheus指标端点（公开访问）"""
    try:
        return generate_latest()
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate metrics")


@router.get("/health/detailed")
async def detailed_health_check(current_user: dict = Depends(get_current_user)):
    """详细健康检查（需要认证）"""

    # 权限检查
    require_permission(current_user, PermissionScope.MONITORING_READ)

    try:
        health_status = await get_health_status()
        return health_status
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/crawler")
async def get_crawler_stats(current_user: dict = Depends(get_current_user)):
    """获取爬虫统计信息"""

    # 权限检查
    require_permission(current_user, PermissionScope.MONITORING_READ)

    try:
        # 这里可以添加实时统计信息的收集
        # 目前返回基本信息
        return {
            "message": "Crawler metrics are available at /monitoring/metrics endpoint",
            "metrics_endpoint": "/api/v1/monitoring/metrics",
            "available_metrics": [
                "crawler_tasks_total",
                "crawler_task_duration_seconds",
                "crawler_active_tasks",
                "crawler_items_processed_total",
                "crawler_items_failed_total",
                "crawler_queue_size",
                "crawler_last_success_timestamp",
                "crawler_price_changes_total",
                "crawler_rank_changes_total",
            ],
        }
    except Exception as e:
        logger.error(f"Failed to get crawler stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/tasks")
async def get_task_stats(current_user: dict = Depends(get_current_user)):
    """获取任务统计信息"""

    # 权限检查
    require_permission(current_user, PermissionScope.MONITORING_READ)

    try:
        return {
            "message": "Task metrics are available at /monitoring/metrics endpoint",
            "metrics_endpoint": "/api/v1/monitoring/metrics",
            "available_metrics": [
                "celery_tasks_total",
                "celery_task_duration_seconds",
                "celery_task_retries_total",
                "celery_active_workers",
                "celery_reserved_tasks",
                "scheduler_runs_total",
                "scheduler_tasks_scheduled_total",
            ],
        }
    except Exception as e:
        logger.error(f"Failed to get task stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metrics/record-event")
async def record_custom_event(
    event_type: str,
    tenant_id: str = None,
    asin: str = None,
    change_type: str = None,
    current_user: dict = Depends(get_current_user),
):
    """记录自定义事件到指标系统"""

    # 权限检查
    require_permission(current_user, PermissionScope.MONITORING_WRITE)

    try:
        tenant_id = tenant_id or current_user["tenant_id"]

        if event_type == "price_change" and asin and change_type:
            crawler_metrics.record_price_change(tenant_id, asin, change_type)
        elif event_type == "rank_change" and asin and change_type:
            crawler_metrics.record_rank_change(tenant_id, asin, change_type)
        elif event_type == "successful_crawl" and asin:
            crawler_metrics.record_successful_crawl(tenant_id, asin)
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid event type or missing required parameters",
            )

        return {"message": "Event recorded successfully"}

    except Exception as e:
        logger.error(f"Failed to record custom event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts(current_user: dict = Depends(get_current_user)):
    """获取监控告警信息"""

    # 权限检查
    require_permission(current_user, PermissionScope.MONITORING_READ)

    try:
        # 这里可以集成告警系统
        # 目前返回模拟数据
        return {
            "active_alerts": [],
            "alert_rules": [
                {
                    "name": "high_failure_rate",
                    "description": "Crawler failure rate > 20%",
                    "enabled": True,
                },
                {
                    "name": "queue_backlog",
                    "description": "Queue size > 1000 tasks",
                    "enabled": True,
                },
                {
                    "name": "long_running_tasks",
                    "description": "Tasks running > 2 hours",
                    "enabled": True,
                },
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
