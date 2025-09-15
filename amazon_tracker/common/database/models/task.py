"""任务管理模型"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, relationship

from amazon_tracker.common.database.base import Base

if TYPE_CHECKING:
    from .tenant import Tenant
    from .user import User


class Task(Base):
    """任务表

    存储系统中的各类异步任务信息
    """

    __tablename__ = "tasks"

    task_id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="任务ID"
    )

    tenant_id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属租户ID",
    )

    user_id: Mapped[Optional[uuid.UUID]] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="创建用户ID",
    )

    task_type: Mapped[str] = Column(
        String(50), nullable=False, comment="任务类型: crawl, analysis, suggestion"
    )

    task_name: Mapped[str] = Column(String(255), nullable=False, comment="任务名称")

    parameters: Mapped[Optional[dict[str, Any]]] = Column(
        JSONB, nullable=True, comment="任务参数"
    )

    status: Mapped[str] = Column(
        String(50),
        nullable=False,
        default="pending",
        comment="状态: pending, running, completed, failed",
    )

    priority: Mapped[int] = Column(
        Integer, nullable=False, default=3, comment="优先级 1=最高, 5=最低"
    )

    progress: Mapped[int] = Column(
        Integer, nullable=False, default=0, comment="进度百分比 0-100"
    )

    error_message: Mapped[Optional[str]] = Column(
        Text, nullable=True, comment="错误信息"
    )

    result: Mapped[Optional[dict[str, Any]]] = Column(
        JSONB, nullable=True, comment="任务结果"
    )

    started_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), nullable=True, comment="开始时间"
    )

    completed_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), nullable=True, comment="完成时间"
    )

    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="创建时间",
    )

    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )

    # 关系定义
    tenant: Mapped["Tenant"] = relationship("Tenant")
    user: Mapped[Optional["User"]] = relationship("User")

    # 索引定义
    __table_args__ = (
        Index("idx_tasks_tenant_created", "tenant_id", "created_at"),
        Index("idx_tasks_status_priority", "status", "priority"),
        Index("idx_tasks_task_type", "task_type"),
        Index("idx_tasks_user_id", "user_id"),
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_priority", "priority"),
        Index("idx_tasks_created_at", "created_at"),
        Index("idx_tasks_started_at", "started_at"),
        Index("idx_tasks_completed_at", "completed_at"),
        # GIN索引用于JSONB查询
        Index("gin_tasks_parameters", "parameters", postgresql_using="gin"),
        Index("gin_tasks_result", "result", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return (
            f"<Task(id={self.task_id}, type='{self.task_type}', "
            f"status='{self.status}', priority={self.priority})>"
        )
