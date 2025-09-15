"""产品爬取相关API端点"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from sqlalchemy import desc
from sqlalchemy.orm import Session

from amazon_tracker.common.auth.jwt_auth import get_current_user
from amazon_tracker.common.auth.permissions import PermissionScope, require_permission
from amazon_tracker.common.database.connection import get_db_session
from amazon_tracker.common.database.models.crawl import (
    CrawlerType,
    CrawlTask,
    TaskPriority,
    TaskStatus,
)
from amazon_tracker.common.database.models.product import (
    MarketplaceType,
    Product,
    ProductPriceHistory,
    ProductRankHistory,
    TrackingFrequency,
)
from amazon_tracker.common.task_queue.crawler_tasks import (
    crawl_amazon_product,
    crawl_multiple_products,
)

from .schemas import (
    BatchCrawlRequest,
    CategoryCrawlRequest,
    CategoryCrawlResponse,
    CrawlTaskResponse,
    PriceHistoryResponse,
    ProductCrawlRequest,
    ProductResponse,
    RankHistoryResponse,
)

router = APIRouter(prefix="/products", tags=["products"])
security = HTTPBearer()


@router.post("/crawl", response_model=CrawlTaskResponse)
async def create_crawl_task(
    request: ProductCrawlRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """创建单个产品爬取任务"""

    # 权限检查
    require_permission(current_user, PermissionScope.CRAWLER_CREATE)

    # 检查产品是否存在
    product = (
        db.query(Product)
        .filter(
            Product.asin == request.asin, Product.tenant_id == current_user["tenant_id"]
        )
        .first()
    )

    if not product:
        # 如果产品不存在，创建新产品记录
        product = Product(
            asin=request.asin,
            title=f"Product {request.asin}",  # 临时标题，爬取后更新
            marketplace=request.marketplace or MarketplaceType.AMAZON_US,
            tracking_frequency=request.tracking_frequency or TrackingFrequency.DAILY,
            tenant_id=current_user["tenant_id"],
            created_by=current_user["user_id"],
        )
        db.add(product)
        db.flush()

    # 检查是否已有运行中的任务
    existing_task = (
        db.query(CrawlTask)
        .filter(
            CrawlTask.product_id == product.id,
            CrawlTask.status.in_(
                [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.RETRYING]
            ),
        )
        .first()
    )

    if existing_task:
        raise HTTPException(
            status_code=409,
            detail=f"Product {request.asin} already has a running crawl task",
        )

    # 创建爬虫任务
    crawl_task = CrawlTask(
        product_id=product.id,
        tenant_id=current_user["tenant_id"],
        crawler_type=CrawlerType.APIFY_AMAZON_SCRAPER,
        task_name=f"Manual crawl for {request.asin}",
        priority=request.priority or TaskPriority.NORMAL,
        crawler_config=request.config or {},
        input_data={
            "asin": request.asin,
            "country": request.marketplace.value.split("_")[1]
            if request.marketplace and "_" in request.marketplace.value
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
        config=request.config,
    )

    return CrawlTaskResponse(
        task_id=crawl_task.task_id,
        product_id=product.id,
        asin=request.asin,
        status=crawl_task.status,
        created_at=crawl_task.created_at,
    )


@router.post("/batch-crawl", response_model=CrawlTaskResponse)
async def create_batch_crawl_task(
    request: BatchCrawlRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """创建批量产品爬取任务"""

    # 权限检查
    require_permission(current_user, PermissionScope.CRAWLER_CREATE)

    if not request.asins:
        raise HTTPException(status_code=400, detail="ASIN list cannot be empty")

    if len(request.asins) > 50:  # 限制批量数量
        raise HTTPException(
            status_code=400, detail="Cannot crawl more than 50 products at once"
        )

    # 查找或创建产品记录
    product_ids = []
    for asin in request.asins:
        product = (
            db.query(Product)
            .filter(
                Product.asin == asin, Product.tenant_id == current_user["tenant_id"]
            )
            .first()
        )

        if not product:
            product = Product(
                asin=asin,
                title=f"Product {asin}",
                marketplace=request.marketplace or MarketplaceType.AMAZON_US,
                tracking_frequency=request.tracking_frequency
                or TrackingFrequency.DAILY,
                tenant_id=current_user["tenant_id"],
                created_by=current_user["user_id"],
            )
            db.add(product)
            db.flush()

        product_ids.append(product.id)

    # 创建批量爬虫任务
    crawl_task = CrawlTask(
        product_id=product_ids[0],  # 主产品ID
        tenant_id=current_user["tenant_id"],
        crawler_type=CrawlerType.APIFY_AMAZON_SCRAPER,
        task_name=f"Batch crawl for {len(request.asins)} products",
        priority=request.priority or TaskPriority.NORMAL,
        crawler_config=request.config or {},
        input_data={
            "asins": request.asins,
            "country": request.marketplace.value.split("_")[1]
            if request.marketplace and "_" in request.marketplace.value
            else "US",
        },
    )

    db.add(crawl_task)
    db.commit()

    # 异步执行批量爬虫任务
    background_tasks.add_task(
        crawl_multiple_products.delay,
        crawl_task_id=str(crawl_task.task_id),
        tenant_id=current_user["tenant_id"],
        product_ids=product_ids,
        config=request.config,
    )

    return CrawlTaskResponse(
        task_id=crawl_task.task_id,
        product_id=product_ids[0],
        asin=f"Batch: {', '.join(request.asins[:3])}{'...' if len(request.asins) > 3 else ''}",
        status=crawl_task.status,
        created_at=crawl_task.created_at,
    )


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


@router.get("/{product_id}/price-history", response_model=list[PriceHistoryResponse])
async def get_price_history(
    product_id: int,
    limit: int = Query(100, ge=1, le=1000),
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

    # 获取价格历史
    price_history = (
        db.query(ProductPriceHistory)
        .filter(ProductPriceHistory.product_id == product_id)
        .order_by(desc(ProductPriceHistory.recorded_at))
        .limit(limit)
        .all()
    )

    return [PriceHistoryResponse.from_orm(record) for record in price_history]


@router.get("/{product_id}/rank-history", response_model=list[RankHistoryResponse])
async def get_rank_history(
    product_id: int,
    limit: int = Query(100, ge=1, le=1000),
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

    # 获取排名历史
    rank_history = (
        db.query(ProductRankHistory)
        .filter(ProductRankHistory.product_id == product_id)
        .order_by(desc(ProductRankHistory.recorded_at))
        .limit(limit)
        .all()
    )

    return [RankHistoryResponse.from_orm(record) for record in rank_history]


@router.put("/{product_id}/tracking-frequency")
async def update_tracking_frequency(
    product_id: int,
    frequency: TrackingFrequency,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """更新产品跟踪频率"""

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

    product.tracking_frequency = frequency
    db.commit()

    return {"message": "Tracking frequency updated successfully"}


@router.post("/{product_id}/enable")
async def enable_product_tracking(
    product_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """启用产品跟踪"""

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

    product.is_active = True
    db.commit()

    return {"message": "Product tracking enabled"}


@router.post("/{product_id}/disable")
async def disable_product_tracking(
    product_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """禁用产品跟踪"""

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

    product.is_active = False
    db.commit()

    return {"message": "Product tracking disabled"}


@router.post("/category-crawl", response_model=CategoryCrawlResponse)
async def create_category_crawl_task(
    request: CategoryCrawlRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """创建品类产品爬取任务"""

    # 权限检查
    require_permission(current_user, PermissionScope.CRAWLER_CREATE)

    # 导入品类提取器
    from amazon_tracker.common.crawlers.category_extractor import category_to_asins

    try:
        # 首先提取品类中的ASIN列表
        extraction_result = await category_to_asins(
            category_url=request.category_url,
            product_limit=request.product_limit,
            sort_by=request.sort_by,
            filters=request.filters,
            scraper_config=request.config,
        )

        if not extraction_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to extract products from category: {extraction_result['error']}",
            )

        asins = extraction_result["asins"]
        if not asins:
            raise HTTPException(
                status_code=404, detail="No products found in the specified category"
            )

        # 创建或更新产品记录
        product_ids = []
        for asin in asins:
            product = (
                db.query(Product)
                .filter(
                    Product.asin == asin, Product.tenant_id == current_user["tenant_id"]
                )
                .first()
            )

            if not product:
                # 从提取的产品信息中获取详细信息
                product_info = next(
                    (p for p in extraction_result["products"] if p["asin"] == asin), {}
                )

                product = Product(
                    asin=asin,
                    title=product_info.get("title", f"Product {asin}"),
                    brand=product_info.get("brand"),
                    category=request.category_name,
                    marketplace=request.marketplace or MarketplaceType.AMAZON_US,
                    current_price=product_info.get("price"),
                    current_rank=product_info.get("rank"),
                    rating=product_info.get("rating"),
                    review_count=product_info.get("review_count", 0),
                    image_url=product_info.get("image_url"),
                    product_url=product_info.get(
                        "product_url", f"https://amazon.com/dp/{asin}"
                    ),
                    availability=product_info.get("availability"),
                    tracking_frequency=request.tracking_frequency
                    or TrackingFrequency.DAILY,
                    tenant_id=current_user["tenant_id"],
                    created_by=current_user["user_id"],
                )
                db.add(product)
                db.flush()

            # 更新产品分类信息
            if product.category != request.category_name:
                product.category = request.category_name

            product_ids.append(product.id)

        # 创建批量爬虫任务
        crawl_task = CrawlTask(
            product_id=product_ids[0],  # 主产品ID
            tenant_id=current_user["tenant_id"],
            crawler_type=CrawlerType.APIFY_AMAZON_SCRAPER,
            task_name=f"Category crawl: {request.category_name}",
            priority=request.priority or TaskPriority.NORMAL,
            crawler_config=request.config or {},
            input_data={
                "asins": asins,
                "category_url": request.category_url,
                "category_name": request.category_name,
                "country": request.marketplace.value.split("_")[1]
                if request.marketplace and "_" in request.marketplace.value
                else "US",
            },
        )

        db.add(crawl_task)
        db.commit()

        # 异步执行品类爬虫任务
        background_tasks.add_task(
            crawl_multiple_products.delay,
            crawl_task_id=str(crawl_task.task_id),
            tenant_id=current_user["tenant_id"],
            product_ids=product_ids,
            config=request.config,
        )

        return CategoryCrawlResponse(
            task_id=str(crawl_task.task_id),
            category_name=request.category_name,
            category_url=request.category_url,
            product_count=len(asins),
            product_ids=product_ids,
            asins_found=asins,
            status=crawl_task.status,
            created_at=crawl_task.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal error during category crawl: {str(e)}"
        )


@router.get(
    "/categories/{category_name}/products", response_model=list[ProductResponse]
)
async def get_category_products(
    category_name: str,
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """获取指定品类的所有产品"""

    # 权限检查
    require_permission(current_user, PermissionScope.PRODUCT_READ)

    # 查询品类产品
    products = (
        db.query(Product)
        .filter(
            Product.category == category_name,
            Product.tenant_id == current_user["tenant_id"],
        )
        .order_by(desc(Product.last_crawled_at))
        .limit(limit)
        .all()
    )

    return [ProductResponse.from_orm(product) for product in products]
