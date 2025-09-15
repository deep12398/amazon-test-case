#!/usr/bin/env python3
"""品类商品监控功能演示和测试脚本"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from amazon_tracker.common.crawlers.category_extractor import category_to_asins
from amazon_tracker.common.database.connection import get_db_session
from amazon_tracker.common.database.models.product import (
    Product,
    ProductPriceHistory,
    ProductRankHistory,
)
from amazon_tracker.common.notification.email_service import EmailNotifier
from amazon_tracker.services.monitoring.anomaly_detector import AnomalyDetector


class CategoryMonitoringDemo:
    """品类商品监控演示类"""

    def __init__(self):
        self.anomaly_detector = AnomalyDetector()
        self.email_notifier = EmailNotifier()

        # 测试用的品类URL列表
        self.test_categories = [
            {
                "name": "蓝牙耳机",
                "url": "https://www.amazon.com/s?k=bluetooth+headphones&ref=sr_pg_1",
                "description": "蓝牙无线耳机品类",
            },
            {
                "name": "无线鼠标",
                "url": "https://www.amazon.com/s?k=wireless+mouse&ref=sr_pg_1",
                "description": "无线电脑鼠标品类",
            },
            {
                "name": "智能手表",
                "url": "https://www.amazon.com/s?k=smart+watch&ref=sr_pg_1",
                "description": "智能可穿戴手表品类",
            },
        ]

    async def demo_category_extraction(self):
        """演示品类产品提取功能"""
        print("🚀 演示1: 品类产品提取功能")
        print("=" * 60)

        # 选择第一个测试品类
        category = self.test_categories[0]
        print(f"测试品类: {category['name']}")
        print(f"测试URL: {category['url']}")

        try:
            # 提取品类产品
            result = await category_to_asins(
                category_url=category["url"],
                product_limit=10,
                sort_by="best_seller",
                filters={"price_min": 20, "price_max": 500, "rating_min": 4.0},
            )

            if result["success"]:
                print(f"✅ 成功提取 {len(result['asins'])} 个产品")
                print(f"品类名称: {result['category_name']}")

                # 显示前5个产品信息
                print("\n🏆 Top 5 产品信息:")
                for i, product in enumerate(result["products"][:5], 1):
                    print(f"  {i}. {product['asin']} - {product['title'][:50]}...")
                    print(
                        f"     价格: ${product.get('price', 'N/A')} | 评分: {product.get('rating', 'N/A')} | 排名: #{product.get('rank', 'N/A')}"
                    )
                    if product.get("buy_box_price"):
                        print(f"     Buy Box价格: ${product['buy_box_price']}")

                return result

            else:
                print(f"❌ 品类产品提取失败: {result['error']}")
                return None

        except Exception as e:
            print(f"❌ 品类产品提取异常: {e}")
            return None

    def demo_anomaly_detection(self):
        """演示异常检测功能"""
        print("\n🔍 演示2: 异常检测功能")
        print("=" * 60)

        # 模拟产品数据进行异常检测测试
        with get_db_session() as db:
            # 查找一些测试产品
            test_products = (
                db.query(Product).filter(Product.is_active == True).limit(3).all()
            )

            if not test_products:
                print("❌ 没有找到可测试的产品数据")
                return False

            print(f"找到 {len(test_products)} 个测试产品")

            for product in test_products:
                print(f"\n📦 测试产品: {product.asin} - {product.title[:40]}...")

                # 执行全面异常检测
                anomaly_result = self.anomaly_detector.check_all_anomalies(product.id)

                print(
                    f"   异常状态: {'🚨 有异常' if anomaly_result['has_anomaly'] else '✅ 正常'}"
                )
                print(f"   异常数量: {anomaly_result['anomaly_count']}")

                # 显示各类异常详情
                if anomaly_result["price_anomaly"]["is_anomaly"]:
                    price_data = anomaly_result["price_anomaly"]
                    print(
                        f"   💰 价格异常: {price_data['direction']} {price_data['change_percent']:.1f}%"
                    )

                if anomaly_result["buy_box_anomaly"]["is_anomaly"]:
                    bb_data = anomaly_result["buy_box_anomaly"]
                    print(
                        f"   🛒 Buy Box异常: {bb_data['direction']} {bb_data['change_percent']:.1f}%"
                    )

                if anomaly_result["bsr_anomaly"]["is_anomaly"]:
                    bsr_data = anomaly_result["bsr_anomaly"]
                    print(
                        f"   📊 BSR异常: {bsr_data['direction']} {bsr_data['change_percent']:.1f}%"
                    )

                if anomaly_result["rating_anomaly"]["is_anomaly"]:
                    rating_data = anomaly_result["rating_anomaly"]
                    print(
                        f"   ⭐ 评分异常: {rating_data['direction']} {rating_data['change']:.1f}分"
                    )

        return True

    def demo_email_notifications(self):
        """演示邮件通知功能"""
        print("\n📧 演示3: 邮件通知功能")
        print("=" * 60)

        # 模拟异常数据进行邮件测试
        mock_price_anomaly = {
            "is_anomaly": True,
            "product_id": 1,
            "product_asin": "B09XS7JWHH",
            "product_title": "Sony WH-1000XM5 Wireless Industry Leading Noise Canceling Headphones",
            "current_price": 329.99,
            "average_price": 349.99,
            "change_percent": 15.8,
            "threshold": 10.0,
            "direction": "decrease",
            "historical_data_points": 7,
            "check_time": datetime.utcnow().isoformat(),
        }

        mock_buy_box_anomaly = {
            "is_anomaly": True,
            "product_id": 1,
            "product_asin": "B09XS7JWHH",
            "product_title": "Sony WH-1000XM5 Wireless Industry Leading Noise Canceling Headphones",
            "current_buy_box_price": 319.99,
            "average_buy_box_price": 349.99,
            "change_percent": 18.5,
            "threshold": 15.0,
            "direction": "decrease",
            "historical_data_points": 7,
            "check_time": datetime.utcnow().isoformat(),
        }

        mock_category_anomalies = [
            {
                "product_id": 1,
                "product_asin": "B09XS7JWHH",
                "product_title": "Sony WH-1000XM5 Wireless Headphones",
                "has_anomaly": True,
                "anomaly_count": 2,
                "price_anomaly": mock_price_anomaly,
                "buy_box_anomaly": mock_buy_box_anomaly,
                "bsr_anomaly": {"is_anomaly": False},
                "rating_anomaly": {"is_anomaly": False},
                "check_time": datetime.utcnow().isoformat(),
            },
            {
                "product_id": 2,
                "product_asin": "B0BDHWDR12",
                "product_title": "Apple AirPods Pro (2nd Generation)",
                "has_anomaly": True,
                "anomaly_count": 1,
                "price_anomaly": {"is_anomaly": False},
                "buy_box_anomaly": {"is_anomaly": False},
                "bsr_anomaly": {
                    "is_anomaly": True,
                    "current_rank": 15,
                    "average_rank": 8,
                    "change_percent": 35.2,
                    "direction": "worse",
                },
                "rating_anomaly": {"is_anomaly": False},
                "check_time": datetime.utcnow().isoformat(),
            },
        ]

        print("📤 测试邮件通知功能...")

        # 测试单个价格异常邮件
        print("   1. 发送价格异常预警邮件...")
        price_result = self.email_notifier.send_price_alert(mock_price_anomaly)
        print(f"      {'✅ 成功' if price_result else '❌ 失败'}")

        # 测试Buy Box异常邮件
        print("   2. 发送Buy Box异常预警邮件...")
        bb_result = self.email_notifier.send_buy_box_alert(mock_buy_box_anomaly)
        print(f"      {'✅ 成功' if bb_result else '❌ 失败'}")

        # 测试品类异常汇总报告
        print("   3. 发送品类异常汇总报告...")
        category_result = self.email_notifier.send_category_anomalies_report(
            category_name="蓝牙耳机", anomalies=mock_category_anomalies
        )
        print(f"      {'✅ 成功' if category_result else '❌ 失败'}")

        return all([price_result, bb_result, category_result])

    def simulate_historical_data(self):
        """模拟历史数据以便测试异常检测"""
        print("\n🗄️ 模拟历史数据生成")
        print("=" * 60)

        with get_db_session() as db:
            # 查找测试产品
            product = db.query(Product).filter(Product.is_active == True).first()

            if not product:
                print("❌ 没有找到可用的测试产品")
                return False

            print(f"为产品 {product.asin} 生成模拟历史数据...")

            # 生成过去7天的价格历史数据
            base_price = 100.0
            base_rank = 50

            for days_ago in range(7, 0, -1):
                record_time = datetime.utcnow() - timedelta(days=days_ago)

                # 模拟价格波动
                price_variation = base_price * (1 + (days_ago - 4) * 0.02)  # ±6%波动
                buy_box_variation = price_variation * 0.95  # Buy Box通常稍低
                rank_variation = base_rank + (days_ago - 4) * 5  # 排名波动

                # 创建价格历史记录
                price_history = ProductPriceHistory(
                    product_id=product.id,
                    price=price_variation,
                    list_price=price_variation * 1.2,
                    buy_box_price=buy_box_variation,
                    currency="USD",
                    recorded_at=record_time,
                )
                db.add(price_history)

                # 创建排名历史记录
                rank_history = ProductRankHistory(
                    product_id=product.id,
                    rank=max(1, int(rank_variation)),
                    category="Electronics",
                    recorded_at=record_time,
                )
                db.add(rank_history)

            # 更新产品当前数据 - 创建明显的异常
            product.current_price = base_price * 0.8  # 价格下降20% (>10%阈值)
            product.buy_box_price = base_price * 0.82  # Buy Box价格下降18% (>15%阈值)
            product.current_rank = base_rank * 1.4  # 排名恶化40% (>30%阈值)

            db.commit()
            print("✅ 历史数据模拟完成，包含明显的异常变化")
            return True

    async def run_full_demo(self):
        """运行完整演示"""
        print("🎯 Amazon品类商品监控系统 - 完整演示")
        print("=" * 80)
        print(f"开始时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()

        demo_results = {}

        # 1. 品类产品提取演示
        extraction_result = await self.demo_category_extraction()
        demo_results["extraction"] = extraction_result is not None

        # 2. 生成模拟历史数据
        historical_data_result = self.simulate_historical_data()
        demo_results["historical_data"] = historical_data_result

        # 3. 异常检测演示
        anomaly_result = self.demo_anomaly_detection()
        demo_results["anomaly_detection"] = anomaly_result

        # 4. 邮件通知演示
        email_result = self.demo_email_notifications()
        demo_results["email_notifications"] = email_result

        # 5. 总结报告
        print("\n📋 演示结果总结")
        print("=" * 60)

        total_tests = len(demo_results)
        passed_tests = sum(1 for result in demo_results.values() if result)

        for test_name, result in demo_results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {test_name.replace('_', ' ').title()}: {status}")

        print(f"\n🎯 总体结果: {passed_tests}/{total_tests} 个测试通过")

        if passed_tests == total_tests:
            print("🎉 所有功能演示成功！品类商品监控系统运行正常")

            print("\n🚀 下一步操作建议:")
            print("   1. 启动crawler_service服务测试API接口")
            print("   2. 启动Celery worker和beat进行定时任务测试")
            print("   3. 配置真实的品类URL进行生产环境测试")
            print("   4. 设置邮件通知接收地址")

        else:
            print("⚠️ 部分功能存在问题，请检查配置和依赖")

        return passed_tests == total_tests

    def display_usage_examples(self):
        """显示使用示例"""
        print("\n📖 API使用示例")
        print("=" * 60)

        print("1. 品类产品爬取API:")
        print(
            """
        POST /crawler-service/api/v1/products/category-crawl
        {
            "category_url": "https://www.amazon.com/s?k=bluetooth+headphones",
            "category_name": "蓝牙耳机",
            "product_limit": 10,
            "sort_by": "best_seller",
            "tracking_frequency": "daily",
            "filters": {
                "price_min": 20,
                "price_max": 500,
                "rating_min": 4.0
            }
        }
        """
        )

        print("2. 查看品类产品:")
        print(
            """
        GET /crawler-service/api/v1/products/categories/蓝牙耳机/products?limit=20
        """
        )

        print("3. 手动触发品类更新:")
        print(
            """
        # Python代码
        from amazon_tracker.common.task_queue.crawler_tasks import update_category_products

        result = update_category_products.delay("蓝牙耳机")
        """
        )


async def main():
    """主函数"""
    demo = CategoryMonitoringDemo()

    # 显示使用示例
    demo.display_usage_examples()

    # 运行完整演示
    success = await demo.run_full_demo()

    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ 演示被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 演示执行失败: {e}")
        sys.exit(1)
