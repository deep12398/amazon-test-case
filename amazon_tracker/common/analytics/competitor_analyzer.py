"""竞品分析引擎"""

import logging
import re
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict

from sqlalchemy.orm import Session

from ..ai.report_generator import CompetitorReportGenerator
from ..crawlers.apify_client import ApifyAmazonScraper
from ..crawlers.data_processor import AmazonDataProcessor
from ..database.connection import get_db_session
from ..database.models.product import (
    Product, ProductPriceHistory, ProductRankHistory,
    CompetitorSet, CompetitorRelationship, CompetitorAnalysisSnapshot
)
from .competitor_data_manager import CompetitorDataManager, StandardizedCompetitorData

logger = logging.getLogger(__name__)


@dataclass
class CompetitorProduct:
    """竞品产品信息"""

    asin: str
    title: str
    brand: Optional[str]
    price: Optional[float]
    rating: Optional[float]
    review_count: int
    rank: Optional[int]
    category: Optional[str]
    image_url: Optional[str]
    features: list[str]
    availability: Optional[str]
    competitive_score: float = 0.0
    similarity_score: float = 0.0


@dataclass
class CompetitorAnalysis:
    """竞品分析结果"""

    analysis_id: str
    main_product: CompetitorProduct
    competitors: list[CompetitorProduct]
    insights: dict[str, Any]
    recommendations: list[str]
    market_position: str
    analysis_type: str
    created_at: datetime
    ai_report: Optional[dict[str, Any]] = None  # LangChain生成的AI报告
    optimization_suggestions: Optional[dict[str, Any]] = None  # 优化建议


