"""监控相关的Celery任务"""

import logging
from typing import Any

from celery import Task

from ...services.monitoring.anomaly_detector import AnomalyDetector
from ..notification.email_service import EmailNotifier
from .celery_app import celery_app

logger = logging.getLogger(__name__)


class MonitoringTask(Task):
    """监控任务基类"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的回调"""
        logger.error(f"Monitoring task {task_id} failed: {exc}")


@celery_app.task(bind=True, base=MonitoringTask, queue="monitoring")
def check_product_anomalies(self, product_id: int) -> dict[str, Any]:
    """检查单个产品的异常情况"""

    task_logger = logging.getLogger(f"monitoring_task_{self.request.id}")

    try:
        # 初始化检测器和通知器
        detector = AnomalyDetector()
        notifier = EmailNotifier()

        # 检查异常
        results = detector.check_all_anomalies(product_id)

        if results.get("has_anomaly"):
            task_logger.info(f"Anomaly detected for product {product_id}")

            # 发送通知
            notification_results = notifier.send_multiple_alerts(results)
            results["notifications_sent"] = notification_results

            # 记录通知结果
            for alert_type, success in notification_results.items():
                if success:
                    task_logger.info(f"{alert_type} notification sent successfully")
                else:
                    task_logger.warning(f"Failed to send {alert_type} notification")
        else:
            task_logger.debug(f"No anomalies detected for product {product_id}")

        return results

    except Exception as e:
        task_logger.error(f"Error checking anomalies for product {product_id}: {e}")
        raise


