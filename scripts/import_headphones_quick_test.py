#!/usr/bin/env python3
"""
蓝牙耳机Demo快速验证脚本

使用5个核心产品快速验证系统功能：
- BSR数据获取能力
- 价格和Buy Box价格监控
- 竞品关系建立
- 数据完整性验证

用法：
    python scripts/import_headphones_quick_test.py
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


class QuickTestImporter:
    """快速验证导入器"""
    
    # 5个核心产品ASIN - 已验证有效
    CORE_ASINS = [
        "B0D1XD1ZV3",  # Apple AirPods Pro 2 (2024) - BSR #1
        "B0863TXGM3",  # Sony WH-1000XM4 (Black) - 高性价比
        "B0756CYWWD",  # Bose QuietComfort 35 II - 经典降噪
        "B08PZHYWJS",  # Apple AirPods Max - Premium头戴
        "B07ZPKN6YR",  # Anker Soundcore Life Q30 - 性价比选择
    ]
    
    def __init__(self):
        self.scraper = ApifyAmazonScraper()
        self.results = {
            'success': [],
            'failed': [],
            'bsr_success_count': 0,
            'total_processed': 0,
            'data_quality_report': {}
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
    
    def analyze_data_quality(self, product_data: Dict) -> Dict[str, Any]:
        """分析数据质量"""
        quality_report = {
            'asin': product_data.get('asin'),
            'data_completeness': {},
            'data_quality_score': 0
        }
        
        # 检查关键字段完整性
        key_fields = {
            'title': product_data.get('title'),
            'brand': product_data.get('brand'),
            'current_price': product_data.get('current_price'),
            'current_rating': product_data.get('current_rating'),
            'current_review_count': product_data.get('current_review_count'),
            'current_rank': product_data.get('current_rank'),
            'rank_category': product_data.get('rank_category')
        }
        
        for field, value in key_fields.items():
            quality_report['data_completeness'][field] = value is not None
        
        # 计算数据质量分数
        complete_fields = sum(1 for v in quality_report['data_completeness'].values() if v)
        quality_report['data_quality_score'] = (complete_fields / len(key_fields)) * 100
        
        return quality_report
    
    def normalize_product_data(self, raw_data: Dict) -> Dict[str, Any]:
        """标准化产品数据 - 适配实际返回格式"""
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
        
        # 价格信息 - 使用实际字段名
        normalized['current_price'] = self.extract_numeric_value(raw_data.get('price'))
        normalized['buy_box_price'] = self.extract_numeric_value(raw_data.get('list_price'))
        
        # 评分和评论 - 使用实际字段名
        normalized['current_rating'] = self.extract_rating(raw_data.get('rating'))
        normalized['current_review_count'] = self.extract_numeric_value(raw_data.get('review_count'))
        
        # BSR排名 - 使用实际字段名
        rank = self.extract_numeric_value(raw_data.get('rank'))
        rank_category = raw_data.get('rank_category')
        normalized['current_rank'] = rank
        normalized['rank_category'] = rank_category
        
        # 统计BSR成功率
        if rank is not None:
            self.results['bsr_success_count'] += 1
        
        # 产品特征
        features = raw_data.get('features', [])
        if isinstance(features, list):
            normalized['features'] = [f.strip() for f in features if f and f.strip()]
        
        # 库存状态 - 使用实际字段名
        availability = raw_data.get('availability', '')
        in_stock = raw_data.get('in_stock', True)
        if availability:
            normalized['availability_status'] = availability
        else:
            normalized['availability_status'] = 'In Stock' if in_stock else 'Out of Stock'
        
        # 卖家信息
        seller_info = raw_data.get('seller_info', {})
        if isinstance(seller_info, dict) and seller_info.get('name'):
            normalized['seller'] = seller_info['name'].get('name', '') if isinstance(seller_info['name'], dict) else str(seller_info['name'])
        else:
            normalized['seller'] = ''
        
        return normalized
    
    async def crawl_products(self) -> List[Dict]:
        """爬取核心产品数据"""
        print(f"🚀 开始快速验证 - 爬取 {len(self.CORE_ASINS)} 个核心蓝牙耳机产品...")
        
        try:
            crawler_result = await self.scraper.scrape_multiple_products(self.CORE_ASINS)
            
            if crawler_result.success and crawler_result.data:
                # 获取products列表
                raw_results = crawler_result.data.get('products', [])
                print(f"✅ 爬虫返回 {len(raw_results)} 条原始数据")
            else:
                raw_results = []
                print(f"❌ 爬虫失败: {crawler_result.error}")
            
            # 标准化数据
            normalized_results = []
            
            for raw_product in raw_results:
                try:
                    normalized = self.normalize_product_data(raw_product)
                    
                    # 数据质量分析
                    quality_report = self.analyze_data_quality(normalized)
                    self.results['data_quality_report'][normalized['asin']] = quality_report
                    
                    normalized_results.append(normalized)
                    
                    # 输出关键信息
                    price_info = f"${normalized['current_price']}" if normalized['current_price'] else "无价格"
                    rank_info = f"BSR#{normalized['current_rank']}" if normalized['current_rank'] else "无BSR"
                    rating_info = f"{normalized['current_rating']}★" if normalized['current_rating'] else "无评分"
                    
                    print(f"  ✓ {normalized['asin']}: {price_info} | {rank_info} | {rating_info} | 质量分数: {quality_report['data_quality_score']:.1f}%")
                    
                except Exception as e:
                    print(f"  ✗ 数据标准化失败: {raw_product.get('asin', 'Unknown')} - {e}")
                    self.results['failed'].append({
                        'asin': raw_product.get('asin', 'Unknown'),
                        'error': str(e)
                    })
            
            self.results['total_processed'] = len(normalized_results)
            
            return normalized_results
            
        except Exception as e:
            print(f"❌ 爬虫执行失败: {e}")
            raise
    
    def save_to_database(self, products_data: List[Dict]) -> None:
        """保存产品数据到数据库"""
        print("💾 开始保存数据到数据库...")
        
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
                            print(f"  ↻ 更新产品: {product_data['asin']}")
                        else:
                            # 创建新产品
                            product = Product(
                                tenant_id=tenant.id,
                                last_updated=datetime.utcnow(),
                                **product_data
                            )
                            session.add(product)
                            print(f"  ✓ 创建产品: {product_data['asin']}")
                        
                        session.flush()
                        saved_products.append(product)
                        
                        # 使用第一个产品作为主产品
                        if product_data['asin'] == self.CORE_ASINS[0]:
                            main_product_id = product.id
                        
                        self.results['success'].append({
                            'asin': product_data['asin'],
                            'title': product_data['title'],
                            'price': product_data.get('current_price'),
                            'rank': product_data.get('current_rank'),
                            'rating': product_data.get('current_rating')
                        })
                        
                    except Exception as e:
                        print(f"  ✗ 保存产品失败: {product_data['asin']} - {e}")
                        self.results['failed'].append({
                            'asin': product_data['asin'],
                            'error': str(e)
                        })
                
                # 创建竞品组（如果有主产品）
                if main_product_id and saved_products:
                    competitor_set = CompetitorSet(
                        name="蓝牙耳机核心竞品组",
                        description="快速验证使用的5个核心蓝牙耳机产品",
                        tenant_id=tenant.id,
                        main_product_id=main_product_id,
                        is_default=True,
                        max_competitors=5
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
                    
                    print(f"  ✓ 创建竞品组，包含 {len(saved_products)} 个产品")
                
                # 提交事务
                session.commit()
                print(f"✅ 成功保存 {len(saved_products)} 个产品到数据库")
                
            except Exception as e:
                session.rollback()
                print(f"❌ 数据库保存失败: {e}")
                raise
    
    def generate_validation_report(self) -> Dict:
        """生成验证报告"""
        total_attempted = len(self.CORE_ASINS)
        successful = len(self.results['success'])
        failed = len(self.results['failed'])
        
        # BSR成功率
        bsr_success_rate = (self.results['bsr_success_count'] / self.results['total_processed']) * 100 if self.results['total_processed'] > 0 else 0
        
        # 数据质量统计
        quality_scores = [report['data_quality_score'] for report in self.results['data_quality_report'].values()]
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        report = {
            'validation_timestamp': datetime.utcnow().isoformat(),
            'test_summary': {
                'total_attempted': total_attempted,
                'successful_imports': successful,
                'failed_imports': failed,
                'success_rate': (successful / total_attempted) * 100 if total_attempted > 0 else 0
            },
            'data_quality_metrics': {
                'bsr_data_availability': bsr_success_rate,
                'average_data_completeness': avg_quality_score,
                'quality_by_product': self.results['data_quality_report']
            },
            'system_validation': {
                'crawler_functional': self.results['total_processed'] > 0,
                'database_integration': successful > 0,
                'competitor_relationships': successful > 1,
                'data_standardization': avg_quality_score > 80
            },
            'successful_products': self.results['success'],
            'failed_products': self.results['failed']
        }
        
        return report
    
    async def run_validation(self) -> Dict:
        """执行快速验证流程"""
        print("=" * 60)
        print("🧪 蓝牙耳机系统快速验证开始")
        print("=" * 60)
        
        try:
            # 第一步：爬取数据
            products_data = await self.crawl_products()
            
            if not products_data:
                raise Exception("没有成功爬取到任何产品数据")
            
            print(f"\n📊 数据质量分析:")
            print(f"  • 产品数量: {len(products_data)}")
            print(f"  • BSR成功率: {(self.results['bsr_success_count'] / len(products_data)) * 100:.1f}%")
            
            # 第二步：保存到数据库
            self.save_to_database(products_data)
            
            # 第三步：生成验证报告
            report = self.generate_validation_report()
            
            print("\n" + "=" * 60)
            print("📋 快速验证完成")
            print("=" * 60)
            print(f"✅ 成功率: {report['test_summary']['success_rate']:.1f}%")
            print(f"✅ BSR数据可用率: {report['data_quality_metrics']['bsr_data_availability']:.1f}%")
            print(f"✅ 平均数据完整度: {report['data_quality_metrics']['average_data_completeness']:.1f}%")
            
            # 系统验证状态
            validation = report['system_validation']
            print(f"\n🔍 系统功能验证:")
            print(f"  • 爬虫功能: {'✅' if validation['crawler_functional'] else '❌'}")
            print(f"  • 数据库集成: {'✅' if validation['database_integration'] else '❌'}")
            print(f"  • 竞品关系: {'✅' if validation['competitor_relationships'] else '❌'}")
            print(f"  • 数据标准化: {'✅' if validation['data_standardization'] else '❌'}")
            
            return report
            
        except Exception as e:
            print(f"\n❌ 验证过程发生错误: {e}")
            report = self.generate_validation_report()
            report['error'] = str(e)
            return report


async def main():
    """主函数"""
    importer = QuickTestImporter()
    
    try:
        report = await importer.run_validation()
        
        # 保存报告到文件
        report_file = "/Users/elias/code/amazon-test-case/logs/quick_validation_report.json"
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n📄 详细报告已保存至: {report_file}")
        
        # 判断验证是否成功
        if (report['test_summary']['success_rate'] >= 80 and 
            report['data_quality_metrics']['bsr_data_availability'] >= 80):
            print("\n🎉 系统验证成功！可以继续进行完整Demo实施。")
            return True
        else:
            print("\n⚠️  系统验证发现问题，需要进一步调查。")
            return False
        
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        return False


if __name__ == "__main__":
    # 运行快速验证
    success = asyncio.run(main())