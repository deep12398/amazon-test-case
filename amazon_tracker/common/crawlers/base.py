"""爬虫基类和通用结构"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CrawlerResult:
    """爬虫结果数据结构"""

    success: bool
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class CrawlerError(Exception):
    """爬虫异常类"""

    def __init__(
        self, message: str, error_code: str = None, details: dict[str, Any] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}


class BaseCrawler(ABC):
    """爬虫基类"""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def crawl(self, input_data: dict[str, Any]) -> CrawlerResult:
        """执行爬虫任务

        Args:
            input_data: 输入数据，包含要爬取的目标信息

        Returns:
            CrawlerResult: 爬虫结果
        """
        pass

    @abstractmethod
    def validate_input(self, input_data: dict[str, Any]) -> bool:
        """验证输入数据

        Args:
            input_data: 待验证的输入数据

        Returns:
            bool: 验证结果
        """
        pass

    def preprocess_input(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """预处理输入数据

        Args:
            input_data: 原始输入数据

        Returns:
            Dict[str, Any]: 处理后的输入数据
        """
        return input_data

    def postprocess_output(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """后处理输出数据

        Args:
            raw_data: 原始输出数据

        Returns:
            Dict[str, Any]: 处理后的输出数据
        """
        return raw_data

    async def health_check(self) -> bool:
        """健康检查

        Returns:
            bool: 服务是否健康
        """
        try:
            # 子类可以重写此方法进行具体的健康检查
            return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False


class AmazonProductData:
    """Amazon产品数据标准结构"""

    @staticmethod
    def create_product_data(
        asin: str,
        title: str,
        price: Optional[float] = None,
        list_price: Optional[float] = None,
        availability: Optional[str] = None,
        rating: Optional[float] = None,
        review_count: Optional[int] = None,
        rank: Optional[int] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        image_url: Optional[str] = None,
        features: Optional[list[str]] = None,
        description: Optional[str] = None,
        variations: Optional[list[dict[str, Any]]] = None,
        seller_info: Optional[dict[str, Any]] = None,
        shipping_info: Optional[dict[str, Any]] = None,
        additional_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """创建标准化的产品数据结构"""

        return {
            # 基本信息
            "asin": asin,
            "title": title,
            "brand": brand,
            "category": category,
            # 价格信息
            "price": price,
            "list_price": list_price,
            "buy_box_price": list_price,  # Buy Box价格使用建议零售价
            "discount_percent": None
            if not price or not list_price
            else round((list_price - price) / list_price * 100, 2),
            "currency": "USD",  # 默认USD，可从输入参数获取
            # 库存和可用性
            "availability": availability,
            "in_stock": availability and "in stock" in availability.lower()
            if availability
            else None,
            # 评价信息
            "rating": rating,
            "review_count": review_count or 0,
            # 排名信息
            "rank": rank,
            "rank_category": category,
            # 媒体信息
            "image_url": image_url,
            "images": [image_url] if image_url else [],
            # 产品详情
            "features": features or [],
            "description": description,
            # 变体信息
            "variations": variations or [],
            # 卖家信息
            "seller_info": seller_info or {},
            # 物流信息
            "shipping_info": shipping_info or {},
            # 爬取元数据
            "scraped_at": datetime.utcnow().isoformat(),
            "data_version": "1.0",
            # 额外数据
            "additional_data": additional_data or {},
        }

    @staticmethod
    def validate_product_data(data: dict[str, Any]) -> bool:
        """验证产品数据完整性"""
        required_fields = ["asin", "title"]

        for field in required_fields:
            if not data.get(field):
                return False

        # ASIN格式验证
        asin = data.get("asin", "")
        if not (len(asin) == 10 and asin.isalnum()):
            return False

        # 价格验证
        price = data.get("price")
        if price is not None and (not isinstance(price, (int, float)) or price < 0):
            return False

        # 评分验证
        rating = data.get("rating")
        if rating is not None and (
            not isinstance(rating, (int, float)) or rating < 0 or rating > 5
        ):
            return False

        return True
