"""市场趋势分析API端点 - 临时禁用"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

# from amazon_tracker.common.analytics.market_analyzer import MarketTrendAnalyzer  # 暂时禁用，因为依赖竞品分析功能
from amazon_tracker.common.auth.jwt_auth import get_current_user
from amazon_tracker.common.auth.permissions import PermissionScope, require_permission
from amazon_tracker.common.database.connection import get_db_session
from amazon_tracker.common.database.models.product import MarketplaceType

router = APIRouter(prefix="/market-trends", tags=["market-trends"])
security = HTTPBearer()


@router.post("/analyze")
async def analyze_market_trends(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """分析市场趋势 - 暂时禁用"""
    require_permission(current_user, PermissionScope.ANALYTICS_READ)

    return {
        "message": "Market trend analysis is temporarily disabled due to system maintenance",
        "status": "disabled",
        "generated_at": datetime.utcnow()
    }


@router.get("/categories")
async def get_trending_categories(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取热门趋势分类 - 暂时禁用"""
    require_permission(current_user, PermissionScope.ANALYTICS_READ)

    return {
        "message": "Trending categories analysis is temporarily disabled due to system maintenance",
        "status": "disabled",
        "trending_categories": [],
        "generated_at": datetime.utcnow()
    }


@router.get("/brands")
async def get_trending_brands(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取热门趋势品牌 - 暂时禁用"""
    require_permission(current_user, PermissionScope.ANALYTICS_READ)

    return {
        "message": "Trending brands analysis is temporarily disabled due to system maintenance",
        "status": "disabled",
        "trending_brands": [],
        "generated_at": datetime.utcnow()
    }


@router.get("/price-analysis")
async def analyze_price_trends(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """专门的价格趋势分析 - 暂时禁用"""
    require_permission(current_user, PermissionScope.ANALYTICS_READ)

    return {
        "message": "Price trend analysis is temporarily disabled due to system maintenance",
        "status": "disabled",
        "generated_at": datetime.utcnow()
    }


@router.get("/market-summary")
async def get_market_summary(
    marketplace: MarketplaceType = Query(default=MarketplaceType.AMAZON_US),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取市场总结 - 简化版本"""
    require_permission(current_user, PermissionScope.ANALYTICS_READ)

    from sqlalchemy import func
    from amazon_tracker.common.database.models.product import Product

    try:
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

        return {
            "marketplace": marketplace.value,
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
            "market_health": "stable",  # 固定值，因为趋势分析暂时禁用
            "key_trends": ["Market trend analysis temporarily disabled"],
            "top_categories": [
                {"category": cat, "product_count": count}
                for cat, count in category_distribution
            ],
            "top_brands": [
                {"brand": brand, "product_count": count}
                for brand, count in brand_distribution
            ],
            "generated_at": datetime.utcnow(),
            "note": "Advanced market trend analysis is temporarily disabled due to system maintenance"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get market summary: {str(e)}"
        )