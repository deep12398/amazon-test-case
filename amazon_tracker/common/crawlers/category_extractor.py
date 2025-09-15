"""Amazon品类产品提取工具"""

import logging
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from .apify_client import ApifyAmazonScraper

logger = logging.getLogger(__name__)


class CategoryProductExtractor:
    """Amazon品类产品提取器"""

    def __init__(self, scraper_config: dict = None):
        self.scraper = ApifyAmazonScraper(scraper_config)

    async def extract_category_asins(
        self,
        category_url: str,
        product_limit: int = 10,
        sort_by: str = "best_seller",
        filters: dict = None,
    ) -> dict[str, Any]:
        """
        从品类页面提取产品ASIN列表

        Args:
            category_url: 品类或搜索页面URL
            product_limit: 需要提取的产品数量
            sort_by: 排序方式
            filters: 过滤条件

        Returns:
            包含ASIN列表和产品信息的字典
        """
        try:
            # 验证URL格式
            if not self._validate_category_url(category_url):
                return {
                    "success": False,
                    "error": "Invalid category URL format",
                    "asins": [],
                    "products": [],
                }

            # 执行品类爬取
            logger.info(f"Extracting products from category: {category_url}")
            crawl_result = await self.scraper.scrape_category_products(
                category_url=category_url,
                product_limit=product_limit,
                sort_by=sort_by,
                filters=filters or {},
            )

            if not crawl_result.success:
                return {
                    "success": False,
                    "error": crawl_result.error,
                    "asins": [],
                    "products": [],
                }

            # 提取产品信息
            products = crawl_result.data.get("products", [])
            extracted_products = []
            asins = []

            for product in products[:product_limit]:
                asin = product.get("asin")
                if asin and len(asin) == 10:
                    asins.append(asin)

                    # 提取关键产品信息
                    extracted_product = {
                        "asin": asin,
                        "title": product.get("title", ""),
                        "brand": product.get("brand", ""),
                        "price": self._parse_price(product.get("price")),
                        "list_price": self._parse_price(product.get("listPrice")),
                        "rating": self._parse_rating(product.get("stars")),
                        "review_count": self._parse_review_count(
                            product.get("reviewsCount")
                        ),
                        "rank": self._parse_rank(product.get("bestSellersRank")),
                        "image_url": product.get("image"),
                        "product_url": product.get("url"),
                        "availability": product.get("availability"),
                        "is_prime": product.get("isPrime", False),
                        "buy_box_price": self._parse_price(product.get("buyBoxPrice")),
                        "category_info": product.get("breadcrumbs", []),
                    }
                    extracted_products.append(extracted_product)

            logger.info(f"Successfully extracted {len(asins)} products from category")

            return {
                "success": True,
                "asins": asins,
                "products": extracted_products,
                "total_found": len(products),
                "category_url": category_url,
                "category_name": self._extract_category_name(category_url, products),
                "crawl_metadata": crawl_result.metadata,
            }

        except Exception as e:
            logger.error(f"Error extracting category products: {e}")
            return {"success": False, "error": str(e), "asins": [], "products": []}

    def _validate_category_url(self, url: str) -> bool:
        """验证品类URL格式"""
        try:
            parsed = urlparse(url)
            if not parsed.netloc.endswith(
                ("amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr", "amazon.co.jp")
            ):
                return False

            # 检查是否为有效的品类、搜索或畅销榜页面
            valid_paths = [
                "/s?",  # 搜索页面
                "/b/",  # 品类页面
                "/gp/bestsellers/",  # 畅销榜
                "/dp/",  # 单个产品（也支持）
            ]

            return any(path in url for path in valid_paths)

        except Exception:
            return False

    def _extract_category_name(self, url: str, products: list) -> str:
        """从URL或产品信息中提取品类名称"""
        try:
            # 从URL参数中提取
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)

            if "k" in query_params:  # 搜索关键词
                return query_params["k"][0]

            # 从产品面包屑中提取
            if products:
                for product in products[:3]:  # 检查前3个产品
                    breadcrumbs = product.get("breadcrumbs", [])
                    if breadcrumbs and len(breadcrumbs) > 1:
                        return breadcrumbs[-1]  # 返回最后一级分类

            # 从URL路径中提取
            if "/gp/bestsellers/" in url:
                return "Best Sellers"
            elif "/b/" in url:
                return "Category Products"
            else:
                return "Search Results"

        except Exception:
            return "Unknown Category"

    def _parse_price(self, price_str: Any) -> Optional[float]:
        """解析价格字符串"""
        if not price_str:
            return None
        try:
            # 移除货币符号和逗号
            price_clean = str(price_str).replace("$", "").replace(",", "").strip()
            return float(price_clean)
        except (ValueError, TypeError):
            return None

    def _parse_rating(self, rating_str: Any) -> Optional[float]:
        """解析评分"""
        if not rating_str:
            return None
        try:
            return float(rating_str)
        except (ValueError, TypeError):
            return None

    def _parse_review_count(self, review_str: Any) -> int:
        """解析评论数量"""
        if not review_str:
            return 0
        try:
            # 移除逗号和其他格式字符
            review_clean = str(review_str).replace(",", "").strip()
            return int(review_clean)
        except (ValueError, TypeError):
            return 0

    def _parse_rank(self, rank_str: Any) -> Optional[int]:
        """解析排名"""
        if not rank_str:
            return None
        try:
            # 提取数字部分
            rank_clean = str(rank_str).replace("#", "").replace(",", "").split()[0]
            return int(rank_clean)
        except (ValueError, TypeError, IndexError):
            return None


# 便捷函数
async def category_to_asins(
    category_url: str,
    product_limit: int = 10,
    sort_by: str = "best_seller",
    filters: dict = None,
    scraper_config: dict = None,
) -> dict[str, Any]:
    """
    便捷函数：从品类URL提取ASIN列表

    Args:
        category_url: Amazon品类URL
        product_limit: 产品数量限制
        sort_by: 排序方式
        filters: 筛选条件
        scraper_config: 爬虫配置

    Returns:
        包含ASIN列表的字典
    """
    extractor = CategoryProductExtractor(scraper_config)
    return await extractor.extract_category_asins(
        category_url=category_url,
        product_limit=product_limit,
        sort_by=sort_by,
        filters=filters,
    )
