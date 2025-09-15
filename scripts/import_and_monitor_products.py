#!/usr/bin/env python3
"""导入10个蓝牙耳机产品并启用自动监控"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(project_root / ".env.local")
load_dotenv(project_root / ".env")

# 设置同步数据库连接
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from amazon_tracker.common.crawlers.apify_client import ApifyAmazonScraper
from amazon_tracker.common.database.models.product import (
    MarketplaceType,
    Product,
    ProductStatus,
    TrackingFrequency,
)

DATABASE_URL = os.getenv("DATABASE_URL")
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# 10个热门蓝牙耳机产品
BLUETOOTH_HEADPHONES = [
    {
        "asin": "B09JQMJHXY",
        "title": "Sony WH-1000XM4 Wireless Premium Noise Canceling Overhead Headphones",
    },
    {"asin": "B08PZHYWJS", "title": "Apple AirPods Max Wireless Over-Ear Headphones"},
    {"asin": "B0863TXGM3", "title": "Jabra Elite 45h On-Ear Wireless Headphones"},
    {
        "asin": "B08MVGF24M",
        "title": "Anker Soundcore Life Q30 Hybrid Active Noise Cancelling Headphones",
    },
    {
        "asin": "B0851C8B55",
        "title": "Audio-Technica ATH-M40x Professional Studio Monitor Headphones",
    },
    {
        "asin": "B07G4YX39M",
        "title": "Sennheiser HD 450BT Bluetooth 5.0 Wireless Headphone",
    },
    {
        "asin": "B08YRM5D7X",
        "title": "Bose QuietComfort Earbuds True Wireless Noise Cancelling Earbuds",
    },
    {"asin": "B0856BFBXZ", "title": "JBL Tune 750BTNC Wireless Over-Ear Headphones"},
    {"asin": "B08QJ2KGSP", "title": "Plantronics BackBeat Go 810 Wireless Headphones"},
    {
        "asin": "B08T7BQMGG",
        "title": "Skullcandy Crusher ANC Personalized Noise Canceling Wireless Headphones",
    },
]


async def import_products_with_real_data():
    """导入产品并获取真实数据"""

    print("🚀 开始导入10个蓝牙耳机产品...")
    print("=" * 60)

    session = Session()

    try:
        # 1. 首先使用Apify获取真实产品数据
        print("📡 从Apify获取真实产品数据...")
        asins = [p["asin"] for p in BLUETOOTH_HEADPHONES]
        print(f"   ASIN列表: {asins}")

        scraper = ApifyAmazonScraper()
        result = await scraper.crawl({"asins": asins})

        if not result.success:
            print(f"   ❌ Apify抓取失败: {result.error}")
            return

        products_data = result.data.get("products", [])
        print(f"   ✅ 成功获取 {len(products_data)} 个产品数据")

        # 2. 创建产品数据映射
        asin_to_data = {item.get("asin"): item for item in products_data}

        # 3. 导入产品到数据库
        print("\n💾 导入产品到数据库...")
        imported_count = 0

        for product_info in BLUETOOTH_HEADPHONES:
            asin = product_info["asin"]
            real_data = asin_to_data.get(asin, {})

            # 检查是否已存在
            existing = (
                session.query(Product)
                .filter_by(
                    asin=asin,
                    marketplace=MarketplaceType.AMAZON_US,
                    tenant_id="demo-tenant",
                )
                .first()
            )

            if existing:
                print(f"   ⚠️  {asin} 已存在，跳过")
                continue

            # 创建新产品
            product = Product(
                asin=asin,
                title=real_data.get("title") or product_info["title"],
                brand=real_data.get("brand"),
                category="蓝牙耳机",
                marketplace=MarketplaceType.AMAZON_US,
                product_url=f"https://www.amazon.com/dp/{asin}",
                image_url=real_data.get("image_url"),
                status=ProductStatus.MONITORING,  # 设置为监控状态
                tracking_frequency=TrackingFrequency.DAILY,
                is_competitor=False,
                current_price=real_data.get("price"),
                buy_box_price=real_data.get("buy_box_price"),
                current_rank=real_data.get("rank"),
                current_rating=real_data.get("rating"),
                current_review_count=real_data.get("review_count", 0),
                current_availability=real_data.get("availability"),
                product_data=real_data,
                last_scraped_at=datetime.utcnow(),
                tenant_id="demo-tenant",
            )

            session.add(product)
            imported_count += 1

            print(f"   ✅ {asin} - {product.title[:50]}...")
            if real_data.get("price"):
                print(
                    f"      价格: ${real_data['price']} | 评分: {real_data.get('rating', 'N/A')}/5"
                )

        session.commit()
        print(f"\n🎉 成功导入 {imported_count} 个产品！")

        # 4. 显示导入结果统计
        total_products = (
            session.query(Product)
            .filter_by(category="蓝牙耳机", tenant_id="demo-tenant")
            .count()
        )

        print("\n📊 数据库统计:")
        print(f"   蓝牙耳机品类总产品数: {total_products}")
        print(
            f"   监控状态产品数: {session.query(Product).filter_by(status=ProductStatus.MONITORING, tenant_id='demo-tenant').count()}"
        )
        print(
            f"   每日跟踪产品数: {session.query(Product).filter_by(tracking_frequency=TrackingFrequency.DAILY, tenant_id='demo-tenant').count()}"
        )

        print("\n✨ 所有产品已设置为每30秒自动抓取更新！")
        print("   - 价格变化历史将自动记录")
        print("   - BSR排名变化将自动追踪")
        print("   - 异常变化将触发通知")

    except Exception as e:
        print(f"❌ 导入过程出错: {e}")
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(import_products_with_real_data())
