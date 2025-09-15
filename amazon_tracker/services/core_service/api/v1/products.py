"""产品管理API端点"""

from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session

from amazon_tracker.common.auth.jwt_auth import get_current_user
from amazon_tracker.common.auth.permissions import PermissionScope, require_permission
from amazon_tracker.common.database.connection import get_db_session
from amazon_tracker.common.database.models.crawl import (
    CrawlerType,
    CrawlTask,
    TaskPriority,
)
from amazon_tracker.common.database.models.product import (
    Product,
    ProductPriceHistory,
    ProductRankHistory,
    ProductStatus,
    TrackingFrequency,
)
from amazon_tracker.common.task_queue.crawler_tasks import crawl_amazon_product

from .schemas import (
    BatchOperationRequest,
    BatchOperationResponse,
    ProductCreateRequest,
    ProductListResponse,
    ProductResponse,
    ProductSearchRequest,
    ProductStatsResponse,
    ProductUpdateRequest,
)

router = APIRouter(prefix="/products", tags=["products"])
security = HTTPBearer()


@router.post("/", response_model=ProductResponse)
async def create_product(
    request: ProductCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """创建新产品"""

    # 权限检查
    require_permission(current_user, PermissionScope.PRODUCT_CREATE)

    # 检查ASIN是否已存在
    existing_product = (
        db.query(Product)
        .filter(
            Product.asin == request.asin, Product.tenant_id == current_user["tenant_id"]
        )
        .first()
    )

    if existing_product:
        raise HTTPException(
            status_code=409, detail=f"Product with ASIN {request.asin} already exists"
        )

    # 创建产品
    product = Product(
        asin=request.asin,
        title=request.title or f"Product {request.asin}",
        brand=request.brand,
        category=request.category,
        marketplace=request.marketplace,
        tracking_frequency=request.tracking_frequency,
        status=ProductStatus.PENDING,
        is_active=True,
        tags=request.tags or [],
        notes=request.notes,
        tenant_id=current_user["tenant_id"],
        created_by=current_user["user_id"],
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    # 自动创建爬虫任务获取产品信息
    crawl_task = CrawlTask(
        product_id=product.id,
        tenant_id=current_user["tenant_id"],
        crawler_type=CrawlerType.APIFY_AMAZON_SCRAPER,
        task_name=f"Initial crawl for {request.asin}",
        priority=TaskPriority.HIGH,
        input_data={
            "asin": request.asin,
            "country": request.marketplace.value.split("_")[1]
            if "_" in request.marketplace.value
            else "US",
        },
    )

    db.add(crawl_task)
    db.commit()

    # 异步执行爬虫任务
    background_tasks.add_task(
        crawl_amazon_product.delay,
        crawl_task_id=str(crawl_task.task_id),
        tenant_id=current_user["tenant_id"],
        product_id=product.id,
    )

    return ProductResponse.from_orm(product)


@router.get("/", response_model=list[ProductListResponse])
async def list_products(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取产品列表"""

    # 权限检查
    require_permission(current_user, PermissionScope.PRODUCT_READ)

    # 查询产品
    query = db.query(Product).filter(
        Product.tenant_id == current_user["tenant_id"], Product.is_deleted == False
    )

    products = (
        query.order_by(desc(Product.created_at)).offset(offset).limit(limit).all()
    )

    return [ProductListResponse.from_orm(product) for product in products]


@router.post("/search", response_model=list[ProductListResponse])
async def search_products(
    request: ProductSearchRequest,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """搜索产品"""

    # 权限检查
    require_permission(current_user, PermissionScope.PRODUCT_READ)

    # 构建查询
    query = db.query(Product).filter(
        Product.tenant_id == current_user["tenant_id"], Product.is_deleted == False
    )

    # 应用搜索条件
    if request.query:
        search_term = f"%{request.query}%"
        query = query.filter(
            or_(
                Product.title.ilike(search_term),
                Product.brand.ilike(search_term),
                Product.category.ilike(search_term),
                Product.asin.ilike(search_term),
            )
        )

    if request.asin:
        query = query.filter(Product.asin.ilike(f"%{request.asin}%"))

    if request.brand:
        query = query.filter(Product.brand.ilike(f"%{request.brand}%"))

    if request.category:
        query = query.filter(Product.category.ilike(f"%{request.category}%"))

    if request.marketplace:
        query = query.filter(Product.marketplace == request.marketplace)

    if request.min_price is not None:
        query = query.filter(Product.current_price >= request.min_price)

    if request.max_price is not None:
        query = query.filter(Product.current_price <= request.max_price)

    if request.min_rating is not None:
        query = query.filter(Product.rating >= request.min_rating)

    if request.tracking_frequency:
        query = query.filter(Product.tracking_frequency == request.tracking_frequency)

    if request.is_active is not None:
        query = query.filter(Product.is_active == request.is_active)

    if request.status:
        query = query.filter(Product.status == request.status)

    if request.tags:
        # PostgreSQL数组包含查询
        for tag in request.tags:
            query = query.filter(Product.tags.contains([tag]))

    # 排序
    sort_column = getattr(Product, request.sort_by, Product.created_at)
    if request.sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    products = query.offset(offset).limit(limit).all()

    return [ProductListResponse.from_orm(product) for product in products]


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取产品详情"""

    # 权限检查
    require_permission(current_user, PermissionScope.PRODUCT_READ)

    product = (
        db.query(Product)
        .filter(
            Product.id == product_id, Product.tenant_id == current_user["tenant_id"]
        )
        .first()
    )

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return ProductResponse.from_orm(product)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    request: ProductUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """更新产品"""

    # 权限检查
    require_permission(current_user, PermissionScope.PRODUCT_UPDATE)

    product = (
        db.query(Product)
        .filter(
            Product.id == product_id, Product.tenant_id == current_user["tenant_id"]
        )
        .first()
    )

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 更新字段
    update_data = request.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    product.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(product)

    return ProductResponse.from_orm(product)


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """删除产品（软删除）"""

    # 权限检查
    require_permission(current_user, PermissionScope.PRODUCT_DELETE)

    product = (
        db.query(Product)
        .filter(
            Product.id == product_id, Product.tenant_id == current_user["tenant_id"]
        )
        .first()
    )

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 软删除
    product.is_deleted = True
    product.is_active = False
    product.updated_at = datetime.utcnow()

    db.commit()

    return {"message": "Product deleted successfully"}


@router.get("/{product_id}/price-history")
async def get_price_history(
    product_id: int,
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取产品价格历史"""

    # 权限检查
    require_permission(current_user, PermissionScope.PRODUCT_READ)

    # 验证产品存在
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id, Product.tenant_id == current_user["tenant_id"]
        )
        .first()
    )

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 计算时间范围
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # 获取价格历史
    price_history = (
        db.query(ProductPriceHistory)
        .filter(
            ProductPriceHistory.product_id == product_id,
            ProductPriceHistory.recorded_at >= start_date,
            ProductPriceHistory.recorded_at <= end_date,
        )
        .order_by(ProductPriceHistory.recorded_at)
        .all()
    )

    # 计算统计信息
    prices = [record.price for record in price_history if record.price]

    stats = {}
    if prices:
        stats = {
            "min_price": min(prices),
            "max_price": max(prices),
            "avg_price": sum(prices) / len(prices),
            "current_price": product.current_price,
            "price_change": (product.current_price - prices[0])
            if product.current_price and prices
            else None,
            "price_change_percent": (
                (product.current_price - prices[0]) / prices[0] * 100
            )
            if product.current_price and prices and prices[0] > 0
            else None,
        }

    return {
        "product_id": product_id,
        "time_period": f"{days} days",
        "history": [
            {
                "date": record.recorded_at,
                "price": record.price,
                "list_price": record.list_price,
                "currency": record.currency,
            }
            for record in price_history
        ],
        "statistics": stats,
    }


@router.get("/{product_id}/rank-history")
async def get_rank_history(
    product_id: int,
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取产品排名历史"""

    # 权限检查
    require_permission(current_user, PermissionScope.PRODUCT_READ)

    # 验证产品存在
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id, Product.tenant_id == current_user["tenant_id"]
        )
        .first()
    )

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 计算时间范围
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # 获取排名历史
    rank_history = (
        db.query(ProductRankHistory)
        .filter(
            ProductRankHistory.product_id == product_id,
            ProductRankHistory.recorded_at >= start_date,
            ProductRankHistory.recorded_at <= end_date,
        )
        .order_by(ProductRankHistory.recorded_at)
        .all()
    )

    # 计算统计信息
    ranks = [record.rank for record in rank_history if record.rank]

    stats = {}
    if ranks:
        stats = {
            "best_rank": min(ranks),
            "worst_rank": max(ranks),
            "avg_rank": sum(ranks) / len(ranks),
            "current_rank": product.current_rank,
            "rank_change": (ranks[0] - product.current_rank)
            if product.current_rank and ranks
            else None,  # 排名越小越好
            "rank_improvement": ranks[0] > product.current_rank
            if product.current_rank and ranks
            else None,
        }

    return {
        "product_id": product_id,
        "time_period": f"{days} days",
        "history": [
            {
                "date": record.recorded_at,
                "rank": record.rank,
                "category": record.category,
            }
            for record in rank_history
        ],
        "statistics": stats,
    }


@router.post("/batch-operation", response_model=BatchOperationResponse)
async def batch_operation(
    request: BatchOperationRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """批量操作产品"""

    # 权限检查
    require_permission(current_user, PermissionScope.PRODUCT_UPDATE)

    # 获取产品
    products = (
        db.query(Product)
        .filter(
            Product.id.in_(request.product_ids),
            Product.tenant_id == current_user["tenant_id"],
        )
        .all()
    )

    if not products:
        raise HTTPException(status_code=404, detail="No products found")

    operation_id = f"batch_{datetime.utcnow().timestamp()}"
    successful_items = 0
    failed_items = 0
    errors = []

    for product in products:
        try:
            if request.operation == "activate":
                product.is_active = True
            elif request.operation == "deactivate":
                product.is_active = False
            elif request.operation == "delete":
                product.is_deleted = True
                product.is_active = False
            elif request.operation == "update_frequency":
                frequency = request.parameters.get("frequency")
                if frequency:
                    product.tracking_frequency = TrackingFrequency(frequency)
            elif request.operation == "add_tags":
                tags_to_add = request.parameters.get("tags", [])
                current_tags = set(product.tags or [])
                current_tags.update(tags_to_add)
                product.tags = list(current_tags)
            elif request.operation == "remove_tags":
                tags_to_remove = set(request.parameters.get("tags", []))
                current_tags = set(product.tags or [])
                product.tags = list(current_tags - tags_to_remove)

            product.updated_at = datetime.utcnow()
            successful_items += 1

        except Exception as e:
            failed_items += 1
            errors.append({"product_id": str(product.id), "error": str(e)})

    db.commit()

    return BatchOperationResponse(
        operation_id=operation_id,
        operation=request.operation,
        total_items=len(request.product_ids),
        successful_items=successful_items,
        failed_items=failed_items,
        errors=errors,
        completed_at=datetime.utcnow(),
    )


@router.get("/stats/overview", response_model=ProductStatsResponse)
async def get_product_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取产品统计概览"""

    # 权限检查
    require_permission(current_user, PermissionScope.PRODUCT_READ)

    # 基础统计
    base_query = db.query(Product).filter(
        Product.tenant_id == current_user["tenant_id"], Product.is_deleted == False
    )

    total_products = base_query.count()
    active_products = base_query.filter(Product.is_active == True).count()
    inactive_products = total_products - active_products

    # 按市场统计
    marketplace_stats = (
        db.query(Product.marketplace, func.count(Product.id))
        .filter(
            Product.tenant_id == current_user["tenant_id"], Product.is_deleted == False
        )
        .group_by(Product.marketplace)
        .all()
    )

    by_marketplace = {str(mp): count for mp, count in marketplace_stats}

    # 按分类统计
    category_stats = (
        db.query(Product.category, func.count(Product.id))
        .filter(
            Product.tenant_id == current_user["tenant_id"],
            Product.is_deleted == False,
            Product.category.isnot(None),
        )
        .group_by(Product.category)
        .limit(10)
        .all()
    )

    by_category = {cat: count for cat, count in category_stats if cat}

    # 按跟踪频率统计
    frequency_stats = (
        db.query(Product.tracking_frequency, func.count(Product.id))
        .filter(
            Product.tenant_id == current_user["tenant_id"], Product.is_deleted == False
        )
        .group_by(Product.tracking_frequency)
        .all()
    )

    by_tracking_frequency = {str(freq): count for freq, count in frequency_stats}

    # 价格统计
    price_stats = (
        db.query(
            func.avg(Product.current_price),
            func.min(Product.current_price),
            func.max(Product.current_price),
        )
        .filter(
            Product.tenant_id == current_user["tenant_id"],
            Product.is_deleted == False,
            Product.current_price.isnot(None),
        )
        .first()
    )

    avg_price = float(price_stats[0]) if price_stats[0] else None
    min_price = float(price_stats[1]) if price_stats[1] else None
    max_price = float(price_stats[2]) if price_stats[2] else None

    # 评分统计
    rating_stats = (
        db.query(func.avg(Product.rating))
        .filter(
            Product.tenant_id == current_user["tenant_id"],
            Product.is_deleted == False,
            Product.rating.isnot(None),
        )
        .scalar()
    )

    avg_rating = float(rating_stats) if rating_stats else None

    return ProductStatsResponse(
        total_products=total_products,
        active_products=active_products,
        inactive_products=inactive_products,
        by_marketplace=by_marketplace,
        by_category=by_category,
        by_tracking_frequency=by_tracking_frequency,
        avg_price=avg_price,
        avg_rating=avg_rating,
        price_range={"min": min_price, "max": max_price}
        if min_price and max_price
        else {},
        last_updated=datetime.utcnow(),
    )
