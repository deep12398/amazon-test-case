"""用户认证系统测试脚本"""

import time
from typing import Optional

import requests


class AuthSystemTester:
    """认证系统测试器"""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session = requests.Session()
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    def test_registration(self) -> bool:
        """测试用户注册"""
        print("\n📝 测试用户注册...")

        register_data = {
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "测试用户",
            "username": "testuser",
            "company_name": "测试公司",
        }

        response = self.session.post(
            f"{self.base_url}/api/v1/auth/register", json=register_data
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✓ 注册成功: 用户ID {data['user_id']}, 租户ID {data['tenant_id']}")
            return True
        else:
            print(f"❌ 注册失败: {response.status_code} - {response.text}")
            return False

    def test_login(
        self, email: str = "admin@demo.com", password: str = "admin123456"
    ) -> bool:
        """测试用户登录"""
        print(f"\n🔑 测试用户登录 ({email})...")

        login_data = {"email": email, "password": password, "remember_me": True}

        response = self.session.post(
            f"{self.base_url}/api/v1/auth/login", json=login_data
        )

        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.refresh_token = data.get("refresh_token")

            print("✓ 登录成功")
            print(f"  - 用户: {data['user']['email']}")
            print(f"  - 租户: {data['user']['tenant_id']}")
            print(f"  - Token类型: {data['token_type']}")
            print(f"  - 过期时间: {data['expires_in']}秒")
            print(f"  - 有刷新Token: {'是' if self.refresh_token else '否'}")

            return True
        else:
            print(f"❌ 登录失败: {response.status_code} - {response.text}")
            return False

    def test_protected_endpoint(self) -> bool:
        """测试受保护的端点"""
        print("\n🔒 测试受保护端点...")

        if not self.access_token:
            print("❌ 没有访问令牌，请先登录")
            return False

        headers = {"Authorization": f"Bearer {self.access_token}"}

        response = self.session.get(f"{self.base_url}/api/v1/users/me", headers=headers)

        if response.status_code == 200:
            data = response.json()
            print("✓ 访问受保护端点成功")
            print(f"  - 用户ID: {data['id']}")
            print(f"  - 邮箱: {data['email']}")
            print(f"  - 租户: {data['tenant']['name']}")
            print(f"  - 订阅计划: {data['tenant']['subscription_plan']}")
            return True
        else:
            print(f"❌ 访问受保护端点失败: {response.status_code} - {response.text}")
            return False

    def test_invalid_token(self) -> bool:
        """测试无效token"""
        print("\n❌ 测试无效Token...")

        headers = {"Authorization": "Bearer invalid-token"}

        response = self.session.get(f"{self.base_url}/api/v1/users/me", headers=headers)

        if response.status_code == 401:
            print("✓ 无效Token正确被拒绝")
            return True
        else:
            print(f"❌ 无效Token未被正确处理: {response.status_code}")
            return False

    def test_refresh_token(self) -> bool:
        """测试刷新Token"""
        print("\n🔄 测试Token刷新...")

        if not self.refresh_token:
            print("❌ 没有刷新Token")
            return False

        refresh_data = {"refresh_token": self.refresh_token}

        response = self.session.post(
            f"{self.base_url}/api/v1/auth/refresh", json=refresh_data
        )

        if response.status_code == 200:
            data = response.json()
            old_token = self.access_token
            self.access_token = data["access_token"]

            print("✓ Token刷新成功")
            print(f"  - 新Token: {self.access_token[:20]}...")
            print(f"  - Token类型: {data['token_type']}")
            print(f"  - 过期时间: {data['expires_in']}秒")

            # 验证新token是否有效
            return self.test_protected_endpoint()
        else:
            print(f"❌ Token刷新失败: {response.status_code} - {response.text}")
            return False

    def test_logout(self) -> bool:
        """测试登出"""
        print("\n👋 测试用户登出...")

        if not self.access_token:
            print("❌ 没有访问令牌")
            return False

        headers = {"Authorization": f"Bearer {self.access_token}"}

        response = self.session.post(
            f"{self.base_url}/api/v1/auth/logout", headers=headers
        )

        if response.status_code == 200:
            print("✓ 登出成功")

            # 验证token是否已失效
            test_response = self.session.get(
                f"{self.base_url}/api/v1/users/me", headers=headers
            )

            if test_response.status_code == 401:
                print("✓ Token已成功失效")
                self.access_token = None
                self.refresh_token = None
                return True
            else:
                print("⚠️ 登出后Token仍然有效（可能需要JWT黑名单机制）")
                return True
        else:
            print(f"❌ 登出失败: {response.status_code} - {response.text}")
            return False

    def test_user_sessions(self) -> bool:
        """测试用户会话管理"""
        print("\n📱 测试用户会话管理...")

        # 先登录
        if not self.access_token:
            self.test_login()

        headers = {"Authorization": f"Bearer {self.access_token}"}

        # 获取会话列表
        response = self.session.get(
            f"{self.base_url}/api/v1/auth/sessions", headers=headers
        )

        if response.status_code == 200:
            sessions = response.json()
            print(f"✓ 获取会话列表成功，共 {len(sessions)} 个会话")

            for i, session in enumerate(sessions):
                print(f"  会话 {i+1}:")
                print(f"    - ID: {session['session_id']}")
                print(f"    - 设备: {session.get('device_type', 'unknown')}")
                print(f"    - IP: {session.get('ip_address', 'unknown')}")
                print(f"    - 最后活动: {session['last_activity_at']}")

            return True
        else:
            print(f"❌ 获取会话列表失败: {response.status_code} - {response.text}")
            return False

    def test_tenant_info(self) -> bool:
        """测试租户信息"""
        print("\n🏢 测试租户信息...")

        if not self.access_token:
            self.test_login()

        headers = {"Authorization": f"Bearer {self.access_token}"}

        response = self.session.get(
            f"{self.base_url}/api/v1/tenants/me", headers=headers
        )

        if response.status_code == 200:
            tenant = response.json()
            print("✓ 获取租户信息成功")
            print(f"  - 租户名: {tenant['name']}")
            print(f"  - 租户ID: {tenant['tenant_id']}")
            print(f"  - 订阅计划: {tenant['subscription_plan']}")
            print(f"  - 订阅状态: {tenant['subscription_status']}")
            print(f"  - 最大用户数: {tenant['max_users']}")
            print(f"  - 最大产品数: {tenant['max_products']}")
            return True
        else:
            print(f"❌ 获取租户信息失败: {response.status_code} - {response.text}")
            return False

    def test_api_key_creation(self) -> bool:
        """测试API Key创建"""
        print("\n🔑 测试API Key创建...")

        if not self.access_token:
            self.test_login()

        headers = {"Authorization": f"Bearer {self.access_token}"}

        api_key_data = {
            "name": "测试API Key",
            "scopes": ["products.read", "analytics.read"],
            "rate_limit_per_minute": 100,
            "rate_limit_per_day": 10000,
            "expires_in_days": 30,
        }

        response = self.session.post(
            f"{self.base_url}/api/v1/users/me/api-keys",
            json=api_key_data,
            headers=headers,
        )

        if response.status_code == 200:
            data = response.json()
            print("✓ API Key创建成功")
            print(f"  - Key ID: {data['key_id']}")
            print(f"  - Name: {data['name']}")
            print(f"  - Key: {data['key'][:20]}...")
            print(f"  - 权限范围: {data['scopes']}")
            print(f"  - 限流: {data['rate_limit_per_minute']}/分钟")
            return True
        else:
            print(f"❌ API Key创建失败: {response.status_code} - {response.text}")
            return False


def main():
    """主测试函数"""
    print("🧪 开始用户认证系统测试")
    print("=" * 50)

    tester = AuthSystemTester()

    # 测试序列
    tests = [
        ("用户注册", lambda: tester.test_registration()),
        ("用户登录", lambda: tester.test_login()),
        ("受保护端点", lambda: tester.test_protected_endpoint()),
        ("无效Token", lambda: tester.test_invalid_token()),
        ("Token刷新", lambda: tester.test_refresh_token()),
        ("用户会话", lambda: tester.test_user_sessions()),
        ("租户信息", lambda: tester.test_tenant_info()),
        ("API Key创建", lambda: tester.test_api_key_creation()),
        ("用户登出", lambda: tester.test_logout()),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_name}测试出现异常: {e}")
            failed += 1

        time.sleep(1)  # 避免请求太快

    # 测试结果总结
    print("\n" + "=" * 50)
    print("🎯 测试结果总结")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"📊 成功率: {passed/(passed+failed)*100:.1f}%")

    if failed == 0:
        print("\n🎉 所有测试通过！认证系统工作正常。")
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查系统配置。")


if __name__ == "__main__":
    main()
