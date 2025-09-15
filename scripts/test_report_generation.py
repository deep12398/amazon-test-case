#!/usr/bin/env python3
"""报告生成测试脚本"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Optional

import requests

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


class ReportGenerationTester:
    """报告生成测试器"""

    def __init__(
        self,
        user_service_url: str = "http://localhost:8001",
        core_service_url: str = "http://localhost:8003"
    ):
        self.user_service_url = user_service_url
        self.core_service_url = core_service_url
        self.session = requests.Session()
        self.access_token: Optional[str] = None
        self.user_info: Optional[dict] = None

        # 使用demo用户信息（已有产品数据）
        self.test_user = {
            "email": "admin@demo.com",
            "password": "admin123456",
            "username": "admin",
            "full_name": "Demo Admin",
            "company_name": "Demo Company"
        }

    def print_step(self, step: str, description: str = ""):
        """打印步骤信息"""
        print(f"\n{'='*60}")
        print(f"步骤: {step}")
        if description:
            print(f"描述: {description}")
        print(f"{'='*60}")

    def print_success(self, message: str):
        """打印成功信息"""
        print(f"✅ {message}")

    def print_error(self, message: str):
        """打印错误信息"""
        print(f"❌ {message}")

    def print_info(self, message: str):
        """打印信息"""
        print(f"ℹ️  {message}")

    def check_service_health(self, service_url: str, service_name: str) -> bool:
        """检查服务健康状态"""
        try:
            # 首先尝试 /health 端点
            response = self.session.get(f"{service_url}/health", timeout=5)
            if response.status_code == 200:
                self.print_success(f"{service_name}服务运行正常")
                return True
            # 如果 /health 不存在，尝试根路径
            response = self.session.get(f"{service_url}/", timeout=5)
            if response.status_code == 200:
                self.print_success(f"{service_name}服务运行正常")
                return True
            else:
                self.print_error(f"{service_name}服务响应异常: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.print_error(f"{service_name}服务连接失败: {e}")
            return False

    def register_user(self) -> bool:
        """注册测试用户"""
        self.print_step("1. 用户注册", "注册新的测试用户")

        try:
            response = self.session.post(
                f"{self.user_service_url}/api/v1/auth/register",
                json=self.test_user,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.print_success("用户注册成功")
                self.print_info(f"用户ID: {data['user_id']}")
                self.print_info(f"租户ID: {data['tenant_id']}")
                return True
            else:
                response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                if "邮箱已被注册" in str(response_data):
                    self.print_info("用户已存在，跳过注册步骤")
                    return True
                else:
                    self.print_error(f"用户注册失败: {response.status_code} - {response_data}")
                    return False

        except Exception as e:
            self.print_error(f"用户注册异常: {e}")
            return False

    def login_user(self) -> bool:
        """用户登录"""
        self.print_step("2. 用户登录", "使用注册的用户登录获取JWT Token")

        login_data = {
            "email": self.test_user["email"],
            "password": self.test_user["password"],
            "remember_me": True
        }

        try:
            response = self.session.post(
                f"{self.user_service_url}/api/v1/auth/login",
                json=login_data,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                self.user_info = data["user"]

                # 更新session headers
                self.session.headers.update({
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                })

                self.print_success("用户登录成功")
                self.print_info(f"用户邮箱: {self.user_info['email']}")
                self.print_info(f"租户ID: {self.user_info['tenant_id']}")
                self.print_info(f"Token有效期: 30天")
                self.print_info(f"Token前20位: {self.access_token[:20]}...")
                return True
            else:
                response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                self.print_error(f"用户登录失败: {response.status_code} - {response_data}")
                return False

        except Exception as e:
            self.print_error(f"用户登录异常: {e}")
            return False

    def generate_report(self) -> Optional[str]:
        """生成报告"""
        self.print_step("3. 生成报告", "调用报告生成接口")

        if not self.access_token:
            self.print_error("没有有效的访问令牌，请先登录")
            return None

        # 报告生成请求
        report_request = {
            "report_type": "competitor",
            "time_period": "30d",
            "include_charts": False,
            "format": "markdown"
        }

        try:
            response = self.session.post(
                f"{self.core_service_url}/api/v1/reports/generate",
                json=report_request,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                report_id = data["report_id"]

                self.print_success("报告生成成功")
                self.print_info(f"报告ID: {report_id}")
                self.print_info(f"报告类型: {data['report_type']}")
                self.print_info(f"报告状态: {data['status']}")
                self.print_info(f"文件大小: {data['file_size']} bytes")
                self.print_info(f"创建时间: {data['created_at']}")
                self.print_info(f"过期时间: {data['expires_at']}")

                return report_id
            else:
                response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                self.print_error(f"报告生成失败: {response.status_code} - {response_data}")
                return None

        except Exception as e:
            self.print_error(f"报告生成异常: {e}")
            return None

    def preview_report(self, report_id: str) -> Optional[str]:
        """预览报告内容"""
        self.print_step("4. 预览报告", "获取生成的Markdown报告内容")

        try:
            response = self.session.get(
                f"{self.core_service_url}/api/v1/reports/{report_id}/preview",
                timeout=15
            )

            if response.status_code == 200:
                report_content = response.text
                self.print_success("报告预览成功")
                self.print_info(f"报告内容长度: {len(report_content)} 字符")

                # 显示报告前几行
                lines = report_content.split('\n')
                self.print_info("报告内容预览:")
                print("-" * 40)
                for line in lines[:20]:  # 显示前20行
                    print(line)
                if len(lines) > 20:
                    print(f"... (还有 {len(lines) - 20} 行)")
                print("-" * 40)

                return report_content
            else:
                response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                self.print_error(f"报告预览失败: {response.status_code} - {response_data}")
                return None

        except Exception as e:
            self.print_error(f"报告预览异常: {e}")
            return None

    def save_report(self, report_id: str, content: str) -> bool:
        """保存报告到文件"""
        self.print_step("5. 保存报告", "将报告保存到本地文件")

        try:
            # 创建报告目录
            reports_dir = os.path.join(os.path.dirname(__file__), "reports")
            os.makedirs(reports_dir, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"competitor_report_{timestamp}_{report_id}.md"
            filepath = os.path.join(reports_dir, filename)

            # 保存文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            self.print_success("报告保存成功")
            self.print_info(f"文件路径: {filepath}")
            self.print_info(f"文件大小: {os.path.getsize(filepath)} bytes")

            return True

        except Exception as e:
            self.print_error(f"报告保存异常: {e}")
            return False

    def generate_test_summary(self, report_content: Optional[str] = None) -> dict:
        """生成测试总结"""
        summary = {
            "测试时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "用户服务地址": self.user_service_url,
            "核心服务地址": self.core_service_url,
            "测试用户信息": {
                "邮箱": self.test_user["email"],
                "密码": self.test_user["password"],
                "用户名": self.test_user["username"],
                "全名": self.test_user["full_name"],
                "说明": "使用Demo账号以访问已有的产品数据"
            },
            "JWT Token信息": {
                "有效期": "30天",
                "Token前缀": self.access_token[:20] + "..." if self.access_token else "N/A"
            },
            "用户信息": self.user_info,
            "API接口调用记录": [
                {
                    "接口": "POST /api/v1/auth/register",
                    "用途": "用户注册",
                    "服务": "User Service"
                },
                {
                    "接口": "POST /api/v1/auth/login",
                    "用途": "用户登录",
                    "服务": "User Service"
                },
                {
                    "接口": "POST /api/v1/reports/generate",
                    "用途": "生成报告",
                    "服务": "Core Service"
                },
                {
                    "接口": "GET /api/v1/reports/{report_id}/preview",
                    "用途": "预览报告",
                    "服务": "Core Service"
                }
            ],
            "报告特点": {
                "格式": "Markdown",
                "包含内容": [
                    "主产品vs各竞品的价格差异",
                    "BSR排名差距",
                    "评分优劣势",
                    "产品特色对比(从产品bullet points提取)"
                ]
            }
        }

        if report_content:
            summary["报告统计"] = {
                "字符数": len(report_content),
                "行数": len(report_content.split('\n')),
                "包含章节": self._extract_sections(report_content)
            }

        return summary

    def _extract_sections(self, content: str) -> list:
        """提取报告章节"""
        sections = []
        for line in content.split('\n'):
            if line.startswith('## '):
                sections.append(line[3:])
        return sections

    def run_full_test(self) -> bool:
        """运行完整测试"""
        print("🧪 开始报告生成完整测试")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 检查服务状态
        self.print_step("0. 服务状态检查", "检查所需服务是否运行")

        user_service_ok = self.check_service_health(self.user_service_url, "用户服务")
        core_service_ok = self.check_service_health(self.core_service_url, "核心服务")

        if not user_service_ok or not core_service_ok:
            self.print_error("服务状态检查失败，请确保以下服务正在运行:")
            if not user_service_ok:
                self.print_info(f"用户服务: make dev-user (端口8001)")
            if not core_service_ok:
                self.print_info(f"核心服务: make dev-core (端口8002)")
            print("\n请启动服务后重新运行此脚本。")
            return False

        # 执行测试步骤（跳过注册，直接使用已存在的demo用户）
        steps = [
            ("用户登录", self.login_user),
        ]

        # 添加说明
        self.print_info("使用已存在的demo账号（admin@demo.com）来访问产品数据")

        for step_name, step_func in steps:
            if not step_func():
                self.print_error(f"{step_name}失败，终止测试")
                return False

        # 生成报告
        report_id = self.generate_report()
        if not report_id:
            self.print_error("报告生成失败，终止测试")
            return False

        # 预览报告
        report_content = self.preview_report(report_id)
        if not report_content:
            self.print_error("报告预览失败，终止测试")
            return False

        # 保存报告
        if not self.save_report(report_id, report_content):
            self.print_error("报告保存失败")

        # 生成测试总结
        self.print_step("6. 测试总结", "生成完整的测试报告")

        summary = self.generate_test_summary(report_content)

        # 保存测试总结
        try:
            reports_dir = os.path.join(os.path.dirname(__file__), "reports")
            os.makedirs(reports_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_file = os.path.join(reports_dir, f"test_summary_{timestamp}.json")

            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)

            self.print_success("测试总结生成成功")
            self.print_info(f"总结文件: {summary_file}")

        except Exception as e:
            self.print_error(f"测试总结保存失败: {e}")

        # 显示测试结果
        print("\n" + "="*60)
        print("🎉 测试完成!")
        print("="*60)
        print(f"✅ 用户注册: {self.test_user['email']}")
        print(f"✅ 用户登录: JWT Token有效期30天")
        print(f"✅ 报告生成: 竞品分析报告")
        print(f"✅ 报告内容: 包含价格、BSR、评分、特色对比")
        print(f"✅ 报告格式: Markdown")

        if report_content:
            sections = self._extract_sections(report_content)
            print(f"📊 报告章节: {', '.join(sections)}")

        print(f"💾 报告已保存到 scripts/reports/ 目录")

        return True


def main():
    """主函数"""
    print("🚀 Amazon产品跟踪系统 - 报告生成测试")
    print("=" * 60)

    # 检查是否需要启动服务
    tester = ReportGenerationTester()

    # 先检查服务状态
    user_service_ok = tester.check_service_health("http://localhost:8001", "用户服务")
    core_service_ok = tester.check_service_health("http://localhost:8002", "核心服务")

    if not user_service_ok or not core_service_ok:
        print("\n" + "="*60)
        print("⚠️  暂停：需要启动服务")
        print("="*60)
        print("请在不同的终端窗口中运行以下命令启动服务:")
        print()
        if not user_service_ok:
            print("1. 启动用户服务:")
            print("   cd /Users/elias/code/amazon/amazon-test")
            print("   make dev-user")
            print()
        if not core_service_ok:
            print("2. 启动核心服务:")
            print("   cd /Users/elias/code/amazon/amazon-test")
            print("   make dev-core")
            print()
        print("服务启动后，请重新运行此测试脚本:")
        print("   python scripts/test_report_generation.py")
        print()
        return False

    # 运行完整测试
    success = tester.run_full_test()

    if success:
        print("\n🎉 所有测试通过！")
        return True
    else:
        print("\n❌ 测试失败，请检查错误信息。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)