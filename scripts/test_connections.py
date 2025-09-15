#!/usr/bin/env python3
"""
测试开发环境连接脚本
Test connections to Redis and PostgreSQL
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_redis_connection():
    """测试Redis连接"""
    try:
        import redis

        # 从.env.example读取Redis配置
        redis_url = "redis://localhost:6379"

        # 创建Redis客户端
        client = redis.from_url(redis_url, decode_responses=True)

        # 测试连接
        pong = client.ping()
        if pong:
            print("✅ Redis连接成功")

            # 测试基本操作
            client.set("test_key", "test_value", ex=10)  # 10秒过期
            value = client.get("test_key")
            if value == "test_value":
                print("✅ Redis读写测试成功")
                client.delete("test_key")
                return True
            else:
                print("❌ Redis读写测试失败")
                return False
        else:
            print("❌ Redis ping失败")
            return False

    except ImportError:
        print("❌ Redis库未安装，请运行: pip install redis")
        return False
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        return False


def test_postgres_connection():
    """测试PostgreSQL连接"""
    try:
        import psycopg2
        from psycopg2 import sql

        # 从.env.example读取PostgreSQL配置
        DATABASE_URL = "postgresql://postgres:I23FWMZYxq2OAuoR@db.rnopjqjtzodeobepvpan.supabase.co:5432/postgres"

        # 创建数据库连接
        conn = psycopg2.connect(DATABASE_URL)

        # 创建游标
        cur = conn.cursor()

        # 测试连接
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print("✅ PostgreSQL连接成功")
        print(f"   数据库版本: {version[0][:50]}...")

        # 测试基本查询
        cur.execute("SELECT current_database(), current_user, now();")
        result = cur.fetchone()
        print(f"   当前数据库: {result[0]}")
        print(f"   当前用户: {result[1]}")
        print(f"   当前时间: {result[2]}")

        # 关闭连接
        cur.close()
        conn.close()

        return True

    except ImportError:
        print("❌ psycopg2库未安装，请运行: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ PostgreSQL连接失败: {e}")
        return False


def test_local_postgres():
    """测试本地PostgreSQL连接（如果存在）"""
    try:
        import psycopg2

        # 测试本地数据库
        LOCAL_DATABASE_URL = (
            "postgresql://dev_user:dev_password@localhost:5432/amazon_tracker_dev"
        )

        conn = psycopg2.connect(LOCAL_DATABASE_URL)
        cur = conn.cursor()

        cur.execute("SELECT version();")
        version = cur.fetchone()
        print("✅ 本地PostgreSQL连接成功")
        print(f"   版本: {version[0][:50]}...")

        cur.close()
        conn.close()
        return True

    except ImportError:
        return False
    except Exception as e:
        print(f"ℹ️  本地PostgreSQL未启动或配置不正确: {e}")
        return False


def main():
    """主函数"""
    print("🔍 开始测试开发环境连接...")
    print("=" * 50)

    results = []

    # 测试Redis连接
    print("\n📡 测试Redis连接:")
    redis_ok = test_redis_connection()
    results.append(("Redis", redis_ok))

    # 测试Supabase PostgreSQL连接
    print("\n🐘 测试Supabase PostgreSQL连接:")
    postgres_ok = test_postgres_connection()
    results.append(("Supabase PostgreSQL", postgres_ok))

    # 测试本地PostgreSQL连接
    print("\n🏠 测试本地PostgreSQL连接:")
    local_postgres_ok = test_local_postgres()
    results.append(("本地PostgreSQL", local_postgres_ok))

    # 总结结果
    print("\n" + "=" * 50)
    print("📊 连接测试结果:")

    all_passed = True
    for service, status in results:
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {service}")
        if not status and service in ["Redis", "Supabase PostgreSQL"]:
            all_passed = False

    if all_passed:
        print("\n🎉 核心服务连接正常，可以开始开发!")
    else:
        print("\n⚠️  部分服务连接失败，请检查配置")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
