"""爬虫相关的Celery任务"""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any

from celery import Task
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..crawlers.apify_client import ApifyAmazonScraper
from ..crawlers.data_processor import AmazonDataProcessor
from ..database.connection import get_db_session
from ..database.models.crawl import (
    CrawlerType,
    CrawlLog,
    CrawlTask,
    TaskPriority,
    TaskStatus,
)
from ..database.models.product import Product, ProductPriceHistory, ProductRankHistory
from .celery_app import celery_app

logger = logging.getLogger(__name__)


class CrawlerTask(Task):
    """爬虫任务基类"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的回调"""
        logger.error(f"Task {task_id} failed: {exc}")

        # 更新数据库中的任务状态
        try:
            with get_db_session() as db:
                if len(args) > 0:
                    crawl_task_id = args[0]
                    task = (
                        db.query(CrawlTask)
                        .filter(CrawlTask.task_id == crawl_task_id)
                        .first()
                    )
                    if task:
                        task.fail_task(str(exc), str(einfo))
                        db.commit()
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")

    def on_success(self, retval, task_id, args, kwargs):
        """任务成功时的回调"""
        logger.info(f"Task {task_id} completed successfully")


@celery_app.task(bind=True, base=CrawlerTask, queue="crawler")
def crawl_amazon_product(
    self,
    crawl_task_id: str,
    tenant_id: str,
    product_id: int,
    config: dict[str, Any] = None,
):
    """爬取单个Amazon产品"""

    task_logger = logging.getLogger(f"crawl_task_{crawl_task_id}")

    with get_db_session() as db:
        try:
            # 获取爬虫任务
            crawl_task = (
                db.query(CrawlTask).filter(CrawlTask.task_id == crawl_task_id).first()
            )
            if not crawl_task:
                raise ValueError(f"Crawl task {crawl_task_id} not found")

            # 获取产品信息
            product = (
                db.query(Product)
                .filter(Product.id == product_id, Product.tenant_id == tenant_id)
                .first()
            )
            if not product:
                raise ValueError(
                    f"Product {product_id} not found for tenant {tenant_id}"
                )

            # 开始任务
            crawl_task.start_task(worker_name=self.request.hostname)
            db.commit()

            # 记录开始日志
            log_entry = CrawlLog(
                task_id=crawl_task_id,
                level="INFO",
                message=f"Starting crawl for product ASIN: {product.asin}",
                details={"product_id": product_id, "asin": product.asin},
            )
            db.add(log_entry)
            db.commit()

            # 初始化爬虫
            scraper_config = config or {}
            scraper = ApifyAmazonScraper(scraper_config)

            # 执行爬取
            task_logger.info(f"Crawling product ASIN: {product.asin}")

            # 在Celery任务中使用同步方式调用异步函数
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                crawl_result = loop.run_until_complete(
                    scraper.scrape_single_product(
                        asin=product.asin,
                        country=product.marketplace.value.split("_")[1]
                        if "_" in product.marketplace.value
                        else "US",
                    )
                )
            finally:
                loop.close()

            if not crawl_result.success:
                raise Exception(f"Crawl failed: {crawl_result.error}")

            # 处理爬取结果
            processor = AmazonDataProcessor()
            raw_products = crawl_result.data.get("products", [])

            if not raw_products:
                raise Exception("No product data returned from crawler")

            # 清洗和验证数据
            processed_products = processor.process_batch(raw_products)

            if not processed_products:
                raise Exception("No valid product data after processing")

            product_data = processed_products[0]  # 取第一个产品

            # 更新产品信息
            updated_fields = _update_product_from_crawl_data(db, product, product_data)

            # 记录价格历史
            if product_data.get("price"):
                price_history = ProductPriceHistory(
                    product_id=product.id,
                    price=product_data["price"],
                    list_price=product_data.get("list_price"),
                    currency=product_data.get("currency", "USD"),
                    recorded_at=datetime.utcnow(),
                )
                db.add(price_history)

            # 记录排名历史
            if product_data.get("rank"):
                rank_history = ProductRankHistory(
                    product_id=product.id,
                    rank=product_data["rank"],
                    category=product_data.get("category"),
                    recorded_at=datetime.utcnow(),
                )
                db.add(rank_history)

            # 完成任务
            crawl_task.complete_task(
                result_data={
                    "product_data": product_data,
                    "updated_fields": updated_fields,
                    "metadata": crawl_result.metadata,
                },
                items_processed=1,
            )

            # 记录成功日志
            log_entry = CrawlLog(
                task_id=crawl_task_id,
                level="INFO",
                message=f"Successfully crawled product ASIN: {product.asin}",
                details={
                    "updated_fields": updated_fields,
                    "price": product_data.get("price"),
                    "rank": product_data.get("rank"),
                },
            )
            db.add(log_entry)

            db.commit()

            task_logger.info(f"Crawl completed for product ASIN: {product.asin}")

            return {
                "success": True,
                "product_id": product_id,
                "asin": product.asin,
                "updated_fields": updated_fields,
            }

        except Exception as e:
            task_logger.error(f"Crawl failed for product {product_id}: {e}")

            # 记录错误日志
            log_entry = CrawlLog(
                task_id=crawl_task_id,
                level="ERROR",
                message=f"Crawl failed: {str(e)}",
                details={"error": str(e), "product_id": product_id},
            )
            db.add(log_entry)

            # 更新任务状态
            if crawl_task:
                crawl_task.fail_task(str(e))

            db.commit()
            raise


