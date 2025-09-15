#!/usr/bin/env python3
"""创建测试产品和分类数据"""

import asyncio
import json
import secrets
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def create_test_data():
    """创建测试数据"""

    DATABASE_URL = "postgresql+asyncpg://postgres:your-password@db.your-project.supabase.co:5432/postgres"

    print("🧪 开始创建测试数据...")

    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        async with engine.begin() as conn:
            # 获取现有租户和用户ID
            tenants_result = await conn.execute(
                text("SELECT tenant_id, name FROM tenants ORDER BY created_at")
            )
            tenants = [(str(row[0]), str(row[1])) for row in tenants_result]

            users_result = await conn.execute(
                text("SELECT id, tenant_id, email FROM users ORDER BY created_at")
            )
            users = [(row[0], str(row[1]), str(row[2])) for row in users_result]

            if not tenants or not users:
                print("❌ 未找到租户或用户数据，请先运行种子数据脚本")
                return False

            print(f"📋 找到 {len(tenants)} 个租户，{len(users)} 个用户")

            # 1. 创建品类数据
            print("🏷️ 创建品类数据...")

            categories_data = [
                {
                    "tenant_id": tenants[0][0],  # 演示租户
                    "name": "蓝牙耳机",
                    "keywords": ["bluetooth", "headphones", "wireless", "earbuds"],
                    "auto_crawl": True,
                    "crawl_schedule": "daily",
                },
                {
                    "tenant_id": tenants[0][0],
                    "name": "智能手机",
                    "keywords": ["smartphone", "phone", "mobile", "android", "iphone"],
                    "auto_crawl": True,
                    "crawl_schedule": "daily",
                },
                {
                    "tenant_id": tenants[1][0]
                    if len(tenants) > 1
                    else tenants[0][0],  # 企业租户
                    "name": "笔记本电脑",
                    "keywords": ["laptop", "notebook", "computer", "gaming"],
                    "auto_crawl": True,
                    "crawl_schedule": "daily",
                },
                {
                    "tenant_id": tenants[0][0],
                    "name": "智能手表",
                    "keywords": ["smartwatch", "wearable", "fitness", "watch"],
                    "auto_crawl": False,
                    "crawl_schedule": "weekly",
                },
            ]

            category_ids = []
            for cat_data in categories_data:
                result = await conn.execute(
                    text(
                        """
                    INSERT INTO categories (
                        tenant_id, name, keywords, auto_crawl, crawl_schedule
                    ) VALUES (
                        :tenant_id, :name, :keywords, :auto_crawl, :crawl_schedule
                    ) RETURNING id, category_id
                """
                    ),
                    cat_data,
                )

                row = result.fetchone()
                category_ids.append((row[0], str(row[1])))
                print(f"  ✓ {cat_data['name']} (ID: {str(row[1])[:8]}...)")

            # 2. 创建产品数据
            print("📦 创建产品数据...")

            products_data = [
                # 演示租户的产品
                {
                    "user_id": users[0][0],
                    "tenant_id": tenants[0][0],
                    "asin": "B08N5WRWNW",
                    "product_url": "https://amazon.com/dp/B08N5WRWNW",
                    "title": "Sony WH-1000XM4 Wireless Noise Canceling Headphones",
                    "brand": "Sony",
                    "category": "蓝牙耳机",
                    "status": "active",
                    "crawl_frequency": "daily",
                },
                {
                    "user_id": users[0][0],
                    "tenant_id": tenants[0][0],
                    "asin": "B08C1W5N87",
                    "product_url": "https://amazon.com/dp/B08C1W5N87",
                    "title": "Apple AirPods Pro (2nd Generation)",
                    "brand": "Apple",
                    "category": "蓝牙耳机",
                    "status": "active",
                    "crawl_frequency": "hourly",
                },
                {
                    "user_id": users[1][0] if len(users) > 1 else users[0][0],
                    "tenant_id": tenants[0][0],
                    "asin": "B0BDJ7HQZW",
                    "product_url": "https://amazon.com/dp/B0BDJ7HQZW",
                    "title": "iPhone 15 Pro Max, 256GB, Natural Titanium",
                    "brand": "Apple",
                    "category": "智能手机",
                    "status": "active",
                    "crawl_frequency": "daily",
                },
                {
                    "user_id": users[0][0],
                    "tenant_id": tenants[0][0],
                    "asin": "B0BC3RYNZM",
                    "product_url": "https://amazon.com/dp/B0BC3RYNZM",
                    "title": "Bose QuietComfort Earbuds",
                    "brand": "Bose",
                    "category": "蓝牙耳机",
                    "status": "paused",
                    "crawl_frequency": "weekly",
                },
            ]

            # 企业租户产品
            if len(tenants) > 1 and len(users) > 2:
                products_data.extend(
                    [
                        {
                            "user_id": users[2][0],
                            "tenant_id": tenants[1][0],
                            "asin": "B09SV2HQ5S",
                            "product_url": "https://amazon.com/dp/B09SV2HQ5S",
                            "title": "MacBook Pro 16-inch M2 Pro",
                            "brand": "Apple",
                            "category": "笔记本电脑",
                            "status": "active",
                            "crawl_frequency": "daily",
                        },
                        {
                            "user_id": users[2][0],
                            "tenant_id": tenants[1][0],
                            "asin": "B0B3PSRHHN",
                            "product_url": "https://amazon.com/dp/B0B3PSRHHN",
                            "title": "ASUS ROG Strix G16 Gaming Laptop",
                            "brand": "ASUS",
                            "category": "笔记本电脑",
                            "status": "active",
                            "crawl_frequency": "daily",
                        },
                    ]
                )

            product_ids = []
            for prod_data in products_data:
                result = await conn.execute(
                    text(
                        """
                    INSERT INTO products (
                        user_id, tenant_id, asin, product_url, title, brand, category, status, crawl_frequency
                    ) VALUES (
                        :user_id, :tenant_id, :asin, :product_url, :title, :brand, :category, :status, :crawl_frequency
                    ) RETURNING id, product_id
                """
                    ),
                    prod_data,
                )

                row = result.fetchone()
                product_ids.append((row[0], str(row[1]), prod_data))
                print(f"  ✓ {prod_data['title'][:50]}... (ASIN: {prod_data['asin']})")

            # 3. 创建产品追踪数据(历史数据)
            print("📊 创建产品历史数据...")

            for prod_id, prod_uuid, prod_data in product_ids[
                :3
            ]:  # 只为前3个产品创建历史数据
                for days_ago in range(30, 0, -1):  # 30天历史数据
                    tracking_date = (datetime.now() - timedelta(days=days_ago)).date()

                    # 模拟价格波动
                    base_price = 200 + (prod_id * 50)  # 基础价格
                    price_variation = (days_ago / 30.0) * 50 + (
                        secrets.randbelow(20) - 10
                    )
                    price = Decimal(str(round(base_price + price_variation, 2)))

                    # 模拟BSR变化
                    bsr = 5000 + secrets.randbelow(20000) - (30 - days_ago) * 100

                    # 模拟评分和评论数
                    rating = Decimal(
                        str(round(4.0 + (secrets.randbelow(10) / 10.0), 1))
                    )
                    review_count = (
                        10000 + secrets.randbelow(5000) + (30 - days_ago) * 10
                    )

                    tracking_data = {
                        "product_id": prod_id,
                        "tenant_id": prod_data["tenant_id"],
                        "tracking_date": tracking_date,
                        "price": price,
                        "bsr": bsr,
                        "rating": rating,
                        "review_count": review_count,
                        "buy_box_price": price + Decimal("5.99"),
                        "availability": "In Stock"
                        if secrets.randbelow(10) > 1
                        else "Temporarily out of stock",
                        "seller_name": f"{prod_data['brand']} Official Store",
                        "raw_data": json.dumps(
                            {
                                "currency": "USD",
                                "marketplace": "amazon.com",
                                "category_rank": bsr,
                                "scraped_at": tracking_date.isoformat(),
                            }
                        ),
                    }

                    await conn.execute(
                        text(
                            """
                        INSERT INTO product_tracking_data (
                            product_id, tenant_id, tracking_date, price, bsr, rating,
                            review_count, buy_box_price, availability, seller_name, raw_data
                        ) VALUES (
                            :product_id, :tenant_id, :tracking_date, :price, :bsr, :rating,
                            :review_count, :buy_box_price, :availability, :seller_name, :raw_data
                        ) ON CONFLICT (product_id, tracking_date) DO NOTHING
                    """
                        ),
                        tracking_data,
                    )

                print(f"  ✓ {prod_data['title'][:40]}... - 30天历史数据")

            # 4. 创建一些任务记录
            print("⚙️ 创建任务记录...")

            task_types = ["crawl", "analysis", "suggestion"]
            task_statuses = ["pending", "running", "completed", "failed"]

            for i in range(8):
                task_data = {
                    "tenant_id": tenants[i % len(tenants)][0],
                    "user_id": users[i % len(users)][0],
                    "task_type": task_types[i % len(task_types)],
                    "task_name": f"Auto {task_types[i % len(task_types)]} task #{i+1}",
                    "parameters": json.dumps(
                        {
                            "product_count": secrets.randbelow(10) + 1,
                            "priority": "normal",
                            "created_by": "system",
                        }
                    ),
                    "status": task_statuses[i % len(task_statuses)],
                    "priority": secrets.randbelow(5) + 1,
                    "progress": 100
                    if task_statuses[i % len(task_statuses)] == "completed"
                    else secrets.randbelow(80),
                    "started_at": None,
                    "completed_at": None,
                }

                # 设置时间
                if task_data["status"] in ["completed", "failed"]:
                    task_data["started_at"] = datetime.now() - timedelta(hours=2)
                    task_data["completed_at"] = datetime.now() - timedelta(hours=1)
                elif task_data["status"] == "running":
                    task_data["started_at"] = datetime.now() - timedelta(minutes=30)

                await conn.execute(
                    text(
                        """
                    INSERT INTO tasks (
                        tenant_id, user_id, task_type, task_name, parameters,
                        status, priority, progress, started_at, completed_at
                    ) VALUES (
                        :tenant_id, :user_id, :task_type, :task_name, :parameters,
                        :status, :priority, :progress, :started_at, :completed_at
                    )
                """
                    ),
                    task_data,
                )

                print(f"  ✓ {task_data['task_name']} - {task_data['status']}")

            print("\n✅ 测试数据创建完成!")

        await engine.dispose()
        return True

    except Exception as e:
        print(f"\n❌ 测试数据创建失败: {e}")
        await engine.dispose()
        return False


if __name__ == "__main__":
    success = asyncio.run(create_test_data())
    exit(0 if success else 1)
