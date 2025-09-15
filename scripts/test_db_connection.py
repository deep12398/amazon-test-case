#!/usr/bin/env python3
"""测试数据库连接"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine

from amazon_tracker.common.config.settings import get_settings


async def test_database_connection():
    """测试数据库连接"""
    settings = get_settings()
    print("🔍 测试数据库连接...")
    print(f"数据库URL: {settings.DATABASE_URL}")

    try:
        # 创建异步引擎
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_size=1,
            max_overflow=0,
            pool_timeout=10,
            pool_recycle=3600,
        )

        # 测试连接
        async with engine.begin() as conn:
            result = await conn.execute("SELECT version()")
            version = result.scalar()
            print("✅ 数据库连接成功!")
            print(f"PostgreSQL版本: {version}")

            # 检查现有表
            result = await conn.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """
            )
            tables = result.fetchall()

            if tables:
                print(f"\n📋 现有表 ({len(tables)}个):")
                for table in tables:
                    print(f"  - {table[0]}")
            else:
                print("\n📋 数据库中暂无表")

        await engine.dispose()
        return True

    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_database_connection())
    sys.exit(0 if success else 1)
