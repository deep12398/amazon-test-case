#!/usr/bin/env python3
"""创建测试用户和生成访问令牌的脚本"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv

load_dotenv(project_root / ".env.local")
load_dotenv(project_root / ".env")

# 转换数据库URL为同步
original_url = os.environ.get("DATABASE_URL", "")
if "+asyncpg" in original_url:
    sync_url = original_url.replace("postgresql+asyncpg://", "postgresql://")
    os.environ["DATABASE_URL"] = sync_url

from amazon_tracker.common.auth.jwt_auth import jwt_auth
from amazon_tracker.common.database.connection import get_db_session
from amazon_tracker.common.database.models.user import Tenant, User, UserStatus


def create_test_user():
    """创建测试用户并生成访问令牌"""
    print("🔑 创建测试用户和访问令牌")
    print("=" * 50)

    try:
        with get_db_session() as db:
            # 检查是否已存在测试用户
            existing_user = (
                db.query(User).filter(User.email == "test@crawler.com").first()
            )

            if existing_user:
                print(f"   测试用户已存在: {existing_user.email}")
                user = existing_user
            else:
                # 创建或获取租户
                tenant = (
                    db.query(Tenant).filter(Tenant.tenant_id == "demo-tenant").first()
                )
                if not tenant:
                    tenant = Tenant(name="测试租户", tenant_id="demo-tenant")
                    db.add(tenant)
                    db.flush()

                # 创建测试用户
                user = User(
                    email="test@crawler.com",
                    username="test_crawler",
                    full_name="Test Crawler User",
                    tenant_id=tenant.tenant_id,
                    status=UserStatus.ACTIVE,  # 直接设为活跃状态
                    is_email_verified=True,
                )
                user.set_password("password123")

                db.add(user)
                db.commit()
                print(f"   ✅ 创建测试用户: {user.email}")

            # 生成访问令牌
            import secrets

            session_id = secrets.token_urlsafe(32)

            access_token = jwt_auth.create_access_token(user, session_id)

            print("\n🔑 访问令牌生成成功:")
            print(f"用户ID: {user.id}")
            print(f"邮箱: {user.email}")
            print(f"租户ID: {user.tenant_id}")
            print("\n访问令牌:")
            print(f"Bearer {access_token}")
            print("\n🧪 测试命令:")
            print(
                f'curl -H "Authorization: Bearer {access_token}" http://localhost:8002/api/v1/products/category-crawl'
            )

            return access_token

    except Exception as e:
        print(f"❌ 创建用户失败: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    create_test_user()
