"""核心服务API数据模型"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, validator

from amazon_tracker.common.database.models.product import (
    MarketplaceType,
    ProductStatus,
    TrackingFrequency,
)


class ProductCreateRequest(BaseModel):
    """创建产品请求"""

    asin: str = Field(..., min_length=10, max_length=10, description="Amazon ASIN")
    title: Optional[str] = Field(None, max_length=500, description="Product title")
    brand: Optional[str] = Field(None, max_length=200, description="Brand name")
    category: Optional[str] = Field(
        None, max_length=200, description="Product category"
    )
    marketplace: MarketplaceType = Field(
        default=MarketplaceType.AMAZON_US, description="Marketplace"
    )
    tracking_frequency: TrackingFrequency = Field(
        default=TrackingFrequency.DAILY, description="Tracking frequency"
    )
    tags: Optional[list[str]] = Field(default_factory=list, description="Product tags")
    notes: Optional[str] = Field(None, max_length=1000, description="User notes")

    @validator("asin")
    def validate_asin(cls, v):
        if not v.isalnum():
            raise ValueError("ASIN must be alphanumeric")
        return v.upper()

    @validator("tags")
    def validate_tags(cls, v):
        if v and len(v) > 20:
            raise ValueError("Cannot have more than 20 tags")
        return [tag.strip() for tag in v if tag.strip()]


class ProductUpdateRequest(BaseModel):
    """更新产品请求"""

    title: Optional[str] = Field(None, max_length=500)
    brand: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = Field(None, max_length=200)
    tracking_frequency: Optional[TrackingFrequency] = None
    is_active: Optional[bool] = None
    tags: Optional[list[str]] = Field(None, description="Product tags")
    notes: Optional[str] = Field(None, max_length=1000)

    @validator("tags")
    def validate_tags(cls, v):
        if v is not None and len(v) > 20:
            raise ValueError("Cannot have more than 20 tags")
        return [tag.strip() for tag in v if tag.strip()] if v else v


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
    status: ProductStatus
    tags: list[str]
    notes: Optional[str]
    last_crawled_at: Optional[datetime]
    next_crawl_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """产品列表响应"""

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
    tracking_frequency: TrackingFrequency
    is_active: bool
    status: ProductStatus
    tags: list[str]
    last_crawled_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ProductSearchRequest(BaseModel):
    """产品搜索请求"""

    query: Optional[str] = Field(None, description="Search query")
    asin: Optional[str] = Field(None, description="Search by ASIN")
    brand: Optional[str] = Field(None, description="Filter by brand")
    category: Optional[str] = Field(None, description="Filter by category")
    marketplace: Optional[MarketplaceType] = Field(
        None, description="Filter by marketplace"
    )
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price")
    min_rating: Optional[float] = Field(None, ge=0, le=5, description="Minimum rating")
    tracking_frequency: Optional[TrackingFrequency] = None
    is_active: Optional[bool] = None
    status: Optional[ProductStatus] = None
    tags: Optional[list[str]] = Field(None, description="Filter by tags")
    sort_by: Optional[str] = Field("created_at", description="Sort field")
    sort_order: Optional[str] = Field("desc", description="Sort order")

    @validator("sort_by")
    def validate_sort_by(cls, v):
        allowed_fields = [
            "created_at",
            "updated_at",
            "title",
            "brand",
            "category",
            "current_price",
            "current_rank",
            "rating",
            "review_count",
        ]
        if v not in allowed_fields:
            raise ValueError(f"sort_by must be one of: {allowed_fields}")
        return v

    @validator("sort_order")
    def validate_sort_order(cls, v):
        if v not in ["asc", "desc"]:
            raise ValueError("sort_order must be asc or desc")
        return v


class AlertCreateRequest(BaseModel):
    """创建价格提醒请求"""

    product_id: int
    alert_type: str = Field(
        ...,
        description="Alert type: price_drop, price_target, rank_change, stock_alert",
    )
    target_value: Optional[float] = Field(None, description="Target price or rank")
    threshold_percentage: Optional[float] = Field(
        None, description="Percentage change threshold"
    )
    is_active: bool = Field(default=True)
    notification_methods: list[str] = Field(
        default=["email"], description="Notification methods"
    )

    @validator("alert_type")
    def validate_alert_type(cls, v):
        allowed_types = ["price_drop", "price_target", "rank_change", "stock_alert"]
        if v not in allowed_types:
            raise ValueError(f"alert_type must be one of: {allowed_types}")
        return v

    @validator("notification_methods")
    def validate_notification_methods(cls, v):
        allowed_methods = ["email", "webhook", "in_app"]
        for method in v:
            if method not in allowed_methods:
                raise ValueError(
                    f"notification method must be one of: {allowed_methods}"
                )
        return v


class AlertResponse(BaseModel):
    """价格提醒响应"""

    id: int
    product_id: int
    alert_type: str
    target_value: Optional[float]
    threshold_percentage: Optional[float]
    current_value: Optional[float]
    is_active: bool
    notification_methods: list[str]
    last_triggered_at: Optional[datetime]
    trigger_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class CompetitorAnalysisRequest(BaseModel):
    """竞品分析请求"""

    product_id: int
    analysis_type: str = Field(
        ..., description="Analysis type: pricing, ranking, features, reviews"
    )
    competitor_asins: Optional[list[str]] = Field(
        None, description="Specific competitor ASINs"
    )
    auto_discover: bool = Field(default=True, description="Auto-discover competitors")
    max_competitors: int = Field(
        default=10, ge=1, le=50, description="Maximum competitors to analyze"
    )

    @validator("analysis_type")
    def validate_analysis_type(cls, v):
        allowed_types = ["pricing", "ranking", "features", "reviews", "comprehensive"]
        if v not in allowed_types:
            raise ValueError(f"analysis_type must be one of: {allowed_types}")
        return v


class CompetitorProductInfo(BaseModel):
    """竞品产品信息"""

    asin: str
    title: str
    brand: Optional[str]
    price: Optional[float]
    rating: Optional[float]
    review_count: int
    rank: Optional[int]
    image_url: Optional[str]
    features: list[str]
    competitive_score: float


class CompetitorAnalysisResponse(BaseModel):
    """竞品分析响应"""

    analysis_id: str
    product_id: int
    analysis_type: str
    main_product: CompetitorProductInfo
    competitors: list[CompetitorProductInfo]
    insights: dict[str, Any]
    recommendations: list[str]
    market_position: str
    created_at: datetime

    class Config:
        from_attributes = True


class MarketTrendRequest(BaseModel):
    """市场趋势分析请求"""

    category: Optional[str] = None
    brand: Optional[str] = None
    marketplace: MarketplaceType = Field(default=MarketplaceType.AMAZON_US)
    time_period: str = Field(default="30d", description="Time period: 7d, 30d, 90d, 1y")
    metrics: list[str] = Field(
        default=["price", "rank", "rating"], description="Metrics to analyze"
    )

    @validator("time_period")
    def validate_time_period(cls, v):
        allowed_periods = ["7d", "30d", "90d", "1y"]
        if v not in allowed_periods:
            raise ValueError(f"time_period must be one of: {allowed_periods}")
        return v

    @validator("metrics")
    def validate_metrics(cls, v):
        allowed_metrics = ["price", "rank", "rating", "review_count", "availability"]
        for metric in v:
            if metric not in allowed_metrics:
                raise ValueError(f"metric must be one of: {allowed_metrics}")
        return v


class TrendDataPoint(BaseModel):
    """趋势数据点"""

    date: datetime
    value: float
    change_percent: Optional[float]


class MarketTrendResponse(BaseModel):
    """市场趋势响应"""

    category: Optional[str]
    brand: Optional[str]
    marketplace: MarketplaceType
    time_period: str
    trend_data: dict[str, list[TrendDataPoint]]
    insights: dict[str, Any]
    forecast: Optional[dict[str, Any]]
    generated_at: datetime


class ReportGenerateRequest(BaseModel):
    """报告生成请求"""

    report_type: str = Field(
        default="competitor_analysis", description="Report type: competitor_analysis"
    )
    main_product_id: int = Field(..., description="Main product ID for comparison")
    competitor_product_ids: Optional[list[int]] = Field(None, description="Competitor product IDs (if not provided, will select automatically)")
    time_period: str = Field(default="30d", description="Time period")
    include_charts: bool = Field(default=True, description="Include charts in report")
    format: str = Field(default="markdown", description="Report format: markdown")

    @validator("report_type")
    def validate_report_type(cls, v):
        allowed_types = ["competitor_analysis"]
        if v not in allowed_types:
            raise ValueError(f"report_type must be one of: {allowed_types}")
        return v

    @validator("format")
    def validate_format(cls, v):
        allowed_formats = ["markdown"]
        if v not in allowed_formats:
            raise ValueError(f"format must be one of: {allowed_formats}")
        return v

    @validator("competitor_product_ids")
    def validate_competitor_product_ids(cls, v):
        if v and len(v) > 10:
            raise ValueError("Cannot compare with more than 10 competitors at once")
        return v


class ReportResponse(BaseModel):
    """报告响应"""

    report_id: str
    report_type: str
    status: str
    file_url: Optional[str]
    file_size: Optional[int]
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class BatchOperationRequest(BaseModel):
    """批量操作请求"""

    product_ids: list[int] = Field(..., min_items=1, max_items=100)
    operation: str = Field(
        ..., description="Operation: activate, deactivate, delete, update_frequency"
    )
    parameters: Optional[dict[str, Any]] = Field(default_factory=dict)

    @validator("operation")
    def validate_operation(cls, v):
        allowed_operations = [
            "activate",
            "deactivate",
            "delete",
            "update_frequency",
            "add_tags",
            "remove_tags",
        ]
        if v not in allowed_operations:
            raise ValueError(f"operation must be one of: {allowed_operations}")
        return v


class BatchOperationResponse(BaseModel):
    """批量操作响应"""

    operation_id: str
    operation: str
    total_items: int
    successful_items: int
    failed_items: int
    errors: list[dict[str, str]]
    completed_at: datetime


class ProductStatsResponse(BaseModel):
    """产品统计响应"""

    total_products: int
    active_products: int
    inactive_products: int
    by_marketplace: dict[str, int]
    by_category: dict[str, int]
    by_tracking_frequency: dict[str, int]
    avg_price: Optional[float]
    avg_rating: Optional[float]
    price_range: dict[str, float]
    last_updated: datetime


# 提醒管理相关模型
class AlertCreateRequest(BaseModel):
    """创建价格提醒请求"""

    product_id: int
    alert_type: str = Field(
        ...,
        description="Alert type: price_drop, price_target, rank_change, stock_alert",
    )
    target_value: Optional[float] = Field(None, description="Target price or rank")
    threshold_percentage: Optional[float] = Field(
        None, description="Percentage change threshold"
    )
    is_active: bool = Field(default=True)
    notification_methods: list[str] = Field(
        default=["email"], description="Notification methods"
    )

    @validator("alert_type")
    def validate_alert_type(cls, v):
        allowed_types = ["price_drop", "price_target", "rank_change", "stock_alert"]
        if v not in allowed_types:
            raise ValueError(f"alert_type must be one of: {allowed_types}")
        return v

    @validator("notification_methods")
    def validate_notification_methods(cls, v):
        allowed_methods = ["email", "webhook", "in_app"]
        for method in v:
            if method not in allowed_methods:
                raise ValueError(
                    f"notification method must be one of: {allowed_methods}"
                )
        return v


class AlertResponse(BaseModel):
    """价格提醒响应"""

    id: int
    product_id: int
    alert_type: str
    target_value: Optional[float]
    threshold_percentage: Optional[float]
    current_value: Optional[float]
    is_active: bool
    notification_methods: list[str]
    last_triggered_at: Optional[datetime]
    trigger_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# 市场趋势分析相关模型
class MarketTrendRequest(BaseModel):
    """市场趋势分析请求"""

    category: Optional[str] = None
    brand: Optional[str] = None
    marketplace: MarketplaceType = Field(default=MarketplaceType.AMAZON_US)
    time_period: str = Field(default="30d", description="Time period: 7d, 30d, 90d, 1y")
    metrics: list[str] = Field(
        default=["price", "rank", "rating"], description="Metrics to analyze"
    )

    @validator("time_period")
    def validate_time_period(cls, v):
        allowed_periods = ["7d", "30d", "90d", "1y"]
        if v not in allowed_periods:
            raise ValueError(f"time_period must be one of: {allowed_periods}")
        return v

    @validator("metrics")
    def validate_metrics(cls, v):
        allowed_metrics = ["price", "rank", "rating", "review_count", "availability"]
        for metric in v:
            if metric not in allowed_metrics:
                raise ValueError(f"metric must be one of: {allowed_metrics}")
        return v


class TrendDataPoint(BaseModel):
    """趋势数据点"""

    date: datetime
    value: float
    change_percent: Optional[float]


class MarketTrendResponse(BaseModel):
    """市场趋势响应"""

    category: Optional[str]
    brand: Optional[str]
    marketplace: MarketplaceType
    time_period: str
    trend_data: dict[str, list[TrendDataPoint]]
    insights: dict[str, Any]
    forecast: Optional[dict[str, Any]]
    generated_at: datetime


