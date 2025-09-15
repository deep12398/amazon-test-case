#!/usr/bin/env python3
"""创建简单的种子测试数据"""

import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def create_seed_data():
    """创建种子数据"""

    DATABASE_URL = "postgresql+asyncpg://postgres:your-password@db.your-project.supabase.co:5432/postgres"

    print("🌱 开始创建种子数据...")

    # 创建引擎
    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        async with engine.begin() as conn:
            # 1. 创建演示租户
            print("🏢 创建演示租户...")

            tenant_id = f"tenant_{secrets.token_urlsafe(16)}"
            trial_ends_at = datetime.utcnow() + timedelta(days=30)

            await conn.execute(
                text(
                    """
                INSERT INTO tenants (
                    tenant_id, name, domain, subscription_plan, subscription_status,
                    trial_ends_at, max_users, max_products, max_api_calls_per_day,
                    settings, timezone, is_deleted
                ) VALUES (
                    :tenant_id, :name, :domain, :plan, :status,
                    :trial_ends, :max_users, :max_products, :max_calls,
                    :settings, :timezone, :is_deleted
                )
            """
                ),
                {
                    "tenant_id": tenant_id,
                    "name": "演示公司",
                    "domain": "demo.localhost",
                    "plan": "PROFESSIONAL",
                    "status": "TRIAL",
                    "trial_ends": trial_ends_at,
                    "max_users": 100,
                    "max_products": 2000,
                    "max_calls": 100000,
                    "settings": '{"theme": "light", "language": "zh-CN"}',
                    "timezone": "Asia/Shanghai",
                    "is_deleted": False,
                },
            )

            print(f"  ✓ 租户ID: {tenant_id}")

            # 2. 创建演示管理员用户
            print("👤 创建演示用户...")

            # 生成密码哈希 (密码: demo123456)
            password = "demo123456"
            salt = secrets.token_urlsafe(24)
            password_hash = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
            ).hex()

            # 管理员用户
            await conn.execute(
                text(
                    """
                INSERT INTO users (
                    email, username, full_name, password_hash, salt,
                    status, is_email_verified, is_super_admin, tenant_id,
                    login_count, failed_login_attempts, password_changed_at,
                    preferences, is_deleted
                ) VALUES (
                    :email, :username, :full_name, :password_hash, :salt,
                    :status, :email_verified, :super_admin, :tenant_id,
                    :login_count, :failed_attempts, :password_changed,
                    :preferences, :is_deleted
                )
            """
                ),
                {
                    "email": "admin@demo.com",
                    "username": "admin",
                    "full_name": "演示管理员",
                    "password_hash": password_hash,
                    "salt": salt,
                    "status": "ACTIVE",
                    "email_verified": True,
                    "super_admin": False,
                    "tenant_id": tenant_id,
                    "login_count": 0,
                    "failed_attempts": 0,
                    "password_changed": datetime.utcnow(),
                    "preferences": '{"dashboard_view": "cards", "timezone": "Asia/Shanghai"}',
                    "is_deleted": False,
                },
            )

            print(f"  ✓ 管理员: admin@demo.com / {password}")

            # 普通用户
            user_salt = secrets.token_urlsafe(24)
            user_password_hash = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), user_salt.encode("utf-8"), 100000
            ).hex()

            await conn.execute(
                text(
                    """
                INSERT INTO users (
                    email, username, full_name, password_hash, salt,
                    status, is_email_verified, is_super_admin, tenant_id,
                    login_count, failed_login_attempts, password_changed_at,
                    preferences, is_deleted
                ) VALUES (
                    :email, :username, :full_name, :password_hash, :salt,
                    :status, :email_verified, :super_admin, :tenant_id,
                    :login_count, :failed_attempts, :password_changed,
                    :preferences, :is_deleted
                )
            """
                ),
                {
                    "email": "user@demo.com",
                    "username": "user",
                    "full_name": "演示用户",
                    "password_hash": user_password_hash,
                    "salt": user_salt,
                    "status": "ACTIVE",
                    "email_verified": True,
                    "super_admin": False,
                    "tenant_id": tenant_id,
                    "login_count": 0,
                    "failed_attempts": 0,
                    "password_changed": datetime.utcnow(),
                    "preferences": '{"dashboard_view": "table", "timezone": "Asia/Shanghai"}',
                    "is_deleted": False,
                },
            )

            print(f"  ✓ 普通用户: user@demo.com / {password}")

            # 3. 创建第二个租户(企业版)
            print("🏢 创建企业租户...")

            enterprise_tenant_id = f"tenant_{secrets.token_urlsafe(16)}"
            subscription_ends_at = datetime.utcnow() + timedelta(days=365)

            await conn.execute(
                text(
                    """
                INSERT INTO tenants (
                    tenant_id, name, domain, subscription_plan, subscription_status,
                    subscription_ends_at, max_users, max_products, max_api_calls_per_day,
                    settings, timezone, is_deleted
                ) VALUES (
                    :tenant_id, :name, :domain, :plan, :status,
                    :subscription_ends, :max_users, :max_products, :max_calls,
                    :settings, :timezone, :is_deleted
                )
            """
                ),
                {
                    "tenant_id": enterprise_tenant_id,
                    "name": "企业客户",
                    "domain": "enterprise.localhost",
                    "plan": "ENTERPRISE",
                    "status": "ACTIVE",
                    "subscription_ends": subscription_ends_at,
                    "max_users": 500,
                    "max_products": 10000,
                    "max_calls": 1000000,
                    "settings": '{"theme": "dark", "language": "en-US", "analytics": true}',
                    "timezone": "UTC",
                    "is_deleted": False,
                },
            )

            print(f"  ✓ 企业租户ID: {enterprise_tenant_id}")

            # 企业管理员
            enterprise_salt = secrets.token_urlsafe(24)
            enterprise_password_hash = hashlib.pbkdf2_hmac(
                "sha256",
                b"enterprise123",
                enterprise_salt.encode("utf-8"),
                100000,
            ).hex()

            await conn.execute(
                text(
                    """
                INSERT INTO users (
                    email, username, full_name, password_hash, salt,
                    status, is_email_verified, is_super_admin, tenant_id,
                    login_count, failed_login_attempts, password_changed_at,
                    preferences, is_deleted
                ) VALUES (
                    :email, :username, :full_name, :password_hash, :salt,
                    :status, :email_verified, :super_admin, :tenant_id,
                    :login_count, :failed_attempts, :password_changed,
                    :preferences, :is_deleted
                )
            """
                ),
                {
                    "email": "admin@enterprise.com",
                    "username": "enterprise_admin",
                    "full_name": "企业管理员",
                    "password_hash": enterprise_password_hash,
                    "salt": enterprise_salt,
                    "status": "ACTIVE",
                    "email_verified": True,
                    "super_admin": False,
                    "tenant_id": enterprise_tenant_id,
                    "login_count": 5,
                    "failed_attempts": 0,
                    "password_changed": datetime.utcnow() - timedelta(days=30),
                    "preferences": '{"dashboard_view": "analytics", "timezone": "UTC"}',
                    "is_deleted": False,
                },
            )

            print("  ✓ 企业管理员: admin@enterprise.com / enterprise123")

            print("\n✅ 种子数据创建完成!")

        await engine.dispose()
        return True

    except Exception as e:
        print(f"\n❌ 种子数据创建失败: {e}")
        await engine.dispose()
        return False


async def main():
    """主函数"""
    success = await create_seed_data()

    if success:
        print(
            """
🎉 数据库初始化完成!

📋 测试账户信息:
┌─────────────────────────────────────────────────────────────┐
│ 演示租户 (demo.localhost)                                    │
│ - 管理员: admin@demo.com / demo123456                       │
│ - 用户:   user@demo.com / demo123456                        │
│                                                             │
│ 企业租户 (enterprise.localhost)                             │
│ - 管理员: admin@enterprise.com / enterprise123              │
└─────────────────────────────────────────────────────────────┘

🚀 系统已就绪，可以开始开发和测试!
        """
        )
    else:
        print("\n💥 数据库初始化失败，请查看错误信息。")

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
