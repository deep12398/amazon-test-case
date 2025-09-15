#!/usr/bin/env python3
"""使用最优化的Apify Actor导入产品并建立监控系统"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(project_root / ".env.local")
load_dotenv(project_root / ".env")

from apify_client import ApifyClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from amazon_tracker.common.database.models.product import (
    MarketplaceType,
    Product,
    ProductPriceHistory,
    ProductRankHistory,
    ProductStatus,
    TrackingFrequency,
)

# 数据库连接
DATABASE_URL = os.getenv("DATABASE_URL")
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# 样本产品 ASIN（从用户提供的数据中提取）
SAMPLE_ASINS = [
    "B09JQMJHXY",  # Apple AirPods Pro
    "B08PZHYWJS",  # Apple AirPods Max  
    "B08MVGF24M",  # Sony WH-1000XM4 Midnight Blue
    "B0863TXGM3",  # Sony WH-1000XM4 Black
]


def get_enhanced_product_data():
    """使用最优化的Apify Actor获取产品数据"""
    print("🔍 使用最优化Actor获取产品数据...")
    
    client = ApifyClient(os.getenv("APIFY_API_TOKEN"))
    
    # 使用第一个Actor (7KgyOHHEiPEcilZXM) - 它有更详细的价格信息
    run_input = {
        "urls": [f"https://www.amazon.com/dp/{asin}" for asin in SAMPLE_ASINS]
    }
    
    print(f"📤 请求数据: {len(SAMPLE_ASINS)} 个产品")
    
    run = client.actor("7KgyOHHEiPEcilZXM").call(run_input=run_input)
    
    print(f"✅ Actor运行完成: {run['id']}")
    print(f"   状态: {run.get('status')}")
    
    # 获取结果
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    
    print(f"📊 获取到 {len(items)} 个产品数据")
    
    return items


def process_amazon_data(raw_data):
    """处理Amazon数据，提取关键信息"""
    processed_products = {}
    
    for item in raw_data:
        asin = item.get('asin')
        if not asin:
            continue
            
        # 提取价格信息
        main_price = item.get('price')
        retail_price = item.get('retailPrice')
        
        # 从buyBoxUsed获取Buy Box价格（如果有的话）
        buy_box_price = None
        buy_box_used = item.get('buyBoxUsed')
        if buy_box_used and buy_box_used.get('price'):
            buy_box_price = buy_box_used['price']
        
        # 评分和评论数 - 需要从文本中提取数字
        rating_text = item.get('productRating', '')
        rating = None
        if rating_text:
            try:
                # 提取数字，处理 "4.7 out of 5 stars" 格式
                import re
                rating_match = re.search(r'(\d+\.?\d*)', str(rating_text))
                if rating_match:
                    rating = float(rating_match.group(1))
            except (ValueError, AttributeError):
                rating = None
        
        review_count_text = item.get('countReview', 0)
        review_count = 0
        if review_count_text:
            try:
                # 处理可能的逗号分隔数字
                review_count = int(str(review_count_text).replace(',', ''))
            except (ValueError, TypeError):
                review_count = 0
        
        # BSR排名 - 尝试从categoriesExtended中提取
        bsr_rank = None
        categories = item.get('categoriesExtended', [])
        if categories:
            # 查找包含rank信息的类别
            for category in categories:
                if isinstance(category, dict) and 'rank' in str(category).lower():
                    # 这里需要进一步解析rank信息
                    pass
        
        # 库存状态
        availability = item.get('warehouseAvailability', 'Unknown')
        
        processed_product = {
            'asin': asin,
            'title': item.get('title', ''),
            'brand': item.get('manufacturer', ''),
            'current_price': main_price,
            'buy_box_price': buy_box_price or main_price,  # 如果没有buyBox价格，使用主价格
            'current_rating': float(rating) if rating else None,
            'current_review_count': int(review_count) if review_count else 0,
            'current_rank': bsr_rank,
            'current_availability': availability,
            'image_url': item.get('mainImage'),
            'raw_data': item  # 保存原始数据
        }
        
        # 如果这个ASIN还没有数据，或者这个价格更低（可能是Buy Box），则更新
        if asin not in processed_products or (main_price and main_price < processed_products[asin].get('current_price', float('inf'))):
            processed_products[asin] = processed_product
        
        print(f"   ✅ {asin}: ${main_price} (Buy Box: ${buy_box_price or 'N/A'})")
    
    return list(processed_products.values())


def import_to_database(products_data):
    """将产品数据导入数据库"""
    print("\n💾 导入产品到数据库...")
    
    session = Session()
    imported_count = 0
    
    try:
        for product_data in products_data:
            asin = product_data['asin']
            
            # 检查产品是否已存在
            existing = session.query(Product).filter_by(
                asin=asin,
                marketplace=MarketplaceType.AMAZON_US,
                tenant_id="demo-tenant"
            ).first()
            
            if existing:
                # 更新现有产品
                existing.current_price = product_data['current_price']
                existing.buy_box_price = product_data['buy_box_price']
                existing.current_rating = product_data['current_rating']
                existing.current_review_count = product_data['current_review_count']
                existing.current_availability = product_data['current_availability']
                existing.product_data = product_data['raw_data']
                existing.last_scraped_at = datetime.utcnow()
                print(f"   🔄 更新: {asin}")
            else:
                # 创建新产品
                product = Product(
                    asin=asin,
                    title=product_data['title'],
                    brand=product_data['brand'],
                    category="蓝牙耳机",
                    marketplace=MarketplaceType.AMAZON_US,
                    product_url=f"https://www.amazon.com/dp/{asin}",
                    image_url=product_data['image_url'],
                    status=ProductStatus.MONITORING,
                    tracking_frequency=TrackingFrequency.DAILY,
                    is_competitor=False,
                    current_price=product_data['current_price'],
                    buy_box_price=product_data['buy_box_price'],
                    current_rank=product_data['current_rank'],
                    current_rating=product_data['current_rating'],
                    current_review_count=product_data['current_review_count'],
                    current_availability=product_data['current_availability'],
                    product_data=product_data['raw_data'],
                    last_scraped_at=datetime.utcnow(),
                    tenant_id="demo-tenant",
                )
                session.add(product)
                imported_count += 1
                print(f"   ✅ 新增: {asin} - {product_data['title'][:50]}...")
            
            # 创建初始价格历史记录
            if product_data['current_price']:
                price_history = ProductPriceHistory(
                    product_id=existing.id if existing else None,  # 需要在提交后获取
                    price=product_data['current_price'],
                    buy_box_price=product_data['buy_box_price'],
                    currency='USD',
                    recorded_at=datetime.utcnow()
                )
                if not existing:
                    # 对于新产品，我们需要在提交后再添加历史记录
                    pass
                else:
                    price_history.product_id = existing.id
                    session.add(price_history)
        
        session.commit()
        
        # 为新产品添加价格历史记录
        if imported_count > 0:
            for product_data in products_data:
                asin = product_data['asin']
                product = session.query(Product).filter_by(
                    asin=asin,
                    marketplace=MarketplaceType.AMAZON_US,
                    tenant_id="demo-tenant"
                ).first()
                
                if product and product_data['current_price']:
                    # 检查是否已有今天的价格记录
                    today = datetime.utcnow().date()
                    existing_history = session.query(ProductPriceHistory).filter(
                        ProductPriceHistory.product_id == product.id,
                        ProductPriceHistory.recorded_at >= today
                    ).first()
                    
                    if not existing_history:
                        price_history = ProductPriceHistory(
                            product_id=product.id,
                            price=product_data['current_price'],
                            buy_box_price=product_data['buy_box_price'],
                            currency='USD',
                            recorded_at=datetime.utcnow()
                        )
                        session.add(price_history)
            
            session.commit()
        
        print(f"\n🎉 成功导入 {imported_count} 个新产品！")
        
        # 显示统计信息
        total_products = session.query(Product).filter_by(
            category="蓝牙耳机",
            tenant_id="demo-tenant"
        ).count()
        
        monitoring_products = session.query(Product).filter_by(
            status=ProductStatus.MONITORING,
            tenant_id="demo-tenant"
        ).count()
        
        print(f"\n📊 数据库统计:")
        print(f"   蓝牙耳机总数: {total_products}")
        print(f"   监控中产品: {monitoring_products}")
        
    except Exception as e:
        print(f"❌ 数据库操作失败: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def test_anomaly_detection():
    """测试异常检测功能"""
    print("\n🔍 测试异常检测功能...")
    
    session = Session()
    try:
        # 获取一个测试产品
        test_product = session.query(Product).filter_by(
            tenant_id="demo-tenant",
            status=ProductStatus.MONITORING
        ).first()
        
        if not test_product:
            print("   ⚠️  没有找到测试产品")
            return
        
        print(f"   测试产品: {test_product.asin} - {test_product.title[:50]}...")
        
        # 模拟价格变化 - 增加15%触发异常
        original_price = test_product.current_price
        if original_price:
            new_price = original_price * 1.15  # 增加15%
            
            # 创建新的价格历史记录
            price_history = ProductPriceHistory(
                product_id=test_product.id,
                price=new_price,
                buy_box_price=new_price,
                currency='USD',
                recorded_at=datetime.utcnow()
            )
            session.add(price_history)
            
            # 更新产品当前价格
            test_product.current_price = new_price
            session.commit()
            
            print(f"   💰 模拟价格变化: ${original_price:.2f} → ${new_price:.2f} (+15%)")
            print("   ⚠️  这应该会触发价格异常警报（阈值10%）")
            
        else:
            print("   ⚠️  测试产品没有价格信息")
            
    except Exception as e:
        print(f"   ❌ 异常检测测试失败: {e}")
        session.rollback()
    finally:
        session.close()


async def main():
    """主函数"""
    print("🚀 开始优化版本的Amazon产品监控系统Demo")
    print("=" * 60)
    
    try:
        # 1. 获取产品数据
        raw_data = get_enhanced_product_data()
        
        if not raw_data:
            print("❌ 没有获取到产品数据")
            return
        
        # 2. 处理数据
        processed_data = process_amazon_data(raw_data)
        print(f"\n✅ 处理完成，得到 {len(processed_data)} 个独特产品")
        
        # 保存处理后的数据到文件
        with open("processed_products.json", "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False, default=str)
        print("💾 处理后的数据已保存到 processed_products.json")
        
        # 3. 导入数据库
        import_to_database(processed_data)
        
        # 4. 测试异常检测
        test_anomaly_detection()
        
        print("\n✨ Demo完成！系统已准备就绪：")
        print("   - 产品数据已导入并设置为每日监控")
        print("   - 价格历史追踪已启动")
        print("   - 异常检测系统已激活")
        print("   - 可以使用Celery任务进行后台监控")
        
        print("\n💡 下一步建议：")
        print("   1. 启动Celery worker: celery -A amazon_tracker.common.task_queue.celery_app worker")
        print("   2. 启动Celery beat: celery -A amazon_tracker.common.task_queue.celery_app beat")
        print("   3. 测试异常通知: python scripts/test_monitoring_system.py")
        
    except Exception as e:
        print(f"❌ Demo执行失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())