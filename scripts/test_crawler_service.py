#!/usr/bin/env python3
"""爬虫服务测试脚本"""

import json
import os
import sys

import requests

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from amazon_tracker.common.database.connection import get_db_session
from amazon_tracker.common.database.models.crawl import CrawlTask
from amazon_tracker.common.database.models.product import (
    Product,
)


class CrawlerServiceTester:
    """爬虫服务测试器"""

    def __init__(self, base_url: str = "http://localhost:8002", token: str = None):
        self.base_url = base_url
        self.token = token
        self.session = requests.Session()

        if token:
            self.session.headers.update(
                {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            )

    def test_health_check(self):
        """测试健康检查"""
        print("🔍 Testing health check...")

        try:
            response = self.session.get(f"{self.base_url}/health")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

    def test_monitoring_endpoints(self):
        """测试监控端点"""
        print("\n🔍 Testing monitoring endpoints...")

        # 测试健康检查
        try:
            response = self.session.get(f"{self.base_url}/api/v1/monitoring/health")
            print(f"Health endpoint status: {response.status_code}")

            if response.status_code == 200:
                health_data = response.json()
                print(f"Overall status: {health_data.get('status')}")
                print(f"Checks: {list(health_data.get('checks', {}).keys())}")
        except Exception as e:
            print(f"❌ Health monitoring failed: {e}")

        # 测试指标端点
        try:
            response = self.session.get(f"{self.base_url}/api/v1/monitoring/metrics")
            print(f"Metrics endpoint status: {response.status_code}")

            if response.status_code == 200:
                metrics_content = response.text
                print(f"Metrics content length: {len(metrics_content)} bytes")
                # 显示前几行指标
                lines = metrics_content.split("\n")[:10]
                print("Sample metrics:")
                for line in lines:
                    if line and not line.startswith("#"):
                        print(f"  {line}")
        except Exception as e:
            print(f"❌ Metrics endpoint failed: {e}")

    def test_create_crawl_task(self, asin: str = "B08N5WRWNW"):
        """测试创建爬虫任务"""
        print(f"\n🔍 Testing create crawl task for ASIN: {asin}...")

        if not self.token:
            print("❌ No authentication token provided")
            return None

        payload = {
            "asin": asin,
            "marketplace": "AMAZON_US",
            "tracking_frequency": "DAILY",
            "priority": "NORMAL",
            "config": {"scrapeDescription": True, "scrapeFeatures": True},
        }

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/products/crawl", json=payload
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                task_data = response.json()
                print(f"Task created: {task_data['task_id']}")
                print(f"Product ID: {task_data['product_id']}")
                return task_data["task_id"]
            else:
                print(f"Error: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Create crawl task failed: {e}")
            return None

    def test_get_task_status(self, task_id: str):
        """测试获取任务状态"""
        print(f"\n🔍 Testing get task status for: {task_id}...")

        if not self.token:
            print("❌ No authentication token provided")
            return

        try:
            response = self.session.get(f"{self.base_url}/api/v1/tasks/{task_id}")
            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                task_data = response.json()
                print(f"Task Status: {task_data['status']}")
                print(f"Created At: {task_data['created_at']}")
                print(f"Items Processed: {task_data['items_processed']}")

                if task_data.get("error_message"):
                    print(f"Error: {task_data['error_message']}")

                return task_data
            else:
                print(f"Error: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Get task status failed: {e}")
            return None

    def test_list_tasks(self):
        """测试获取任务列表"""
        print("\n🔍 Testing list tasks...")

        if not self.token:
            print("❌ No authentication token provided")
            return

        try:
            response = self.session.get(f"{self.base_url}/api/v1/tasks/")
            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                tasks = response.json()
                print(f"Found {len(tasks)} tasks")

                for task in tasks[:5]:  # 显示前5个任务
                    print(f"  Task {task['task_id'][:8]}... - Status: {task['status']}")

                return tasks
            else:
                print(f"Error: {response.text}")
                return None

        except Exception as e:
            print(f"❌ List tasks failed: {e}")
            return None

    def test_batch_crawl(self, asins: list = None):
        """测试批量爬虫"""
        print("\n🔍 Testing batch crawl...")

        if not self.token:
            print("❌ No authentication token provided")
            return None

        if not asins:
            asins = ["B08N5WRWNW", "B07XJ8C8F5", "B08CFSZLQ6"]

        payload = {
            "asins": asins,
            "marketplace": "AMAZON_US",
            "tracking_frequency": "DAILY",
            "priority": "NORMAL",
        }

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/products/batch-crawl", json=payload
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                task_data = response.json()
                print(f"Batch task created: {task_data['task_id']}")
                return task_data["task_id"]
            else:
                print(f"Error: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Batch crawl failed: {e}")
            return None

    def test_database_integration(self):
        """测试数据库集成"""
        print("\n🔍 Testing database integration...")

        try:
            with get_db_session() as db:
                # 查询最近的任务
                recent_tasks = (
                    db.query(CrawlTask)
                    .order_by(CrawlTask.created_at.desc())
                    .limit(5)
                    .all()
                )

                print(f"Found {len(recent_tasks)} recent tasks in database")

                for task in recent_tasks:
                    print(
                        f"  Task {str(task.task_id)[:8]}... - Status: {task.status.value}"
                    )

                # 查询产品数量
                product_count = db.query(Product).count()
                print(f"Total products in database: {product_count}")

                return True

        except Exception as e:
            print(f"❌ Database integration test failed: {e}")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 Starting Crawler Service Tests")
        print(f"Base URL: {self.base_url}")
        print(f"Authenticated: {'Yes' if self.token else 'No'}")
        print("=" * 50)

        # 基础测试
        health_ok = self.test_health_check()
        self.test_monitoring_endpoints()
        db_ok = self.test_database_integration()

        if not self.token:
            print("\n⚠️  Skipping authenticated tests (no token provided)")
            print("\n📝 Test Summary:")
            print(f"  Health Check: {'✅' if health_ok else '❌'}")
            print(f"  Database: {'✅' if db_ok else '❌'}")
            return

        # 认证测试
        self.test_list_tasks()

        # 创建单个爬虫任务
        task_id = self.test_create_crawl_task()

        if task_id:
            # 等待一下然后检查状态
            import time

            time.sleep(2)
            self.test_get_task_status(task_id)

        # 创建批量爬虫任务
        batch_task_id = self.test_batch_crawl()

        print("\n📝 Test Summary:")
        print(f"  Health Check: {'✅' if health_ok else '❌'}")
        print(f"  Database: {'✅' if db_ok else '❌'}")
        print(f"  Single Crawl: {'✅' if task_id else '❌'}")
        print(f"  Batch Crawl: {'✅' if batch_task_id else '❌'}")


def get_test_token():
    """获取测试用的认证令牌"""
    try:
        # 尝试从用户服务获取令牌
        response = requests.post(
            "http://localhost:8001/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "admin123"},
        )

        if response.status_code == 200:
            login_data = response.json()
            return login_data.get("access_token")
        else:
            print(f"Failed to get test token: {response.text}")
            return None

    except Exception as e:
        print(f"Failed to get test token: {e}")
        return None


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Test Crawler Service")
    parser.add_argument(
        "--url", default="http://localhost:8002", help="Service base URL"
    )
    parser.add_argument("--token", help="Authentication token")
    parser.add_argument(
        "--get-token", action="store_true", help="Try to get test token automatically"
    )
    parser.add_argument("--asin", default="B08N5WRWNW", help="ASIN to test with")

    args = parser.parse_args()

    token = args.token
    if args.get_token and not token:
        print("🔐 Attempting to get test token...")
        token = get_test_token()
        if token:
            print("✅ Got test token")
        else:
            print("❌ Failed to get test token")

    tester = CrawlerServiceTester(base_url=args.url, token=token)
    tester.run_all_tests()


if __name__ == "__main__":
    main()
