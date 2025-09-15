#!/usr/bin/env python3
"""初始化Demo数据脚本 - 批量导入蓝牙耳机产品"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from amazon_tracker.common.crawlers.apify_client import ApifyAmazonScraper
from amazon_tracker.common.database.connection import get_db_session
from amazon_tracker.common.database.models.product import (
    MarketplaceType,
    Product,
    ProductPriceHistory,
    ProductRankHistory,
    ProductStatus,
    TrackingFrequency,
)
from amazon_tracker.common.database.models.tenant import Tenant
from amazon_tracker.common.database.models.user import User


class DemoDataInitializer:
    """Demo数据初始化器"""

    def __init__(self):
        self.scraper = ApifyAmazonScraper()

        # 预选的蓝牙耳机产品ASIN列表（涵盖不同价位和品牌）
        self.bluetooth_headphones = [
            {
                "asin": "B09XS7JWHH",
                "name": "Sony WH-1000XM5",
                "brand": "Sony",
                "category": "bluetooth-headphones",
                "estimated_price": 300,
            },
            {
                "asin": "B0BDHWDR12",
                "name": "Apple AirPods Pro (2nd Gen)",
                "brand": "Apple",
                "category": "bluetooth-earbuds",
                "estimated_price": 250,
            },
            {
                "asin": "B098FKXT8L",
                "name": "Bose QuietComfort 45",
                "brand": "Bose",
                "category": "bluetooth-headphones",
                "estimated_price": 280,
            },
            {
                "asin": "B08WM3LMJF",
                "name": "JBL Tune 510BT",
                "brand": "JBL",
                "category": "bluetooth-headphones",
                "estimated_price": 40,
            },
            {
                "asin": "B07NM3RSRQ",
                "name": "Anker Soundcore Life Q20",
                "brand": "Anker",
                "category": "bluetooth-headphones",
                "estimated_price": 60,
            },
            {
                "asin": "B075G56CDY",
                "name": "Beats Studio3 Wireless",
                "brand": "Beats",
                "category": "bluetooth-headphones",
                "estimated_price": 200,
            },
            {
                "asin": "B0B8QZ9FYB",
                "name": "Sennheiser Momentum 4",
                "brand": "Sennheiser",
                "category": "bluetooth-headphones",
                "estimated_price": 350,
            },
            {
                "asin": "B07RGZ5NKS",
                "name": "TOZO T6 True Wireless",
                "brand": "TOZO",
                "category": "bluetooth-earbuds",
                "estimated_price": 30,
            },
            {
                "asin": "B0B2SH4CN6",
                "name": "Samsung Galaxy Buds2 Pro",
                "brand": "Samsung",
                "category": "bluetooth-earbuds",
                "estimated_price": 150,
            },
            {
                "asin": "B07Q2T2CKG",
                "name": "Bose Noise Cancelling Headphones 700",
                "brand": "Bose",
                "category": "bluetooth-headphones",
                "estimated_price": 320,
            },
        ]

    async def create_demo_tenant_and_user(self) -> tuple[str, str]:
        """创建Demo租户和用户"""

        with get_db_session() as db:
            # 检查是否已存在Demo租户
            demo_tenant = db.query(Tenant).filter(Tenant.name == "Demo Company").first()

            if not demo_tenant:
                # 创建Demo租户
                demo_tenant = Tenant(
                    name="Demo Company",
                    subdomain="demo",
                    api_key="demo_api_key_12345",
                    plan_type="premium",
                    max_products=100,
                    max_users=10,
                    status="active",
                )
                db.add(demo_tenant)
                db.flush()
                print(f"✅ 创建Demo租户: {demo_tenant.name}")
            else:
                print(f"📋 使用现有Demo租户: {demo_tenant.name}")

            # 检查是否已存在Demo用户
            demo_user = db.query(User).filter(User.email == "demo@example.com").first()

            if not demo_user:
                # 创建Demo用户
                demo_user = User(
                    tenant_id=demo_tenant.id,
                    email="demo@example.com",
                    username="demo_user",
                    password_hash="$2b$12$dummy_hash_for_demo",  # 仅用于演示
                    role="admin",
                    status="active",
                )
                db.add(demo_user)
                db.flush()
                print(f"✅ 创建Demo用户: {demo_user.email}")
            else:
                print(f"📋 使用现有Demo用户: {demo_user.email}")

            db.commit()
            return str(demo_tenant.id), str(demo_user.id)

    async def crawl_and_import_product(
        self, product_info: dict, tenant_id: str, user_id: str
    ) -> bool:
        """爬取并导入单个产品"""

        try:
            print(
                f"🔄 开始爬取产品: {product_info['name']} (ASIN: {product_info['asin']})"
            )

            # 使用Apify爬取产品数据
            result = await self.scraper.scrape_single_product(
                asin=product_info["asin"], country="US"
            )

            if not result.success:
                print(f"❌ 爬取失败: {product_info['asin']} - {result.error}")
                return False

            products_data = result.data.get("products", [])
            if not products_data:
                print(f"❌ 未获取到产品数据: {product_info['asin']}")
                return False

            product_data = products_data[0]  # 取第一个产品数据

            # 保存到数据库
            with get_db_session() as db:
                # 检查产品是否已存在
                existing_product = (
                    db.query(Product)
                    .filter(
                        Product.asin == product_info["asin"],
                        Product.tenant_id == tenant_id,
                    )
                    .first()
                )

                if existing_product:
                    print(f"📋 产品已存在，更新数据: {product_info['asin']}")
                    product = existing_product
                else:
                    # 创建新产品
                    product = Product(
                        asin=product_info["asin"],
                        tenant_id=tenant_id,
                        created_by=user_id,
                        marketplace=MarketplaceType.AMAZON_US,
                        tracking_frequency=TrackingFrequency.DAILY,
                        status=ProductStatus.ACTIVE,
                    )
                    db.add(product)
                    db.flush()
                    print(f"✅ 创建新产品: {product_info['asin']}")

                # 更新产品信息
                product.title = product_data.get("title", product_info["name"])
                product.brand = product_data.get("brand", product_info["brand"])
                product.category = product_info["category"]
                product.current_price = product_data.get("price")
                product.current_rating = product_data.get("rating")
                product.current_review_count = product_data.get("review_count", 0)
                product.current_rank = product_data.get("rank")
                product.image_url = product_data.get("image_url")
                product.current_availability = product_data.get("availability")
                product.product_data = product_data
                product.last_scraped_at = datetime.utcnow()

                # 创建价格历史记录
                if product_data.get("price"):
                    price_history = ProductPriceHistory(
                        product_id=product.id,
                        price=product_data["price"],
                        list_price=product_data.get("list_price"),
                        currency="USD",
                        recorded_at=datetime.utcnow(),
                    )
                    db.add(price_history)

                    # 创建一些模拟历史数据（过去30天）
                    await self._create_mock_price_history(
                        db, product.id, product_data["price"]
                    )

                # 创建排名历史记录
                if product_data.get("rank"):
                    rank_history = ProductRankHistory(
                        product_id=product.id,
                        rank=product_data["rank"],
                        category=product_info["category"],
                        rating=product_data.get("rating"),
                        review_count=product_data.get("review_count", 0),
                        recorded_at=datetime.utcnow(),
                    )
                    db.add(rank_history)

                    # 创建一些模拟历史数据
                    await self._create_mock_rank_history(
                        db, product.id, product_data.get("rank")
                    )

                db.commit()
                print(f"✅ 产品数据保存成功: {product_info['name']}")
                return True

        except Exception as e:
            print(f"❌ 处理产品时发生错误 {product_info['asin']}: {e}")
            return False

    async def _create_mock_price_history(
        self, db, product_id: int, current_price: float
    ):
        """创建模拟价格历史数据"""

        import random

        # 生成过去30天的价格数据
        for days_ago in range(30, 0, -1):
            # 价格在当前价格的±15%范围内波动
            variation = random.uniform(-0.15, 0.15)
            historical_price = current_price * (1 + variation)
            historical_price = max(
                historical_price, current_price * 0.7
            )  # 最低不低于70%

            price_history = ProductPriceHistory(
                product_id=product_id,
                price=round(historical_price, 2),
                currency="USD",
                recorded_at=datetime.utcnow() - timedelta(days=days_ago),
            )
            db.add(price_history)

    async def _create_mock_rank_history(self, db, product_id: int, current_rank: int):
        """创建模拟排名历史数据"""

        import random

        if not current_rank:
            return

        # 生成过去30天的排名数据
        for days_ago in range(30, 0, -1):
            # 排名在当前排名的±30%范围内波动
            variation = random.uniform(-0.3, 0.3)
            historical_rank = int(current_rank * (1 + variation))
            historical_rank = max(historical_rank, 1)  # 排名不低于1

            rank_history = ProductRankHistory(
                product_id=product_id,
                rank=historical_rank,
                recorded_at=datetime.utcnow() - timedelta(days=days_ago),
            )
            db.add(rank_history)

    async def import_all_products(self):
        """批量导入所有产品"""

        print("🚀 开始初始化Demo数据...")
        print(f"📋 计划导入 {len(self.bluetooth_headphones)} 个蓝牙耳机产品")

        # 创建租户和用户
        tenant_id, user_id = await self.create_demo_tenant_and_user()

        success_count = 0
        failed_products = []

        # 逐个导入产品
        for i, product_info in enumerate(self.bluetooth_headphones, 1):
            print(
                f"\n📦 [{i}/{len(self.bluetooth_headphones)}] 处理产品: {product_info['name']}"
            )

            try:
                success = await self.crawl_and_import_product(
                    product_info, tenant_id, user_id
                )

                if success:
                    success_count += 1
                else:
                    failed_products.append(product_info["asin"])

                # 添加延迟避免被限流
                await asyncio.sleep(2)

            except Exception as e:
                print(f"❌ 产品 {product_info['asin']} 导入失败: {e}")
                failed_products.append(product_info["asin"])

        # 输出结果总结
        print("\n🎉 Demo数据初始化完成!")
        print(f"✅ 成功导入: {success_count} 个产品")
        print(f"❌ 导入失败: {len(failed_products)} 个产品")

        if failed_products:
            print(f"失败的ASIN: {', '.join(failed_products)}")

        print("\n📊 Demo账户信息:")
        print("  - 租户: Demo Company")
        print("  - 用户: demo@example.com")
        print("  - API密钥: demo_api_key_12345")

    async def cleanup_demo_data(self):
        """清理Demo数据"""

        print("🧹 清理Demo数据...")

        with get_db_session() as db:
            # 删除Demo租户相关的所有数据
            demo_tenant = db.query(Tenant).filter(Tenant.name == "Demo Company").first()

            if demo_tenant:
                # 由于外键约束，删除租户会级联删除相关数据
                db.delete(demo_tenant)
                db.commit()
                print("✅ Demo数据清理完成")
            else:
                print("📋 没有找到Demo数据")


async def main():
    """主函数"""

    import argparse

    parser = argparse.ArgumentParser(description="Amazon产品追踪系统 Demo数据初始化")
    parser.add_argument(
        "--action",
        choices=["init", "cleanup"],
        default="init",
        help="操作类型: init(初始化数据) 或 cleanup(清理数据)",
    )

    args = parser.parse_args()

    initializer = DemoDataInitializer()

    if args.action == "init":
        await initializer.import_all_products()
    elif args.action == "cleanup":
        await initializer.cleanup_demo_data()


if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容）
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 运行主函数
    asyncio.run(main())