@celery_app.task(bind=True, base=CrawlerTask, queue="crawler")
def crawl_multiple_products(
    self,
    crawl_task_id: str,
    tenant_id: str,
    product_ids: list[int],
    config: dict[str, Any] = None,
):
    """批量爬取多个Amazon产品"""

    task_logger = logging.getLogger(f"crawl_task_{crawl_task_id}")

    with get_db_session() as db:
        try:
            # 获取爬虫任务
            crawl_task = (
                db.query(CrawlTask).filter(CrawlTask.task_id == crawl_task_id).first()
            )
            if not crawl_task:
                raise ValueError(f"Crawl task {crawl_task_id} not found")

            # 获取产品列表
            products = (
                db.query(Product)
                .filter(Product.id.in_(product_ids), Product.tenant_id == tenant_id)
                .all()
            )

            if not products:
                raise ValueError(f"No products found for tenant {tenant_id}")

            # 开始任务
            crawl_task.start_task(worker_name=self.request.hostname)
            db.commit()

            # 准备爬取数据
            asins = [product.asin for product in products]

            # 记录开始日志
            log_entry = CrawlLog(
                task_id=crawl_task_id,
                level="INFO",
                message=f"Starting batch crawl for {len(asins)} products",
                details={
                    "product_count": len(asins),
                    "asins": asins[:10],
                },  # 只记录前10个ASIN
            )
            db.add(log_entry)
            db.commit()

            # 初始化爬虫
            scraper_config = config or {}
            scraper = ApifyAmazonScraper(scraper_config)

            # 执行批量爬取
            task_logger.info(f"Crawling {len(asins)} products")

            # 在Celery任务中使用同步方式调用异步函数
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                crawl_result = loop.run_until_complete(
                    scraper.scrape_multiple_products(
                        asins=asins,
                        country="US",  # 默认美国站
                    )
                )
            finally:
                loop.close()

            if not crawl_result.success:
                raise Exception(f"Batch crawl failed: {crawl_result.error}")

            # 处理爬取结果
            processor = AmazonDataProcessor()
            raw_products = crawl_result.data.get("products", [])

            # 清洗和验证数据
            processed_products = processor.process_batch(raw_products)

            # 更新产品信息
            updated_products = []
            for product_data in processed_products:
                asin = product_data.get("asin")
                if not asin:
                    continue

                # 找到对应的产品
                product = next((p for p in products if p.asin == asin), None)
                if not product:
                    continue

                # 更新产品信息
                updated_fields = _update_product_from_crawl_data(
                    db, product, product_data
                )

                # 记录价格历史
                if product_data.get("price"):
                    price_history = ProductPriceHistory(
                        product_id=product.id,
                        price=product_data["price"],
                        list_price=product_data.get("list_price"),
                        buy_box_price=product_data.get("buy_box_price"),
                        currency=product_data.get("currency", "USD"),
                        recorded_at=datetime.utcnow(),
                    )
                    db.add(price_history)

                # 记录排名历史
                if product_data.get("rank"):
                    rank_history = ProductRankHistory(
                        product_id=product.id,
                        rank=product_data["rank"],
                        category=product_data.get("category"),
                        recorded_at=datetime.utcnow(),
                    )
                    db.add(rank_history)

                updated_products.append(
                    {
                        "product_id": product.id,
                        "asin": asin,
                        "updated_fields": updated_fields,
                    }
                )

            # 完成任务
            crawl_task.complete_task(
                result_data={
                    "updated_products": updated_products,
                    "total_requested": len(products),
                    "total_processed": len(processed_products),
                    "metadata": crawl_result.metadata,
                },
                items_processed=len(processed_products),
            )

            # 记录成功日志
            log_entry = CrawlLog(
                task_id=crawl_task_id,
                level="INFO",
                message=f"Batch crawl completed: {len(processed_products)}/{len(products)} products processed",
                details={
                    "processed_count": len(processed_products),
                    "requested_count": len(products),
                },
            )
            db.add(log_entry)

            db.commit()

            task_logger.info(
                f"Batch crawl completed: {len(processed_products)}/{len(products)} products"
            )

            return {
                "success": True,
                "total_requested": len(products),
                "total_processed": len(processed_products),
                "updated_products": updated_products,
            }

        except Exception as e:
            task_logger.error(f"Batch crawl failed: {e}")

            # 记录错误日志
            log_entry = CrawlLog(
                task_id=crawl_task_id,
                level="ERROR",
                message=f"Batch crawl failed: {str(e)}",
                details={"error": str(e), "product_count": len(product_ids)},
            )
            db.add(log_entry)

            # 更新任务状态
            if crawl_task:
                crawl_task.fail_task(str(e))

            db.commit()
            raise


