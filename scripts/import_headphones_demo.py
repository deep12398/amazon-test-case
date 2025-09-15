#!/usr/bin/env python3
"""
蓝牙耳机Demo产品导入脚本

基于docs/headphones-demo-specification.md中定义的20个产品，
使用ZhSGsaq9MHRnWtStl爬虫(94.6% BSR可用率)批量导入产品数据。

功能：
1. 批量爬取20个蓝牙耳机产品数据
2. 数据标准化和清洗  
3. 存储到数据库并建立竞品关系
4. 生成导入报告

用法：
    python scripts/import_headphones_demo.py
"""

import asyncio
import os
import sys
import json
import re
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from amazon_tracker.common.crawlers.apify_client import ApifyAmazonScraper
from amazon_tracker.common.database.connection import get_db_session
from amazon_tracker.common.database.models.product import Product, CompetitorSet, CompetitorRelationship
from amazon_tracker.common.database.models.user import Tenant


class HeadphonesDemoImporter:
    """蓝牙耳机Demo数据导入器"""
    
    # 20个Demo产品ASIN列表 - 来自headphones-demo-specification.md
    DEMO_ASINS = [
        # Apple系列 (4个)
        "B0D1XD1ZV3",  # Apple AirPods Pro 2 (2024)
        "B09JQMJHXY",  # Apple AirPods Pro (1st Gen) with MagSafe
        "B08PZHYWJS",  # Apple AirPods Max
        "B0CHWRXH8B",  # Apple AirPods (3rd Generation)
        
        # Sony系列 (4个) 
        "B0863TXGM3",  # Sony WH-1000XM4 (Black)
        "B08MVGF24M",  # Sony WH-1000XM4 (Midnight Blue)
        "B0C33XXS56",  # Sony WH-1000XM5
        "B09FC1PG9H",  # Sony WF-1000XM4 (真无线)
        
        # Bose系列 (3个)
        "B0756CYWWD",  # Bose QuietComfort 35 II
        "B08YRM5D7X",  # Bose QuietComfort Earbuds
        "B09NQBL7SF",  # Bose QuietComfort 45
        
        # 其他品牌 (4个)
        "B07ZPKN6YR",  # Anker Soundcore Life Q30
        "B08HMWZBXC",  # Jabra Elite 85h
        "B08QJ2KGSP",  # Sennheiser Momentum 3 Wireless
        "B0856BFBXZ",  # Audio-Technica ATH-M50xBT2
        
        # 新兴品牌 (5个)
        "B093MBYX7P",  # Nothing Ear (stick)
        "B09K7S1HKZ",  # Beats Studio Buds+
        "B08T7BQMGG",  # Skullcandy Crusher ANC
        "B08R7YP5KB",  # Marshall Major IV
        "B09JB4DCTM",  # 1MORE ComfoBuds Pro
    ]
    
    def __init__(self):
        self.scraper = ApifyAmazonScraper()
        self.session = None
        self.results = {
            'success': [],
            'failed': [],
            'total_processed': 0,
            'bsr_success_rate': 0,
            'import_summary': {}
        }
        
    def extract_numeric_value(self, value: Any) -> Optional[float]:
        """从各种格式中提取数值"""
        if value is None:
            return None
            
        if isinstance(value, (int, float)):
            return float(value)
            
        if isinstance(value, str):
            # 移除货币符号和逗号
            cleaned = re.sub(r'[$,]', '', value)
            # 提取数字
            match = re.search(r'(\d+\.?\d*)', cleaned)
            if match:
                return float(match.group(1))
                
        return None
    
    def extract_rating(self, rating_data: Any) -> Optional[float]:
        """提取评分数据"""
        if rating_data is None:
            return None
            
        if isinstance(rating_data, (int, float)):
            return float(rating_data)
            
        if isinstance(rating_data, str):
            # 处理 "4.7 out of 5 stars" 格式
            match = re.search(r'(\d+\.?\d*)', rating_data)
            if match:
                rating = float(match.group(1))
                return rating if 0 <= rating <= 5 else None
                
        return None
    
    def process_bsr_data(self, bsr_data: List[Dict]) -> tuple[Optional[int], Optional[str]]:
        """处理BSR排名数据，返回主要排名和类别"""
        if not bsr_data or not isinstance(bsr_data, list):
            return None, None
            
        # 优先使用更具体的类别排名
        headphone_categories = [
            'Earbud Headphones', 'Over-Ear Headphones', 
            'Headphones', 'Cell Phones & Accessories'
        ]
        
        for category in headphone_categories:
            for rank_info in bsr_data:
                if isinstance(rank_info, dict) and rank_info.get('category') == category:
                    rank = rank_info.get('rank')
                    if rank and isinstance(rank, int) and rank > 0:
                        return rank, category
                        
        # 如果没找到特定类别，使用第一个有效排名
        for rank_info in bsr_data:
            if isinstance(rank_info, dict):
                rank = rank_info.get('rank')
                category = rank_info.get('category')
                if rank and isinstance(rank, int) and rank > 0:
                    return rank, category
                    
        return None, None
    
    def normalize_product_data(self, raw_data: Dict) -> Dict[str, Any]:
        """标准化产品数据"""
        asin = raw_data.get('asin', '')
        
        # 基础信息
        normalized = {
            'asin': asin,
            'title': raw_data.get('title', '').strip(),
            'brand': raw_data.get('brand', '').strip(),
            'marketplace': 'amazon_us',
            'category': '蓝牙耳机',
            'product_url': f"https://www.amazon.com/dp/{asin}",
        }
        
        # 价格信息
        price_data = raw_data.get('price', {})
        if isinstance(price_data, dict):
            normalized['current_price'] = self.extract_numeric_value(price_data.get('value'))
        else:
            normalized['current_price'] = self.extract_numeric_value(price_data)
            
        # Buy Box价格
        buy_box_data = raw_data.get('buyBoxUsed', {}) or raw_data.get('buyBox', {})
        if isinstance(buy_box_data, dict):
            normalized['buy_box_price'] = self.extract_numeric_value(buy_box_data.get('price'))
        
        # 评分和评论
        normalized['current_rating'] = self.extract_rating(raw_data.get('stars'))
        normalized['current_review_count'] = self.extract_numeric_value(raw_data.get('reviewsCount'))
        
        # BSR排名
        bsr_data = raw_data.get('bestsellerRanks', [])
        rank, category = self.process_bsr_data(bsr_data)
        normalized['current_rank'] = rank
        normalized['rank_category'] = category
        
        # 产品特征
        features = raw_data.get('features', [])
        if isinstance(features, list):
            normalized['features'] = [f.strip() for f in features if f and f.strip()]
        
        # 库存状态
        availability = raw_data.get('availability', '')
        normalized['availability_status'] = 'In Stock' if 'stock' in availability.lower() else availability
        
        # 卖家信息
        normalized['seller'] = raw_data.get('seller', '')
        
        return normalized
    
    async def crawl_products(self) -> List[Dict]:
        """批量爬取产品数据"""
        print(f"开始爬取 {len(self.DEMO_ASINS)} 个蓝牙耳机产品...")
        
        input_data = {
            "asins": self.DEMO_ASINS,
            "amazonDomain": "amazon.com", 
            "proxyCountry": "AUTO_SELECT_PROXY_COUNTRY",
            "useCaptchaSolver": False
        }
        
        try:
            crawler_result = await self.scraper.scrape_multiple_products(self.DEMO_ASINS)
            raw_results = crawler_result.data if crawler_result.success else []
            print(f"爬虫返回 {len(raw_results)} 条原始数据")
            
            # 标准化数据
            normalized_results = []
            bsr_success_count = 0
            
            for raw_product in raw_results:
                try:
                    normalized = self.normalize_product_data(raw_product)
                    normalized_results.append(normalized)
                    
                    # 统计BSR成功率
                    if normalized.get('current_rank'):
                        bsr_success_count += 1
                        
                    print(f"✓ 处理成功: {normalized['asin']} - {normalized['title'][:50]}...")
                    
                except Exception as e:
                    print(f"✗ 数据标准化失败: {raw_product.get('asin', 'Unknown')} - {e}")
                    self.results['failed'].append({
                        'asin': raw_product.get('asin', 'Unknown'),
                        'error': str(e)
                    })
            
            # 计算BSR成功率
            if normalized_results:
                self.results['bsr_success_rate'] = (bsr_success_count / len(normalized_results)) * 100
                print(f"BSR数据成功率: {self.results['bsr_success_rate']:.1f}% ({bsr_success_count}/{len(normalized_results)})")
            
            return normalized_results
            
        except Exception as e:
            print(f"爬虫执行失败: {e}")
            raise
    
    def save_to_database(self, products_data: List[Dict]) -> None:
        """保存产品数据到数据库"""
        print("开始保存数据到数据库...")
        
        with get_db_session() as session:
            try:
                # 获取或创建默认租户
                tenant = session.query(Tenant).first()
                if not tenant:
                    tenant = Tenant(
                        name="Demo Tenant",
                        domain="demo.localhost",
                        is_active=True
                    )
                    session.add(tenant)
                    session.flush()
                
                saved_products = []
                main_product_id = None
                
                for product_data in products_data:
                    try:
                        # 检查产品是否已存在
                        existing = session.query(Product).filter_by(
                            asin=product_data['asin'],
                            tenant_id=tenant.id
                        ).first()
                        
                        if existing:
                            # 更新现有产品
                            for key, value in product_data.items():
                                if hasattr(existing, key) and value is not None:
                                    setattr(existing, key, value)
                            existing.last_updated = datetime.utcnow()
                            product = existing
                            print(f"✓ 更新产品: {product_data['asin']}")
                        else:
                            # 创建新产品
                            product = Product(
                                tenant_id=tenant.id,
                                last_updated=datetime.utcnow(),
                                **product_data
                            )
                            session.add(product)
                            print(f"✓ 创建产品: {product_data['asin']}")
                        
                        session.flush()
                        saved_products.append(product)
                        
                        # 记录第一个产品作为主产品 (Apple AirPods Pro 2)
                        if product_data['asin'] == "B0D1XD1ZV3":
                            main_product_id = product.id
                        
                        self.results['success'].append({
                            'asin': product_data['asin'],
                            'title': product_data['title'],
                            'price': product_data.get('current_price'),
                            'rank': product_data.get('current_rank'),
                            'rating': product_data.get('current_rating')
                        })
                        
                    except Exception as e:
                        print(f"✗ 保存产品失败: {product_data['asin']} - {e}")
                        self.results['failed'].append({
                            'asin': product_data['asin'],
                            'error': str(e)
                        })
            
                # 创建竞品组（如果有主产品）
                if main_product_id and saved_products:
                    competitor_set = CompetitorSet(
                        name="蓝牙耳机竞品组",
                        description="基于headphones-demo-specification.md的20个蓝牙耳机产品",
                        tenant_id=tenant.id,
                        main_product_id=main_product_id,
                        is_default=True,
                        max_competitors=20
                    )
                    session.add(competitor_set)
                    session.flush()
                    
                    # 添加所有产品到竞品关系
                    for product in saved_products:
                        relationship = CompetitorRelationship(
                            competitor_set_id=competitor_set.id,
                            competitor_product_id=product.id,
                            weight=1.0
                        )
                        session.add(relationship)
                    
                    print(f"✓ 创建竞品组，包含 {len(saved_products)} 个产品")
            
                # 提交事务
                session.commit()
                print(f"✓ 成功保存 {len(saved_products)} 个产品到数据库")
                
                # 更新统计信息
                self.results['import_summary'] = {
                    'competitor_set_id': competitor_set.id if main_product_id and saved_products else None,
                    'total_products': len(saved_products),
                    'tenant_id': tenant.id,
                    'main_product_id': main_product_id
                }
                
            except Exception as e:
                session.rollback()
                print(f"数据库保存失败: {e}")
                raise
    
    def generate_report(self) -> Dict:
        """生成导入报告"""
        total_attempted = len(self.DEMO_ASINS)
        successful = len(self.results['success'])
        failed = len(self.results['failed'])
        
        report = {
            'import_timestamp': datetime.utcnow().isoformat(),
            'total_attempted': total_attempted,
            'successful_imports': successful,
            'failed_imports': failed,
            'success_rate': (successful / total_attempted) * 100 if total_attempted > 0 else 0,
            'bsr_data_availability': self.results['bsr_success_rate'],
            'summary': self.results['import_summary'],
            'successful_products': self.results['success'],
            'failed_products': self.results['failed']
        }
        
        return report
    
    async def run_import(self) -> Dict:
        """执行完整的导入流程"""
        print("=" * 60)
        print("🎧 蓝牙耳机Demo产品导入开始")
        print("=" * 60)
        
        try:
            # 第一步：爬取数据
            products_data = await self.crawl_products()
            
            if not products_data:
                raise Exception("没有成功爬取到任何产品数据")
            
            # 第二步：保存到数据库
            self.save_to_database(products_data)
            
            # 第三步：生成报告
            report = self.generate_report()
            
            print("\n" + "=" * 60)
            print("📊 导入完成统计")
            print("=" * 60)
            print(f"总计尝试: {report['total_attempted']} 个产品")
            print(f"成功导入: {report['successful_imports']} 个产品")
            print(f"导入失败: {report['failed_imports']} 个产品")
            print(f"成功率: {report['success_rate']:.1f}%")
            print(f"BSR数据可用率: {report['bsr_data_availability']:.1f}%")
            
            if report['successful_products']:
                print("\n✅ 成功导入的产品:")
                for product in report['successful_products'][:5]:  # 显示前5个
                    rank_info = f"BSR#{product['rank']}" if product['rank'] else "无BSR"
                    price_info = f"${product['price']}" if product['price'] else "无价格"
                    rating_info = f"{product['rating']}★" if product['rating'] else "无评分"
                    print(f"  • {product['asin']}: {price_info} | {rank_info} | {rating_info}")
                
                if len(report['successful_products']) > 5:
                    print(f"  ... 还有 {len(report['successful_products']) - 5} 个产品")
            
            if report['failed_products']:
                print("\n❌ 导入失败的产品:")
                for product in report['failed_products']:
                    print(f"  • {product['asin']}: {product['error']}")
            
            return report
            
        except Exception as e:
            print(f"\n❌ 导入过程发生错误: {e}")
            report = self.generate_report()
            report['error'] = str(e)
            return report


async def main():
    """主函数"""
    importer = HeadphonesDemoImporter()
    
    try:
        report = await importer.run_import()
        
        # 保存报告到文件
        report_file = "/Users/elias/code/amazon-test-case/logs/headphones_import_report.json"
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n📄 详细报告已保存至: {report_file}")
        
        return report
        
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        return None


if __name__ == "__main__":
    # 运行导入脚本
    asyncio.run(main())