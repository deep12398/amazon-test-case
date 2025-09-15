"""数据库连接管理"""

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..config.settings import get_settings

logger = logging.getLogger(__name__)

# 全局引擎和会话工厂
_engine = None
_SessionLocal = None


def init_db():
    """初始化数据库连接"""
    global _engine, _SessionLocal

    settings = get_settings()

    try:
        # 转换为同步数据库URL（移除asyncpg驱动）
        sync_db_url = (
            settings.DATABASE_URL.replace("+asyncpg", "")
            if "+asyncpg" in settings.DATABASE_URL
            else settings.DATABASE_URL
        )

        # 创建数据库引擎
        _engine = create_engine(
            sync_db_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=settings.DEBUG,
        )

        # 创建会话工厂
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

        logger.info("Database initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def close_db():
    """关闭数据库连接"""
    global _engine

    if _engine:
        _engine.dispose()
        logger.info("Database connections closed")


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """获取数据库会话上下文管理器"""
    if not _SessionLocal:
        init_db()

    session = _SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI依赖注入用的数据库会话生成器"""
    with get_db_session() as session:
        yield session
