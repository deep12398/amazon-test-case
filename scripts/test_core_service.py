#!/usr/bin/env python3
"""核心服务测试脚本"""

import json
import os
import sys

import requests

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from amazon_tracker.common.database.connection import get_db_session
from amazon_tracker.common.database.models.product import Product


class CoreServiceTester:
    """核心服务测试器"""

    def __init__(self, base_url: str = "http://localhost:8003", token: str = None):
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

    def test_create_product(self, asin: str = "B08N5WRWNW"):
        """测试创建产品"""
        print(f"\n🔍 Testing create product with ASIN: {asin}...")

        if not self.token:
            print("❌ No authentication token provided")
            return None

        payload = {
            "asin": asin,
            "title": f"Test Product {asin}",
            "brand": "Test Brand",
            "category": "Electronics",
            "marketplace": "AMAZON_US",
            "tracking_frequency": "DAILY",
            "tags": ["test", "automation"],
            "notes": "Created by test script",
        }

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/products/", json=payload
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code in [200, 201]:
                product_data = response.json()
                print(
                    f"Product created: ID={product_data['id']}, ASIN={product_data['asin']}"
                )
                return product_data["id"]
            else:
                print(f"Error: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Create product failed: {e}")
            return None

    def test_list_products(self):
        """测试获取产品列表"""
        print("\n🔍 Testing list products...")

        if not self.token:
            print("❌ No authentication token provided")
            return None

        try:
            response = self.session.get(f"{self.base_url}/api/v1/products/")
            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                products = response.json()
                print(f"Found {len(products)} products")

                for product in products[:3]:  # 显示前3个产品
                    print(
                        f"  Product: {product['title'][:50]}... (ASIN: {product['asin']})"
                    )

                return products
            else:
                print(f"Error: {response.text}")
                return None

        except Exception as e:
            print(f"❌ List products failed: {e}")
            return None

    def test_search_products(self, query: str = "test"):
        """测试搜索产品"""
        print(f"\n🔍 Testing search products with query: '{query}'...")

        if not self.token:
            print("❌ No authentication token provided")
            return None

        payload = {"query": query, "sort_by": "created_at", "sort_order": "desc"}

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/products/search", json=payload
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                products = response.json()
                print(f"Search found {len(products)} products")
                return products
            else:
                print(f"Error: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Search products failed: {e}")
            return None

    def test_create_alert(self, product_id: int):
        """测试创建价格提醒"""
        print(f"\n🔍 Testing create price alert for product {product_id}...")

        if not self.token:
            print("❌ No authentication token provided")
            return None

        payload = {
            "product_id": product_id,
            "alert_type": "price_drop",
            "target_value": 50.0,
            "is_active": True,
            "notification_methods": ["email", "in_app"],
        }

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/alerts/", json=payload
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code in [200, 201]:
                alert_data = response.json()
                print(
                    f"Alert created: ID={alert_data['id']}, Type={alert_data['alert_type']}"
                )
                return alert_data["id"]
            else:
                print(f"Error: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Create alert failed: {e}")
            return None

    def test_competitor_analysis(self, product_id: int):
        """测试竞品分析"""
        print(f"\n🔍 Testing competitor analysis for product {product_id}...")

        if not self.token:
            print("❌ No authentication token provided")
            return None

        payload = {
            "product_id": product_id,
            "analysis_type": "comprehensive",
            "auto_discover": True,
            "max_competitors": 5,
        }

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/competitors/analyze", json=payload
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                analysis = response.json()
                print(f"Analysis ID: {analysis['analysis_id']}")
                print(f"Main product: {analysis['main_product']['title'][:50]}...")
                print(f"Competitors found: {len(analysis['competitors'])}")
                print(f"Market position: {analysis['market_position']}")
                return analysis
            else:
                print(f"Error: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Competitor analysis failed: {e}")
            return None

    def test_market_trends(self):
        """测试市场趋势分析"""
        print("\n🔍 Testing market trends analysis...")

        if not self.token:
            print("❌ No authentication token provided")
            return None

        payload = {
            "marketplace": "AMAZON_US",
            "time_period": "30d",
            "metrics": ["price", "rank"],
        }

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/market-trends/analyze", json=payload
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                trends = response.json()
                print(f"Product count: {trends.get('product_count', 0)}")
                print(f"Time period: {trends['time_period']}")
                print(f"Trends analyzed: {list(trends['trend_data'].keys())}")
                return trends
            else:
                print(f"Error: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Market trends analysis failed: {e}")
            return None

    def test_generate_report(self, product_ids: list = None):
        """测试报告生成"""
        print("\n🔍 Testing report generation...")

        if not self.token:
            print("❌ No authentication token provided")
            return None

        payload = {
            "report_type": "product",
            "product_ids": product_ids[:3]
            if product_ids and len(product_ids) > 3
            else product_ids,
            "time_period": "30d",
            "include_charts": True,
            "format": "json",
        }

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/reports/generate", json=payload
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code in [200, 201]:
                report = response.json()
                print(f"Report generated: ID={report['report_id']}")
                print(f"Report type: {report['report_type']}")
                print(f"File size: {report['file_size']} bytes")
                print(f"File URL: {report.get('file_url', 'N/A')}")
                return report
            else:
                print(f"Error: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Report generation failed: {e}")
            return None

    def test_product_stats(self):
        """测试产品统计"""
        print("\n🔍 Testing product statistics...")

        if not self.token:
            print("❌ No authentication token provided")
            return None

        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/products/stats/overview"
            )
            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                stats = response.json()
                print(f"Total products: {stats['total_products']}")
                print(f"Active products: {stats['active_products']}")
                print(f"Average price: ${stats.get('avg_price', 0):.2f}")
                print(f"Average rating: {stats.get('avg_rating', 0):.2f}/5.0")
                return stats
            else:
                print(f"Error: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Product stats failed: {e}")
            return None

    def test_database_integration(self):
        """测试数据库集成"""
        print("\n🔍 Testing database integration...")

        try:
            with get_db_session() as db:
                # 查询产品数量
                product_count = db.query(Product).count()
                print(f"Total products in database: {product_count}")

                # 查询最近的产品
                recent_products = (
                    db.query(Product).order_by(Product.created_at.desc()).limit(5).all()
                )

                print("Recent products:")
                for product in recent_products:
                    print(f"  {product.asin}: {product.title[:50]}...")

                return True

        except Exception as e:
            print(f"❌ Database integration test failed: {e}")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 Starting Core Service Tests")
        print(f"Base URL: {self.base_url}")
        print(f"Authenticated: {'Yes' if self.token else 'No'}")
        print("=" * 50)

        # 基础测试
        health_ok = self.test_health_check()
        db_ok = self.test_database_integration()

        if not self.token:
            print("\n⚠️  Skipping authenticated tests (no token provided)")
            print("\n📝 Test Summary:")
            print(f"  Health Check: {'✅' if health_ok else '❌'}")
            print(f"  Database: {'✅' if db_ok else '❌'}")
            return

        # 认证测试
        products = self.test_list_products()
        stats = self.test_product_stats()
        search_results = self.test_search_products()

        # 创建测试产品
        product_id = self.test_create_product("B08TEST001")

        # 如果成功创建产品，进行更多测试
        if product_id:
            alert_id = self.test_create_alert(product_id)
            competitor_analysis = self.test_competitor_analysis(product_id)

        # 市场趋势测试
        market_trends = self.test_market_trends()

        # 报告生成测试
        product_ids = [p["id"] for p in (products or [])[:3]]
        if product_id:
            product_ids.append(product_id)

        if product_ids:
            report = self.test_generate_report(product_ids)

        print("\n📝 Test Summary:")
        print(f"  Health Check: {'✅' if health_ok else '❌'}")
        print(f"  Database: {'✅' if db_ok else '❌'}")
        print(f"  List Products: {'✅' if products else '❌'}")
        print(f"  Product Stats: {'✅' if stats else '❌'}")
        print(f"  Search Products: {'✅' if search_results is not None else '❌'}")
        print(f"  Create Product: {'✅' if product_id else '❌'}")
        print(f"  Create Alert: {'✅' if product_id and alert_id else '❌'}")
        print(
            f"  Competitor Analysis: {'✅' if product_id and competitor_analysis else '❌'}"
        )
        print(f"  Market Trends: {'✅' if market_trends else '❌'}")
        print(f"  Report Generation: {'✅' if product_ids and report else '❌'}")


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

    parser = argparse.ArgumentParser(description="Test Core Service")
    parser.add_argument(
        "--url", default="http://localhost:8003", help="Service base URL"
    )
    parser.add_argument("--token", help="Authentication token")
    parser.add_argument(
        "--get-token", action="store_true", help="Try to get test token automatically"
    )

    args = parser.parse_args()

    token = args.token
    if args.get_token and not token:
        print("🔐 Attempting to get test token...")
        token = get_test_token()
        if token:
            print("✅ Got test token")
        else:
            print("❌ Failed to get test token")

    tester = CoreServiceTester(base_url=args.url, token=token)
    tester.run_all_tests()


if __name__ == "__main__":
    main()
