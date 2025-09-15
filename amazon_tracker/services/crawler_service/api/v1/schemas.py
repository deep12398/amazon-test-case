"""爬虫服务API数据模型"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, validator

from amazon_tracker.common.database.models.crawl import (
    CrawlerType,
    TaskPriority,
    TaskStatus,
)
from amazon_tracker.common.database.models.product import (
    MarketplaceType,
    TrackingFrequency,
)


class ProductCrawlRequest(BaseModel):
    """单个产品爬取请求"""

    asin: str = Field(..., min_length=10, max_length=10, description="Amazon ASIN")
    marketplace: Optional[MarketplaceType] = Field(
        default=MarketplaceType.AMAZON_US, description="Amazon marketplace"
    )
    tracking_frequency: Optional[TrackingFrequency] = Field(
        default=TrackingFrequency.DAILY, description="Tracking frequency"
    )
    priority: Optional[TaskPriority] = Field(
        default=TaskPriority.NORMAL, description="Task priority"
    )
    config: Optional[dict[str, Any]] = Field(
        default_factory=dict, description="Crawler configuration"
    )

    @validator("asin")
    def validate_asin(cls, v):
        if not v.isalnum():
            raise ValueError("ASIN must be alphanumeric")
        return v.upper()


class BatchCrawlRequest(BaseModel):
    """批量产品爬取请求"""

    asins: list[str] = Field(
        ..., min_items=1, max_items=50, description="List of ASINs"
    )
    marketplace: Optional[MarketplaceType] = Field(
        default=MarketplaceType.AMAZON_US, description="Amazon marketplace"
    )
    tracking_frequency: Optional[TrackingFrequency] = Field(
        default=TrackingFrequency.DAILY, description="Tracking frequency"
    )
    priority: Optional[TaskPriority] = Field(
        default=TaskPriority.NORMAL, description="Task priority"
    )
    config: Optional[dict[str, Any]] = Field(
        default_factory=dict, description="Crawler configuration"
    )

    @validator("asins")
    def validate_asins(cls, v):
        validated = []
        for asin in v:
            if len(asin) != 10 or not asin.isalnum():
                raise ValueError(f"Invalid ASIN: {asin}")
            validated.append(asin.upper())
        return validated


class CategoryCrawlRequest(BaseModel):
    """品类产品爬取请求"""

    category_url: str = Field(..., description="Amazon category or search URL")
    category_name: str = Field(
        ..., min_length=1, max_length=200, description="Category name for tracking"
    )
    product_limit: int = Field(
        default=10, ge=1, le=50, description="Number of products to crawl"
    )
    marketplace: Optional[MarketplaceType] = Field(
        default=MarketplaceType.AMAZON_US, description="Amazon marketplace"
    )
    tracking_frequency: Optional[TrackingFrequency] = Field(
        default=TrackingFrequency.DAILY, description="Tracking frequency"
    )
    priority: Optional[TaskPriority] = Field(
        default=TaskPriority.NORMAL, description="Task priority"
    )
    sort_by: Optional[str] = Field(
        default="best_seller",
        description="Sort products by: best_seller, price_low_high, price_high_low, newest, rating",
    )
    filters: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional filters (price range, brand, etc.)",
    )
    config: Optional[dict[str, Any]] = Field(
        default_factory=dict, description="Crawler configuration"
    )

    @validator("category_url")
    def validate_category_url(cls, v):
        if not v.startswith(("https://www.amazon.", "https://amazon.")):
            raise ValueError("Category URL must be a valid Amazon URL")
        if not any(param in v for param in ["s?k=", "/b/", "/gp/bestsellers/"]):
            raise ValueError("URL must be a category, search, or bestseller page")
        return v

    @validator("sort_by")
    def validate_sort_by(cls, v):
        valid_sorts = [
            "best_seller",
            "price_low_high",
            "price_high_low",
            "newest",
            "rating",
            "relevance",
        ]
        if v not in valid_sorts:
            raise ValueError(f"sort_by must be one of: {', '.join(valid_sorts)}")
        return v


class CrawlTaskResponse(BaseModel):
    """爬虫任务响应"""

    task_id: str
    product_id: int
    asin: str
    status: TaskStatus
    created_at: datetime

    class Config:
        from_attributes = True


class CategoryCrawlResponse(BaseModel):
    """品类爬取任务响应"""

    task_id: str
    category_name: str
    category_url: str
    product_count: int
    product_ids: list[int]
    asins_found: list[str]
    status: TaskStatus
    created_at: datetime

    class Config:
        from_attributes = True


class CrawlTaskListResponse(BaseModel):
    """爬虫任务列表响应"""

    task_id: str
    product_id: int
    task_name: str
    crawler_type: CrawlerType
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    execution_time: Optional[int]
    items_processed: int
    items_failed: int

    class Config:
        from_attributes = True


class CrawlTaskDetailResponse(CrawlTaskListResponse):
    """爬虫任务详情响应"""

    crawler_config: dict[str, Any]
    input_data: dict[str, Any]
    result_data: dict[str, Any]
    error_message: Optional[str]
    error_traceback: Optional[str]
    external_task_id: Optional[str]
    external_status: Optional[str]
    external_url: Optional[str]
    retry_count: int
    max_retries: int
    worker_name: Optional[str]

    class Config:
        from_attributes = True


class CrawlLogResponse(BaseModel):
    """爬虫日志响应"""

    id: int
    task_id: str
    level: str
    message: str
    details: dict[str, Any]
    logged_at: datetime

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    """产品响应"""

    id: int
    asin: str
    title: str
    brand: Optional[str]
    category: Optional[str]
    marketplace: MarketplaceType
    current_price: Optional[float]
    current_rank: Optional[int]
    rating: Optional[float]
    review_count: int
    image_url: Optional[str]
    availability: Optional[str]
    tracking_frequency: TrackingFrequency
    is_active: bool
    last_crawled_at: Optional[datetime]
    next_crawl_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class PriceHistoryResponse(BaseModel):
    """价格历史响应"""

    id: int
    product_id: int
    price: float
    list_price: Optional[float]
    currency: str
    recorded_at: datetime

    class Config:
        from_attributes = True


class RankHistoryResponse(BaseModel):
    """排名历史响应"""

    id: int
    product_id: int
    rank: int
    category: Optional[str]
    recorded_at: datetime

    class Config:
        from_attributes = True


class TaskStatsResponse(BaseModel):
    """任务统计响应"""

    total_tasks: int
    pending_tasks: int
    running_tasks: int
    success_tasks: int
    failed_tasks: int
    cancelled_tasks: int
    success_rate: float
    avg_execution_time: Optional[float]
    total_items_processed: int
    date_range_days: int


class ScheduleResponse(BaseModel):
    """调度响应"""

    schedule_id: str
    name: str
    description: Optional[str]
    cron_expression: str
    timezone: str
    crawler_type: CrawlerType
    is_active: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    created_at: datetime

    class Config:
        from_attributes = True


class CreateScheduleRequest(BaseModel):
    """创建调度请求"""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    cron_expression: str = Field(..., description="Cron expression for scheduling")
    timezone: str = Field(default="UTC", description="Timezone")
    crawler_type: CrawlerType
    task_template: dict[str, Any] = Field(default_factory=dict)
    product_filters: dict[str, Any] = Field(default_factory=dict)

    @validator("cron_expression")
    def validate_cron(cls, v):
        # 简单的cron表达式验证
        parts = v.split()
        if len(parts) != 5:
            raise ValueError("Cron expression must have 5 fields")
        return v


class UpdateScheduleRequest(BaseModel):
    """更新调度请求"""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    task_template: Optional[dict[str, Any]] = None
    product_filters: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None

    @validator("cron_expression")
    def validate_cron(cls, v):
        if v is not None:
            parts = v.split()
            if len(parts) != 5:
                raise ValueError("Cron expression must have 5 fields")
        return v
