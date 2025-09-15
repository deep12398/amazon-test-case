#!/usr/bin/env python3
"""应用数据库优化脚本"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def apply_database_optimizations():
    """应用数据库优化"""

    # 数据库连接
    DATABASE_URL = "postgresql+asyncpg://postgres:your-password@db.your-project.supabase.co:5432/postgres"

    print("🔧 开始应用数据库优化...")

    try:
        # 创建异步引擎
        engine = create_async_engine(
            DATABASE_URL, echo=False, pool_size=1, max_overflow=0, pool_timeout=10
        )

        async with engine.begin() as conn:
            # 1. 启用必要的扩展
            print("📦 启用PostgreSQL扩展...")

            extensions = [
                "CREATE EXTENSION IF NOT EXISTS pg_trgm;",
                "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;",
                'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";',
            ]

            for ext in extensions:
                try:
                    await conn.execute(text(ext))
                    print(f"  ✓ {ext.split()[-1][:-1]}")
                except Exception as e:
                    print(f"  ⚠️ 跳过扩展 {ext}: {e}")

            # 2. 创建性能优化索引
            print("🏗️ 创建性能优化索引...")

            indexes = [
                # 租户相关索引
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tenants_subscription_status ON tenants (subscription_status);",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tenants_created_at ON tenants (created_at DESC);",
                # 用户相关索引
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_verified ON users (is_email_verified) WHERE is_email_verified = true;",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_login ON users (last_login_at DESC) WHERE last_login_at IS NOT NULL;",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_status_tenant ON users (status, tenant_id) WHERE status = 'ACTIVE';",
                # 会话相关索引
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_active ON user_sessions (is_active, expires_at) WHERE is_active = true;",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_cleanup ON user_sessions (expires_at) WHERE expires_at < NOW();",
            ]

            for idx in indexes:
                try:
                    await conn.execute(text(idx))
                    index_name = idx.split("idx_")[1].split()[0]
                    print(f"  ✓ {index_name}")
                except Exception as e:
                    print(f"  ⚠️ 跳过索引: {e}")

            # 3. 设置表统计信息目标
            print("📊 优化表统计信息...")

            stats_commands = [
                "ALTER TABLE users ALTER COLUMN email SET STATISTICS 1000;",
                "ALTER TABLE tenants ALTER COLUMN tenant_id SET STATISTICS 1000;",
                "ALTER TABLE user_sessions ALTER COLUMN expires_at SET STATISTICS 500;",
            ]

            for cmd in stats_commands:
                try:
                    await conn.execute(text(cmd))
                    table_col = cmd.split()[2:4]
                    print(f"  ✓ {'.'.join(table_col)}")
                except Exception as e:
                    print(f"  ⚠️ 跳过统计优化: {e}")

            # 4. 设置表填充因子
            print("🎛️ 设置表填充因子...")

            fillfactor_commands = [
                "ALTER TABLE users SET (fillfactor = 85);",
                "ALTER TABLE user_sessions SET (fillfactor = 80);",
                "ALTER TABLE tenants SET (fillfactor = 90);",
            ]

            for cmd in fillfactor_commands:
                try:
                    await conn.execute(text(cmd))
                    table = cmd.split()[2]
                    print(f"  ✓ {table}")
                except Exception as e:
                    print(f"  ⚠️ 跳过填充因子设置: {e}")

            # 5. 创建维护存储过程
            print("⚙️ 创建维护存储过程...")

            # 清理过期会话的存储过程
            cleanup_proc = """
            CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
            RETURNS INTEGER AS $$
            DECLARE
                deleted_count INTEGER;
            BEGIN
                DELETE FROM user_sessions
                WHERE expires_at < NOW() - INTERVAL '7 days'
                AND is_active = false;

                GET DIAGNOSTICS deleted_count = ROW_COUNT;

                -- 记录清理日志
                INSERT INTO system_logs (log_level, message, created_at)
                VALUES ('INFO', 'Cleaned up ' || deleted_count || ' expired sessions', NOW())
                ON CONFLICT DO NOTHING;

                RETURN deleted_count;
            END;
            $$ LANGUAGE plpgsql;
            """

            try:
                await conn.execute(text(cleanup_proc))
                print("  ✓ cleanup_expired_sessions()")
            except Exception as e:
                print(f"  ⚠️ 跳过存储过程创建: {e}")

        await engine.dispose()
        print("\n✅ 数据库优化应用完成!")
        return True

    except Exception as e:
        print(f"\n❌ 数据库优化失败: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(apply_database_optimizations())
    if success:
        print("\n🎉 数据库优化成功完成!")
    else:
        print("\n💥 数据库优化失败，请检查日志。")
    exit(0 if success else 1)
