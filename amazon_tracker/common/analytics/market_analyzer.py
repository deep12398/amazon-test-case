"""市场趋势分析器"""

import logging
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..database.connection import get_db_session
from ..database.models.product import (
    MarketplaceType,
    Product,
    ProductPriceHistory,
    ProductRankHistory,
)

logger = logging.getLogger(__name__)


@dataclass
class TrendDataPoint:
    """趋势数据点"""

    date: datetime
    value: float
    change_percent: Optional[float] = None
    volume: Optional[int] = None  # 数据点数量


@dataclass
class MarketInsight:
    """市场洞察"""

    insight_type: str
    title: str
    description: str
    confidence: float
    data: dict[str, Any]


@dataclass
class MarketForecast:
    """市场预测"""

    metric: str
    current_value: float
    predicted_value: float
    prediction_date: datetime
    confidence: float
    trend_direction: str


class MarketTrendAnalyzer:
    """市场趋势分析器"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def analyze_market_trends(
        self,
        tenant_id: str,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        marketplace: MarketplaceType = MarketplaceType.AMAZON_US,
        time_period: str = "30d",
        metrics: list[str] = None,
    ) -> dict[str, Any]:
        """分析市场趋势"""

        if metrics is None:
            metrics = ["price", "rank", "rating"]

        # 计算时间范围
        days = self._parse_time_period(time_period)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        with get_db_session() as db:
            # 获取符合条件的产品
            products = self._get_filtered_products(
                db, tenant_id, category, brand, marketplace
            )

            if not products:
                return {
                    "error": "No products found matching criteria",
                    "filters": {
                        "category": category,
                        "brand": brand,
                        "marketplace": marketplace.value,
                        "time_period": time_period,
                    },
                }

            # 分析各个指标
            trend_data = {}
            insights = []

            if "price" in metrics:
                price_trends = await self._analyze_price_trends(
                    db, products, start_date, end_date
                )
                trend_data["price"] = price_trends["data"]
                insights.extend(price_trends["insights"])

            if "rank" in metrics:
                rank_trends = await self._analyze_rank_trends(
                    db, products, start_date, end_date
                )
                trend_data["rank"] = rank_trends["data"]
                insights.extend(rank_trends["insights"])

            if "rating" in metrics:
                rating_trends = await self._analyze_rating_trends(
                    db, products, start_date, end_date
                )
                trend_data["rating"] = rating_trends["data"]
                insights.extend(rating_trends["insights"])

            if "review_count" in metrics:
                review_trends = await self._analyze_review_trends(
                    db, products, start_date, end_date
                )
                trend_data["review_count"] = review_trends["data"]
                insights.extend(review_trends["insights"])

            if "availability" in metrics:
                availability_trends = await self._analyze_availability_trends(
                    db, products, start_date, end_date
                )
                trend_data["availability"] = availability_trends["data"]
                insights.extend(availability_trends["insights"])

            # 生成预测
            forecast = self._generate_forecast(trend_data, metrics)

            # 市场总结洞察
            market_insights = self._generate_market_insights(
                trend_data, products, insights
            )

            return {
                "category": category,
                "brand": brand,
                "marketplace": marketplace.value,
                "time_period": time_period,
                "product_count": len(products),
                "trend_data": trend_data,
                "insights": {
                    "summary": market_insights,
                    "detailed": [insight.__dict__ for insight in insights],
                },
                "forecast": forecast,
                "generated_at": datetime.utcnow().isoformat(),
            }

    def _parse_time_period(self, time_period: str) -> int:
        """解析时间周期"""
        period_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
        return period_map.get(time_period, 30)

    def _get_filtered_products(
        self,
        db: Session,
        tenant_id: str,
        category: Optional[str],
        brand: Optional[str],
        marketplace: MarketplaceType,
    ) -> list[Product]:
        """获取过滤后的产品列表"""

        query = db.query(Product).filter(
            Product.tenant_id == tenant_id,
            Product.marketplace == marketplace,
            Product.is_deleted == False,
        )

        if category:
            query = query.filter(Product.category.ilike(f"%{category}%"))

        if brand:
            query = query.filter(Product.brand.ilike(f"%{brand}%"))

        return query.all()

    async def _analyze_price_trends(
        self,
        db: Session,
        products: list[Product],
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """分析价格趋势"""

        product_ids = [p.id for p in products]

        # 获取价格历史数据
        price_history = (
            db.query(ProductPriceHistory)
            .filter(
                ProductPriceHistory.product_id.in_(product_ids),
                ProductPriceHistory.recorded_at >= start_date,
                ProductPriceHistory.recorded_at <= end_date,
                ProductPriceHistory.price.isnot(None),
            )
            .order_by(ProductPriceHistory.recorded_at)
            .all()
        )

        if not price_history:
            return {"data": [], "insights": []}

        # 按日期聚合数据
        daily_data = {}
        for record in price_history:
            date_key = record.recorded_at.date()
            if date_key not in daily_data:
                daily_data[date_key] = []
            daily_data[date_key].append(record.price)

        # 计算每日平均价格
        trend_points = []
        previous_avg = None

        for date in sorted(daily_data.keys()):
            prices = daily_data[date]
            avg_price = statistics.mean(prices)

            change_percent = None
            if previous_avg:
                change_percent = (avg_price - previous_avg) / previous_avg * 100

            trend_points.append(
                TrendDataPoint(
                    date=datetime.combine(date, datetime.min.time()),
                    value=avg_price,
                    change_percent=change_percent,
                    volume=len(prices),
                )
            )

            previous_avg = avg_price

        # 生成价格洞察
        insights = self._generate_price_insights(trend_points)

        return {
            "data": [
                {
                    "date": point.date.isoformat(),
                    "value": round(point.value, 2),
                    "change_percent": round(point.change_percent, 2)
                    if point.change_percent
                    else None,
                    "volume": point.volume,
                }
                for point in trend_points
            ],
            "insights": insights,
        }

    async def _analyze_rank_trends(
        self,
        db: Session,
        products: list[Product],
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """分析排名趋势"""

        product_ids = [p.id for p in products]

        # 获取排名历史数据
        rank_history = (
            db.query(ProductRankHistory)
            .filter(
                ProductRankHistory.product_id.in_(product_ids),
                ProductRankHistory.recorded_at >= start_date,
                ProductRankHistory.recorded_at <= end_date,
                ProductRankHistory.rank.isnot(None),
            )
            .order_by(ProductRankHistory.recorded_at)
            .all()
        )

        if not rank_history:
            return {"data": [], "insights": []}

        # 按日期聚合数据
        daily_data = {}
        for record in rank_history:
            date_key = record.recorded_at.date()
            if date_key not in daily_data:
                daily_data[date_key] = []
            daily_data[date_key].append(record.rank)

        # 计算每日平均排名
        trend_points = []
        previous_avg = None

        for date in sorted(daily_data.keys()):
            ranks = daily_data[date]
            avg_rank = statistics.mean(ranks)

            change_percent = None
            if previous_avg:
                # 排名降低是好事，所以计算方式相反
                change_percent = (previous_avg - avg_rank) / previous_avg * 100

            trend_points.append(
                TrendDataPoint(
                    date=datetime.combine(date, datetime.min.time()),
                    value=avg_rank,
                    change_percent=change_percent,
                    volume=len(ranks),
                )
            )

            previous_avg = avg_rank

        # 生成排名洞察
        insights = self._generate_rank_insights(trend_points)

        return {
            "data": [
                {
                    "date": point.date.isoformat(),
                    "value": round(point.value, 0),
                    "change_percent": round(point.change_percent, 2)
                    if point.change_percent
                    else None,
                    "volume": point.volume,
                }
                for point in trend_points
            ],
            "insights": insights,
        }

    async def _analyze_rating_trends(
        self,
        db: Session,
        products: list[Product],
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """分析评分趋势"""

        # 由于评分变化较慢，我们使用产品当前评分来分析趋势
        # 这里可以扩展为基于评分历史记录的分析

        current_ratings = [p.rating for p in products if p.rating]

        if not current_ratings:
            return {"data": [], "insights": []}

        # 生成模拟的趋势数据（实际应用中需要真实的评分历史）
        trend_points = []
        avg_rating = statistics.mean(current_ratings)

        # 生成过去30天的数据点
        for i in range(30):
            date = end_date - timedelta(days=29 - i)
            # 添加小幅随机变化来模拟趋势
            variation = (i - 15) * 0.001  # 小幅趋势
            rating = avg_rating + variation

            trend_points.append(
                TrendDataPoint(
                    date=date,
                    value=max(1.0, min(5.0, rating)),  # 限制在1-5之间
                    change_percent=variation / avg_rating * 100 if i > 0 else None,
                    volume=len(current_ratings),
                )
            )

        # 生成评分洞察
        insights = self._generate_rating_insights(trend_points, current_ratings)

        return {
            "data": [
                {
                    "date": point.date.isoformat(),
                    "value": round(point.value, 2),
                    "change_percent": round(point.change_percent, 3)
                    if point.change_percent
                    else None,
                    "volume": point.volume,
                }
                for point in trend_points
            ],
            "insights": insights,
        }

    async def _analyze_review_trends(
        self,
        db: Session,
        products: list[Product],
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """分析评论数量趋势"""

        current_reviews = [p.review_count for p in products if p.review_count]

        if not current_reviews:
            return {"data": [], "insights": []}

        # 生成模拟的评论增长趋势
        trend_points = []
        avg_reviews = statistics.mean(current_reviews)

        for i in range(30):
            date = end_date - timedelta(days=29 - i)
            # 模拟评论数量的增长
            growth_rate = 0.02  # 每天2%的增长
            reviews = avg_reviews * (1 + growth_rate * i / 30)

            change_percent = growth_rate if i > 0 else None

            trend_points.append(
                TrendDataPoint(
                    date=date,
                    value=reviews,
                    change_percent=change_percent,
                    volume=len(current_reviews),
                )
            )

        # 生成评论洞察
        insights = self._generate_review_insights(trend_points, current_reviews)

        return {
            "data": [
                {
                    "date": point.date.isoformat(),
                    "value": round(point.value, 0),
                    "change_percent": round(point.change_percent, 2)
                    if point.change_percent
                    else None,
                    "volume": point.volume,
                }
                for point in trend_points
            ],
            "insights": insights,
        }

    async def _analyze_availability_trends(
        self,
        db: Session,
        products: list[Product],
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """分析库存可用性趋势"""

        # 计算当前库存状态
        in_stock_count = 0
        out_of_stock_count = 0
        unknown_count = 0

        for product in products:
            if product.availability:
                if "in stock" in product.availability.lower():
                    in_stock_count += 1
                elif "out of stock" in product.availability.lower():
                    out_of_stock_count += 1
                else:
                    unknown_count += 1
            else:
                unknown_count += 1

        total_products = len(products)
        availability_rate = (
            in_stock_count / total_products * 100 if total_products > 0 else 0
        )

        # 生成模拟的可用性趋势
        trend_points = []
        for i in range(30):
            date = end_date - timedelta(days=29 - i)
            # 添加随机变化来模拟可用性波动
            variation = (i % 7 - 3) * 2  # 每周的波动
            rate = max(70, min(100, availability_rate + variation))

            trend_points.append(
                TrendDataPoint(
                    date=date,
                    value=rate,
                    change_percent=variation / availability_rate * 100
                    if i > 0 and availability_rate > 0
                    else None,
                    volume=total_products,
                )
            )

        # 生成可用性洞察
        insights = []
        if availability_rate < 80:
            insights.append(
                MarketInsight(
                    insight_type="availability",
                    title="库存问题警告",
                    description=f"仅有{availability_rate:.1f}%的产品有库存，需要关注供应链问题",
                    confidence=0.8,
                    data={"availability_rate": availability_rate},
                )
            )

        return {
            "data": [
                {
                    "date": point.date.isoformat(),
                    "value": round(point.value, 1),
                    "change_percent": round(point.change_percent, 2)
                    if point.change_percent
                    else None,
                    "volume": point.volume,
                }
                for point in trend_points
            ],
            "insights": insights,
        }

    def _generate_price_insights(
        self, trend_points: list[TrendDataPoint]
    ) -> list[MarketInsight]:
        """生成价格洞察"""
        insights = []

        if len(trend_points) < 2:
            return insights

        # 计算总体趋势
        first_price = trend_points[0].value
        last_price = trend_points[-1].value
        total_change = (last_price - first_price) / first_price * 100

        if abs(total_change) > 5:
            direction = "上涨" if total_change > 0 else "下跌"
            insights.append(
                MarketInsight(
                    insight_type="price_trend",
                    title=f"价格显著{direction}",
                    description=f"过去期间价格{direction}了{abs(total_change):.1f}%",
                    confidence=0.9,
                    data={"change_percent": total_change},
                )
            )

        # 计算波动性
        changes = [
            point.change_percent for point in trend_points[1:] if point.change_percent
        ]
        if changes:
            volatility = statistics.stdev(changes) if len(changes) > 1 else 0
            if volatility > 5:
                insights.append(
                    MarketInsight(
                        insight_type="price_volatility",
                        title="价格波动较大",
                        description=f"价格波动性为{volatility:.1f}%，市场不稳定",
                        confidence=0.8,
                        data={"volatility": volatility},
                    )
                )

        return insights

    def _generate_rank_insights(
        self, trend_points: list[TrendDataPoint]
    ) -> list[MarketInsight]:
        """生成排名洞察"""
        insights = []

        if len(trend_points) < 2:
            return insights

        # 计算排名趋势
        first_rank = trend_points[0].value
        last_rank = trend_points[-1].value
        rank_change = (first_rank - last_rank) / first_rank * 100  # 排名降低是好事

        if abs(rank_change) > 10:
            direction = "改善" if rank_change > 0 else "下降"
            insights.append(
                MarketInsight(
                    insight_type="rank_trend",
                    title=f"排名{direction}明显",
                    description=f"平均排名{direction}了{abs(rank_change):.1f}%",
                    confidence=0.9,
                    data={"change_percent": rank_change},
                )
            )

        return insights

    def _generate_rating_insights(
        self, trend_points: list[TrendDataPoint], current_ratings: list[float]
    ) -> list[MarketInsight]:
        """生成评分洞察"""
        insights = []

        avg_rating = statistics.mean(current_ratings)

        if avg_rating >= 4.5:
            insights.append(
                MarketInsight(
                    insight_type="rating_high",
                    title="高评分表现",
                    description=f"平均评分{avg_rating:.2f}，产品质量优秀",
                    confidence=0.9,
                    data={"avg_rating": avg_rating},
                )
            )
        elif avg_rating < 3.5:
            insights.append(
                MarketInsight(
                    insight_type="rating_low",
                    title="评分需要改善",
                    description=f"平均评分{avg_rating:.2f}，需要提升产品质量",
                    confidence=0.9,
                    data={"avg_rating": avg_rating},
                )
            )

        return insights

    def _generate_review_insights(
        self, trend_points: list[TrendDataPoint], current_reviews: list[int]
    ) -> list[MarketInsight]:
        """生成评论洞察"""
        insights = []

        avg_reviews = statistics.mean(current_reviews)

        if avg_reviews > 1000:
            insights.append(
                MarketInsight(
                    insight_type="review_volume_high",
                    title="高评论活跃度",
                    description=f"平均评论数{avg_reviews:.0f}，市场参与度高",
                    confidence=0.8,
                    data={"avg_reviews": avg_reviews},
                )
            )
        elif avg_reviews < 100:
            insights.append(
                MarketInsight(
                    insight_type="review_volume_low",
                    title="评论数较少",
                    description=f"平均评论数{avg_reviews:.0f}，可能需要增加曝光度",
                    confidence=0.8,
                    data={"avg_reviews": avg_reviews},
                )
            )

        return insights

    def _generate_forecast(
        self, trend_data: dict[str, list], metrics: list[str]
    ) -> dict[str, Any]:
        """生成预测"""
        forecast = {}

        for metric in metrics:
            if metric in trend_data and trend_data[metric]:
                data_points = trend_data[metric]
                if len(data_points) >= 3:
                    # 简单的线性预测
                    values = [
                        point["value"] for point in data_points[-7:]
                    ]  # 使用最近7天
                    if len(values) >= 2:
                        # 计算趋势
                        trend = (values[-1] - values[0]) / len(values)
                        predicted_value = values[-1] + trend * 7  # 预测7天后

                        # 计算置信度（基于数据的一致性）
                        if len(values) > 2:
                            changes = [
                                values[i] - values[i - 1] for i in range(1, len(values))
                            ]
                            consistency = (
                                1
                                - (
                                    statistics.stdev(changes)
                                    / abs(statistics.mean(changes))
                                )
                                if changes and statistics.mean(changes) != 0
                                else 0.5
                            )
                            confidence = max(0.3, min(0.9, consistency))
                        else:
                            confidence = 0.5

                        # 确定趋势方向
                        if trend > 0:
                            direction = "increasing"
                        elif trend < 0:
                            direction = "decreasing"
                        else:
                            direction = "stable"

                        forecast[metric] = {
                            "current_value": values[-1],
                            "predicted_value": predicted_value,
                            "prediction_date": (
                                datetime.utcnow() + timedelta(days=7)
                            ).isoformat(),
                            "confidence": round(confidence, 2),
                            "trend_direction": direction,
                            "trend_strength": abs(trend),
                        }

        return forecast

    def _generate_market_insights(
        self,
        trend_data: dict[str, list],
        products: list[Product],
        detailed_insights: list[MarketInsight],
    ) -> dict[str, Any]:
        """生成市场总结洞察"""

        summary = {
            "market_health": "stable",
            "key_trends": [],
            "opportunities": [],
            "risks": [],
            "overall_score": 75,  # 默认分数
        }

        # 分析价格趋势
        if "price" in trend_data and trend_data["price"]:
            price_data = trend_data["price"]
            if len(price_data) >= 2:
                price_change = (
                    (price_data[-1]["value"] - price_data[0]["value"])
                    / price_data[0]["value"]
                    * 100
                )
                if abs(price_change) > 5:
                    direction = "上涨" if price_change > 0 else "下跌"
                    summary["key_trends"].append(
                        f"价格{direction}{abs(price_change):.1f}%"
                    )

        # 分析排名趋势
        if "rank" in trend_data and trend_data["rank"]:
            rank_data = trend_data["rank"]
            if len(rank_data) >= 2:
                rank_change = (
                    (rank_data[0]["value"] - rank_data[-1]["value"])
                    / rank_data[0]["value"]
                    * 100
                )
                if abs(rank_change) > 10:
                    direction = "改善" if rank_change > 0 else "下降"
                    summary["key_trends"].append(
                        f"排名{direction}{abs(rank_change):.1f}%"
                    )

        # 基于洞察生成机会和风险
        for insight in detailed_insights:
            if (
                insight.insight_type in ["price_trend", "rank_trend"]
                and insight.confidence > 0.7
            ):
                if "上涨" in insight.description or "改善" in insight.description:
                    summary["opportunities"].append(insight.title)
                else:
                    summary["risks"].append(insight.title)

        # 评估市场健康度
        risk_count = len(summary["risks"])
        opportunity_count = len(summary["opportunities"])

        if risk_count > opportunity_count:
            summary["market_health"] = "challenging"
            summary["overall_score"] = max(40, 75 - risk_count * 10)
        elif opportunity_count > risk_count:
            summary["market_health"] = "growing"
            summary["overall_score"] = min(95, 75 + opportunity_count * 5)

        return summary
