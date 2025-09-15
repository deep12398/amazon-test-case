"""竞品数据管理器 - 处理竞品数据的采集、转换和标准化"""

import json
import re
import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional, Dict, Tuple
from urllib.parse import urlparse, parse_qs

import logging

from ..crawlers.apify_client import ApifyAmazonScraper
from ..database.connection import get_db_session
from ..database.models.product import (
    Product, 
    CompetitorSet, 
    CompetitorRelationship,
    CompetitorSetStatus,
    CompetitorRelationshipType,
    MarketplaceType,
    ProductStatus,
    TrackingFrequency
)

logger = logging.getLogger(__name__)


@dataclass
class StandardizedCompetitorData:
    """标准化的竞品数据格式"""
    asin: str
    title: str
    brand: Optional[str]
    price: Optional[float]
    list_price: Optional[float]
    rating: Optional[float]
    review_count: int
    rank: Optional[int]
    category: Optional[str]
    image_url: Optional[str]
    product_url: str
    availability: Optional[str]
    bullet_points: List[str]
    description: Optional[str]
    marketplace: str
    seller_info: Dict[str, Any]
    variations: List[Dict[str, Any]]
    crawled_at: datetime
    source_data: Dict[str, Any]


class URLProcessor:
    """URL处理器 - 从Amazon URL中提取ASIN"""
    
    @staticmethod
    def extract_asin_from_url(url: str) -> Optional[str]:
        """从Amazon URL中提取ASIN"""
        try:
            # 常见的Amazon URL模式
            patterns = [
                r'/dp/([A-Z0-9]{10})',           # /dp/ASIN
                r'/gp/product/([A-Z0-9]{10})',   # /gp/product/ASIN
                r'/product/([A-Z0-9]{10})',      # /product/ASIN
                r'asin=([A-Z0-9]{10})',          # ?asin=ASIN
                r'/([A-Z0-9]{10})(?:/|$|\?)',    # 直接的ASIN
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url, re.IGNORECASE)
                if match:
                    asin = match.group(1).upper()
                    # 验证ASIN格式（10位字母数字）
                    if len(asin) == 10 and asin.isalnum():
                        return asin
            
            logger.warning(f"Could not extract ASIN from URL: {url}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting ASIN from URL {url}: {e}")
            return None
    
    @staticmethod
    def detect_marketplace(url: str) -> MarketplaceType:
        """从URL检测市场类型"""
        url_lower = url.lower()
        
        if 'amazon.co.uk' in url_lower:
            return MarketplaceType.AMAZON_UK
        elif 'amazon.de' in url_lower:
            return MarketplaceType.AMAZON_DE
        elif 'amazon.fr' in url_lower:
            return MarketplaceType.AMAZON_FR
        elif 'amazon.co.jp' in url_lower:
            return MarketplaceType.AMAZON_JP
        elif 'amazon.ca' in url_lower:
            return MarketplaceType.AMAZON_CA
        elif 'amazon.com.au' in url_lower:
            return MarketplaceType.AMAZON_AU
        elif 'amazon.in' in url_lower:
            return MarketplaceType.AMAZON_IN
        else:
            return MarketplaceType.AMAZON_US
    
    @staticmethod
    def extract_urls_from_text(text: str) -> List[str]:
        """从文本中提取Amazon URL"""
        url_pattern = r'https?://(?:www\.)?amazon\.(?:com|co\.uk|de|fr|co\.jp|ca|com\.au|in)[^\s<>"\']*'
        urls = re.findall(url_pattern, text, re.IGNORECASE)
        return list(set(urls))  # 去重


