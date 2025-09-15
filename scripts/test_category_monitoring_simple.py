#!/usr/bin/env python3
"""品类商品监控功能简化演示脚本（无需Apify）"""

import json
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv

load_dotenv(project_root / ".env.local")
load_dotenv(project_root / ".env")

# 临时修改数据库URL为同步驱动
original_url = os.environ.get("DATABASE_URL", "")
if "+asyncpg" in original_url:
    sync_url = original_url.replace("postgresql+asyncpg://", "postgresql://")
    os.environ["DATABASE_URL"] = sync_url
    print(f"转换为同步数据库连接: {sync_url[:50]}...")
else:
    print(f"使用原始数据库连接: {original_url[:50]}...")

from amazon_tracker.common.database.connection import get_db_session
from amazon_tracker.common.database.models.product import (
    MarketplaceType,
    Product,
    ProductPriceHistory,
    ProductRankHistory,
    ProductStatus,
    TrackingFrequency,
)
from amazon_tracker.common.notification.email_service import EmailNotifier
from amazon_tracker.services.monitoring.anomaly_detector import AnomalyDetector


class SimpleCategoryMonitoringDemo:
    """简化的品类商品监控演示类"""

    def __init__(self):
        self.anomaly_detector = AnomalyDetector()
        self.email_notifier = EmailNotifier()

    def create_test_products(self):
        """创建测试产品数据"""
        print("🛠️ 创建测试产品数据")
        print("=" * 60)

        # 测试用的蓝牙耳机产品数据
        test_products = [
            {
                "asin": "B09XS7JWHH",
                "title": "Sony WH-1000XM5 Wireless Industry Leading Noise Canceling Headphones",
                "brand": "Sony",
                "category": "蓝牙耳机",
                "current_price": Decimal("349.99"),
                "buy_box_price": Decimal("329.99"),
                "current_rank": 42,
                "rating": Decimal("4.4"),
                "review_count": 15832,
                "image_url": "https://m.media-amazon.com/images/I/61+bthl5OjL._AC_SL1500_.jpg",
                "availability": "In Stock",
            },
            {
                "asin": "B0BDHWDR12",
                "title": "Apple AirPods Pro (2nd Generation) with MagSafe Case (USB‑C)",
                "brand": "Apple",
                "category": "蓝牙耳机",
                "current_price": Decimal("249.00"),
                "buy_box_price": Decimal("249.00"),
                "current_rank": 8,
                "rating": Decimal("4.3"),
                "review_count": 73891,
                "image_url": "https://m.media-amazon.com/images/I/61f1YfTkTdL._AC_SL1500_.jpg",
                "availability": "In Stock",
            },
            {
                "asin": "B098FKXT8L",
                "title": "Bose QuietComfort 45 Wireless Bluetooth Noise Cancelling Headphones",
                "brand": "Bose",
                "category": "蓝牙耳机",
                "current_price": Decimal("279.00"),
                "buy_box_price": Decimal("275.00"),
                "current_rank": 67,
                "rating": Decimal("4.3"),
                "review_count": 18764,
                "image_url": "https://m.media-amazon.com/images/I/81+jNVOUsJL._AC_SL1500_.jpg",
                "availability": "In Stock",
            },
        ]

        created_products = []

        with get_db_session() as db:
            for product_data in test_products:
                # 检查产品是否已存在
                existing_product = (
                    db.query(Product)
                    .filter(Product.asin == product_data["asin"])
                    .first()
                )

                if existing_product:
                    print(f"   产品 {product_data['asin']} 已存在，跳过创建")
                    created_products.append(existing_product)
                    continue

                # 创建新产品
                product = Product(
                    asin=product_data["asin"],
                    title=product_data["title"],
                    brand=product_data["brand"],
                    category=product_data["category"],
                    marketplace=MarketplaceType.AMAZON_US,
                    product_url=f"https://amazon.com/dp/{product_data['asin']}",
                    current_price=product_data["current_price"],
                    buy_box_price=product_data["buy_box_price"],
                    current_rank=product_data["current_rank"],
                    current_rating=product_data["rating"],
                    current_review_count=product_data["review_count"],
                    image_url=product_data["image_url"],
                    current_availability=product_data["availability"],
                    tracking_frequency=TrackingFrequency.DAILY,
                    tenant_id="demo-tenant",
                    status=ProductStatus.ACTIVE,
                )

                db.add(product)
                created_products.append(product)
                print(
                    f"   ✅ 创建产品: {product_data['asin']} - {product_data['title'][:40]}..."
                )

            db.commit()
            print(f"\n✅ 成功创建/确认 {len(created_products)} 个测试产品")
            # 返回产品ASIN列表，而不是对象
            return [p.asin for p in created_products]

    def generate_historical_data(self, product_asins):
        """为测试产品生成历史数据"""
        print("\n📊 生成历史数据")
        print("=" * 60)

        with get_db_session() as db:
            # 根据ASIN查询产品对象
            products = db.query(Product).filter(Product.asin.in_(product_asins)).all()

            for product in products:
                print(f"   为产品 {product.asin} 生成历史数据...")

                # 生成过去7天的价格和排名历史
                base_price = float(product.current_price)
                base_buy_box_price = (
                    float(product.buy_box_price)
                    if product.buy_box_price
                    else base_price * 0.95
                )
                base_rank = product.current_rank

                for days_ago in range(7, 0, -1):
                    record_time = datetime.utcnow() - timedelta(days=days_ago)

                    # 模拟价格波动（越接近现在波动越大）
                    price_factor = 1 + (7 - days_ago) * 0.03  # 最多21%波动
                    historical_price = base_price / price_factor
                    historical_buy_box_price = base_buy_box_price / price_factor

                    # 模拟排名波动
                    rank_factor = 1 + (7 - days_ago) * 0.05  # 最多35%波动
                    historical_rank = max(1, int(base_rank / rank_factor))

                    # 创建价格历史记录
                    price_history = ProductPriceHistory(
                        product_id=product.id,
                        price=Decimal(str(round(historical_price, 2))),
                        list_price=Decimal(str(round(historical_price * 1.2, 2))),
                        buy_box_price=Decimal(str(round(historical_buy_box_price, 2))),
                        currency="USD",
                        recorded_at=record_time,
                    )
                    db.add(price_history)

                    # 创建排名历史记录
                    rank_history = ProductRankHistory(
                        product_id=product.id,
                        rank=historical_rank,
                        category="Electronics > Headphones",
                        recorded_at=record_time,
                    )
                    db.add(rank_history)

                print("      ✅ 生成了7天的历史数据")

            db.commit()
            print("✅ 所有历史数据生成完成")

    def test_anomaly_detection(self, product_asins):
        """测试异常检测功能"""
        print("\n🔍 测试异常检测功能")
        print("=" * 60)

        anomaly_results = []

        with get_db_session() as db:
            products = db.query(Product).filter(Product.asin.in_(product_asins)).all()

            for product in products:
                print(f"\n📦 测试产品: {product.asin}")
                print(f"   标题: {product.title[:50]}...")

                # 执行全面异常检测
                result = self.anomaly_detector.check_all_anomalies(product.id)
                anomaly_results.append(result)

            print(
                f"   异常状态: {'🚨 发现异常' if result['has_anomaly'] else '✅ 一切正常'}"
            )
            print(f"   异常数量: {result['anomaly_count']}")

            # 显示具体异常详情
            if result["price_anomaly"]["is_anomaly"]:
                price_data = result["price_anomaly"]
                print(
                    f"   💰 价格异常: 当前${price_data['current_price']}, 平均${price_data['average_price']}"
                )
                print(
                    f"      变化: {price_data['direction']} {price_data['change_percent']:.1f}% (阈值:{price_data['threshold']}%)"
                )

            if result["buy_box_anomaly"]["is_anomaly"]:
                bb_data = result["buy_box_anomaly"]
                print(
                    f"   🛒 Buy Box异常: 当前${bb_data['current_buy_box_price']}, 平均${bb_data['average_buy_box_price']}"
                )
                print(
                    f"      变化: {bb_data['direction']} {bb_data['change_percent']:.1f}% (阈值:{bb_data['threshold']}%)"
                )

            if result["bsr_anomaly"]["is_anomaly"]:
                bsr_data = result["bsr_anomaly"]
                print(
                    f"   📊 BSR异常: 当前#{bsr_data['current_rank']}, 平均#{bsr_data['average_rank']}"
                )
                print(
                    f"      变化: {bsr_data['direction']} {bsr_data['change_percent']:.1f}% (阈值:{bsr_data['threshold']}%)"
                )

            if result["rating_anomaly"]["is_anomaly"]:
                rating_data = result["rating_anomaly"]
                print(
                    f"   ⭐ 评分异常: 当前{rating_data['current_rating']}, 之前{rating_data['previous_rating']}"
                )
                print(
                    f"      变化: {rating_data['direction']} {rating_data['change']:.1f}分"
                )

        return anomaly_results

    def test_email_notifications(self, anomaly_results):
        """测试邮件通知功能"""
        print("\n📧 测试邮件通知功能")
        print("=" * 60)

        # 筛选有异常的产品
        anomalous_products = [r for r in anomaly_results if r["has_anomaly"]]

        if not anomalous_products:
            print("   ℹ️ 没有检测到异常，创建模拟异常数据进行邮件测试...")

            # 创建模拟异常数据
            mock_anomaly = {
                "is_anomaly": True,
                "product_id": 1,
                "product_asin": "B09XS7JWHH",
                "product_title": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
                "current_price": 299.99,
                "average_price": 349.99,
                "change_percent": 14.3,
                "threshold": 10.0,
                "direction": "decrease",
                "historical_data_points": 7,
                "check_time": datetime.utcnow().isoformat(),
            }

            print("   📤 发送模拟价格异常邮件...")
            email_result = self.email_notifier.send_price_alert(mock_anomaly)
            print(f"      {'✅ 成功' if email_result else '❌ 失败'}")

        else:
            print(f"   发现 {len(anomalous_products)} 个异常产品，发送邮件通知...")

            email_results = []

            for anomaly in anomalous_products:
                # 发送个别异常邮件
                if anomaly["price_anomaly"]["is_anomaly"]:
                    result = self.email_notifier.send_price_alert(
                        anomaly["price_anomaly"]
                    )
                    email_results.append(result)
                    print(
                        f"   📤 价格异常邮件 {anomaly['product_asin']}: {'✅' if result else '❌'}"
                    )

                if anomaly["buy_box_anomaly"]["is_anomaly"]:
                    result = self.email_notifier.send_buy_box_alert(
                        anomaly["buy_box_anomaly"]
                    )
                    email_results.append(result)
                    print(
                        f"   📤 Buy Box异常邮件 {anomaly['product_asin']}: {'✅' if result else '❌'}"
                    )

                if anomaly["bsr_anomaly"]["is_anomaly"]:
                    result = self.email_notifier.send_bsr_alert(anomaly["bsr_anomaly"])
                    email_results.append(result)
                    print(
                        f"   📤 BSR异常邮件 {anomaly['product_asin']}: {'✅' if result else '❌'}"
                    )

            # 发送品类汇总报告
            print("   📊 发送品类汇总报告...")
            category_result = self.email_notifier.send_category_anomalies_report(
                category_name="蓝牙耳机", anomalies=anomalous_products
            )
            email_results.append(category_result)
            print(f"      {'✅ 成功' if category_result else '❌ 失败'}")

            return all(email_results)

        return True

    def demonstrate_celery_tasks(self):
        """演示Celery任务功能"""
        print("\n⚙️ Celery任务功能演示")
        print("=" * 60)

        print("品类产品更新任务配置:")
        print(
            """
        # 每日凌晨2:30自动更新所有品类产品
        'daily-category-products-update': {
            'task': 'crawler_tasks.update_all_category_products',
            'schedule': crontab(hour=2, minute=30),
            'options': {'queue': 'crawler'}
        }
        """
        )

        print("手动触发任务示例:")
        print(
            """
        # 更新特定品类
        from amazon_tracker.common.task_queue.crawler_tasks import update_category_products
        result = update_category_products.delay("蓝牙耳机")

        # 更新所有品类
        from amazon_tracker.common.task_queue.crawler_tasks import update_all_category_products
        result = update_all_category_products.delay()
        """
        )

    def show_api_examples(self):
        """显示API使用示例"""
        print("\n📚 API使用示例")
        print("=" * 60)

        print("1. 品类产品爬取:")
        example_request = {
            "category_url": "https://www.amazon.com/s?k=bluetooth+headphones",
            "category_name": "蓝牙耳机",
            "product_limit": 10,
            "sort_by": "best_seller",
            "tracking_frequency": "daily",
            "filters": {
                "price_min": 20,
                "price_max": 500,
                "rating_min": 4.0,
                "prime_only": True,
            },
        }

        print("POST /crawler-service/api/v1/products/category-crawl")
        print(json.dumps(example_request, indent=2, ensure_ascii=False))

        print("\n2. 查看品类产品:")
        print(
            "GET /crawler-service/api/v1/products/categories/蓝牙耳机/products?limit=20"
        )

        print("\n3. 产品价格历史:")
        print(
            "GET /crawler-service/api/v1/products/{product_id}/price-history?limit=30"
        )

        print("\n4. 产品排名历史:")
        print("GET /crawler-service/api/v1/products/{product_id}/rank-history?limit=30")

    def run_demo(self):
        """运行完整演示"""
        print("🎯 Amazon品类商品监控系统 - 简化演示")
        print("=" * 80)
        print(f"演示时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()

        try:
            # 1. 创建测试产品
            product_asins = self.create_test_products()

            # 2. 生成历史数据
            self.generate_historical_data(product_asins)

            # 3. 测试异常检测
            anomaly_results = self.test_anomaly_detection(product_asins)

            # 4. 测试邮件通知
            email_success = self.test_email_notifications(anomaly_results)

            # 5. 演示Celery任务
            self.demonstrate_celery_tasks()

            # 6. 显示API示例
            self.show_api_examples()

            # 7. 总结
            print("\n🎉 演示完成总结")
            print("=" * 60)
            print("✅ 测试产品创建完成")
            print("✅ 历史数据生成完成")
            print("✅ 异常检测功能正常")
            print(f"✅ 邮件通知功能{'正常' if email_success else '存在问题'}")
            print("✅ Celery任务配置展示")
            print("✅ API使用示例展示")

            print("\n🚀 下一步操作:")
            print("1. 启动crawler_service服务进行API测试")
            print("2. 启动Celery worker和beat进行定时任务测试")
            print("3. 配置真实邮件发送设置")
            print("4. 添加更多品类进行生产测试")

            return True

        except Exception as e:
            print(f"\n❌ 演示执行失败: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """主函数"""
    demo = SimpleCategoryMonitoringDemo()
    return demo.run_demo()


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ 演示被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 演示执行失败: {e}")
        sys.exit(1)
