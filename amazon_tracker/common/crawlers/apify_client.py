"""Apify客户端和Amazon爬虫实现"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

# 加载环境变量
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(project_root / ".env.local")
load_dotenv(project_root / ".env")

from apify_client import ApifyClient as ApifySDK

from .base import AmazonProductData, BaseCrawler, CrawlerError, CrawlerResult

logger = logging.getLogger(__name__)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class ApifyClient:
    """Apify API客户端 - 使用官方SDK"""

    def __init__(self, api_token: str = None):
        self.api_token = api_token or os.getenv("APIFY_API_TOKEN")
        if not self.api_token:
            raise ValueError("Apify API token is required")

        # 初始化官方SDK客户端
        self.client = ApifySDK(self.api_token)

    async def run_actor(
        self,
        actor_id: str,
        input_data: dict[str, Any],
        timeout: int = 300,
        memory_mb: int = 1024,
        build: str = "latest",
    ) -> dict[str, Any]:
        """运行Apify Actor - 使用官方SDK"""

        try:
            # 使用官方SDK运行Actor
            run = await asyncio.to_thread(
                self.client.actor(actor_id).call,
                run_input=input_data,
                memory_mbytes=memory_mb,
                build=build,
            )

            logger.info(f"Started Apify actor run: {run['id']}")

            # 获取数据集数据
            items = []
            if run.get("defaultDatasetId"):
                dataset_items = await asyncio.to_thread(
                    self.client.dataset(run["defaultDatasetId"]).list_items
                )
                # ListPage对象转换为列表
                items = (
                    list(dataset_items.items) if hasattr(dataset_items, "items") else []
                )

            # 返回结果
            result = {
                "id": run["id"],
                "status": run["status"],
                "startedAt": run["startedAt"],
                "finishedAt": run["finishedAt"],
                "stats": run.get("stats", {}),
                "defaultDatasetId": run.get("defaultDatasetId"),
                "items": items,
            }

            return result

        except Exception as e:
            logger.error(f"Apify actor run failed: {e}")
            raise CrawlerError(
                f"Apify actor run failed: {str(e)}", error_code="APIFY_RUN_ERROR"
            )

    async def get_actor_info(self, actor_id: str) -> dict[str, Any]:
        """获取Actor信息 - 使用官方SDK"""

        try:
            actor_info = await asyncio.to_thread(self.client.actor(actor_id).get)
            return actor_info
        except Exception as e:
            logger.error(f"Failed to get actor info: {e}")
            raise CrawlerError(f"Failed to get actor info: {str(e)}")


class ApifyAmazonScraper(BaseCrawler):
    """Apify Amazon产品爬虫"""

    # Apify Store中的Amazon爬虫Actor ID
    AMAZON_ASIN_SCRAPER = "ZhSGsaq9MHRnWtStl"  # junglee/amazon-asins-scraper
    AMAZON_ASIN_SCRAPER = "ZhSGsaq9MHRnWtStl"  # axesso_data/amazon-product-details-scraper
    AMAZON_PRODUCT_SCRAPER = "junglee~free-amazon-product-scraper"  # 备用产品爬虫

    def __init__(self, config: dict[str, Any] = None):
        super().__init__(config)
        self.apify_client = ApifyClient(config.get("apify_token") if config else None)
        self.default_config = {
            "timeout": 300,
            "memory_mb": 4096,
            "max_retries": 3,
            "actor_id": self.AMAZON_ASIN_SCRAPER,  # 默认使用ASIN爬虫
        }
        self.default_config.update(config or {})

    def validate_input(self, input_data: dict[str, Any]) -> bool:
        """验证输入数据"""

        # 检查必需字段 - ASIN爬虫主要需要asins
        if not input_data.get("asins") and not input_data.get("productUrls"):
            return False

        # 验证ASIN格式
        asins = input_data.get("asins", [])
        if asins:
            for asin in asins:
                if not isinstance(asin, str) or len(asin) != 10:
                    return False

        # 验证URL格式
        urls = input_data.get("productUrls", [])
        if urls:
            for url in urls:
                if not isinstance(url, str) or "amazon." not in url:
                    return False

        return True

    def preprocess_input(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """预处理输入数据为Apify ASIN爬虫格式"""

        processed = {
            "asins": input_data.get("asins", []),
            "amazonDomain": "amazon.com",  # 固定使用amazon.com
            "proxyCountry": "AUTO_SELECT_PROXY_COUNTRY",
            "useCaptchaSolver": False,
        }

        # 如果有productUrls，提取ASIN
        if input_data.get("productUrls"):
            for url in input_data["productUrls"]:
                # 简单的ASIN提取逻辑
                parts = url.split("/")
                for i, part in enumerate(parts):
                    if part == "dp" and i + 1 < len(parts):
                        asin = parts[i + 1]
                        if len(asin) == 10:
                            processed["asins"].append(asin)

        # 移除重复的ASIN
        processed["asins"] = list(set(processed["asins"]))

        return processed

    async def crawl_test(self, input_data: dict[str, Any]) -> CrawlerResult:
        """执行Amazon产品爬取"""

        try:
            # 保存结果到JSON文件
            filename = f"apify_result_20250914_151452.json"
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)

            result_file_path = logs_dir / filename
            with open(result_file_path, 'r', encoding='utf-8') as f:
                result = json.load(f)  # 直接把 JSON 内容解析成 dict

            # 处理结果
            items = result.get("items", [])
            processed_items = []

            for item in items:
                try:
                    processed_item = self._process_amazon_item(item)
                    if AmazonProductData.validate_product_data(processed_item):
                        processed_items.append(processed_item)
                    else:
                        self.logger.warning(
                            f"Invalid product data for ASIN: {item.get('asin')}"
                        )
                except Exception as e:
                    self.logger.error(f"Error processing item: {e}")
                    continue

            return CrawlerResult(
                success=True,
                data={
                    "products": processed_items,
                    "total_items": len(processed_items),
                    "raw_items": len(items),
                },
                metadata={
                    "run_id": result.get("id"),
                    "status": result.get("status"),
                    "started_at": result.get("startedAt"),
                    "finished_at": result.get("finishedAt"),
                    "stats": result.get("stats", {}),
                },
            )

        except CrawlerError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in Amazon scraper: {e}")
            return CrawlerResult(success=False, error=f"Unexpected error: {str(e)}")

    async def crawl(self, input_data: dict[str, Any]) -> CrawlerResult:
        """执行Amazon产品爬取"""

        try:
            # 验证输入
            if not self.validate_input(input_data):
                return CrawlerResult(success=False, error="Invalid input data")

            # 预处理输入
            processed_input = self.preprocess_input(input_data)

            # 运行爬虫
            self.logger.info(
                f"Starting Apify Amazon scraper with input: {processed_input}"
            )

            result = await self.apify_client.run_actor(
                actor_id=self.default_config["actor_id"],
                input_data=processed_input,
                timeout=self.default_config["timeout"],
                memory_mb=self.default_config["memory_mb"],
            )

            # 保存结果到JSON文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"apify_result_{timestamp}.json"
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)

            result_file_path = logs_dir / filename
            with open(result_file_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, cls=DateTimeEncoder, indent=4, ensure_ascii=False)

            self.logger.info(f"Apify result saved to: {result_file_path}")

            # 处理结果
            items = result.get("items", [])
            processed_items = []

            for item in items:
                try:
                    processed_item = self._process_amazon_item(item)
                    if AmazonProductData.validate_product_data(processed_item):
                        processed_items.append(processed_item)
                    else:
                        self.logger.warning(
                            f"Invalid product data for ASIN: {item.get('asin')}"
                        )
                except Exception as e:
                    self.logger.error(f"Error processing item: {e}")
                    continue

            return CrawlerResult(
                success=True,
                data={
                    "products": processed_items,
                    "total_items": len(processed_items),
                    "raw_items": len(items),
                },
                metadata={
                    "run_id": result.get("id"),
                    "status": result.get("status"),
                    "started_at": result.get("startedAt"),
                    "finished_at": result.get("finishedAt"),
                    "stats": result.get("stats", {}),
                },
            )

        except CrawlerError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in Amazon scraper: {e}")
            return CrawlerResult(success=False, error=f"Unexpected error: {str(e)}")

    def _process_amazon_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """处理单个Amazon商品数据"""

        # 价格处理
        price = None
        list_price = None

        # 现价
        if item.get("price") and isinstance(item["price"], dict):
            try:
                price = float(item["price"]["value"])
            except (ValueError, TypeError):
                pass
        elif item.get("price"):
            price_str = str(item["price"]).replace("$", "").replace(",", "")
            try:
                price = float(price_str)
            except ValueError:
                pass

        # 原价，建议零售价
        if item.get("listPrice") and isinstance(item["listPrice"], dict):
            try:
                list_price = float(item["listPrice"]["value"])
            except (ValueError, TypeError):
                pass
        elif item.get("listPrice"):
            list_price_str = str(item["listPrice"]).replace("$", "").replace(",", "")
            try:
                list_price = float(list_price_str)
            except ValueError:
                pass

        # 评分处理
        rating = None
        if item.get("stars"):
            try:
                rating = float(item["stars"])
            except (ValueError, TypeError):
                pass

        # 评价数量处理
        review_count = 0
        if item.get("reviewsCount"):
            try:
                review_count_str = str(item["reviewsCount"]).replace(",", "")
                review_count = int(review_count_str)
            except (ValueError, TypeError):
                pass

        # 排名处理（支持数组）
        rank = None
        category = None
        if item.get("bestsellerRanks") and isinstance(item["bestsellerRanks"], list):
            try:
                rank = int(item["bestsellerRanks"][0]["rank"])
                category = item["bestsellerRanks"][0]["category"]
            except (ValueError, TypeError, KeyError, IndexError):
                pass

        # 卖家信息
        seller_info = {}
        if item.get("seller") and isinstance(item["seller"], dict):
            seller = item["seller"]
            seller_info = {
                "name": seller.get("name"),
                "url": seller.get("url"),
                "rating": seller.get("averageRating"),
                "reviews_count": seller.get("reviewsCount"),
            }

        # 变体信息（支持 variantDetails）
        variations = []
        if item.get("variantDetails") and isinstance(item["variantDetails"], list):
            for variant in item["variantDetails"]:
                variations.append({
                    "asin": variant.get("asin"),
                    "title": variant.get("name"),
                    "price": variant.get("price"),
                    "image": variant.get("thumbnail"),
                    "url": None,  # 可选：如果你有 variant URL
                })

        return AmazonProductData.create_product_data(
            asin=item.get("asin", ""),
            title=item.get("title", ""),
            price=price,
            list_price=list_price,
            availability=item.get("availability"),
            rating=rating,
            review_count=review_count,
            rank=rank,
            category=category,
            brand=item.get("brand"),
            image_url=item.get("image"),
            features=item.get("features", []),
            description=item.get("description"),
            variations=variations,
            seller_info=seller_info,
            shipping_info={
                "free_shipping": item.get("freeShipping", False),
                "prime": item.get("isPrime", False),
            },
            additional_data={
                "url": item.get("url"),
                "breadcrumbs": item.get("breadcrumbs", []),
                "coupon": item.get("coupon"),
                "deal": item.get("deal"),
                "sponsored": item.get("sponsored", False),
            },
        )

    async def health_check(self) -> bool:
        """检查Apify服务健康状态"""
        try:
            actor_info = await self.apify_client.get_actor_info(
                self.default_config["actor_id"]
            )
            return actor_info is not None
        except Exception as e:
            self.logger.error(f"Apify health check failed: {e}")
            return False

    async def scrape_single_product(
        self, asin: str, country: str = "US"
    ) -> CrawlerResult:
        """爬取单个产品"""
        return await self.crawl({"asins": [asin], "country": country})

    async def scrape_multiple_products(
        self, asins: list[str], country: str = "US"
    ) -> CrawlerResult:
        """爬取多个产品"""
        return await self.crawl({"asins": asins, "country": country})

    async def scrape_from_urls(self, urls: list[str]) -> CrawlerResult:
        """从URL列表爬取产品"""
        return await self.crawl({"productUrls": urls})

    async def scrape_category_products(
        self,
        category_url: str,
        product_limit: int = 10,
        sort_by: str = "best_seller",
        filters: dict = None,
    ) -> CrawlerResult:
        """从品类页面爬取产品列表"""

        input_data = {
            "categoryOrProductUrls": [category_url],
            "country": "US",
            "maxProducts": product_limit,
            "scrapeDescription": True,
            "scrapeFeatures": True,
            "scrapeQuestions": False,
            "scrapeReviews": False,
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
            },
        }

        # 添加排序参数
        sort_mapping = {
            "best_seller": "popularity-rank",
            "price_low_high": "price-asc-rank",
            "price_high_low": "price-desc-rank",
            "newest": "date-desc-rank",
            "rating": "review-rank",
            "relevance": "relevance",
        }

        if sort_by in sort_mapping:
            input_data["sortBy"] = sort_mapping[sort_by]

        # 添加筛选条件
        if filters:
            if "price_min" in filters:
                input_data["minPrice"] = filters["price_min"]
            if "price_max" in filters:
                input_data["maxPrice"] = filters["price_max"]
            if "rating_min" in filters:
                input_data["minReviewScore"] = filters["rating_min"]
            if "prime_only" in filters and filters["prime_only"]:
                input_data["isPrime"] = True

        return await self.crawl(input_data)

    def _extract_category_asins(self, crawl_result: CrawlerResult) -> list[str]:
        """从品类爬取结果中提取ASIN列表"""
        if not crawl_result.success:
            return []

        products = crawl_result.data.get("products", [])
        asins = []

        for product in products:
            asin = product.get("asin")
            if asin and len(asin) == 10:
                asins.append(asin)

        return asins[:50]  # 限制最大50个产品