class DataNormalizer:
    """数据标准化器"""
    
    @staticmethod
    def normalize_price(price_value: Any) -> Optional[float]:
        """标准化价格数据"""
        if price_value is None:
            return None
        
        try:
            # 如果已经是数字
            if isinstance(price_value, (int, float)):
                return float(price_value)
            
            # 如果是字符串，清理并转换
            if isinstance(price_value, str):
                # 移除货币符号和逗号
                clean_price = re.sub(r'[^\d.]', '', price_value)
                if clean_price:
                    return float(clean_price)
            
            return None
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def normalize_rating(rating_value: Any) -> Optional[float]:
        """标准化评分数据"""
        if rating_value is None:
            return None
        
        try:
            rating = float(rating_value)
            # 评分应该在0-5之间
            if 0 <= rating <= 5:
                return rating
            return None
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def normalize_review_count(review_count_value: Any) -> int:
        """标准化评论数量"""
        if review_count_value is None:
            return 0
        
        try:
            if isinstance(review_count_value, (int, float)):
                return int(review_count_value)
            
            if isinstance(review_count_value, str):
                # 移除逗号和其他非数字字符
                clean_count = re.sub(r'[^\d]', '', review_count_value)
                if clean_count:
                    return int(clean_count)
            
            return 0
        except (ValueError, TypeError):
            return 0
    
    @staticmethod
    def normalize_rank(rank_value: Any) -> Optional[int]:
        """标准化排名数据"""
        if rank_value is None:
            return None
        
        try:
            if isinstance(rank_value, (int, float)):
                return int(rank_value)
            
            if isinstance(rank_value, str):
                # 移除#号和逗号，提取第一个数字
                clean_rank = re.sub(r'[^\d]', '', rank_value.split()[0] if rank_value.split() else rank_value)
                if clean_rank:
                    return int(clean_rank)
            
            return None
        except (ValueError, TypeError, IndexError):
            return None