@celery_app.task(bind=True, queue="scheduler")
def schedule_product_tracking(self):
    """调度产品跟踪任务"""

    task_logger = logging.getLogger("scheduler")

    with get_db_session() as db:
        try:
            # 查找需要跟踪的产品
            now = datetime.utcnow()

            # 根据跟踪频率计算下次爬取时间
            products_to_track = (
                db.query(Product)
                .filter(
                    Product.is_active == True,
                    Product.is_deleted == False,
                    Product.next_crawl_at <= now,
                )
                .all()
            )

            if not products_to_track:
                task_logger.info("No products to track at this time")
                return {"scheduled_tasks": 0}

            scheduled_count = 0

            for product in products_to_track:
                try:
                    # 检查是否已有进行中的任务
                    existing_task = (
                        db.query(CrawlTask)
                        .filter(
                            CrawlTask.product_id == product.id,
                            CrawlTask.status.in_(
                                [
                                    TaskStatus.PENDING,
                                    TaskStatus.RUNNING,
                                    TaskStatus.RETRYING,
                                ]
                            ),
                        )
                        .first()
                    )

                    if existing_task:
                        task_logger.debug(
                            f"Product {product.id} already has running task"
                        )
                        continue

                    # 创建爬虫任务
                    crawl_task = CrawlTask(
                        product_id=product.id,
                        tenant_id=product.tenant_id,
                        crawler_type=CrawlerType.APIFY_AMAZON_SCRAPER,
                        task_name=f"Scheduled tracking for {product.asin}",
                        priority=TaskPriority.NORMAL,
                        scheduled_at=now,
                        input_data={
                            "asin": product.asin,
                            "country": product.marketplace.value.split("_")[1]
                            if "_" in product.marketplace.value
                            else "US",
                        },
                    )

                    db.add(crawl_task)
                    db.flush()  # 获取任务ID

                    # 异步执行爬虫任务
                    crawl_amazon_product.delay(
                        crawl_task_id=str(crawl_task.task_id),
                        tenant_id=product.tenant_id,
                        product_id=product.id,
                    )

                    # 更新产品的下次爬取时间
                    _update_next_crawl_time(product)

                    scheduled_count += 1

                except Exception as e:
                    task_logger.error(
                        f"Failed to schedule task for product {product.id}: {e}"
                    )
                    continue

            db.commit()

            task_logger.info(f"Scheduled {scheduled_count} tracking tasks")

            return {"scheduled_tasks": scheduled_count}

        except Exception as e:
            task_logger.error(f"Scheduler task failed: {e}")
            raise


