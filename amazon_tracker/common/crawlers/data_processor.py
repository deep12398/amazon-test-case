"""Amazon数据处理器"""

import logging
import re
from typing import Any, Optional

from .base import AmazonProductData

logger = logging.getLogger(__name__)


class AmazonDataProcessor:
    """Amazon产品数据处理器"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def clean_product_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """清洗单个产品数据"""
        try:
            cleaned_data = {}

            # 基本信息清洗
            cleaned_data["asin"] = self._clean_asin(raw_data.get("asin"))
            cleaned_data["title"] = self._clean_title(raw_data.get("title"))
            cleaned_data["brand"] = self._clean_brand(raw_data.get("brand"))
            cleaned_data["category"] = self._clean_category(raw_data.get("category"))

            # 价格信息清洗
            cleaned_data["price"] = self._clean_price(raw_data.get("price"))
            cleaned_data["list_price"] = self._clean_price(raw_data.get("list_price"))

            # 库存和可用性
            cleaned_data["availability"] = self._clean_availability(
                raw_data.get("availability")
            )

            # 评价信息清洗
            cleaned_data["rating"] = self._clean_rating(raw_data.get("rating"))
            cleaned_data["review_count"] = self._clean_review_count(
                raw_data.get("review_count")
            )

            # 排名信息清洗
            cleaned_data["rank"] = self._clean_rank(raw_data.get("rank"))

            # 媒体信息清洗
            cleaned_data["image_url"] = self._clean_image_url(raw_data.get("image_url"))
            cleaned_data["images"] = self._clean_images(raw_data.get("images"))

            # 产品详情清洗
            cleaned_data["features"] = self._clean_features(raw_data.get("features"))
            cleaned_data["description"] = self._clean_description(
                raw_data.get("description")
            )

            # 变体信息清洗
            cleaned_data["variations"] = self._clean_variations(
                raw_data.get("variations")
            )

            # 卖家信息清洗
            cleaned_data["seller_info"] = self._clean_seller_info(
                raw_data.get("seller_info")
            )

            # 物流信息清洗
            cleaned_data["shipping_info"] = self._clean_shipping_info(
                raw_data.get("shipping_info")
            )

            # 额外数据清洗
            cleaned_data["additional_data"] = self._clean_additional_data(
                raw_data.get("additional_data")
            )

            return cleaned_data

        except Exception as e:
            self.logger.error(f"Error cleaning product data: {e}")
            raise

    def _clean_asin(self, asin: Any) -> Optional[str]:
        """清洗ASIN"""
        if not asin:
            return None

        asin_str = str(asin).strip().upper()

        # ASIN应该是10位字母数字组合
        if len(asin_str) == 10 and asin_str.isalnum():
            return asin_str

        # 从URL中提取ASIN
        asin_match = re.search(r"/([A-Z0-9]{10})/", str(asin))
        if asin_match:
            return asin_match.group(1)

        return None

    def _clean_title(self, title: Any) -> Optional[str]:
        """清洗标题"""
        if not title:
            return None

        title_str = str(title).strip()

        # 移除多余的空白字符
        title_str = re.sub(r"\s+", " ", title_str)

        # 限制长度
        if len(title_str) > 500:
            title_str = title_str[:497] + "..."

        return title_str if title_str else None

    def _clean_brand(self, brand: Any) -> Optional[str]:
        """清洗品牌"""
        if not brand:
            return None

        brand_str = str(brand).strip()

        # 移除多余的空白字符
        brand_str = re.sub(r"\s+", " ", brand_str)

        # 移除常见的前缀
        brand_str = re.sub(r"^(Brand:\s*|by\s+)", "", brand_str, flags=re.IGNORECASE)

        return brand_str if brand_str else None

    def _clean_category(self, category: Any) -> Optional[str]:
        """清洗分类"""
        if not category:
            return None

        if isinstance(category, list):
            # 如果是面包屑导航，取最后一级分类
            category = category[-1] if category else None

        if not category:
            return None

        category_str = str(category).strip()
        category_str = re.sub(r"\s+", " ", category_str)

        return category_str if category_str else None

    def _clean_price(self, price: Any) -> Optional[float]:
        """清洗价格"""
        if price is None:
            return None

        try:
            # 如果已经是数字
            if isinstance(price, (int, float)):
                return float(price) if price > 0 else None

            # 清理价格字符串
            price_str = str(price).strip()

            # 移除货币符号和逗号
            price_str = re.sub(r"[$,\s]", "", price_str)

            # 提取数字（支持小数）
            price_match = re.search(r"(\d+\.?\d*)", price_str)
            if price_match:
                price_value = float(price_match.group(1))
                return price_value if price_value > 0 else None

        except (ValueError, TypeError):
            pass

        return None

    def _clean_availability(self, availability: Any) -> Optional[str]:
        """清洗库存状态"""
        if not availability:
            return None

        availability_str = str(availability).strip().lower()

        # 标准化库存状态
        if any(word in availability_str for word in ["in stock", "available", "有货"]):
            return "In Stock"
        elif any(
            word in availability_str for word in ["out of stock", "unavailable", "缺货"]
        ):
            return "Out of Stock"
        elif any(word in availability_str for word in ["temporarily", "暂时"]):
            return "Temporarily Unavailable"

        return availability_str.title()

    def _clean_rating(self, rating: Any) -> Optional[float]:
        """清洗评分"""
        if rating is None:
            return None

        try:
            # 如果已经是数字
            if isinstance(rating, (int, float)):
                rating_value = float(rating)
                return rating_value if 0 <= rating_value <= 5 else None

            # 从字符串中提取评分
            rating_str = str(rating).strip()
            rating_match = re.search(r"(\d+\.?\d*)", rating_str)

            if rating_match:
                rating_value = float(rating_match.group(1))
                return rating_value if 0 <= rating_value <= 5 else None

        except (ValueError, TypeError):
            pass

        return None

    def _clean_review_count(self, review_count: Any) -> int:
        """清洗评论数量"""
        if review_count is None:
            return 0

        try:
            # 如果已经是数字
            if isinstance(review_count, int):
                return max(0, review_count)

            # 清理评论数量字符串
            count_str = str(review_count).strip()

            # 移除逗号和其他非数字字符
            count_str = re.sub(r"[,\s]", "", count_str)

            # 提取数字
            count_match = re.search(r"(\d+)", count_str)
            if count_match:
                return max(0, int(count_match.group(1)))

        except (ValueError, TypeError):
            pass

        return 0

    def _clean_rank(self, rank: Any) -> Optional[int]:
        """清洗排名"""
        if rank is None:
            return None

        try:
            # 如果已经是数字
            if isinstance(rank, int):
                return rank if rank > 0 else None

            # 从字符串中提取排名
            rank_str = str(rank).strip()

            # 移除#号、逗号等
            rank_str = re.sub(r"[#,\s]", "", rank_str)

            # 提取第一个数字
            rank_match = re.search(r"(\d+)", rank_str)
            if rank_match:
                rank_value = int(rank_match.group(1))
                return rank_value if rank_value > 0 else None

        except (ValueError, TypeError):
            pass

        return None

    def _clean_image_url(self, image_url: Any) -> Optional[str]:
        """清洗图片URL"""
        if not image_url:
            return None

        url_str = str(image_url).strip()

        # 验证URL格式
        if url_str.startswith(("http://", "https://")):
            return url_str

        return None

    def _clean_images(self, images: Any) -> list[str]:
        """清洗图片列表"""
        if not images:
            return []

        if not isinstance(images, list):
            images = [images]

        cleaned_images = []
        for img in images:
            cleaned_url = self._clean_image_url(img)
            if cleaned_url:
                cleaned_images.append(cleaned_url)

        return cleaned_images

    def _clean_features(self, features: Any) -> list[str]:
        """清洗产品特性列表"""
        if not features:
            return []

        if not isinstance(features, list):
            features = [features]

        cleaned_features = []
        for feature in features:
            if feature:
                feature_str = str(feature).strip()
                feature_str = re.sub(r"\s+", " ", feature_str)
                if feature_str:
                    cleaned_features.append(feature_str)

        return cleaned_features

    def _clean_description(self, description: Any) -> Optional[str]:
        """清洗产品描述"""
        if not description:
            return None

        desc_str = str(description).strip()

        # 移除HTML标签
        desc_str = re.sub(r"<[^>]+>", "", desc_str)

        # 移除多余的空白字符
        desc_str = re.sub(r"\s+", " ", desc_str)

        # 限制长度
        if len(desc_str) > 2000:
            desc_str = desc_str[:1997] + "..."

        return desc_str if desc_str else None

    def _clean_variations(self, variations: Any) -> list[dict[str, Any]]:
        """清洗产品变体信息"""
        if not variations:
            return []

        if not isinstance(variations, list):
            return []

        cleaned_variations = []
        for variation in variations:
            if isinstance(variation, dict):
                cleaned_var = {}

                # 清洗变体ASIN
                if variation.get("asin"):
                    cleaned_var["asin"] = self._clean_asin(variation["asin"])

                # 清洗变体标题
                if variation.get("title"):
                    cleaned_var["title"] = self._clean_title(variation["title"])

                # 清洗变体价格
                if variation.get("price"):
                    cleaned_var["price"] = self._clean_price(variation["price"])

                # 清洗变体图片
                if variation.get("image"):
                    cleaned_var["image"] = self._clean_image_url(variation["image"])

                # 清洗变体URL
                if variation.get("url"):
                    cleaned_var["url"] = str(variation["url"]).strip()

                if any(cleaned_var.values()):
                    cleaned_variations.append(cleaned_var)

        return cleaned_variations

    def _clean_seller_info(self, seller_info: Any) -> dict[str, Any]:
        """清洗卖家信息"""
        if not seller_info or not isinstance(seller_info, dict):
            return {}

        cleaned_seller = {}

        # 清洗卖家名称
        if seller_info.get("name"):
            cleaned_seller["name"] = str(seller_info["name"]).strip()

        # 清洗卖家URL
        if seller_info.get("url"):
            url = str(seller_info["url"]).strip()
            if url.startswith(("http://", "https://")):
                cleaned_seller["url"] = url

        # 清洗卖家评分
        if seller_info.get("rating"):
            rating = self._clean_rating(seller_info["rating"])
            if rating is not None:
                cleaned_seller["rating"] = rating

        return cleaned_seller

    def _clean_shipping_info(self, shipping_info: Any) -> dict[str, Any]:
        """清洗物流信息"""
        if not shipping_info or not isinstance(shipping_info, dict):
            return {}

        cleaned_shipping = {}

        # 清洗免费配送信息
        if "free_shipping" in shipping_info:
            cleaned_shipping["free_shipping"] = bool(shipping_info["free_shipping"])

        # 清洗Prime信息
        if "prime" in shipping_info:
            cleaned_shipping["prime"] = bool(shipping_info["prime"])

        return cleaned_shipping

    def _clean_additional_data(self, additional_data: Any) -> dict[str, Any]:
        """清洗额外数据"""
        if not additional_data or not isinstance(additional_data, dict):
            return {}

        cleaned_additional = {}

        # 清洗产品URL
        if additional_data.get("url"):
            url = str(additional_data["url"]).strip()
            if url.startswith(("http://", "https://")):
                cleaned_additional["url"] = url

        # 清洗面包屑导航
        if additional_data.get("breadcrumbs"):
            breadcrumbs = additional_data["breadcrumbs"]
            if isinstance(breadcrumbs, list):
                cleaned_breadcrumbs = []
                for crumb in breadcrumbs:
                    if crumb:
                        cleaned_breadcrumbs.append(str(crumb).strip())
                if cleaned_breadcrumbs:
                    cleaned_additional["breadcrumbs"] = cleaned_breadcrumbs

        # 清洗优惠券信息
        if additional_data.get("coupon"):
            cleaned_additional["coupon"] = str(additional_data["coupon"]).strip()

        # 清洗促销信息
        if additional_data.get("deal"):
            cleaned_additional["deal"] = str(additional_data["deal"]).strip()

        # 清洗广告标记
        if "sponsored" in additional_data:
            cleaned_additional["sponsored"] = bool(additional_data["sponsored"])

        return cleaned_additional

    def validate_cleaned_data(self, data: dict[str, Any]) -> bool:
        """验证清洗后的数据"""
        try:
            return AmazonProductData.validate_product_data(data)
        except Exception as e:
            self.logger.error(f"Data validation error: {e}")
            return False

    def process_batch(self, raw_products: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """批量处理产品数据"""
        processed_products = []

        for i, raw_product in enumerate(raw_products):
            try:
                # 清洗数据
                cleaned_data = self.clean_product_data(raw_product)

                # 验证数据
                if self.validate_cleaned_data(cleaned_data):
                    processed_products.append(cleaned_data)
                else:
                    self.logger.warning(
                        f"Product {i+1} failed validation: ASIN={raw_product.get('asin')}"
                    )

            except Exception as e:
                self.logger.error(f"Error processing product {i+1}: {e}")
                continue

        self.logger.info(
            f"Processed {len(processed_products)}/{len(raw_products)} products successfully"
        )
        return processed_products

    def extract_price_changes(
        self, current_data: dict[str, Any], previous_data: dict[str, Any]
    ) -> dict[str, Any]:
        """提取价格变化信息"""
        changes = {}

        current_price = current_data.get("price")
        previous_price = previous_data.get("price")

        if current_price is not None and previous_price is not None:
            if current_price != previous_price:
                change_amount = current_price - previous_price
                change_percent = (change_amount / previous_price) * 100

                changes["price_change"] = {
                    "previous_price": previous_price,
                    "current_price": current_price,
                    "change_amount": round(change_amount, 2),
                    "change_percent": round(change_percent, 2),
                    "change_type": "increase" if change_amount > 0 else "decrease",
                }

        # 检查排名变化
        current_rank = current_data.get("rank")
        previous_rank = previous_data.get("rank")

        if current_rank is not None and previous_rank is not None:
            if current_rank != previous_rank:
                rank_change = previous_rank - current_rank  # 排名降低是好事

                changes["rank_change"] = {
                    "previous_rank": previous_rank,
                    "current_rank": current_rank,
                    "change": rank_change,
                    "change_type": "improved" if rank_change > 0 else "declined",
                }

        return changes
