"""爬虫任务相关数据模型"""

import enum
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
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

from ..base import BaseModel, TenantMixin


class TaskStatus(enum.Enum):
    """任务状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskPriority(enum.Enum):
    """任务优先级枚举"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class CrawlerType(enum.Enum):
    """爬虫类型枚举"""

    APIFY_AMAZON_SCRAPER = "apify_amazon_scraper"
    APIFY_AMAZON_REVIEWS = "apify_amazon_reviews"
    CUSTOM_SCRAPER = "custom_scraper"


class CrawlTask(BaseModel, TenantMixin):
    """爬虫任务表"""

    __tablename__ = "crawl_tasks"

    # 任务标识
    task_id = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True
    )

    # 关联产品
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)

    # 任务信息
    crawler_type = Column(SQLEnum(CrawlerType), nullable=False)
    task_name = Column(String(200), nullable=False)

    # 任务配置
    crawler_config = Column(JSONB, default=dict)  # 爬虫配置参数
    input_data = Column(JSONB, default=dict)  # 输入数据

    # 任务状态
    status = Column(
        SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True
    )
    priority = Column(
        SQLEnum(TaskPriority), default=TaskPriority.NORMAL, nullable=False
    )

    # 时间信息
    scheduled_at = Column(DateTime(timezone=True), nullable=True)  # 预定执行时间
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # 任务过期时间

    # 重试信息
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    retry_delay = Column(Integer, default=300, nullable=False)  # 重试延迟(秒)

    # 执行信息
    worker_name = Column(String(100), nullable=True)  # 执行的worker名称
    execution_time = Column(Integer, nullable=True)  # 执行时间(秒)

    # 结果和错误
    result_data = Column(JSONB, default=dict)  # 结果数据
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)

    # 外部服务信息
    external_task_id = Column(
        String(200), nullable=True, index=True
    )  # 外部任务ID (如Apify Run ID)
    external_status = Column(String(50), nullable=True)
    external_url = Column(Text, nullable=True)  # 外部任务URL

    # 数据统计
    items_processed = Column(Integer, default=0, nullable=False)
    items_failed = Column(Integer, default=0, nullable=False)
    data_size = Column(Integer, nullable=True)  # 数据大小(bytes)

    # 关系
    product = relationship("Product", back_populates="crawl_tasks")
    crawl_logs = relationship(
        "CrawlLog", back_populates="task", cascade="all, delete-orphan"
    )

    # 索引
    __table_args__ = (
        Index("ix_crawl_task_tenant_status", "tenant_id", "status"),
        Index("ix_crawl_task_scheduled_at", "scheduled_at"),
        Index("ix_crawl_task_priority_created", "priority", "created_at"),
        Index("ix_crawl_task_external_id", "external_task_id"),
    )

    def start_task(self, worker_name: str = None):
        """开始任务"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.worker_name = worker_name

    def complete_task(self, result_data: dict[str, Any], items_processed: int = 0):
        """完成任务"""
        self.status = TaskStatus.SUCCESS
        self.finished_at = datetime.utcnow()
        self.result_data = result_data
        self.items_processed = items_processed

        if self.started_at:
            self.execution_time = int(
                (self.finished_at - self.started_at).total_seconds()
            )

    def fail_task(self, error_message: str, traceback: str = None):
        """任务失败"""
        self.status = TaskStatus.FAILED
        self.finished_at = datetime.utcnow()
        self.error_message = error_message
        self.error_traceback = traceback

        if self.started_at:
            self.execution_time = int(
                (self.finished_at - self.started_at).total_seconds()
            )

    def should_retry(self) -> bool:
        """检查是否应该重试"""
        return self.status == TaskStatus.FAILED and self.retry_count < self.max_retries

    def schedule_retry(self):
        """调度重试"""
        if self.should_retry():
            self.retry_count += 1
            self.status = TaskStatus.RETRYING
            self.scheduled_at = datetime.utcnow() + timedelta(seconds=self.retry_delay)
            self.error_message = None
            self.error_traceback = None

    def cancel_task(self, reason: str = None):
        """取消任务"""
        self.status = TaskStatus.CANCELLED
        self.finished_at = datetime.utcnow()
        if reason:
            self.error_message = f"Cancelled: {reason}"

    @property
    def is_completed(self) -> bool:
        """检查任务是否已完成"""
        return self.status in [
            TaskStatus.SUCCESS,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.TIMEOUT,
        ]

    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.items_processed == 0:
            return 0.0
        return (self.items_processed - self.items_failed) / self.items_processed

    def __repr__(self):
        return f"<CrawlTask(task_id='{self.task_id}', product_id={self.product_id}, status='{self.status.value}')>"


class CrawlLog(BaseModel):
    """爬虫日志表"""

    __tablename__ = "crawl_logs"

    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("crawl_tasks.task_id"),
        nullable=False,
        index=True,
    )

    # 日志信息
    level = Column(String(20), nullable=False)  # DEBUG, INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    details = Column(JSONB, default=dict)  # 详细信息

    # 时间戳
    logged_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    # 关系
    task = relationship("CrawlTask", back_populates="crawl_logs")

    # 索引
    __table_args__ = (
        Index("ix_crawl_log_task_logged", "task_id", "logged_at"),
        Index("ix_crawl_log_level", "level"),
    )

    def __repr__(self):
        return f"<CrawlLog(task_id='{self.task_id}', level='{self.level}', logged_at={self.logged_at})>"


class CrawlSchedule(BaseModel, TenantMixin):
    """爬虫调度表"""

    __tablename__ = "crawl_schedules"

    # 调度标识
    schedule_id = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True
    )
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # 调度配置
    cron_expression = Column(String(100), nullable=False)  # Cron表达式
    timezone = Column(String(50), default="UTC", nullable=False)

    # 任务配置
    crawler_type = Column(SQLEnum(CrawlerType), nullable=False)
    task_template = Column(JSONB, default=dict)  # 任务模板

    # 过滤条件
    product_filters = Column(JSONB, default=dict)  # 产品过滤条件

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)

    # 执行统计
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    total_runs = Column(Integer, default=0, nullable=False)
    successful_runs = Column(Integer, default=0, nullable=False)
    failed_runs = Column(Integer, default=0, nullable=False)

    # 错误信息
    last_error = Column(Text, nullable=True)
    consecutive_failures = Column(Integer, default=0, nullable=False)

    # 索引
    __table_args__ = (
        Index("ix_schedule_tenant_active", "tenant_id", "is_active"),
        Index("ix_schedule_next_run", "next_run_at"),
    )

    def record_success(self):
        """记录成功执行"""
        self.last_run_at = datetime.utcnow()
        self.total_runs += 1
        self.successful_runs += 1
        self.consecutive_failures = 0
        self.last_error = None

    def record_failure(self, error_message: str):
        """记录执行失败"""
        self.last_run_at = datetime.utcnow()
        self.total_runs += 1
        self.failed_runs += 1
        self.consecutive_failures += 1
        self.last_error = error_message

        # 如果连续失败次数过多，暂停调度
        if self.consecutive_failures >= 5:
            self.is_active = False

    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.total_runs == 0:
            return 0.0
        return self.successful_runs / self.total_runs

    def __repr__(self):
        return f"<CrawlSchedule(schedule_id='{self.schedule_id}', name='{self.name}', is_active={self.is_active})>"


class CrawlStatistics(BaseModel):
    """爬虫统计表"""

    __tablename__ = "crawl_statistics"

    # 统计维度
    tenant_id = Column(String(64), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False)
    crawler_type = Column(SQLEnum(CrawlerType), nullable=False)

    # 任务统计
    total_tasks = Column(Integer, default=0, nullable=False)
    successful_tasks = Column(Integer, default=0, nullable=False)
    failed_tasks = Column(Integer, default=0, nullable=False)
    cancelled_tasks = Column(Integer, default=0, nullable=False)

    # 时间统计
    total_execution_time = Column(Integer, default=0, nullable=False)  # 总执行时间(秒)
    avg_execution_time = Column(Numeric(10, 2), nullable=True)  # 平均执行时间

    # 数据统计
    total_items_processed = Column(Integer, default=0, nullable=False)
    total_items_failed = Column(Integer, default=0, nullable=False)
    total_data_size = Column(BigInteger, default=0, nullable=False)  # 总数据大小(bytes)

    # 成本统计 (如果使用付费服务)
    total_cost = Column(Numeric(10, 4), nullable=True)

    # 索引和约束
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "date", "crawler_type", name="uq_crawl_stats_tenant_date_type"
        ),
        Index("ix_crawl_stats_tenant_date", "tenant_id", "date"),
    )

    def __repr__(self):
        return f"<CrawlStatistics(tenant_id='{self.tenant_id}', date={self.date}, crawler_type='{self.crawler_type.value}')>"