def _update_product_from_crawl_data(
    db: Session, product: Product, product_data: dict[str, Any]
) -> list[str]:
    """从爬取数据更新产品信息"""
    updated_fields = []

    # 更新标题
    if product_data.get("title") and product_data["title"] != product.title:
        product.title = product_data["title"]
        updated_fields.append("title")

    # 更新品牌
    if product_data.get("brand") and product_data["brand"] != product.brand:
        product.brand = product_data["brand"]
        updated_fields.append("brand")

    # 更新分类
    if product_data.get("category") and product_data["category"] != product.category:
        product.category = product_data["category"]
        updated_fields.append("category")

    # 更新当前价格
    if product_data.get("price") and product_data["price"] != product.current_price:
        product.current_price = product_data["price"]
        updated_fields.append("current_price")

    # 更新Buy Box价格
    if (
        product_data.get("buy_box_price")
        and product_data["buy_box_price"] != product.buy_box_price
    ):
        product.buy_box_price = product_data["buy_box_price"]
        updated_fields.append("buy_box_price")

    # 更新当前排名
    if product_data.get("rank") and product_data["rank"] != product.current_rank:
        product.current_rank = product_data["rank"]
        updated_fields.append("current_rank")

    # 更新评分
    if product_data.get("rating") and product_data["rating"] != product.current_rating:
        product.current_rating = product_data["rating"]
        updated_fields.append("current_rating")

    # 更新评论数
    if (
        product_data.get("review_count")
        and product_data["review_count"] != product.current_review_count
    ):
        product.current_review_count = product_data["review_count"]
        updated_fields.append("review_count")

    # 更新图片URL
    if product_data.get("image_url") and product_data["image_url"] != product.image_url:
        product.image_url = product_data["image_url"]
        updated_fields.append("image_url")

    # 更新最后爬取时间
    product.last_crawled_at = datetime.utcnow()
    updated_fields.append("last_crawled_at")

    return updated_fields


def _update_next_crawl_time(product: Product):
    """更新产品的下次爬取时间"""
    from ..database.models.product import TrackingFrequency

    now = datetime.utcnow()

    if product.tracking_frequency == TrackingFrequency.HOURLY:
        product.next_crawl_at = now + timedelta(hours=1)
    elif product.tracking_frequency == TrackingFrequency.EVERY_6_HOURS:
        product.next_crawl_at = now + timedelta(hours=6)
    elif product.tracking_frequency == TrackingFrequency.EVERY_12_HOURS:
        product.next_crawl_at = now + timedelta(hours=12)
    elif product.tracking_frequency == TrackingFrequency.DAILY:
        product.next_crawl_at = now + timedelta(days=1)
    elif product.tracking_frequency == TrackingFrequency.WEEKLY:
        product.next_crawl_at = now + timedelta(weeks=1)
    else:
        # 默认每日
        product.next_crawl_at = now + timedelta(days=1)