class CompetitorDiscovery:
    """竞品发现器"""

    def __init__(self):
        self.scraper = ApifyAmazonScraper()
        self.processor = AmazonDataProcessor()

    async def discover_competitors(
        self,
        product: Product,
        max_competitors: int = 10,
        discovery_methods: list[str] = None,
    ) -> list[str]:
        """发现竞品ASIN"""

        if discovery_methods is None:
            discovery_methods = ["category", "keywords", "brand"]

        competitor_asins = set()

        try:
            # 方法1: 基于分类搜索
            if "category" in discovery_methods and product.category:
                category_competitors = await self._discover_by_category(
                    product.category, product.marketplace, exclude_asin=product.asin
                )
                competitor_asins.update(category_competitors[: max_competitors // 2])

            # 方法2: 基于关键词搜索
            if "keywords" in discovery_methods and product.title:
                keyword_competitors = await self._discover_by_keywords(
                    product.title, product.marketplace, exclude_asin=product.asin
                )
                competitor_asins.update(keyword_competitors[: max_competitors // 2])

            # 方法3: 基于品牌搜索（寻找替代品牌）
            if "brand" in discovery_methods and product.brand:
                brand_competitors = await self._discover_alternative_brands(
                    product.category or "",
                    product.brand,
                    product.marketplace,
                    exclude_asin=product.asin,
                )
                competitor_asins.update(brand_competitors[: max_competitors // 3])

        except Exception as e:
            logger.error(f"Error discovering competitors: {e}")

        return list(competitor_asins)[:max_competitors]

    async def _discover_by_category(
        self, category: str, marketplace: str, exclude_asin: str
    ) -> list[str]:
        """基于分类发现竞品"""
        # 这里可以集成Amazon API或使用爬虫搜索
        # 暂时返回模拟数据
        return []

    async def _discover_by_keywords(
        self, title: str, marketplace: str, exclude_asin: str
    ) -> list[str]:
        """基于关键词发现竞品"""
        # 提取关键词
        keywords = self._extract_keywords(title)

        # 使用关键词搜索类似产品
        # 这里可以集成Amazon搜索API
        # 暂时返回模拟数据
        return []

    async def _discover_alternative_brands(
        self, category: str, brand: str, marketplace: str, exclude_asin: str
    ) -> list[str]:
        """发现替代品牌的竞品"""
        # 搜索同类别不同品牌的产品
        # 暂时返回模拟数据
        return []

    def _extract_keywords(self, title: str) -> list[str]:
        """从标题中提取关键词"""
        # 移除常见的停用词
        stop_words = {
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "amazon",
            "pack",
            "set",
            "new",
            "best",
            "top",
            "premium",
            "quality",
        }

        # 清理标题并提取单词
        clean_title = re.sub(r"[^\w\s]", " ", title.lower())
        words = [
            word
            for word in clean_title.split()
            if word not in stop_words and len(word) > 2
        ]

        return words[:10]  # 返回前10个关键词


class CompetitorAnalyzer:
    """竞品分析器"""

    def __init__(self):
        self.discovery = CompetitorDiscovery()
        self.scraper = ApifyAmazonScraper()
        self.processor = AmazonDataProcessor()
        self.report_generator = CompetitorReportGenerator()
        self.data_manager = CompetitorDataManager()

    async def analyze_competitors(
        self,
        product_id: int,
        tenant_id: str,
        analysis_type: str = "comprehensive",
        competitor_asins: Optional[list[str]] = None,
        auto_discover: bool = True,
        max_competitors: int = 10,
    ) -> CompetitorAnalysis:
        """执行竞品分析"""

        analysis_id = f"analysis_{datetime.utcnow().timestamp()}"

        with get_db_session() as db:
            # 获取主产品
            product = (
                db.query(Product)
                .filter(Product.id == product_id, Product.tenant_id == tenant_id)
                .first()
            )

            if not product:
                raise ValueError(f"Product {product_id} not found")

            # 创建主产品对象
            main_product = CompetitorProduct(
                asin=product.asin,
                title=product.title,
                brand=product.brand,
                price=product.current_price,
                rating=product.rating,
                review_count=product.review_count or 0,
                rank=product.current_rank,
                category=product.category,
                image_url=product.image_url,
                features=[],
                availability=product.availability,
            )

            # 获取竞品ASIN
            if not competitor_asins and auto_discover:
                competitor_asins = await self.discovery.discover_competitors(
                    product, max_competitors
                )

            competitor_asins = competitor_asins or []

            # 爬取竞品数据
            competitors = []
            if competitor_asins:
                competitor_data = await self._crawl_competitors(competitor_asins)

                for data in competitor_data:
                    competitor = CompetitorProduct(
                        asin=data.get("asin", ""),
                        title=data.get("title", ""),
                        brand=data.get("brand"),
                        price=data.get("price"),
                        rating=data.get("rating"),
                        review_count=data.get("review_count", 0),
                        rank=data.get("rank"),
                        category=data.get("category"),
                        image_url=data.get("image_url"),
                        features=data.get("features", []),
                        availability=data.get("availability"),
                    )

                    # 计算竞争力评分
                    competitor.competitive_score = self._calculate_competitive_score(
                        main_product, competitor
                    )

                    # 计算相似度评分
                    competitor.similarity_score = self._calculate_similarity_score(
                        main_product, competitor
                    )

                    competitors.append(competitor)

            # 执行分析
            insights = await self._generate_insights(
                main_product, competitors, analysis_type, db
            )

            recommendations = self._generate_recommendations(
                main_product, competitors, insights
            )

            market_position = self._determine_market_position(main_product, competitors)

            # 生成AI报告（如果是comprehensive分析）
            ai_report = None
            optimization_suggestions = None

            if analysis_type in ["comprehensive", "ai_enhanced"] and competitors:
                try:
                    # 转换为AI报告需要的格式
                    main_product_data = self._convert_to_dict(main_product)
                    competitors_data = [
                        self._convert_to_dict(comp) for comp in competitors
                    ]

                    # 生成竞品分析报告
                    ai_report = await self.report_generator.generate_competitor_report(
                        main_product=main_product_data,
                        competitors=competitors_data,
                        report_id=analysis_id,
                    )

                    # 生成优化建议
                    historical_data = await self._analyze_trends(main_product, db)
                    optimization_suggestions = (
                        await self.report_generator.generate_optimization_suggestions(
                            product_data=main_product_data,
                            competitor_insights=insights,
                            historical_data=historical_data,
                        )
                    )

                    logger.info(f"AI report generated for analysis {analysis_id}")

                except Exception as e:
                    logger.error(f"Failed to generate AI report: {e}")

            return CompetitorAnalysis(
                analysis_id=analysis_id,
                main_product=main_product,
                competitors=sorted(
                    competitors, key=lambda x: x.competitive_score, reverse=True
                ),
                insights=insights,
                recommendations=recommendations,
                market_position=market_position,
                analysis_type=analysis_type,
                created_at=datetime.utcnow(),
                ai_report=ai_report,
                optimization_suggestions=optimization_suggestions,
            )

    async def _crawl_competitors(self, asins: list[str]) -> list[dict[str, Any]]:
        """爬取竞品数据"""
        try:
            crawl_result = await self.scraper.scrape_multiple_products(asins)

            if crawl_result.success:
                raw_data = crawl_result.data.get("products", [])
                return self.processor.process_batch(raw_data)

        except Exception as e:
            logger.error(f"Error crawling competitors: {e}")

        return []

    def _calculate_competitive_score(
        self, main_product: CompetitorProduct, competitor: CompetitorProduct
    ) -> float:
        """计算竞争力评分"""
        score = 0.0

        # 价格竞争力 (30%)
        if main_product.price and competitor.price:
            price_ratio = competitor.price / main_product.price
            if price_ratio < 1:  # 竞品价格更低
                score += 30 * (1 - price_ratio)
            else:  # 竞品价格更高
                score += 30 * max(0, 1 - (price_ratio - 1) * 0.5)

        # 评分竞争力 (25%)
        if main_product.rating and competitor.rating:
            if competitor.rating > main_product.rating:
                score += 25 * (competitor.rating - main_product.rating) / 5

        # 评论数量竞争力 (20%)
        if main_product.review_count and competitor.review_count:
            review_ratio = competitor.review_count / max(main_product.review_count, 1)
            score += 20 * min(review_ratio, 2) / 2  # 最多得20分

        # 排名竞争力 (25%)
        if main_product.rank and competitor.rank:
            if competitor.rank < main_product.rank:  # 排名更好
                rank_improvement = (
                    main_product.rank - competitor.rank
                ) / main_product.rank
                score += 25 * min(rank_improvement, 1)

        return min(score, 100.0)

    def _calculate_similarity_score(
        self, main_product: CompetitorProduct, competitor: CompetitorProduct
    ) -> float:
        """计算相似度评分"""
        score = 0.0

        # 品牌相似性 (20%)
        if main_product.brand and competitor.brand:
            if main_product.brand.lower() == competitor.brand.lower():
                score += 20
            elif (
                main_product.brand.lower() in competitor.brand.lower()
                or competitor.brand.lower() in main_product.brand.lower()
            ):
                score += 10

        # 分类相似性 (30%)
        if main_product.category and competitor.category:
            if main_product.category.lower() == competitor.category.lower():
                score += 30
            elif (
                main_product.category.lower() in competitor.category.lower()
                or competitor.category.lower() in main_product.category.lower()
            ):
                score += 15

        # 标题相似性 (30%)
        if main_product.title and competitor.title:
            title_similarity = self._calculate_text_similarity(
                main_product.title, competitor.title
            )
            score += 30 * title_similarity

        # 价格区间相似性 (20%)
        if main_product.price and competitor.price:
            price_diff_percent = (
                abs(main_product.price - competitor.price) / main_product.price
            )
            if price_diff_percent < 0.1:  # 价格相差10%以内
                score += 20
            elif price_diff_percent < 0.3:  # 价格相差30%以内
                score += 10

        return min(score, 100.0)

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    async def _generate_insights(
        self,
        main_product: CompetitorProduct,
        competitors: list[CompetitorProduct],
        analysis_type: str,
        db: Session,
    ) -> dict[str, Any]:
        """生成分析洞察"""
        insights = {}

        if not competitors:
            return {
                "message": "No competitors found for analysis",
                "competitor_count": 0,
            }

        # 价格分析
        competitor_prices = [c.price for c in competitors if c.price]
        if competitor_prices and main_product.price:
            insights["pricing"] = {
                "avg_competitor_price": statistics.mean(competitor_prices),
                "min_competitor_price": min(competitor_prices),
                "max_competitor_price": max(competitor_prices),
                "main_product_price": main_product.price,
                "price_position": self._get_price_position(
                    main_product.price, competitor_prices
                ),
                "price_advantage": main_product.price
                < statistics.mean(competitor_prices),
            }

        # 评分分析
        competitor_ratings = [c.rating for c in competitors if c.rating]
        if competitor_ratings and main_product.rating:
            insights["rating"] = {
                "avg_competitor_rating": statistics.mean(competitor_ratings),
                "main_product_rating": main_product.rating,
                "rating_advantage": main_product.rating
                > statistics.mean(competitor_ratings),
                "rating_percentile": self._get_percentile(
                    main_product.rating, competitor_ratings
                ),
            }

        # 排名分析
        competitor_ranks = [c.rank for c in competitors if c.rank]
        if competitor_ranks and main_product.rank:
            insights["ranking"] = {
                "avg_competitor_rank": statistics.mean(competitor_ranks),
                "main_product_rank": main_product.rank,
                "rank_advantage": main_product.rank < statistics.mean(competitor_ranks),
                "rank_percentile": self._get_percentile(
                    main_product.rank, competitor_ranks, reverse=True
                ),
            }

        # 功能分析
        if analysis_type in ["features", "comprehensive"]:
            insights["features"] = await self._analyze_features(
                main_product, competitors
            )

        # 市场份额估算
        total_reviews = (
            sum(c.review_count for c in competitors) + main_product.review_count
        )
        if total_reviews > 0:
            insights["market_share"] = {
                "estimated_share": main_product.review_count / total_reviews * 100,
                "review_count": main_product.review_count,
                "total_market_reviews": total_reviews,
            }

        # 趋势分析（基于历史数据）
        insights["trends"] = await self._analyze_trends(main_product, db)

        insights["competitor_count"] = len(competitors)
        insights["analysis_date"] = datetime.utcnow().isoformat()

        return insights

    def _get_price_position(self, price: float, competitor_prices: list[float]) -> str:
        """获取价格位置"""
        sorted_prices = sorted(competitor_prices)
        position = sum(1 for p in sorted_prices if p < price) / len(sorted_prices)

        if position < 0.25:
            return "low"
        elif position < 0.75:
            return "medium"
        else:
            return "high"

    def _get_percentile(
        self, value: float, values: list[float], reverse: bool = False
    ) -> float:
        """获取百分位数"""
        if reverse:
            # 对于排名，数值越小越好
            better_count = sum(1 for v in values if v > value)
        else:
            # 对于评分，数值越大越好
            better_count = sum(1 for v in values if v < value)

        return better_count / len(values) * 100 if values else 50.0

    async def _analyze_features(
        self, main_product: CompetitorProduct, competitors: list[CompetitorProduct]
    ) -> dict[str, Any]:
        """分析产品功能"""
        all_features = set()
        for competitor in competitors:
            all_features.update(competitor.features)

        main_features = set(main_product.features)

        return {
            "unique_features": list(main_features - all_features),
            "missing_features": list(all_features - main_features),
            "common_features": list(main_features.intersection(all_features)),
            "feature_coverage": len(main_features) / len(all_features)
            if all_features
            else 0,
        }

    async def _analyze_trends(
        self, main_product: CompetitorProduct, db: Session
    ) -> dict[str, Any]:
        """分析趋势数据"""
        # 获取30天内的价格和排名趋势
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        # 价格趋势
        price_history = (
            db.query(ProductPriceHistory)
            .join(Product)
            .filter(
                Product.asin == main_product.asin,
                ProductPriceHistory.recorded_at >= thirty_days_ago,
            )
            .order_by(ProductPriceHistory.recorded_at)
            .all()
        )

        # 排名趋势
        rank_history = (
            db.query(ProductRankHistory)
            .join(Product)
            .filter(
                Product.asin == main_product.asin,
                ProductRankHistory.recorded_at >= thirty_days_ago,
            )
            .order_by(ProductRankHistory.recorded_at)
            .all()
        )

        trends = {}

        if len(price_history) >= 2:
            first_price = price_history[0].price
            last_price = price_history[-1].price
            if first_price and last_price:
                price_change = (last_price - first_price) / first_price * 100
                trends["price_trend"] = {
                    "change_percent": price_change,
                    "direction": "up"
                    if price_change > 0
                    else "down"
                    if price_change < 0
                    else "stable",
                    "data_points": len(price_history),
                }

        if len(rank_history) >= 2:
            first_rank = rank_history[0].rank
            last_rank = rank_history[-1].rank
            if first_rank and last_rank:
                rank_change = (
                    (first_rank - last_rank) / first_rank * 100
                )  # 排名降低是好事
                trends["rank_trend"] = {
                    "change_percent": rank_change,
                    "direction": "improved"
                    if rank_change > 0
                    else "declined"
                    if rank_change < 0
                    else "stable",
                    "data_points": len(rank_history),
                }

        return trends

    def _convert_to_dict(self, competitor_product: CompetitorProduct) -> dict[str, Any]:
        """将CompetitorProduct对象转换为字典格式"""
        return {
            "asin": competitor_product.asin,
            "title": competitor_product.title,
            "brand": competitor_product.brand,
            "price": competitor_product.price,
            "rating": competitor_product.rating,
            "review_count": competitor_product.review_count,
            "rank": competitor_product.rank,
            "category": competitor_product.category,
            "image_url": competitor_product.image_url,
            "features": competitor_product.features,
            "availability": competitor_product.availability,
            "competitive_score": competitor_product.competitive_score,
            "similarity_score": competitor_product.similarity_score,
        }

    def _generate_recommendations(
        self,
        main_product: CompetitorProduct,
        competitors: list[CompetitorProduct],
        insights: dict[str, Any],
    ) -> list[str]:
        """生成建议"""
        recommendations = []

        if not competitors:
            return ["Consider adding competitor ASINs for more detailed analysis"]

        # 价格建议
        pricing = insights.get("pricing", {})
        if pricing:
            if pricing.get("price_position") == "high":
                avg_price = pricing.get("avg_competitor_price")
                if avg_price:
                    recommendations.append(
                        f"Consider reducing price to be more competitive. "
                        f"Average competitor price is ${avg_price:.2f}"
                    )
            elif pricing.get("price_advantage"):
                recommendations.append(
                    "You have a price advantage over competitors. "
                    "Consider highlighting this in marketing."
                )

        # 评分建议
        rating = insights.get("rating", {})
        if rating and not rating.get("rating_advantage"):
            recommendations.append(
                "Focus on improving product quality and customer satisfaction "
                "to increase your rating above competitors."
            )

        # 排名建议
        ranking = insights.get("ranking", {})
        if ranking and not ranking.get("rank_advantage"):
            recommendations.append(
                "Consider optimizing your listing with better keywords, "
                "images, and customer reviews to improve ranking."
            )

        # 功能建议
        features = insights.get("features", {})
        if features:
            missing_features = features.get("missing_features", [])
            if missing_features:
                recommendations.append(
                    f"Consider adding these features that competitors have: "
                    f"{', '.join(missing_features[:3])}"
                )

            unique_features = features.get("unique_features", [])
            if unique_features:
                recommendations.append(
                    f"Highlight your unique features in marketing: "
                    f"{', '.join(unique_features[:3])}"
                )

        # 市场份额建议
        market_share = insights.get("market_share", {})
        if market_share and market_share.get("estimated_share", 0) < 10:
            recommendations.append(
                "Your estimated market share is low. "
                "Consider increasing marketing efforts and improving product visibility."
            )

        return recommendations

    def _determine_market_position(
        self, main_product: CompetitorProduct, competitors: list[CompetitorProduct]
    ) -> str:
        """确定市场定位"""
        if not competitors:
            return "unknown"

        # 基于竞争力评分确定位置
        competitor_scores = [c.competitive_score for c in competitors]

        if not competitor_scores:
            return "unknown"

        avg_score = statistics.mean(competitor_scores)
        max_score = max(competitor_scores)

        # 计算主产品相对于竞品的表现
        price_position = "unknown"
        rating_position = "unknown"

        if main_product.price:
            competitor_prices = [c.price for c in competitors if c.price]
            if competitor_prices:
                avg_competitor_price = statistics.mean(competitor_prices)
                if main_product.price < avg_competitor_price * 0.8:
                    price_position = "low"
                elif main_product.price > avg_competitor_price * 1.2:
                    price_position = "premium"
                else:
                    price_position = "mid"

        if main_product.rating:
            competitor_ratings = [c.rating for c in competitors if c.rating]
            if competitor_ratings:
                avg_competitor_rating = statistics.mean(competitor_ratings)
                if main_product.rating > avg_competitor_rating:
                    rating_position = "high"
                else:
                    rating_position = "low"

        # 确定整体市场定位
        if price_position == "premium" and rating_position == "high":
            return "premium_leader"
        elif price_position == "low" and rating_position == "high":
            return "value_leader"
        elif price_position == "mid" and rating_position == "high":
            return "market_leader"
        elif price_position == "low":
            return "budget_option"
        elif price_position == "premium":
            return "premium_option"
        else:
            return "follower"
    
    async def create_competitor_set_from_urls(
        self,
        main_product_id: int,
        competitor_urls: List[str],
        set_name: str,
        tenant_id: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """从竞品URL列表创建竞品集合"""
        
        try:
            # 处理URL并获取标准化数据
            standardized_data, errors = await self.data_manager.process_competitor_urls(
                competitor_urls, tenant_id
            )
            
            if not standardized_data:
                return {
                    "success": False,
                    "error": "No valid competitor data found",
                    "errors": errors
                }
            
            # 检测重复并合并
            duplicates = self.data_manager.detect_duplicates(standardized_data)
            if duplicates:
                # 合并重复项
                final_data = []
                processed_asins = set()
                
                for data in standardized_data:
                    if data.asin in processed_asins:
                        continue
                    
                    if data.asin in duplicates:
                        consolidated = self.data_manager.consolidate_duplicates(duplicates[data.asin])
                        final_data.append(consolidated)
                    else:
                        final_data.append(data)
                    
                    processed_asins.add(data.asin)
                
                standardized_data = final_data
            
            # 创建竞品集合
            competitor_set, creation_errors = await self.data_manager.create_competitor_set(
                main_product_id=main_product_id,
                competitor_data=standardized_data,
                set_name=set_name,
                description=description,
                tenant_id=tenant_id
            )
            
            if competitor_set:
                return {
                    "success": True,
                    "competitor_set_id": competitor_set.id,
                    "competitor_count": len(standardized_data),
                    "duplicates_found": len(duplicates),
                    "errors": errors + creation_errors
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create competitor set",
                    "errors": errors + creation_errors
                }
        
        except Exception as e:
            logger.error(f"Error creating competitor set from URLs: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def create_competitor_set_from_raw_data(
        self,
        main_product_id: int,
        raw_competitor_data: List[Dict[str, Any]],
        set_name: str,
        tenant_id: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """从原始竞品数据创建竞品集合（处理用户提供的示例数据格式）"""
        
        try:
            # 标准化原始数据
            standardized_data = self.data_manager.process_raw_competitor_data(raw_competitor_data)
            
            if not standardized_data:
                return {
                    "success": False,
                    "error": "No valid competitor data found in raw data"
                }
            
            # 检测重复并合并
            duplicates = self.data_manager.detect_duplicates(standardized_data)
            if duplicates:
                final_data = []
                processed_asins = set()
                
                for data in standardized_data:
                    if data.asin in processed_asins:
                        continue
                    
                    if data.asin in duplicates:
                        consolidated = self.data_manager.consolidate_duplicates(duplicates[data.asin])
                        final_data.append(consolidated)
                    else:
                        final_data.append(data)
                    
                    processed_asins.add(data.asin)
                
                standardized_data = final_data
            
            # 创建竞品集合
            competitor_set, errors = await self.data_manager.create_competitor_set(
                main_product_id=main_product_id,
                competitor_data=standardized_data,
                set_name=set_name,
                description=description,
                tenant_id=tenant_id
            )
            
            if competitor_set:
                return {
                    "success": True,
                    "competitor_set_id": competitor_set.id,
                    "competitor_count": len(standardized_data),
                    "duplicates_found": len(duplicates),
                    "processed_items": len(raw_competitor_data),
                    "errors": errors
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create competitor set",
                    "errors": errors
                }
        
        except Exception as e:
            logger.error(f"Error creating competitor set from raw data: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def analyze_competitor_set(
        self,
        competitor_set_id: int,
        tenant_id: str,
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """分析特定的竞品集合"""
        
        try:
            with get_db_session() as db:
                # 获取竞品集合
                competitor_set = db.query(CompetitorSet).filter(
                    CompetitorSet.id == competitor_set_id,
                    CompetitorSet.tenant_id == tenant_id
                ).first()
                
                if not competitor_set:
                    return {
                        "success": False,
                        "error": "Competitor set not found"
                    }
                
                # 获取主产品
                main_product = competitor_set.main_product
                
                # 获取竞品关系
                relationships = db.query(CompetitorRelationship).filter(
                    CompetitorRelationship.competitor_set_id == competitor_set_id,
                    CompetitorRelationship.is_active == True
                ).all()
                
                if not relationships:
                    return {
                        "success": False,
                        "error": "No active competitors found in set"
                    }
                
                # 构建竞品数据
                competitors = []
                for rel in relationships:
                    competitor_product = rel.competitor_product
                    competitor = CompetitorProduct(
                        asin=competitor_product.asin,
                        title=competitor_product.title,
                        brand=competitor_product.brand,
                        price=competitor_product.current_price,
                        rating=competitor_product.current_rating,
                        review_count=competitor_product.current_review_count or 0,
                        rank=competitor_product.current_rank,
                        category=competitor_product.category,
                        image_url=competitor_product.image_url,
                        features=competitor_product.bullet_points or [],
                        availability=competitor_product.current_availability,
                        competitive_score=rel.competitive_score or 0.0,
                        similarity_score=rel.similarity_score or 0.0
                    )
                    competitors.append(competitor)
                
                # 构建主产品对象
                main_product_obj = CompetitorProduct(
                    asin=main_product.asin,
                    title=main_product.title,
                    brand=main_product.brand,
                    price=main_product.current_price,
                    rating=main_product.current_rating,
                    review_count=main_product.current_review_count or 0,
                    rank=main_product.current_rank,
                    category=main_product.category,
                    image_url=main_product.image_url,
                    features=main_product.bullet_points or [],
                    availability=main_product.current_availability
                )
                
                # 执行分析
                analysis_id = f"set_analysis_{competitor_set_id}_{datetime.utcnow().timestamp()}"
                
                insights = await self._generate_insights(
                    main_product_obj, competitors, analysis_type, db
                )
                
                recommendations = self._generate_recommendations(
                    main_product_obj, competitors, insights
                )
                
                market_position = self._determine_market_position(main_product_obj, competitors)
                
                # 生成AI报告
                ai_report = None
                optimization_suggestions = None
                
                if analysis_type in ["comprehensive", "ai_enhanced"]:
                    try:
                        main_product_data = self._convert_to_dict(main_product_obj)
                        competitors_data = [self._convert_to_dict(comp) for comp in competitors]
                        
                        ai_report = await self.report_generator.generate_competitor_report(
                            main_product=main_product_data,
                            competitors=competitors_data,
                            report_id=analysis_id
                        )
                        
                        historical_data = await self._analyze_trends(main_product_obj, db)
                        optimization_suggestions = await self.report_generator.generate_optimization_suggestions(
                            product_data=main_product_data,
                            competitor_insights=insights,
                            historical_data=historical_data
                        )
                    
                    except Exception as e:
                        logger.error(f"Failed to generate AI report: {e}")
                
                # 保存分析结果
                analysis_snapshot = CompetitorAnalysisSnapshot(
                    tenant_id=tenant_id,
                    analysis_id=analysis_id,
                    competitor_set_id=competitor_set_id,
                    analysis_type=analysis_type,
                    insights=insights,
                    recommendations=recommendations,
                    market_position=market_position,
                    ai_report=ai_report,
                    optimization_suggestions=optimization_suggestions,
                    competitor_count=len(competitors)
                )
                
                db.add(analysis_snapshot)
                
                # 更新竞品集合的最后分析时间
                competitor_set.last_analysis_at = datetime.utcnow()
                competitor_set.last_analysis_id = analysis_id
                
                db.commit()
                
                return {
                    "success": True,
                    "analysis_id": analysis_id,
                    "competitor_set_id": competitor_set_id,
                    "main_product": main_product_data if 'main_product_data' in locals() else self._convert_to_dict(main_product_obj),
                    "competitors": competitors_data if 'competitors_data' in locals() else [self._convert_to_dict(comp) for comp in competitors],
                    "insights": insights,
                    "recommendations": recommendations,
                    "market_position": market_position,
                    "ai_report": ai_report,
                    "optimization_suggestions": optimization_suggestions,
                    "competitor_count": len(competitors)
                }
        
        except Exception as e:
            logger.error(f"Error analyzing competitor set {competitor_set_id}: {e}")
            return {
                "success": False,
                "error": f"Analysis failed: {str(e)}"
            }
    
    def get_competitor_sets_for_product(
        self,
        product_id: int,
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """获取产品的所有竞品集合"""
        
        try:
            with get_db_session() as db:
                competitor_sets = db.query(CompetitorSet).filter(
                    CompetitorSet.main_product_id == product_id,
                    CompetitorSet.tenant_id == tenant_id,
                    CompetitorSet.status.in_(['ACTIVE', 'INACTIVE'])
                ).all()
                
                result = []
                for cs in competitor_sets:
                    competitor_count = db.query(CompetitorRelationship).filter(
                        CompetitorRelationship.competitor_set_id == cs.id,
                        CompetitorRelationship.is_active == True
                    ).count()
                    
                    result.append({
                        "id": cs.id,
                        "name": cs.name,
                        "description": cs.description,
                        "status": cs.status.value,
                        "is_default": cs.is_default,
                        "competitor_count": competitor_count,
                        "last_analysis_at": cs.last_analysis_at,
                        "last_analysis_id": cs.last_analysis_id,
                        "created_at": cs.created_at
                    })
                
                return result
        
        except Exception as e:
            logger.error(f"Error getting competitor sets for product {product_id}: {e}")
            return []
    
    async def enhanced_multi_dimensional_analysis(
        self,
        main_product: CompetitorProduct,
        competitors: List[CompetitorProduct]
    ) -> Dict[str, Any]:
        """增强的多维度分析"""
        
        analysis = {
            "price_analysis": self._analyze_price_competitiveness(main_product, competitors),
            "bsr_analysis": self._analyze_bsr_performance(main_product, competitors),
            "rating_analysis": self._analyze_rating_advantage(main_product, competitors),
            "feature_analysis": self._analyze_feature_comparison(main_product, competitors),
            "market_positioning": self._analyze_market_positioning(main_product, competitors),
            "competitive_gaps": self._identify_competitive_gaps(main_product, competitors),
            "opportunity_matrix": self._generate_opportunity_matrix(main_product, competitors)
        }
        
        return analysis
    
    def _analyze_price_competitiveness(
        self,
        main_product: CompetitorProduct,
        competitors: List[CompetitorProduct]
    ) -> Dict[str, Any]:
        """价格竞争力分析"""
        
        competitor_prices = [c.price for c in competitors if c.price]
        
        if not competitor_prices or not main_product.price:
            return {"status": "insufficient_data"}
        
        analysis = {
            "main_product_price": main_product.price,
            "competitor_price_range": {
                "min": min(competitor_prices),
                "max": max(competitor_prices),
                "avg": statistics.mean(competitor_prices),
                "median": statistics.median(competitor_prices)
            },
            "price_percentile": self._get_percentile(main_product.price, competitor_prices),
            "competitive_advantage": main_product.price < statistics.mean(competitor_prices),
            "price_gap_analysis": {
                "to_lowest": main_product.price - min(competitor_prices),
                "to_average": main_product.price - statistics.mean(competitor_prices)
            }
        }
        
        # 价格策略建议
        if analysis["price_percentile"] > 75:
            analysis["strategy"] = "premium_pricing"
            analysis["recommendation"] = "Consider justifying premium with unique features"
        elif analysis["price_percentile"] < 25:
            analysis["strategy"] = "value_pricing"
            analysis["recommendation"] = "Leverage price advantage in marketing"
        else:
            analysis["strategy"] = "competitive_pricing"
            analysis["recommendation"] = "Monitor competitors for price changes"
        
        return analysis
    
    def _analyze_bsr_performance(
        self,
        main_product: CompetitorProduct,
        competitors: List[CompetitorProduct]
    ) -> Dict[str, Any]:
        """BSR排名表现分析"""
        
        competitor_ranks = [c.rank for c in competitors if c.rank]
        
        if not competitor_ranks or not main_product.rank:
            return {"status": "insufficient_data"}
        
        analysis = {
            "main_product_rank": main_product.rank,
            "competitor_rank_range": {
                "best": min(competitor_ranks),
                "worst": max(competitor_ranks),
                "avg": statistics.mean(competitor_ranks),
                "median": statistics.median(competitor_ranks)
            },
            "rank_percentile": self._get_percentile(main_product.rank, competitor_ranks, reverse=True),
            "competitive_advantage": main_product.rank < statistics.mean(competitor_ranks)
        }
        
        # 排名改进机会
        if analysis["rank_percentile"] < 50:
            analysis["opportunity"] = "high"
            analysis["recommendation"] = "Focus on listing optimization and marketing"
        elif analysis["rank_percentile"] < 75:
            analysis["opportunity"] = "medium"
            analysis["recommendation"] = "Incremental improvements in visibility"
        else:
            analysis["opportunity"] = "low"
            analysis["recommendation"] = "Maintain current position"
        
        return analysis
    
    def _analyze_rating_advantage(
        self,
        main_product: CompetitorProduct,
        competitors: List[CompetitorProduct]
    ) -> Dict[str, Any]:
        """评分优势分析"""
        
        competitor_ratings = [c.rating for c in competitors if c.rating]
        competitor_reviews = [c.review_count for c in competitors if c.review_count]
        
        if not competitor_ratings or not main_product.rating:
            return {"status": "insufficient_data"}
        
        analysis = {
            "main_product_rating": main_product.rating,
            "main_product_reviews": main_product.review_count,
            "competitor_rating_stats": {
                "avg": statistics.mean(competitor_ratings),
                "min": min(competitor_ratings),
                "max": max(competitor_ratings)
            },
            "rating_advantage": main_product.rating > statistics.mean(competitor_ratings),
            "review_volume_advantage": main_product.review_count > statistics.mean(competitor_reviews) if competitor_reviews else False
        }
        
        # 信任度分析
        rating_weight = main_product.rating * (1 + min(main_product.review_count / 1000, 2))
        competitor_trust_scores = []
        for i, rating in enumerate(competitor_ratings):
            review_count = competitor_reviews[i] if i < len(competitor_reviews) else 0
            trust_score = rating * (1 + min(review_count / 1000, 2))
            competitor_trust_scores.append(trust_score)
        
        analysis["trust_score"] = rating_weight
        analysis["avg_competitor_trust"] = statistics.mean(competitor_trust_scores) if competitor_trust_scores else 0
        analysis["trust_advantage"] = rating_weight > statistics.mean(competitor_trust_scores) if competitor_trust_scores else True
        
        return analysis
    
    def _analyze_feature_comparison(
        self,
        main_product: CompetitorProduct,
        competitors: List[CompetitorProduct]
    ) -> Dict[str, Any]:
        """特征对比分析"""
        
        # 收集所有特征
        all_features = set()
        for competitor in competitors:
            all_features.update(competitor.features)
        
        main_features = set(main_product.features)
        
        analysis = {
            "unique_features": list(main_features - all_features),
            "missing_features": list(all_features - main_features),
            "common_features": list(main_features.intersection(all_features)),
            "feature_coverage": len(main_features) / len(all_features) if all_features else 0,
            "differentiation_score": len(main_features - all_features) / len(all_features) if all_features else 0
        }
        
        # 特征频次分析
        feature_frequency = {}
        for competitor in competitors:
            for feature in competitor.features:
                feature_frequency[feature] = feature_frequency.get(feature, 0) + 1
        
        # 识别重要缺失特征（超过50%竞品都有的特征）
        important_missing = []
        for feature in analysis["missing_features"]:
            if feature_frequency.get(feature, 0) > len(competitors) * 0.5:
                important_missing.append({
                    "feature": feature,
                    "competitor_coverage": feature_frequency[feature] / len(competitors)
                })
        
        analysis["important_missing_features"] = important_missing
        
        return analysis
    
    def _analyze_market_positioning(
        self,
        main_product: CompetitorProduct,
        competitors: List[CompetitorProduct]
    ) -> Dict[str, Any]:
        """市场定位分析"""
        
        # 价格-质量矩阵
        price_quality_map = []
        if main_product.price and main_product.rating:
            price_quality_map.append({
                "product": "main",
                "asin": main_product.asin,
                "price": main_product.price,
                "quality": main_product.rating,
                "reviews": main_product.review_count
            })
        
        for comp in competitors:
            if comp.price and comp.rating:
                price_quality_map.append({
                    "product": "competitor",
                    "asin": comp.asin,
                    "price": comp.price,
                    "quality": comp.rating,
                    "reviews": comp.review_count
                })
        
        # 市场象限分析
        if price_quality_map:
            prices = [item["price"] for item in price_quality_map]
            qualities = [item["quality"] for item in price_quality_map]
            
            price_median = statistics.median(prices)
            quality_median = statistics.median(qualities)
            
            main_item = next((item for item in price_quality_map if item["product"] == "main"), None)
            
            if main_item:
                if main_item["price"] > price_median and main_item["quality"] > quality_median:
                    quadrant = "premium"
                elif main_item["price"] < price_median and main_item["quality"] > quality_median:
                    quadrant = "value_leader"
                elif main_item["price"] > price_median and main_item["quality"] < quality_median:
                    quadrant = "overpriced"
                else:
                    quadrant = "budget"
                
                return {
                    "quadrant": quadrant,
                    "price_quality_map": price_quality_map,
                    "market_medians": {
                        "price": price_median,
                        "quality": quality_median
                    }
                }
        
        return {"status": "insufficient_data"}
    
    def _identify_competitive_gaps(
        self,
        main_product: CompetitorProduct,
        competitors: List[CompetitorProduct]
    ) -> List[Dict[str, Any]]:
        """识别竞争差距"""
        
        gaps = []
        
        # 价格差距
        if main_product.price:
            competitor_prices = [c.price for c in competitors if c.price]
            if competitor_prices:
                min_competitor_price = min(competitor_prices)
                if main_product.price > min_competitor_price * 1.1:  # 10%以上价格差距
                    gaps.append({
                        "type": "price",
                        "severity": "high" if main_product.price > min_competitor_price * 1.3 else "medium",
                        "description": f"Price is {((main_product.price - min_competitor_price) / min_competitor_price * 100):.1f}% higher than lowest competitor",
                        "action": "Consider price adjustment or value justification"
                    })
        
        # 评分差距
        if main_product.rating:
            competitor_ratings = [c.rating for c in competitors if c.rating]
            if competitor_ratings:
                max_competitor_rating = max(competitor_ratings)
                if max_competitor_rating > main_product.rating + 0.3:
                    gaps.append({
                        "type": "rating",
                        "severity": "high" if max_competitor_rating > main_product.rating + 0.5 else "medium",
                        "description": f"Rating is {(max_competitor_rating - main_product.rating):.1f} points lower than best competitor",
                        "action": "Focus on product quality and customer service improvements"
                    })
        
        # 评论数量差距
        competitor_reviews = [c.review_count for c in competitors if c.review_count]
        if competitor_reviews:
            max_competitor_reviews = max(competitor_reviews)
            if max_competitor_reviews > main_product.review_count * 2:  # 2倍以上差距
                gaps.append({
                    "type": "review_volume",
                    "severity": "medium",
                    "description": f"Review count is significantly lower than top competitor ({max_competitor_reviews} vs {main_product.review_count})",
                    "action": "Implement review acquisition strategies"
                })
        
        return gaps
    
    def _generate_opportunity_matrix(
        self,
        main_product: CompetitorProduct,
        competitors: List[CompetitorProduct]
    ) -> Dict[str, Any]:
        """生成机会矩阵"""
        
        opportunities = {
            "quick_wins": [],  # 容易实现的机会
            "strategic_investments": [],  # 需要战略投资的机会
            "monitoring": [],  # 需要监控的领域
            "maintain": []  # 保持现状的领域
        }
        
        # 价格机会
        if main_product.price:
            competitor_prices = [c.price for c in competitors if c.price]
            if competitor_prices:
                avg_price = statistics.mean(competitor_prices)
                if main_product.price > avg_price * 1.2:
                    opportunities["quick_wins"].append({
                        "type": "pricing",
                        "description": "Consider price reduction to be more competitive",
                        "impact": "high",
                        "effort": "low"
                    })
                elif main_product.price < avg_price * 0.8:
                    opportunities["strategic_investments"].append({
                        "type": "pricing",
                        "description": "Opportunity to increase price with better positioning",
                        "impact": "medium",
                        "effort": "medium"
                    })
        
        # 功能机会
        feature_analysis = self._analyze_feature_comparison(main_product, competitors)
        if feature_analysis.get("important_missing_features"):
            for missing in feature_analysis["important_missing_features"]:
                if missing["competitor_coverage"] > 0.7:  # 70%以上竞品都有
                    opportunities["strategic_investments"].append({
                        "type": "features",
                        "description": f"Add missing feature: {missing['feature']}",
                        "impact": "high",
                        "effort": "high"
                    })
        
        # 评分改进机会
        if main_product.rating and main_product.rating < 4.0:
            opportunities["strategic_investments"].append({
                "type": "quality",
                "description": "Improve product quality to increase rating",
                "impact": "high", 
                "effort": "high"
            })
        
        return opportunities
