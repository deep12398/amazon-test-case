#!/usr/bin/env python3
"""简单的数据库连接测试"""

import asyncio

from sqlalchemy.ext.asyncio import create_async_engine


async def test_connection():
    """测试数据库连接"""
    # 从环境变量或直接配置数据库URL
    DATABASE_URL = "postgresql+asyncpg://postgres:your-password@db.your-project.supabase.co:5432/postgres"

    print("🔍 测试数据库连接...")
    print("数据库: Supabase PostgreSQL")

    try:
        # 创建异步引擎
        engine = create_async_engine(
            DATABASE_URL, echo=False, pool_size=1, max_overflow=0, pool_timeout=10
        )

        # 测试连接
        async with engine.begin() as conn:
            # 检查PostgreSQL版本
            from sqlalchemy import text

            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print("✅ 数据库连接成功!")
            print(f"PostgreSQL版本: {version}")

            # 检查现有表
            result = await conn.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """
                )
            )
            tables = result.fetchall()

            if tables:
                print(f"\n📋 现有表 ({len(tables)}个):")
                for table in tables:
                    print(f"  - {table[0]}")
            else:
                print("\n📋 数据库中暂无表 (这是正常的，准备创建新表)")

            # 检查是否有alembic版本表
            result = await conn.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'alembic_version'
            """
                )
            )
            has_alembic = result.fetchone()

            if has_alembic:
                print("\n🔧 发现Alembic版本表，检查迁移状态...")
                result = await conn.execute(
                    text("SELECT version_num FROM alembic_version")
                )
                version_num = result.scalar()
                if version_num:
                    print(f"  当前迁移版本: {version_num}")
                else:
                    print("  未找到迁移版本")
            else:
                print("\n🔧 未发现Alembic版本表，数据库未初始化")

        await engine.dispose()
        return True

    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    if success:
        print("\n🎉 数据库连接测试成功! 可以继续进行数据库迁移。")
    else:
        print("\n💥 数据库连接测试失败，请检查网络和配置。")
    exit(0 if success else 1)
