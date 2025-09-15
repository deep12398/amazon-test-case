"""异常检测服务"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Any, Optional

from ...common.database.connection import get_db_session
from ...common.database.models.product import (
    Product,
    ProductPriceHistory,
    ProductRankHistory,
)

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """异常检测器"""

    def __init__(self):
        self.price_threshold = 10.0  # 价格变动阈值 10%
        self.buy_box_threshold = 15.0  # Buy Box价格变动阈值 15%
        self.bsr_threshold = 30.0  # BSR变动阈值 30%
        self.rating_threshold = 0.5  # 评分变动阈值 0.5分
        self.review_threshold = 20.0  # 评论数量变动阈值 20%
        self.history_days = 7  # 历史数据天数

    def check_price_anomaly(
        self, product_id: int, current_price: Optional[float] = None
    ) -> dict[str, Any]:
        """检测价格异常

        Args:
            product_id: 产品ID
            current_price: 当前价格（可选，如果不提供则从产品表获取）

        Returns:
            异常检测结果
        """
        with get_db_session() as db:
            try:
                # 获取产品信息
                product = db.query(Product).filter(Product.id == product_id).first()
                if not product:
                    return {"is_anomaly": False, "error": "Product not found"}

                # 使用当前价格或从产品获取
                if current_price is None:
                    current_price = product.current_price

                if current_price is None:
                    return {"is_anomaly": False, "error": "No current price available"}

                # 获取历史价格数据（过去7天）
                cutoff_date = datetime.utcnow() - timedelta(days=self.history_days)

                price_history = (
                    db.query(ProductPriceHistory)
                    .filter(
                        ProductPriceHistory.product_id == product_id,
                        ProductPriceHistory.recorded_at >= cutoff_date,
                    )
                    .order_by(ProductPriceHistory.recorded_at.desc())
                    .all()
                )

                if len(price_history) < 2:
                    return {
                        "is_anomaly": False,
                        "reason": "Insufficient historical data",
                    }

                # 计算历史平均价格
                historical_prices = [
                    float(record.price)
                    for record in price_history
                    if record.price is not None
                ]

                if not historical_prices:
                    return {"is_anomaly": False, "reason": "No valid historical prices"}

                avg_price = statistics.mean(historical_prices)

                # 计算变化百分比
                change_percent = abs(current_price - avg_price) / avg_price * 100

                is_anomaly = change_percent > self.price_threshold

                return {
                    "is_anomaly": is_anomaly,
                    "product_id": product_id,
                    "product_asin": product.asin,
                    "product_title": product.title,
                    "current_price": current_price,
                    "average_price": round(avg_price, 2),
                    "change_percent": round(change_percent, 2),
                    "threshold": self.price_threshold,
                    "direction": "increase"
                    if current_price > avg_price
                    else "decrease",
                    "historical_data_points": len(historical_prices),
                    "check_time": datetime.utcnow().isoformat(),
                }

            except Exception as e:
                logger.error(
                    f"Error checking price anomaly for product {product_id}: {e}"
                )
                return {"is_anomaly": False, "error": str(e)}

    def check_bsr_anomaly(
        self, product_id: int, current_rank: Optional[int] = None
    ) -> dict[str, Any]:
        """检测BSR排名异常

        Args:
            product_id: 产品ID
            current_rank: 当前排名（可选，如果不提供则从产品表获取）

        Returns:
            异常检测结果
        """
        with get_db_session() as db:
            try:
                # 获取产品信息
                product = db.query(Product).filter(Product.id == product_id).first()
                if not product:
                    return {"is_anomaly": False, "error": "Product not found"}

                # 使用当前排名或从产品获取
                if current_rank is None:
                    current_rank = product.current_rank

                if current_rank is None:
                    return {"is_anomaly": False, "error": "No current rank available"}

                # 获取历史排名数据（过去7天）
                cutoff_date = datetime.utcnow() - timedelta(days=self.history_days)

                rank_history = (
                    db.query(ProductRankHistory)
                    .filter(
                        ProductRankHistory.product_id == product_id,
                        ProductRankHistory.recorded_at >= cutoff_date,
                    )
                    .order_by(ProductRankHistory.recorded_at.desc())
                    .all()
                )

                if len(rank_history) < 2:
                    return {
                        "is_anomaly": False,
                        "reason": "Insufficient historical data",
                    }

                # 计算历史平均排名
                historical_ranks = [
                    record.rank for record in rank_history if record.rank is not None
                ]

                if not historical_ranks:
                    return {"is_anomaly": False, "reason": "No valid historical ranks"}

                avg_rank = statistics.mean(historical_ranks)

                # 计算变化百分比
                change_percent = abs(current_rank - avg_rank) / avg_rank * 100

                is_anomaly = change_percent > self.bsr_threshold

                return {
                    "is_anomaly": is_anomaly,
                    "product_id": product_id,
                    "product_asin": product.asin,
                    "product_title": product.title,
                    "current_rank": current_rank,
                    "average_rank": round(avg_rank),
                    "change_percent": round(change_percent, 2),
                    "threshold": self.bsr_threshold,
                    "direction": "worse" if current_rank > avg_rank else "better",
                    "historical_data_points": len(historical_ranks),
                    "check_time": datetime.utcnow().isoformat(),
                }

            except Exception as e:
                logger.error(
                    f"Error checking BSR anomaly for product {product_id}: {e}"
                )
                return {"is_anomaly": False, "error": str(e)}

    def check_buy_box_anomaly(
        self, product_id: int, current_buy_box_price: Optional[float] = None
    ) -> dict[str, Any]:
        """检测Buy Box价格异常

        Args:
            product_id: 产品ID
            current_buy_box_price: 当前Buy Box价格（可选，如果不提供则从产品表获取）

        Returns:
            异常检测结果
        """
        with get_db_session() as db:
            try:
                # 获取产品信息
                product = db.query(Product).filter(Product.id == product_id).first()
                if not product:
                    return {"is_anomaly": False, "error": "Product not found"}

                # 使用当前Buy Box价格或从产品获取
                if current_buy_box_price is None:
                    current_buy_box_price = product.buy_box_price

                if current_buy_box_price is None:
                    return {
                        "is_anomaly": False,
                        "error": "No current Buy Box price available",
                    }

                # 获取历史Buy Box价格数据（过去7天）
                cutoff_date = datetime.utcnow() - timedelta(days=self.history_days)

                price_history = (
                    db.query(ProductPriceHistory)
                    .filter(
                        ProductPriceHistory.product_id == product_id,
                        ProductPriceHistory.recorded_at >= cutoff_date,
                        ProductPriceHistory.buy_box_price.isnot(None),
                    )
                    .all()
                )

                if len(price_history) < 2:  # 至少需要2个历史数据点
                    return {
                        "is_anomaly": False,
                        "error": "Insufficient Buy Box price history data",
                        "current_buy_box_price": current_buy_box_price,
                        "historical_data_points": len(price_history),
                    }

                # 计算平均Buy Box价格
                historical_prices = [float(p.buy_box_price) for p in price_history]
                avg_buy_box_price = statistics.mean(historical_prices)

                # 计算变化百分比
                if avg_buy_box_price == 0:
                    change_percent = 0
                else:
                    change_percent = (
                        abs(
                            (current_buy_box_price - avg_buy_box_price)
                            / avg_buy_box_price
                        )
                        * 100
                    )

                # 判断是否异常
                is_anomaly = change_percent > self.buy_box_threshold

                return {
                    "is_anomaly": is_anomaly,
                    "product_id": product_id,
                    "product_asin": product.asin,
                    "product_title": product.title,
                    "current_buy_box_price": current_buy_box_price,
                    "average_buy_box_price": round(avg_buy_box_price, 2),
                    "change_percent": round(change_percent, 2),
                    "threshold": self.buy_box_threshold,
                    "direction": "increase"
                    if current_buy_box_price > avg_buy_box_price
                    else "decrease",
                    "historical_data_points": len(historical_prices),
                    "check_time": datetime.utcnow().isoformat(),
                }

            except Exception as e:
                logger.error(
                    f"Error checking Buy Box anomaly for product {product_id}: {e}"
                )
                return {"is_anomaly": False, "error": str(e)}

    def check_rating_anomaly(
        self, product_id: int, current_rating: Optional[float] = None
    ) -> dict[str, Any]:
        """检测评分异常

        Args:
            product_id: 产品ID
            current_rating: 当前评分（可选，如果不提供则从产品表获取）

        Returns:
            异常检测结果
        """
        with get_db_session() as db:
            try:
                # 获取产品信息
                product = db.query(Product).filter(Product.id == product_id).first()
                if not product:
                    return {"is_anomaly": False, "error": "Product not found"}

                # 使用当前评分或从产品获取
                if current_rating is None:
                    current_rating = float(product.rating) if product.rating else None

                if current_rating is None:
                    return {"is_anomaly": False, "error": "No current rating available"}

                # 获取历史评分数据（通过产品数据快照）
                cutoff_date = datetime.utcnow() - timedelta(days=self.history_days)

                # 简化检测：比较与上次记录的评分
                if product.rating and float(product.rating) != current_rating:
                    change = abs(current_rating - float(product.rating))
                    is_anomaly = change > self.rating_threshold

                    return {
                        "is_anomaly": is_anomaly,
                        "product_id": product_id,
                        "product_asin": product.asin,
                        "product_title": product.title,
                        "current_rating": current_rating,
                        "previous_rating": float(product.rating),
                        "change": round(change, 2),
                        "threshold": self.rating_threshold,
                        "direction": "increase"
                        if current_rating > float(product.rating)
                        else "decrease",
                        "check_time": datetime.utcnow().isoformat(),
                    }

                return {"is_anomaly": False, "message": "No significant rating change"}

            except Exception as e:
                logger.error(
                    f"Error checking rating anomaly for product {product_id}: {e}"
                )
                return {"is_anomaly": False, "error": str(e)}

    def check_all_anomalies(self, product_id: int) -> dict[str, Any]:
        """检查产品的所有异常（价格、Buy Box价格、BSR和评分）

        Args:
            product_id: 产品ID

        Returns:
            所有异常检测结果
        """
        price_result = self.check_price_anomaly(product_id)
        buy_box_result = self.check_buy_box_anomaly(product_id)
        bsr_result = self.check_bsr_anomaly(product_id)
        rating_result = self.check_rating_anomaly(product_id)

        # 检查是否有任何异常
        has_anomaly = any(
            [
                price_result.get("is_anomaly", False),
                buy_box_result.get("is_anomaly", False),
                bsr_result.get("is_anomaly", False),
                rating_result.get("is_anomaly", False),
            ]
        )

        return {
            "product_id": product_id,
            "has_anomaly": has_anomaly,
            "anomaly_count": sum(
                [
                    1
                    for result in [
                        price_result,
                        buy_box_result,
                        bsr_result,
                        rating_result,
                    ]
                    if result.get("is_anomaly", False)
                ]
            ),
            "price_anomaly": price_result,
            "buy_box_anomaly": buy_box_result,
            "bsr_anomaly": bsr_result,
            "rating_anomaly": rating_result,
            "check_time": datetime.utcnow().isoformat(),
        }

    def scan_all_products(
        self, tenant_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """扫描所有产品的异常情况

        Args:
            tenant_id: 可选的租户ID，如果提供则只检查该租户的产品

        Returns:
            所有异常检测结果列表
        """
        anomalies = []

        with get_db_session() as db:
            try:
                # 查询活跃产品
                query = db.query(Product).filter(Product.status == "ACTIVE")

                if tenant_id:
                    query = query.filter(Product.tenant_id == tenant_id)

                products = query.all()

                for product in products:
                    result = self.check_all_anomalies(product.id)
                    if result.get("has_anomaly"):
                        anomalies.append(result)

                logger.info(
                    f"Scanned {len(products)} products, found {len(anomalies)} anomalies"
                )

            except Exception as e:
                logger.error(f"Error scanning products for anomalies: {e}")

        return anomalies
