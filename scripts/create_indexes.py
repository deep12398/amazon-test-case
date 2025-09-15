#!/usr/bin/env python3
"""创建数据库索引脚本"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def create_database_indexes():
    """创建数据库索引"""

    DATABASE_URL = "postgresql+asyncpg://postgres:your-password@db.your-project.supabase.co:5432/postgres"

    print("🏗️ 创建数据库索引...")

    # 创建引擎
    engine = create_async_engine(DATABASE_URL, echo=False)

    # 索引列表(不使用CONCURRENTLY，因为在事务中不支持)
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_tenants_subscription_status ON tenants (subscription_status);",
        "CREATE INDEX IF NOT EXISTS idx_tenants_created_at ON tenants (created_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_users_email_verified ON users (is_email_verified) WHERE is_email_verified = true;",
        "CREATE INDEX IF NOT EXISTS idx_users_last_login ON users (last_login_at DESC) WHERE last_login_at IS NOT NULL;",
        "CREATE INDEX IF NOT EXISTS idx_users_status_tenant ON users (status, tenant_id) WHERE status = 'ACTIVE';",
        "CREATE INDEX IF NOT EXISTS idx_sessions_active ON user_sessions (is_active, expires_at) WHERE is_active = true;",
        "CREATE INDEX IF NOT EXISTS idx_sessions_cleanup ON user_sessions (expires_at) WHERE is_active = false;",
    ]

    try:
        # 逐个创建索引(不在事务中)
        for idx_sql in indexes:
            async with engine.connect() as conn:
                await conn.execute(text(idx_sql))
                await conn.commit()

                index_name = idx_sql.split()[4]
                print(f"  ✓ {index_name}")

        # 设置统计信息
        stats_commands = [
            "ALTER TABLE users ALTER COLUMN email SET STATISTICS 1000;",
            "ALTER TABLE tenants ALTER COLUMN tenant_id SET STATISTICS 1000;",
            "ALTER TABLE user_sessions ALTER COLUMN expires_at SET STATISTICS 500;",
        ]

        print("\n📊 设置表统计信息...")
        for cmd in stats_commands:
            async with engine.connect() as conn:
                await conn.execute(text(cmd))
                await conn.commit()

                table_col = cmd.split()[2:4]
                print(f"  ✓ {'.'.join(table_col)}")

        await engine.dispose()
        print("\n✅ 索引创建完成!")
        return True

    except Exception as e:
        print(f"\n❌ 索引创建失败: {e}")
        await engine.dispose()
        return False


if __name__ == "__main__":
    success = asyncio.run(create_database_indexes())
    exit(0 if success else 1)
