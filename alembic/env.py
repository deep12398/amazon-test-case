import os
import sys
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from alembic import context

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# 加载环境变量 - 优先加载.env.local
project_root = os.path.join(os.path.dirname(__file__), "..")
load_dotenv(os.path.join(project_root, ".env.local"))
load_dotenv(os.path.join(project_root, ".env"))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 设置数据库URL，优先使用环境变量，并转换为同步驱动
database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise ValueError("DATABASE_URL environment variable is not set")

# 转换异步URL为同步URL
if "postgresql+asyncpg://" in database_url:
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    print(f"Converted to sync database URL for Alembic: {database_url[:50]}...")

config.set_main_option("sqlalchemy.url", database_url)

# 导入所有模型以确保它们被注册到Base.metadata中
try:
    from amazon_tracker.common.database.base import Base

    # 导入所有模型
    from amazon_tracker.common.database.models import *  # noqa: F401,F403
except Exception as e:
    print(f"Warning: Could not import models: {e}")
    # 如果无法连接数据库，使用基础Base类
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using synchronous engine."""

    # 创建同步引擎
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