@celery_app.task(bind=True, name="crawler_tasks.update_category_products")
def update_category_products(self, category_name: str, tenant_id: str = None):
    """
    更新指定品类的所有产品数据

    Args:
        category_name: 品类名称
        tenant_id: 租户ID（可选，如果不指定则更新所有租户）
    """
    from ...services.monitoring.anomaly_detector import AnomalyDetector
    from ..database.connection import get_db_session
    from ..database.models.product import Product

    task_logger = get_task_logger(__name__)
    task_logger.info(f"Starting category products update for: {category_name}")

    session = get_db_session()
    anomaly_detector = AnomalyDetector()

    try:
        # 构建查询条件
        query = session.query(Product).filter(
            Product.category == category_name, Product.is_active == True
        )

        if tenant_id:
            query = query.filter(Product.tenant_id == tenant_id)

        # 获取需要更新的产品
        products = query.all()

        if not products:
            task_logger.info(f"No active products found for category: {category_name}")
            return {
                "success": True,
                "category_name": category_name,
                "processed_products": 0,
                "message": "No products to update",
            }

        task_logger.info(
            f"Found {len(products)} products to update in category: {category_name}"
        )

        # 按租户分组更新
        tenant_products = {}
        for product in products:
            tenant_id = product.tenant_id
            if tenant_id not in tenant_products:
                tenant_products[tenant_id] = []
            tenant_products[tenant_id].append(product)

        updated_count = 0
        failed_count = 0
        anomalies_found = 0

        # 对每个租户的产品进行批量更新
        for tenant_id, tenant_product_list in tenant_products.items():
            try:
                # 提取ASIN列表
                asins = [p.asin for p in tenant_product_list]

                # 执行批量爬取
                task_logger.info(
                    f"Crawling {len(asins)} products for tenant {tenant_id}"
                )
                crawl_result = crawl_multiple_products.delay(
                    crawl_task_id=f"category-update-{category_name}-{tenant_id}",
                    tenant_id=tenant_id,
                    product_ids=[p.id for p in tenant_product_list],
                )

                # 等待批量爬取完成（异步处理）
                updated_count += len(asins)

                # 检查产品异常
                for product in tenant_product_list:
                    try:
                        # 检查价格异常
                        price_anomaly = anomaly_detector.check_price_anomaly(product.id)
                        if price_anomaly.get("is_anomaly"):
                            anomalies_found += 1
                            task_logger.info(
                                f"Price anomaly detected for {product.asin}: {price_anomaly}"
                            )

                        # 检查BSR异常
                        bsr_anomaly = anomaly_detector.check_bsr_anomaly(product.id)
                        if bsr_anomaly.get("is_anomaly"):
                            anomalies_found += 1
                            task_logger.info(
                                f"BSR anomaly detected for {product.asin}: {bsr_anomaly}"
                            )

                    except Exception as e:
                        task_logger.warning(
                            f"Anomaly check failed for product {product.asin}: {e}"
                        )

            except Exception as e:
                task_logger.error(
                    f"Failed to update products for tenant {tenant_id}: {e}"
                )
                failed_count += len(tenant_product_list)

        task_logger.info(
            f"Category update completed for {category_name}: "
            f"{updated_count} updated, {failed_count} failed, {anomalies_found} anomalies"
        )

        return {
            "success": True,
            "category_name": category_name,
            "processed_products": updated_count,
            "failed_products": failed_count,
            "anomalies_found": anomalies_found,
            "tenant_count": len(tenant_products),
        }

    except Exception as e:
        task_logger.error(f"Category update failed for {category_name}: {str(e)}")
        raise e

    finally:
        session.close()


