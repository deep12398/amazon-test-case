"""市场趋势分析API端点"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from amazon_tracker.common.analytics.market_analyzer import MarketTrendAnalyzer
from amazon_tracker.common.auth.jwt_auth import get_current_user
from amazon_tracker.common.auth.permissions import PermissionScope, require_permission
from amazon_tracker.common.database.connection import get_db_session
from amazon_tracker.common.database.models.product import MarketplaceType

from .schemas import MarketTrendRequest, MarketTrendResponse, TrendDataPoint

router = APIRouter(prefix="/market-trends", tags=["market-trends"])
security = HTTPBearer()


@router.post("/analyze", response_model=MarketTrendResponse)
async def analyze_market_trends(
    request: MarketTrendRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """分析市场趋势"""

    # 权限检查
    require_permission(current_user, PermissionScope.ANALYTICS_READ)

    try:
        analyzer = MarketTrendAnalyzer()

        # 执行市场趋势分析
        analysis_result = await analyzer.analyze_market_trends(
            tenant_id=current_user["tenant_id"],
            category=request.category,
            brand=request.brand,
            marketplace=request.marketplace,
            time_period=request.time_period,
            metrics=request.metrics,
        )

        if "error" in analysis_result:
            raise HTTPException(status_code=404, detail=analysis_result["error"])

        # 转换趋势数据格式
        trend_data = {}
        for metric, data_points in analysis_result["trend_data"].items():
            trend_data[metric] = [
                TrendDataPoint(
                    date=datetime.fromisoformat(point["date"].replace("Z", "+00:00")),
                    value=point["value"],
                    change_percent=point.get("change_percent"),
                )
                for point in data_points
            ]

        return MarketTrendResponse(
            category=analysis_result.get("category"),
            brand=analysis_result.get("brand"),
            marketplace=MarketplaceType(analysis_result["marketplace"]),
            time_period=analysis_result["time_period"],
            trend_data=trend_data,
            insights=analysis_result["insights"],
            forecast=analysis_result.get("forecast"),
            generated_at=datetime.fromisoformat(analysis_result["generated_at"]),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Market trend analysis failed: {str(e)}"
        )


@router.get("/categories")
async def get_trending_categories(
    marketplace: MarketplaceType = Query(default=MarketplaceType.AMAZON_US),
    time_period: str = Query(default="30d", regex="^(7d|30d|90d|1y)$"),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取热门趋势分类"""

    # 权限检查
    require_permission(current_user, PermissionScope.ANALYTICS_READ)

    try:
        analyzer = MarketTrendAnalyzer()

        # 获取所有分类的趋势
        from sqlalchemy import func

        from amazon_tracker.common.database.models.product import Product

        # 获取该租户下的所有分类
        categories = (
            db.query(Product.category, func.count(Product.id).label("product_count"))
            .filter(
                Product.tenant_id == current_user["tenant_id"],
                Product.marketplace == marketplace,
                Product.is_deleted == False,
                Product.category.isnot(None),
                Product.category != "",
            )
            .group_by(Product.category)
            .order_by(func.count(Product.id).desc())
            .limit(limit)
            .all()
        )

        trending_categories = []

        for category, product_count in categories:
            # 为每个分类分析趋势
            try:
                trend_analysis = await analyzer.analyze_market_trends(
                    tenant_id=current_user["tenant_id"],
                    category=category,
                    marketplace=marketplace,
                    time_period=time_period,
                    metrics=["price", "rank"],
                )

                if "error" not in trend_analysis:
                    # 计算趋势得分
                    trend_score = _calculate_trend_score(trend_analysis)

                    trending_categories.append(
                        {
                            "category": category,
                            "product_count": product_count,
                            "trend_score": trend_score,
                            "insights": trend_analysis["insights"]["summary"],
                            "forecast": trend_analysis.get("forecast", {}),
                        }
                    )

            except Exception:
                # 跳过分析失败的分类
                continue

        # 按趋势得分排序
        trending_categories.sort(key=lambda x: x["trend_score"], reverse=True)

        return {
            "marketplace": marketplace.value,
            "time_period": time_period,
            "trending_categories": trending_categories,
            "total_analyzed": len(trending_categories),
            "generated_at": datetime.utcnow(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get trending categories: {str(e)}"
        )


@router.get("/brands")
async def get_trending_brands(
    category: Optional[str] = Query(None),
    marketplace: MarketplaceType = Query(default=MarketplaceType.AMAZON_US),
    time_period: str = Query(default="30d", regex="^(7d|30d|90d|1y)$"),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取热门趋势品牌"""

    # 权限检查
    require_permission(current_user, PermissionScope.ANALYTICS_READ)

    try:
        from sqlalchemy import func

        from amazon_tracker.common.database.models.product import Product

        # 构建品牌查询
        query = db.query(
            Product.brand,
            func.count(Product.id).label("product_count"),
            func.avg(Product.current_price).label("avg_price"),
            func.avg(Product.rating).label("avg_rating"),
        ).filter(
            Product.tenant_id == current_user["tenant_id"],
            Product.marketplace == marketplace,
            Product.is_deleted == False,
            Product.brand.isnot(None),
            Product.brand != "",
        )

        if category:
            query = query.filter(Product.category.ilike(f"%{category}%"))

        brands = (
            query.group_by(Product.brand)
            .order_by(func.count(Product.id).desc())
            .limit(limit)
            .all()
        )

        trending_brands = []
        analyzer = MarketTrendAnalyzer()

        for brand, product_count, avg_price, avg_rating in brands:
            try:
                # 为每个品牌分析趋势
                trend_analysis = await analyzer.analyze_market_trends(
                    tenant_id=current_user["tenant_id"],
                    category=category,
                    brand=brand,
                    marketplace=marketplace,
                    time_period=time_period,
                    metrics=["price", "rating"],
                )

                if "error" not in trend_analysis:
                    trend_score = _calculate_trend_score(trend_analysis)

                    trending_brands.append(
                        {
                            "brand": brand,
                            "category": category,
                            "product_count": product_count,
                            "avg_price": float(avg_price) if avg_price else None,
                            "avg_rating": float(avg_rating) if avg_rating else None,
                            "trend_score": trend_score,
                            "insights": trend_analysis["insights"]["summary"],
                            "forecast": trend_analysis.get("forecast", {}),
                        }
                    )

            except Exception:
                continue

        # 按趋势得分排序
        trending_brands.sort(key=lambda x: x["trend_score"], reverse=True)

        return {
            "category": category,
            "marketplace": marketplace.value,
            "time_period": time_period,
            "trending_brands": trending_brands,
            "total_analyzed": len(trending_brands),
            "generated_at": datetime.utcnow(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get trending brands: {str(e)}"
        )


@router.get("/price-analysis")
async def analyze_price_trends(
    category: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    marketplace: MarketplaceType = Query(default=MarketplaceType.AMAZON_US),
    time_period: str = Query(default="30d", regex="^(7d|30d|90d|1y)$"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """专门的价格趋势分析"""

    # 权限检查
    require_permission(current_user, PermissionScope.ANALYTICS_READ)

    try:
        analyzer = MarketTrendAnalyzer()

        # 执行价格趋势分析
        analysis_result = await analyzer.analyze_market_trends(
            tenant_id=current_user["tenant_id"],
            category=category,
            brand=brand,
            marketplace=marketplace,
            time_period=time_period,
            metrics=["price"],
        )

        if "error" in analysis_result:
            raise HTTPException(status_code=404, detail=analysis_result["error"])

        price_data = analysis_result["trend_data"].get("price", [])

        if not price_data:
            return {
                "message": "No price data available for analysis",
                "filters": {
                    "category": category,
                    "brand": brand,
                    "marketplace": marketplace.value,
                    "time_period": time_period,
                },
            }

        # 计算价格统计
        prices = [point["value"] for point in price_data]
        price_changes = [
            point["change_percent"]
            for point in price_data[1:]
            if point.get("change_percent")
        ]

        statistics_data = {
            "min_price": min(prices),
            "max_price": max(prices),
            "avg_price": sum(prices) / len(prices),
            "current_price": prices[-1],
            "total_change_percent": ((prices[-1] - prices[0]) / prices[0] * 100)
            if prices[0] > 0
            else 0,
            "volatility": (max(prices) - min(prices)) / min(prices) * 100
            if min(prices) > 0
            else 0,
        }

        if price_changes:
            import statistics

            statistics_data.update(
                {
                    "avg_daily_change": statistics.mean(price_changes),
                    "max_daily_change": max(price_changes),
                    "min_daily_change": min(price_changes),
                }
            )

        # 价格区间分析
        price_ranges = _analyze_price_ranges(prices)

        # 趋势预测
        forecast = analysis_result.get("forecast", {}).get("price", {})

        return {
            "filters": {
                "category": category,
                "brand": brand,
                "marketplace": marketplace.value,
                "time_period": time_period,
            },
            "product_count": analysis_result.get("product_count", 0),
            "price_data": price_data,
            "statistics": statistics_data,
            "price_ranges": price_ranges,
            "insights": analysis_result["insights"],
            "forecast": forecast,
            "generated_at": datetime.utcnow(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Price trend analysis failed: {str(e)}"
        )


@router.get("/market-summary")
async def get_market_summary(
    marketplace: MarketplaceType = Query(default=MarketplaceType.AMAZON_US),
    time_period: str = Query(default="30d", regex="^(7d|30d|90d|1y)$"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取市场总结"""

    # 权限检查
    require_permission(current_user, PermissionScope.ANALYTICS_READ)

    try:
        from sqlalchemy import func

        from amazon_tracker.common.database.models.product import Product

        # 基础统计
        base_query = db.query(Product).filter(
            Product.tenant_id == current_user["tenant_id"],
            Product.marketplace == marketplace,
            Product.is_deleted == False,
        )

        total_products = base_query.count()
        active_products = base_query.filter(Product.is_active == True).count()

        # 价格统计
        price_stats = (
            base_query.filter(Product.current_price.isnot(None))
            .with_entities(
                func.min(Product.current_price).label("min_price"),
                func.max(Product.current_price).label("max_price"),
                func.avg(Product.current_price).label("avg_price"),
            )
            .first()
        )

        # 评分统计
        rating_stats = (
            base_query.filter(Product.rating.isnot(None))
            .with_entities(
                func.avg(Product.rating).label("avg_rating"),
                func.count(Product.id).label("rated_products"),
            )
            .first()
        )

        # 分类分布
        category_distribution = (
            base_query.filter(Product.category.isnot(None), Product.category != "")
            .with_entities(Product.category, func.count(Product.id).label("count"))
            .group_by(Product.category)
            .order_by(func.count(Product.id).desc())
            .limit(10)
            .all()
        )

        # 品牌分布
        brand_distribution = (
            base_query.filter(Product.brand.isnot(None), Product.brand != "")
            .with_entities(Product.brand, func.count(Product.id).label("count"))
            .group_by(Product.brand)
            .order_by(func.count(Product.id).desc())
            .limit(10)
            .all()
        )

        # 整体市场趋势
        analyzer = MarketTrendAnalyzer()
        overall_trend = await analyzer.analyze_market_trends(
            tenant_id=current_user["tenant_id"],
            marketplace=marketplace,
            time_period=time_period,
            metrics=["price", "rating"],
        )

        market_health = "stable"
        trend_insights = []

        if "error" not in overall_trend:
            market_health = overall_trend["insights"]["summary"].get(
                "market_health", "stable"
            )
            trend_insights = overall_trend["insights"]["summary"].get("key_trends", [])

        return {
            "marketplace": marketplace.value,
            "time_period": time_period,
            "overview": {
                "total_products": total_products,
                "active_products": active_products,
                "tracking_rate": (active_products / total_products * 100)
                if total_products > 0
                else 0,
            },
            "price_overview": {
                "min_price": float(price_stats.min_price)
                if price_stats.min_price
                else None,
                "max_price": float(price_stats.max_price)
                if price_stats.max_price
                else None,
                "avg_price": float(price_stats.avg_price)
                if price_stats.avg_price
                else None,
                "price_range": float(price_stats.max_price - price_stats.min_price)
                if price_stats.min_price and price_stats.max_price
                else None,
            },
            "rating_overview": {
                "avg_rating": float(rating_stats.avg_rating)
                if rating_stats.avg_rating
                else None,
                "rated_products": rating_stats.rated_products,
                "rating_coverage": (rating_stats.rated_products / total_products * 100)
                if total_products > 0
                else 0,
            },
            "market_health": market_health,
            "key_trends": trend_insights,
            "top_categories": [
                {"category": cat, "product_count": count}
                for cat, count in category_distribution
            ],
            "top_brands": [
                {"brand": brand, "product_count": count}
                for brand, count in brand_distribution
            ],
            "generated_at": datetime.utcnow(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get market summary: {str(e)}"
        )


def _calculate_trend_score(trend_analysis: dict) -> float:
    """计算趋势得分"""
    score = 50.0  # 基础分数

    # 基于洞察计算得分
    insights = trend_analysis.get("insights", {})
    summary = insights.get("summary", {})

    # 市场健康度影响
    health = summary.get("market_health", "stable")
    if health == "growing":
        score += 20
    elif health == "challenging":
        score -= 20

    # 整体得分影响
    overall_score = summary.get("overall_score", 75)
    score += (overall_score - 75) * 0.4

    # 机会和风险影响
    opportunities = len(summary.get("opportunities", []))
    risks = len(summary.get("risks", []))
    score += opportunities * 5 - risks * 8

    # 预测影响
    forecast = trend_analysis.get("forecast", {})
    for metric, prediction in forecast.items():
        confidence = prediction.get("confidence", 0.5)
        direction = prediction.get("trend_direction", "stable")

        if direction == "increasing" and metric in ["rating", "review_count"]:
            score += confidence * 10
        elif direction == "decreasing" and metric == "price":
            score += confidence * 5  # 价格下降可能是好事

    return max(0, min(100, score))


def _analyze_price_ranges(prices: list[float]) -> dict:
    """分析价格区间"""
    if not prices:
        return {}

    min_price = min(prices)
    max_price = max(prices)
    price_range = max_price - min_price

    # 定义价格区间
    ranges = {
        "budget": {"min": min_price, "max": min_price + price_range * 0.3, "count": 0},
        "mid_range": {
            "min": min_price + price_range * 0.3,
            "max": min_price + price_range * 0.7,
            "count": 0,
        },
        "premium": {"min": min_price + price_range * 0.7, "max": max_price, "count": 0},
    }

    # 统计每个区间的价格点数量
    for price in prices:
        if price <= ranges["budget"]["max"]:
            ranges["budget"]["count"] += 1
        elif price <= ranges["mid_range"]["max"]:
            ranges["mid_range"]["count"] += 1
        else:
            ranges["premium"]["count"] += 1

    # 计算百分比
    total_points = len(prices)
    for range_name in ranges:
        ranges[range_name]["percentage"] = (
            (ranges[range_name]["count"] / total_points * 100)
            if total_points > 0
            else 0
        )

    return ranges