class CompetitorDataManager:
    """竞品数据管理器"""
    
    def __init__(self):
        self.scraper = ApifyAmazonScraper()
        self.url_processor = URLProcessor()
        self.normalizer = DataNormalizer()
    
    async def process_competitor_urls(
        self, 
        urls: List[str],
        tenant_id: str
    ) -> Tuple[List[StandardizedCompetitorData], List[str]]:
        """处理竞品URL列表，返回标准化数据和错误列表"""
        
        standardized_data = []
        errors = []
        
        # 提取ASIN
        asins = []
        url_to_asin = {}
        
        for url in urls:
            asin = self.url_processor.extract_asin_from_url(url)
            if asin:
                asins.append(asin)
                url_to_asin[asin] = url
            else:
                errors.append(f"Could not extract ASIN from URL: {url}")
        
        if not asins:
            return [], errors
        
        # 爬取数据
        try:
            crawl_result = await self.scraper.scrape_multiple_products(asins)
            
            if not crawl_result.success:
                errors.append(f"Failed to crawl products: {crawl_result.error}")
                return [], errors
            
            products_data = crawl_result.data.get('products', [])
            
            for product_data in products_data:
                try:
                    standardized = self.standardize_product_data(
                        product_data, 
                        url_to_asin.get(product_data.get('asin', ''), '')
                    )
                    if standardized:
                        standardized_data.append(standardized)
                except Exception as e:
                    errors.append(f"Error processing product {product_data.get('asin', 'unknown')}: {str(e)}")
        
        except Exception as e:
            errors.append(f"Crawling failed: {str(e)}")
        
        return standardized_data, errors
    
    def process_raw_competitor_data(
        self, 
        raw_data: List[Dict[str, Any]]
    ) -> List[StandardizedCompetitorData]:
        """处理原始竞品数据（如用户提供的示例数据）"""
        
        standardized_data = []
        
        for item in raw_data:
            try:
                standardized = self.standardize_raw_data(item)
                if standardized:
                    standardized_data.append(standardized)
            except Exception as e:
                logger.error(f"Error processing raw data item: {e}")
                continue
        
        return standardized_data
    
    def standardize_product_data(
        self, 
        product_data: Dict[str, Any],
        original_url: str = ""
    ) -> Optional[StandardizedCompetitorData]:
        """标准化产品数据"""
        
        try:
            # 必需字段验证
            asin = product_data.get('asin')
            if not asin:
                return None
            
            title = product_data.get('title', '')
            if not title:
                return None
            
            # 标准化各个字段
            price = self.normalizer.normalize_price(product_data.get('price'))
            list_price = self.normalizer.normalize_price(product_data.get('list_price'))
            rating = self.normalizer.normalize_rating(product_data.get('rating'))
            review_count = self.normalizer.normalize_review_count(product_data.get('review_count'))
            rank = self.normalizer.normalize_rank(product_data.get('rank'))
            
            # 构建标准化数据
            standardized = StandardizedCompetitorData(
                asin=asin.upper(),
                title=title.strip(),
                brand=product_data.get('brand', '').strip() if product_data.get('brand') else None,
                price=price,
                list_price=list_price,
                rating=rating,
                review_count=review_count,
                rank=rank,
                category=product_data.get('category', '').strip() if product_data.get('category') else None,
                image_url=product_data.get('image_url'),
                product_url=original_url or product_data.get('url', f"https://amazon.com/dp/{asin}"),
                availability=product_data.get('availability'),
                bullet_points=product_data.get('features', []) or [],
                description=product_data.get('description'),
                marketplace=self.url_processor.detect_marketplace(original_url).value if original_url else 'amazon_us',
                seller_info=product_data.get('seller_info', {}),
                variations=product_data.get('variations', []),
                crawled_at=datetime.utcnow(),
                source_data=product_data
            )
            
            return standardized
            
        except Exception as e:
            logger.error(f"Error standardizing product data for ASIN {product_data.get('asin')}: {e}")
            return None
    
    def standardize_raw_data(self, raw_item: Dict[str, Any]) -> Optional[StandardizedCompetitorData]:
        """标准化原始数据（用于处理用户提供的示例数据格式）"""
        
        try:
            # 处用户提供的数据格式
            asin = raw_item.get('asin')
            if not asin:
                return None
            
            title = raw_item.get('title', '')
            if not title:
                return None
            
            # 处理价格（可能是 'price.value' 格式）
            price_value = raw_item.get('price.value') or raw_item.get('price')
            price = self.normalizer.normalize_price(price_value)
            
            # 处理评分
            rating = self.normalizer.normalize_rating(raw_item.get('stars') or raw_item.get('rating'))
            
            # 处理评论数量
            review_count = self.normalizer.normalize_review_count(
                raw_item.get('reviewsCount') or raw_item.get('review_count')
            )
            
            # 从URL提取市场类型
            url = raw_item.get('url', '')
            marketplace = self.url_processor.detect_marketplace(url) if url else MarketplaceType.AMAZON_US
            
            # 构建标准化数据
            standardized = StandardizedCompetitorData(
                asin=asin.upper(),
                title=title.strip(),
                brand=raw_item.get('brand', '').strip() if raw_item.get('brand') else None,
                price=price,
                list_price=None,  # 原始数据中可能不包含
                rating=rating,
                review_count=review_count,
                rank=None,  # 原始数据中可能不包含BSR
                category=raw_item.get('breadCrumbs', '').strip() if raw_item.get('breadCrumbs') else None,
                image_url=raw_item.get('thumbnailImage'),
                product_url=url,
                availability=None,
                bullet_points=[],  # 原始数据中可能不包含
                description=raw_item.get('description'),
                marketplace=marketplace.value,
                seller_info={},
                variations=[],
                crawled_at=datetime.utcnow(),
                source_data=raw_item
            )
            
            return standardized
            
        except Exception as e:
            logger.error(f"Error standardizing raw data for item {raw_item.get('asin', 'unknown')}: {e}")
            return None
    
    async def create_competitor_set(
        self,
        main_product_id: int,
        competitor_data: List[StandardizedCompetitorData],
        set_name: str,
        description: str = "",
        tenant_id: str = "",
        auto_create_products: bool = True
    ) -> Tuple[Optional[CompetitorSet], List[str]]:
        """创建竞品集合"""
        
        errors = []
        
        try:
            with get_db_session() as db:
                # 验证主产品存在
                main_product = db.query(Product).filter(
                    Product.id == main_product_id,
                    Product.tenant_id == tenant_id
                ).first()
                
                if not main_product:
                    errors.append(f"Main product {main_product_id} not found")
                    return None, errors
                
                # 创建竞品集
                competitor_set = CompetitorSet(
                    tenant_id=tenant_id,
                    name=set_name,
                    description=description,
                    main_product_id=main_product_id,
                    status=CompetitorSetStatus.ACTIVE,
                    is_default=True,  # 如果这是第一个竞品集
                    max_competitors=len(competitor_data)
                )
                
                db.add(competitor_set)
                db.flush()  # 获取ID
                
                # 处理竞品数据
                for data in competitor_data:
                    try:
                        # 查找或创建竞品产品
                        competitor_product = db.query(Product).filter(
                            Product.asin == data.asin,
                            Product.tenant_id == tenant_id
                        ).first()
                        
                        if not competitor_product and auto_create_products:
                            competitor_product = Product(
                                tenant_id=tenant_id,
                                asin=data.asin,
                                title=data.title,
                                brand=data.brand,
                                category=data.category,
                                marketplace=MarketplaceType(data.marketplace),
                                product_url=data.product_url,
                                image_url=data.image_url,
                                current_price=data.price,
                                current_rating=data.rating,
                                current_review_count=data.review_count,
                                current_rank=data.rank,
                                current_availability=data.availability,
                                bullet_points=data.bullet_points,
                                description=data.description,
                                is_competitor=True,
                                status=ProductStatus.ACTIVE,
                                tracking_frequency=TrackingFrequency.WEEKLY,
                                product_data=data.source_data
                            )
                            db.add(competitor_product)
                            db.flush()
                        
                        if competitor_product:
                            # 创建竞品关系
                            relationship = CompetitorRelationship(
                                tenant_id=tenant_id,
                                competitor_set_id=competitor_set.id,
                                competitor_product_id=competitor_product.id,
                                relationship_type=CompetitorRelationshipType.DIRECT,
                                priority=1,
                                weight=1.0,
                                is_active=True,
                                manually_added=True,
                                added_by_url=data.product_url,
                                source="manual_import"
                            )
                            db.add(relationship)
                    
                    except Exception as e:
                        errors.append(f"Error processing competitor {data.asin}: {str(e)}")
                        continue
                
                db.commit()
                return competitor_set, errors
                
        except Exception as e:
            logger.error(f"Error creating competitor set: {e}")
            errors.append(f"Failed to create competitor set: {str(e)}")
            return None, errors
    
    def detect_duplicates(self, data_list: List[StandardizedCompetitorData]) -> Dict[str, List[StandardizedCompetitorData]]:
        """检测重复的竞品数据（同一ASIN不同卖家）"""
        
        duplicates = {}
        
        for data in data_list:
            asin = data.asin
            if asin in duplicates:
                duplicates[asin].append(data)
            else:
                duplicates[asin] = [data]
        
        # 只返回有重复的
        return {k: v for k, v in duplicates.items() if len(v) > 1}
    
    def consolidate_duplicates(
        self, 
        duplicates: List[StandardizedCompetitorData]
    ) -> StandardizedCompetitorData:
        """合并重复数据，选择最佳价格和信息"""
        
        if len(duplicates) == 1:
            return duplicates[0]
        
        # 选择最低价格的作为主要数据
        primary = min(duplicates, key=lambda x: x.price or float('inf'))
        
        # 合并信息
        all_prices = [d.price for d in duplicates if d.price is not None]
        
        # 创建合并后的数据
        consolidated = StandardizedCompetitorData(
            asin=primary.asin,
            title=primary.title,
            brand=primary.brand,
            price=min(all_prices) if all_prices else None,
            list_price=primary.list_price,
            rating=primary.rating,
            review_count=primary.review_count,
            rank=primary.rank,
            category=primary.category,
            image_url=primary.image_url,
            product_url=primary.product_url,
            availability=primary.availability,
            bullet_points=primary.bullet_points,
            description=primary.description,
            marketplace=primary.marketplace,
            seller_info={
                "multiple_sellers": True,
                "price_range": {"min": min(all_prices), "max": max(all_prices)} if all_prices else None,
                "seller_count": len(duplicates)
            },
            variations=primary.variations,
            crawled_at=primary.crawled_at,
            source_data={
                **primary.source_data,
                "consolidated_from": len(duplicates),
                "all_prices": all_prices
            }
        )
        
        return consolidated