@celery_app.task(bind=True, name="crawler_tasks.update_all_category_products")
def update_all_category_products(self):
    """更新所有活跃品类的产品数据"""
    from sqlalchemy import distinct

    from ..database.connection import get_db_session
    from ..database.models.product import Product

    task_logger = get_task_logger(__name__)
    task_logger.info("Starting update for all category products")

    session = get_db_session()

    try:
        # 获取所有活跃的品类
        categories = (
            session.query(distinct(Product.category))
            .filter(Product.is_active == True, Product.category.isnot(None))
            .all()
        )

        if not categories:
            task_logger.info("No active categories found")
            return {
                "success": True,
                "processed_categories": 0,
                "message": "No categories to update",
            }

        category_names = [cat[0] for cat in categories]
        task_logger.info(
            f"Found {len(category_names)} active categories: {category_names}"
        )

        # 异步启动每个品类的更新任务
        results = []
        for category_name in category_names:
            try:
                result = update_category_products.delay(category_name)
                results.append(
                    {
                        "category_name": category_name,
                        "task_id": result.id,
                        "status": "started",
                    }
                )
                task_logger.info(f"Started update task for category: {category_name}")

            except Exception as e:
                task_logger.error(
                    f"Failed to start update for category {category_name}: {e}"
                )
                results.append(
                    {
                        "category_name": category_name,
                        "status": "failed",
                        "error": str(e),
                    }
                )

        return {
            "success": True,
            "processed_categories": len(category_names),
            "category_results": results,
        }

    except Exception as e:
        task_logger.error(f"Failed to update all category products: {str(e)}")
        raise e

    finally:
        session.close()


def run_async(coro):
    def _run():
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    with ThreadPoolExecutor() as executor:
        return executor.submit(_run).result()

