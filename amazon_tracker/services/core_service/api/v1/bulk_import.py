"""批量产品导入API端点"""

import csv
import io
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from amazon_tracker.common.auth.jwt_auth import get_current_user
from amazon_tracker.common.auth.permissions import PermissionScope, require_permission
from amazon_tracker.common.database.connection import get_db_session
from amazon_tracker.common.database.models.product import (
    MarketplaceType,
    Product,
    ProductStatus,
    TrackingFrequency,
)
from amazon_tracker.common.task_queue.crawler_tasks import crawl_amazon_product

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bulk-import", tags=["bulk-import"])
security = HTTPBearer()


class BulkImportRequest(BaseModel):
    """批量导入请求"""

    asins: list[str] = Field(..., min_items=1, max_items=50)
    marketplace: MarketplaceType = MarketplaceType.AMAZON_US
    tracking_frequency: TrackingFrequency = TrackingFrequency.DAILY
    category: Optional[str] = None
    auto_crawl: bool = True


class BulkImportResult(BaseModel):
    """批量导入结果"""

    total_requested: int
    successful_imports: int
    failed_imports: int
    duplicate_products: int
    import_details: list[dict]
    failed_asins: list[str]


class ProductImportItem(BaseModel):
    """产品导入项"""

    asin: str = Field(..., min_length=10, max_length=10)
    title: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    marketplace: MarketplaceType = MarketplaceType.AMAZON_US
    tracking_frequency: TrackingFrequency = TrackingFrequency.DAILY


