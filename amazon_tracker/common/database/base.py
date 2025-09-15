"""数据库基类和连接管理"""

import os
from pathlib import Path
from typing import Any

# 加载环境变量
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(project_root / ".env.local")
load_dotenv(project_root / ".env")

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    String,
    create_engine,
    event,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.sql import func

# 创建数据库引擎配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://dev_user:dev_password@localhost:5432/amazon_tracker_dev",
)

# 转换为同步URL（移除asyncpg驱动）
SYNC_DATABASE_URL = (
    DATABASE_URL.replace("+asyncpg", "") if "+asyncpg" in DATABASE_URL else DATABASE_URL
)

# 数据库引擎配置（同步版本）
engine = create_engine(
    SYNC_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    echo=False,  # 生产环境设置为False
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基类
Base = declarative_base()

# 元数据
metadata = Base.metadata


class BaseModel(Base):
    """所有数据表的基类"""

    __abstract__ = True

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"


class TenantMixin:
    """多租户支持Mixin"""

    tenant_id = Column(String(64), nullable=False, index=True)

    @classmethod
    def get_tenant_query(cls, session: Session, tenant_id: str):
        """获取指定租户的查询"""
        return session.query(cls).filter(
            cls.tenant_id == tenant_id, cls.is_deleted == False
        )


def get_db_session() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)


def close_db():
    """关闭数据库连接"""
    engine.dispose()


# 设置会话级别的应用变量（用于审计日志）
@event.listens_for(SessionLocal, "after_begin")
def receive_after_begin(session, transaction, connection):
    """会话开始后设置应用变量"""
    # 这些变量将在triggers中使用
    from sqlalchemy import text

    connection.execute(text("SET LOCAL app.current_user_id = ''"))
    connection.execute(text("SET LOCAL app.current_tenant_id = ''"))


def set_session_context(session: Session, user_id: str = "", tenant_id: str = ""):
    """设置会话上下文（用于审计日志）"""
    from sqlalchemy import text

    session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))
    session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
