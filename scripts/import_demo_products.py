#!/usr/bin/env python
"""
Demo产品导入脚本 - 导入10个有BSR数据的蓝牙耳机产品
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from apify_client import ApifyClient
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from amazon_tracker.common.cache.redis_manager import RedisCache
from amazon_tracker.common.database.connection import get_db_session
from amazon_tracker.common.database.models.product import (
    MarketplaceType,
    Product,
    ProductPriceHistory,
    ProductRankHistory,
    ProductStatus,
    TrackingFrequency,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv(".env.local")

# Demo产品列表 - 全部选择有BSR的产品
DEMO_PRODUCTS = [
    {"asin": "B0863TXGM3", "name": "Sony WH-1000XM4", "brand": "Sony"},
    {"asin": "B0756CYWWD", "name": "Bose QuietComfort 35 II", "brand": "Bose"},
    {"asin": "B08MVGF24M", "name": "Sony WH-1000XM4 (Blue)", "brand": "Sony"},
    {"asin": "B0C33XXS56", "name": "Sony WH-1000XM5", "brand": "Sony"},
    {"asin": "B08PZHYWJS", "name": "Apple AirPods Max", "brand": "Apple"},
    {"asin": "B07ZPKN6YR", "name": "Anker Soundcore Life Q30", "brand": "Anker"},
    {"asin": "B08HMWZBXC", "name": "Jabra Elite 85h", "brand": "Jabra"},
    {"asin": "B08QJ2KGSP", "name": "Sennheiser Momentum 3", "brand": "Sennheiser"},
    {"asin": "B0856BFBXZ", "name": "Audio-Technica ATH-M50xBT2", "brand": "Audio-Technica"},
    {"asin": "B08R7YP5KB", "name": "Marshall Major IV", "brand": "Marshall"},
]


class DemoProductImporter:
    """Demo产品导入器"""

    def __init__(self):
        self.apify_client = ApifyClient(os.getenv("APIFY_API_TOKEN"))
        self.redis_cache = RedisCache()
        self.tenant_id = "demo-tenant"  # Demo租户ID

    def fetch_products_from_apify(self, asins: List[str]) -> List[Dict[str, Any]]:
        """从Apify获取产品数据"""
        logger.info(f"开始从Apify获取{len(asins)}个产品数据")

        run_input = {
            "asins": asins,
            "amazonDomain": "amazon.com",
            "maxConcurrency": 5,
            "proxyCountry": "AUTO_SELECT_PROXY_COUNTRY",
            "useCaptchaSolver": False,
        }

        try:
            # 运行Actor
            run = self.apify_client.actor("ZhSGsaq9MHRnWtStl").call(run_input=run_input)
            
            # 获取结果
            items = list(self.apify_client.dataset(run["defaultDatasetId"]).iterate_items())
            logger.info(f"成功获取{len(items)}个产品数据")
            
            # 按ASIN分组，去重
            products_by_asin = {}
            for item in items:
                asin = item.get("asin")
                if asin and asin not in products_by_asin:
                    products_by_asin[asin] = item
            
            return list(products_by_asin.values())
            
        except Exception as e:
            logger.error(f"从Apify获取数据失败: {e}")
            return []

    def parse_price(self, price_data: Any) -> Decimal:
        """解析价格数据"""
        if isinstance(price_data, dict):
            return Decimal(str(price_data.get("value", 0)))
        elif isinstance(price_data, (int, float)):
            return Decimal(str(price_data))
        return Decimal("0")

    def parse_bsr(self, bsr_data: List[Dict]) -> tuple:
        """解析BSR数据，返回(主排名, 类别名称)"""
        if not bsr_data:
            return None, None
        
        # 获取第一个排名（通常是主类别）
        main_rank = bsr_data[0]
        return main_rank.get("rank"), main_rank.get("category")

    def import_products(self):
        """导入Demo产品"""
        asins = [p["asin"] for p in DEMO_PRODUCTS]
        
        # 从Apify获取数据
        apify_products = self.fetch_products_from_apify(asins)
        
        if not apify_products:
            logger.error("未能从Apify获取产品数据")
            return
        
        # 创建ASIN到产品信息的映射
        demo_map = {p["asin"]: p for p in DEMO_PRODUCTS}
        
        with get_db_session() as db:
            imported_count = 0
            
            for apify_data in apify_products:
                asin = apify_data.get("asin")
                if not asin or asin not in demo_map:
                    continue
                
                demo_info = demo_map[asin]
                
                try:
                    # 检查产品是否已存在
                    existing = (
                        db.query(Product)
                        .filter(
                            Product.asin == asin,
                            Product.tenant_id == self.tenant_id,
                            Product.marketplace == MarketplaceType.AMAZON_US,
                        )
                        .first()
                    )
                    
                    # 解析数据
                    price = self.parse_price(apify_data.get("price"))
                    bsr_rank, bsr_category = self.parse_bsr(apify_data.get("bestsellerRanks", []))
                    rating = apify_data.get("productRating")
                    review_count = apify_data.get("countReview", 0)
                    
                    if existing:
                        # 更新现有产品
                        existing.current_price = price
                        existing.current_rank = bsr_rank
                        existing.current_rating = Decimal(str(rating)) if rating else None
                        existing.current_review_count = review_count
                        existing.product_data = apify_data
                        existing.last_scraped_at = datetime.utcnow()
                        existing.status = ProductStatus.MONITORING
                        existing.tracking_frequency = TrackingFrequency.HOURLY  # 测试用，设置为每小时
                        product = existing
                        logger.info(f"更新现有产品: {asin}")
                    else:
                        # 创建新产品
                        product = Product(
                            tenant_id=self.tenant_id,
                            asin=asin,
                            title=apify_data.get("name", demo_info["name"]),
                            brand=demo_info["brand"],
                            category=bsr_category or "Bluetooth Headphones",
                            marketplace=MarketplaceType.AMAZON_US,
                            product_url=f"https://www.amazon.com/dp/{asin}",
                            image_url=apify_data.get("thumbnailImage"),
                            status=ProductStatus.MONITORING,
                            tracking_frequency=TrackingFrequency.HOURLY,  # 测试用
                            is_competitor=True,
                            current_price=price,
                            current_rank=bsr_rank,
                            current_rating=Decimal(str(rating)) if rating else None,
                            current_review_count=review_count,
                            current_availability=apify_data.get("availability"),
                            product_data=apify_data,
                            last_scraped_at=datetime.utcnow(),
                        )
                        db.add(product)
                        db.flush()
                        logger.info(f"创建新产品: {asin}")
                    
                    # 添加价格历史
                    if price:
                        price_history = ProductPriceHistory(
                            product_id=product.id,
                            price=price,
                            buy_box_price=self.parse_price(apify_data.get("buyBoxUsed", {}).get("price")),
                            currency="USD",
                        )
                        db.add(price_history)
                    
                    # 添加排名历史
                    if bsr_rank:
                        rank_history = ProductRankHistory(
                            product_id=product.id,
                            rank=bsr_rank,
                            category=bsr_category,
                            rating=Decimal(str(rating)) if rating else None,
                            review_count=review_count,
                        )
                        db.add(rank_history)
                    
                    # 缓存到Redis（24小时TTL）
                    cache_key = f"product:{self.tenant_id}:{asin}"
                    cache_data = {
                        "asin": asin,
                        "title": product.title,
                        "price": float(price) if price else None,
                        "rank": bsr_rank,
                        "rating": float(rating) if rating else None,
                        "last_updated": datetime.utcnow().isoformat(),
                    }
                    self.redis_cache.set(cache_key, json.dumps(cache_data), ttl=86400)
                    
                    imported_count += 1
                    logger.info(
                        f"✅ 导入产品 {imported_count}/10: {asin} - {demo_info['name']}"
                        f" (价格: ${price}, BSR: {bsr_rank})"
                    )
                    
                except Exception as e:
                    logger.error(f"导入产品 {asin} 失败: {e}")
                    continue
            
            # 提交所有更改
            db.commit()
            logger.info(f"\n🎉 成功导入 {imported_count} 个产品")
            
            # 打印导入摘要
            self.print_import_summary(db)

    def print_import_summary(self, db: Session):
        """打印导入摘要"""
        products = (
            db.query(Product)
            .filter(Product.tenant_id == self.tenant_id)
            .all()
        )
        
        print("\n" + "="*60)
        print("📊 Demo产品导入摘要")
        print("="*60)
        
        for product in products:
            bsr_info = f"BSR: #{product.current_rank}" if product.current_rank else "BSR: N/A"
            price_info = f"${product.current_price}" if product.current_price else "N/A"
            print(
                f"{product.asin} - {product.title[:30]}...\n"
                f"  💰 价格: {price_info} | 📈 {bsr_info} | ⭐ {product.current_rating or 'N/A'}"
            )
        
        print("="*60)
        print(f"✅ 总计: {len(products)} 个产品已导入并开始监控")
        print(f"🔄 更新频率: 每小时")
        print(f"📧 异常通知: 价格变化>10% 或 BSR变化>30%")


def main():
    """主函数"""
    importer = DemoProductImporter()
    importer.import_products()


if __name__ == "__main__":
    main()