@router.post("/asins", response_model=BulkImportResult)
async def bulk_import_by_asins(
    request: BulkImportRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """通过ASIN列表批量导入产品"""

    # 权限检查
    require_permission(current_user, PermissionScope.PRODUCT_CREATE)

    logger.info(f"Starting bulk import for {len(request.asins)} ASINs")

    import_results = {
        "successful": [],
        "failed": [],
        "duplicates": [],
    }

    # 验证ASIN格式
    valid_asins = []
    for asin in request.asins:
        if len(asin) == 10 and asin.isalnum():
            valid_asins.append(asin)
        else:
            import_results["failed"].append(
                {"asin": asin, "reason": "Invalid ASIN format"}
            )

    # 检查重复产品
    for asin in valid_asins:
        existing_product = (
            db.query(Product)
            .filter(
                Product.asin == asin, Product.tenant_id == current_user["tenant_id"]
            )
            .first()
        )

        if existing_product:
            import_results["duplicates"].append(
                {
                    "asin": asin,
                    "product_id": existing_product.id,
                    "status": "Already exists",
                }
            )
        else:
            # 创建产品记录
            try:
                product = Product(
                    asin=asin,
                    title=f"Product {asin}",  # 临时标题，爬取后更新
                    category=request.category,
                    marketplace=request.marketplace,
                    tracking_frequency=request.tracking_frequency,
                    status=ProductStatus.PENDING,
                    tenant_id=current_user["tenant_id"],
                    created_by=current_user["user_id"],
                )

                db.add(product)
                db.flush()

                # 如果开启自动爬取，创建爬虫任务
                if request.auto_crawl:
                    crawl_amazon_product.delay(
                        product_id=product.id,
                        tenant_id=current_user["tenant_id"],
                        config={
                            "country": request.marketplace.value.split("_")[1]
                            if "_" in request.marketplace.value
                            else "US"
                        },
                    )

                import_results["successful"].append(
                    {
                        "asin": asin,
                        "product_id": product.id,
                        "status": "Created",
                        "crawl_scheduled": request.auto_crawl,
                    }
                )

                logger.info(f"Successfully created product for ASIN: {asin}")

            except Exception as e:
                logger.error(f"Failed to create product for ASIN {asin}: {e}")
                import_results["failed"].append({"asin": asin, "reason": str(e)})

    db.commit()

    return BulkImportResult(
        total_requested=len(request.asins),
        successful_imports=len(import_results["successful"]),
        failed_imports=len(import_results["failed"]),
        duplicate_products=len(import_results["duplicates"]),
        import_details=import_results["successful"] + import_results["duplicates"],
        failed_asins=[item["asin"] for item in import_results["failed"]],
    )


@router.post("/csv", response_model=BulkImportResult)
async def bulk_import_from_csv(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """通过CSV文件批量导入产品

    CSV格式要求:
    asin,title,brand,category,marketplace,tracking_frequency
    B07ABC123,Product Title,Brand Name,electronics,AMAZON_US,daily
    """

    # 权限检查
    require_permission(current_user, PermissionScope.PRODUCT_CREATE)

    # 验证文件类型
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    try:
        # 读取CSV内容
        content = await file.read()
        csv_content = io.StringIO(content.decode("utf-8"))
        csv_reader = csv.DictReader(csv_content)

        import_results = {
            "successful": [],
            "failed": [],
            "duplicates": [],
        }

        row_count = 0
        for row in csv_reader:
            row_count += 1

            # 限制导入数量
            if row_count > 100:
                import_results["failed"].append(
                    {
                        "row": row_count,
                        "reason": "Exceeded maximum import limit (100 products)",
                    }
                )
                break

            try:
                # 验证必需字段
                asin = row.get("asin", "").strip()
                if not asin or len(asin) != 10:
                    import_results["failed"].append(
                        {"row": row_count, "asin": asin, "reason": "Invalid ASIN"}
                    )
                    continue

                # 检查重复
                existing_product = (
                    db.query(Product)
                    .filter(
                        Product.asin == asin,
                        Product.tenant_id == current_user["tenant_id"],
                    )
                    .first()
                )

                if existing_product:
                    import_results["duplicates"].append(
                        {
                            "row": row_count,
                            "asin": asin,
                            "product_id": existing_product.id,
                            "status": "Already exists",
                        }
                    )
                    continue

                # 解析其他字段
                marketplace_str = row.get("marketplace", "AMAZON_US").strip()
                try:
                    marketplace = MarketplaceType(marketplace_str)
                except ValueError:
                    marketplace = MarketplaceType.AMAZON_US

                frequency_str = row.get("tracking_frequency", "DAILY").strip()
                try:
                    frequency = TrackingFrequency(frequency_str.lower())
                except ValueError:
                    frequency = TrackingFrequency.DAILY

                # 创建产品
                product = Product(
                    asin=asin,
                    title=row.get("title", f"Product {asin}").strip()
                    or f"Product {asin}",
                    brand=row.get("brand", "").strip() or None,
                    category=row.get("category", "").strip() or None,
                    marketplace=marketplace,
                    tracking_frequency=frequency,
                    status=ProductStatus.PENDING,
                    tenant_id=current_user["tenant_id"],
                    created_by=current_user["user_id"],
                )

                db.add(product)
                db.flush()

                # 自动创建爬虫任务
                crawl_amazon_product.delay(
                    product_id=product.id, tenant_id=current_user["tenant_id"]
                )

                import_results["successful"].append(
                    {
                        "row": row_count,
                        "asin": asin,
                        "product_id": product.id,
                        "status": "Created",
                        "crawl_scheduled": True,
                    }
                )

            except Exception as e:
                logger.error(f"Error processing CSV row {row_count}: {e}")
                import_results["failed"].append(
                    {
                        "row": row_count,
                        "asin": row.get("asin", "Unknown"),
                        "reason": str(e),
                    }
                )

        db.commit()

        logger.info(
            f"CSV import completed: {len(import_results['successful'])} successful, "
            f"{len(import_results['failed'])} failed, "
            f"{len(import_results['duplicates'])} duplicates"
        )

        return BulkImportResult(
            total_requested=row_count,
            successful_imports=len(import_results["successful"]),
            failed_imports=len(import_results["failed"]),
            duplicate_products=len(import_results["duplicates"]),
            import_details=import_results["successful"] + import_results["duplicates"],
            failed_asins=[item.get("asin", "") for item in import_results["failed"]],
        )

    except Exception as e:
        logger.error(f"CSV import error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process CSV file: {str(e)}"
        )


@router.get("/template")
async def download_csv_template():
    """下载CSV导入模板"""

    csv_template = """asin,title,brand,category,marketplace,tracking_frequency
B07ABC1234,Example Product Title,Example Brand,electronics,AMAZON_US,daily
B08DEF5678,Another Product,Another Brand,home-garden,AMAZON_US,weekly"""

    from fastapi.responses import StreamingResponse

    def generate():
        yield csv_template

    return StreamingResponse(
        io.StringIO(csv_template),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=product_import_template.csv"
        },
    )


@router.post("/demo-products", response_model=BulkImportResult)
async def import_demo_products(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """导入预设的Demo产品（蓝牙耳机）"""

    # 权限检查
    require_permission(current_user, PermissionScope.PRODUCT_CREATE)

    # 预设的蓝牙耳机ASIN
    demo_asins = [
        "B09XS7JWHH",  # Sony WH-1000XM5
        "B0BDHWDR12",  # Apple AirPods Pro 2
        "B098FKXT8L",  # Bose QC45
        "B08WM3LMJF",  # JBL Tune 510BT
        "B07NM3RSRQ",  # Anker Soundcore Life Q20
        "B075G56CDY",  # Beats Studio3
        "B0B8QZ9FYB",  # Sennheiser Momentum 4
        "B07RGZ5NKS",  # TOZO T6
        "B0B2SH4CN6",  # Samsung Galaxy Buds2 Pro
        "B07Q2T2CKG",  # Bose 700
    ]

    # 使用批量导入逻辑
    request = BulkImportRequest(
        asins=demo_asins,
        category="bluetooth-headphones",
        marketplace=MarketplaceType.AMAZON_US,
        tracking_frequency=TrackingFrequency.DAILY,
        auto_crawl=True,
    )

    return await bulk_import_by_asins(request, current_user, db)