@celery_app.task(bind=True, queue="crawler")
def crawl_products_batch(self, tenant_id: str = None):
    """批量抓取产品数据（支持指定租户）"""
    task_logger = logging.getLogger("batch_crawler")
    print(f"开始任务 (租户: {tenant_id or 'all'})")
    with get_db_session() as db:
        try:

            # 提取所有ASIN
            # asins = [p.asin for p in active_products]
            # asins = ["B09JQMJHXY"]
            asins = [
                "B0DD41G2NZ", "B09FLNSYDZ", "B09DT48V16", "B0F8BLGGD5", "B0DLKB5V35",
                "B00NJ2M33I", "B08HT46TVP", "B0BR9SSP86", "B0BTYCRJSS", "B07SKLLYTW"
            ]

            task_logger.info(f"Crawling {len(asins)} products: {asins}")

            # 使用Apify爬虫批量抓取（同步方式）
            scraper_config = {}
            scraper = ApifyAmazonScraper(scraper_config)

            # 在Celery任务中使用同步方式调用异步函数
            result = run_async(scraper.crawl({"asins": asins}))

            if not result.success:
                task_logger.error(f"Apify crawl failed: {result.error}")
                return {"processed": 0, "error": result.error}

            # 处理结果数据
            processed_count = 0
            created_count = 0
            updated_count = 0

            # 已经处理过的asin就不再处理了
            asin_list = []

            for product_data in result.data.get("products", []):
                asin = product_data.get("asin")
                print("结果：", asin)
                if not asin or asin in asin_list:
                    continue
                asin_list.append(asin)

                try:
                    from ..database.models.product import MarketplaceType

                    # 查找现有产品（按租户过滤）
                    query = db.query(Product).filter(
                        Product.asin == asin,
                        Product.marketplace == MarketplaceType.AMAZON_US,
                    )

                    # 如果指定了租户ID，只查找该租户的产品
                    if tenant_id:
                        query = query.filter(Product.tenant_id == tenant_id)

                    existing_product = query.first()

                    if existing_product:
                        # 更新现有产品
                        changes = _update_product_from_crawl_data(db, existing_product, product_data)

                        # 记录价格历史
                        if product_data.get("price"):
                            price_history = ProductPriceHistory(
                                product_id=existing_product.id,
                                price=product_data["price"],
                                list_price=product_data.get("list_price"),
                                buy_box_price=product_data.get("buy_box_price"),
                                currency=product_data.get("currency", "USD"),
                                recorded_at=datetime.utcnow(),
                            )
                            db.add(price_history)

                        # 记录排名历史
                        if product_data.get("rank"):
                            rank_history = ProductRankHistory(
                                product_id=existing_product.id,
                                rank=product_data["rank"],
                                category=product_data.get("category"),
                                recorded_at=datetime.utcnow(),
                                review_count=product_data.get("review_count"),
                                rating=product_data.get("rating")
                            )
                            db.add(rank_history)

                        updated_count += 1
                        task_logger.info(f"Updated product {asin}: {len(changes)} changes")

                    else:
                        # 创建新产品
                        from ..database.models.product import MarketplaceType, ProductStatus

                        new_product = Product(
                            asin=asin,
                            title=product_data.get("title", f"Product {asin}"),
                            brand=product_data.get("brand"),
                            category=product_data.get("category"),
                            marketplace=MarketplaceType.AMAZON_US,
                            tenant_id=tenant_id or "demo",  # 使用传入的租户ID，fallback到demo
                            product_url=f"https://www.amazon.com/dp/{asin}",
                            image_url=product_data.get("image_url"),
                            status=ProductStatus.ACTIVE,
                            current_price=product_data.get("price"),
                            buy_box_price=product_data.get("buy_box_price"),
                            current_rank=product_data.get("rank"),
                            current_rating=product_data.get("rating"),
                            current_review_count=product_data.get("review_count", 0),
                            current_availability=product_data.get("availability"),
                            product_data=product_data,
                            bullet_points=product_data.get("bullet_points", []),
                            description=product_data.get("description"),
                            last_scraped_at=datetime.utcnow(),
                        )

                        db.add(new_product)
                        db.flush()  # 获取新产品的ID

                        # 记录初始价格历史
                        if product_data.get("price"):
                            price_history = ProductPriceHistory(
                                product_id=new_product.id,
                                price=product_data["price"],
                                list_price=product_data.get("list_price"),
                                buy_box_price=product_data.get("buy_box_price"),
                                currency=product_data.get("currency", "USD"),
                                recorded_at=datetime.utcnow(),
                            )
                            db.add(price_history)

                        # 记录初始排名历史
                        if product_data.get("rank"):
                            rank_history = ProductRankHistory(
                                product_id=new_product.id,
                                rank=product_data["rank"],
                                category=product_data.get("category"),
                                recorded_at=datetime.utcnow(),
                                review_count=product_data.get("review_count"),
                                rating=product_data.get("rating")
                            )
                            db.add(rank_history)

                        created_count += 1
                        task_logger.info(f"Created new product {asin}")

                    processed_count += 1

                except IntegrityError as e:
                    # 处理重复ASIN的情况 - 数据库唯一约束阻止插入
                    if "uq_product_asin_marketplace_tenant" in str(e):
                        task_logger.info(f"Product {asin} already exists for tenant {tenant_id}, skipping creation")
                        # 尝试更新现有产品
                        try:
                            existing_product = (
                                db.query(Product)
                                .filter(
                                    Product.asin == asin,
                                    Product.marketplace == MarketplaceType.AMAZON_US,
                                    Product.tenant_id == tenant_id
                                )
                                .first()
                            )
                            if existing_product:
                                _update_product_from_crawl_data(db, existing_product, product_data)
                                updated_count += 1
                                task_logger.info(f"Updated existing product {asin}")
                        except Exception as update_e:
                            task_logger.error(f"Failed to update existing product {asin}: {update_e}")
                    else:
                        task_logger.error(f"Database constraint error for product {asin}: {e}")
                    continue
                except Exception as e:
                    task_logger.error(f"Failed to process product {asin}: {e}")
                    continue

            db.commit()
            task_logger.info(
                f"Batch crawl completed: {processed_count} products processed "
                f"({created_count} created, {updated_count} updated)"
            )
            return {
                "processed": processed_count,
                "created": created_count,
                "updated": updated_count,
                "success": True
            }

        except Exception as e:
            task_logger.error(f"Batch crawl failed: {e}")
            db.rollback()
            raise