@celery_app.task(bind=True, base=MonitoringTask, queue="monitoring")
def scan_all_product_anomalies(self, tenant_id: str = None) -> dict[str, Any]:
    """扫描所有产品的异常情况 - 支持价格>10%和BSR>30%变化检测"""

    task_logger = logging.getLogger(f"monitoring_scan_{self.request.id}")

    try:
        from ..database.connection import get_db_session
        from ..database.models.product import Product, ProductStatus
        from apify_client import ApifyClient
        from decimal import Decimal
        import json
        import os
        
        # 初始化通知器
        notifier = EmailNotifier()
        apify_client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

        total_checked = 0
        anomalies_found = 0
        notifications_sent = {"price_alerts": 0, "bsr_alerts": 0, "failed": 0}

        with get_db_session() as db:
            # 获取监控中的产品（按租户过滤）
            query = db.query(Product)
            if tenant_id:
                query = query.filter(Product.tenant_id == tenant_id)
            products = query.all()
            
            task_logger.info(f"开始检查 {len(products)} 个产品的异常情况")
            
            # 批量获取产品最新数据
            asins = [p.asin for p in products[:10]]  # 限制10个避免超时
            
            if not asins:
                return {"total_products_scanned": 0, "anomalies_found": 0}
            
            # 从Apify获取最新数据
            run_input = {
                "asins": asins,
                "amazonDomain": "amazon.com",
                "maxConcurrency": 5,
                "proxyCountry": "AUTO_SELECT_PROXY_COUNTRY",
                "useCaptchaSolver": False,
            }
            
            run = apify_client.actor("ZhSGsaq9MHRnWtStl").call(run_input=run_input)
            items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())
            
            # 按ASIN索引数据
            latest_data = {}
            for item in items:
                asin = item.get("asin")
                if asin and asin not in latest_data:
                    latest_data[asin] = item
            
            # 检查每个产品的变化
            for product in products:
                if product.asin not in latest_data:
                    continue
                    
                total_checked += 1
                current_data = latest_data[product.asin]
                
                # 解析新数据
                new_price = None
                if current_data.get("price"):
                    price_data = current_data["price"]
                    if isinstance(price_data, dict):
                        new_price = Decimal(str(price_data.get("value", 0)))
                    else:
                        new_price = Decimal(str(price_data))

                print("新产品的价格：", new_price, "旧产品的价格：", product.current_price)

                new_bsr = None
                bsr_data = current_data.get("bestsellerRanks", [])
                if bsr_data and len(bsr_data) > 0:
                    new_bsr = bsr_data[0].get("rank")

                # 检查价格变化（>10%）
                price_change_detected = False
                if product.current_price and new_price:
                    price_change_percent = abs(float(new_price - product.current_price)) / float(product.current_price) * 100
                    if price_change_percent > 10:
                        price_change_detected = True
                        
                        # 发送价格变化通知
                        try:
                            alert_data = {
                                "product_id": product.id,
                                "asin": product.asin,
                                "title": product.title,
                                "old_price": float(product.current_price),
                                "new_price": float(new_price),
                                "change_percent": price_change_percent,
                                "alert_type": "price_change"
                            }
                            
                            success = notifier.send_price_change_alert(alert_data)
                            if success:
                                notifications_sent["price_alerts"] += 1
                            else:
                                notifications_sent["failed"] += 1
                                
                        except Exception as e:
                            task_logger.error(f"价格通知发送失败 {product.asin}: {e}")
                            notifications_sent["failed"] += 1
                
                # 检查BSR变化（>30%）
                bsr_change_detected = False
                if product.current_rank and new_bsr:
                    bsr_change_percent = abs(new_bsr - product.current_rank) / product.current_rank * 100
                    if bsr_change_percent > 30:
                        bsr_change_detected = True
                        
                        # 发送BSR变化通知
                        try:
                            alert_data = {
                                "product_id": product.id,
                                "asin": product.asin,
                                "title": product.title,
                                "old_rank": product.current_rank,
                                "new_rank": new_bsr,
                                "change_percent": bsr_change_percent,
                                "alert_type": "bsr_change"
                            }
                            
                            success = notifier.send_rank_alert(alert_data)
                            if success:
                                notifications_sent["bsr_alerts"] += 1
                            else:
                                notifications_sent["failed"] += 1
                                
                        except Exception as e:
                            task_logger.error(f"BSR通知发送失败 {product.asin}: {e}")
                            notifications_sent["failed"] += 1
                
                # 更新产品数据
                if new_price:
                    product.current_price = new_price
                if new_bsr:
                    product.current_rank = new_bsr
                if current_data.get("productRating"):
                    product.current_rating = Decimal(str(current_data["productRating"]))
                if current_data.get("countReview"):
                    product.current_review_count = current_data["countReview"]
                
                product.product_data = current_data
                from datetime import datetime
                product.last_scraped_at = datetime.utcnow()
                
                if price_change_detected or bsr_change_detected:
                    anomalies_found += 1
                    task_logger.info(
                        f"检测到异常 {product.asin}: "
                        f"价格变化={price_change_detected}, BSR变化={bsr_change_detected}"
                    )
            
            db.commit()
            task_logger.info(f"完成扫描：{total_checked}个产品，{anomalies_found}个异常")

        return {
            "total_products_scanned": total_checked,
            "anomalies_found": anomalies_found,
            "notifications_sent": notifications_sent,
            "task_status": "completed"
        }

    except Exception as e:
        task_logger.error(f"Error during anomaly scan: {e}")
        raise


@celery_app.task(bind=True, base=MonitoringTask, queue="monitoring")
def test_monitoring_system(self, product_id: int) -> dict[str, Any]:
    """测试监控系统功能"""

    task_logger = logging.getLogger(f"monitoring_test_{self.request.id}")

    try:
        # 测试异常检测
        detector = AnomalyDetector()
        detection_results = detector.check_all_anomalies(product_id)

        # 测试邮件通知（如果有异常的话）
        notification_results = {}
        if detection_results.get("has_anomaly"):
            notifier = EmailNotifier()
            notification_results = notifier.send_multiple_alerts(detection_results)

        return {
            "test_status": "success",
            "product_id": product_id,
            "detection_results": detection_results,
            "notification_results": notification_results,
            "test_time": task_logger.__dict__.get("test_time"),
        }

    except Exception as e:
        task_logger.error(f"Monitoring system test failed: {e}")
        return {"test_status": "failed", "error": str(e), "product_id": product_id}
