"""爬虫调度管理API端点"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from sqlalchemy import desc
from sqlalchemy.orm import Session

from amazon_tracker.common.auth.jwt_auth import get_current_user
from amazon_tracker.common.auth.permissions import PermissionScope, require_permission
from amazon_tracker.common.database.connection import get_db_session
from amazon_tracker.common.database.models.crawl import CrawlerType, CrawlSchedule

from .schemas import CreateScheduleRequest, ScheduleResponse, UpdateScheduleRequest

router = APIRouter(prefix="/schedules", tags=["schedules"])
security = HTTPBearer()


@router.get("/", response_model=list[ScheduleResponse])
async def list_schedules(
    is_active: Optional[bool] = None,
    crawler_type: Optional[CrawlerType] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取调度列表"""

    # 权限检查
    require_permission(current_user, PermissionScope.SCHEDULER_READ)

    # 构建查询
    query = db.query(CrawlSchedule).filter(
        CrawlSchedule.tenant_id == current_user["tenant_id"]
    )

    if is_active is not None:
        query = query.filter(CrawlSchedule.is_active == is_active)

    if crawler_type:
        query = query.filter(CrawlSchedule.crawler_type == crawler_type)

    schedules = (
        query.order_by(desc(CrawlSchedule.created_at)).offset(offset).limit(limit).all()
    )

    return [ScheduleResponse.from_orm(schedule) for schedule in schedules]


@router.post("/", response_model=ScheduleResponse)
async def create_schedule(
    request: CreateScheduleRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """创建新的爬虫调度"""

    # 权限检查
    require_permission(current_user, PermissionScope.SCHEDULER_CREATE)

    # 检查名称是否重复
    existing_schedule = (
        db.query(CrawlSchedule)
        .filter(
            CrawlSchedule.name == request.name,
            CrawlSchedule.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if existing_schedule:
        raise HTTPException(
            status_code=409,
            detail=f"Schedule with name '{request.name}' already exists",
        )

    # 创建调度
    schedule = CrawlSchedule(
        name=request.name,
        description=request.description,
        cron_expression=request.cron_expression,
        timezone=request.timezone,
        crawler_type=request.crawler_type,
        task_template=request.task_template,
        product_filters=request.product_filters,
        tenant_id=current_user["tenant_id"],
        created_by=current_user["user_id"],
    )

    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    return ScheduleResponse.from_orm(schedule)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取调度详情"""

    # 权限检查
    require_permission(current_user, PermissionScope.SCHEDULER_READ)

    try:
        schedule_uuid = uuid.UUID(schedule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid schedule ID format")

    schedule = (
        db.query(CrawlSchedule)
        .filter(
            CrawlSchedule.schedule_id == schedule_uuid,
            CrawlSchedule.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return ScheduleResponse.from_orm(schedule)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    request: UpdateScheduleRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """更新调度配置"""

    # 权限检查
    require_permission(current_user, PermissionScope.SCHEDULER_UPDATE)

    try:
        schedule_uuid = uuid.UUID(schedule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid schedule ID format")

    schedule = (
        db.query(CrawlSchedule)
        .filter(
            CrawlSchedule.schedule_id == schedule_uuid,
            CrawlSchedule.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # 检查名称是否重复（如果要更新名称）
    if request.name and request.name != schedule.name:
        existing_schedule = (
            db.query(CrawlSchedule)
            .filter(
                CrawlSchedule.name == request.name,
                CrawlSchedule.tenant_id == current_user["tenant_id"],
            )
            .first()
        )

        if existing_schedule:
            raise HTTPException(
                status_code=409,
                detail=f"Schedule with name '{request.name}' already exists",
            )

    # 更新字段
    update_data = request.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(schedule, field, value)

    db.commit()
    db.refresh(schedule)

    return ScheduleResponse.from_orm(schedule)


@router.post("/{schedule_id}/enable")
async def enable_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """启用调度"""

    # 权限检查
    require_permission(current_user, PermissionScope.SCHEDULER_UPDATE)

    try:
        schedule_uuid = uuid.UUID(schedule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid schedule ID format")

    schedule = (
        db.query(CrawlSchedule)
        .filter(
            CrawlSchedule.schedule_id == schedule_uuid,
            CrawlSchedule.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule.is_active = True
    schedule.consecutive_failures = 0  # 重置失败计数
    db.commit()

    return {"message": "Schedule enabled successfully"}


@router.post("/{schedule_id}/disable")
async def disable_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """禁用调度"""

    # 权限检查
    require_permission(current_user, PermissionScope.SCHEDULER_UPDATE)

    try:
        schedule_uuid = uuid.UUID(schedule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid schedule ID format")

    schedule = (
        db.query(CrawlSchedule)
        .filter(
            CrawlSchedule.schedule_id == schedule_uuid,
            CrawlSchedule.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule.is_active = False
    db.commit()

    return {"message": "Schedule disabled successfully"}


@router.post("/{schedule_id}/run-now")
async def run_schedule_now(
    schedule_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """立即执行调度"""

    # 权限检查
    require_permission(current_user, PermissionScope.SCHEDULER_EXECUTE)

    try:
        schedule_uuid = uuid.UUID(schedule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid schedule ID format")

    schedule = (
        db.query(CrawlSchedule)
        .filter(
            CrawlSchedule.schedule_id == schedule_uuid,
            CrawlSchedule.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # TODO: 实现立即执行调度的逻辑
    # 这里需要根据调度配置创建相应的爬虫任务

    return {"message": "Schedule execution triggered"}


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """删除调度"""

    # 权限检查
    require_permission(current_user, PermissionScope.SCHEDULER_DELETE)

    try:
        schedule_uuid = uuid.UUID(schedule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid schedule ID format")

    schedule = (
        db.query(CrawlSchedule)
        .filter(
            CrawlSchedule.schedule_id == schedule_uuid,
            CrawlSchedule.tenant_id == current_user["tenant_id"],
        )
        .first()
    )

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # 软删除
    schedule.is_deleted = True
    schedule.is_active = False
    db.commit()

    return {"message": "Schedule deleted successfully"}
