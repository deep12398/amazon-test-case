"""任务队列相关组件"""

from .celery_app import CeleryConfig, celery_app
from .crawler_tasks import (
    crawl_amazon_product,
    crawl_multiple_products,
    schedule_product_tracking,
)

__all__ = [
    "celery_app",
    "CeleryConfig",
    "crawl_amazon_product",
    "crawl_multiple_products",
    "schedule_product_tracking",
]
