"""健康检查组件"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# 加载环境变量
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(project_root / ".env.local")
load_dotenv(project_root / ".env")

from sqlalchemy import text

from ..crawlers.apify_client import ApifyAmazonScraper
from ..database.connection import get_db_session
from ..database.models.crawl import CrawlTask, TaskStatus

logger = logging.getLogger(__name__)


class HealthCheckResult:
    """健康检查结果"""

    def __init__(
        self,
        service: str,
        status: str,
        details: dict[str, Any] = None,
        error: str = None,
    ):
        self.service = service
        self.status = status  # "healthy", "unhealthy", "degraded"
        self.details = details or {}
        self.error = error
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "status": self.status,
            "details": self.details,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


class HealthChecker:
    """健康检查器"""

    def __init__(self):
        self.checks = {}
        self.last_results = {}

    def register_check(self, name: str, check_func, interval: int = 60):
        """注册健康检查"""
        self.checks[name] = {"func": check_func, "interval": interval, "last_run": None}

    async def run_all_checks(self) -> dict[str, HealthCheckResult]:
        """运行所有健康检查"""
        results = {}

        for name, check_config in self.checks.items():
            try:
                result = await self._run_check(name, check_config)
                results[name] = result
                self.last_results[name] = result
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                results[name] = HealthCheckResult(
                    service=name, status="unhealthy", error=str(e)
                )

        return results

    async def _run_check(
        self, name: str, check_config: dict[str, Any]
    ) -> HealthCheckResult:
        """运行单个健康检查"""
        check_func = check_config["func"]

        # 检查是否需要运行
        last_run = check_config.get("last_run")
        interval = check_config.get("interval", 60)

        if last_run and (datetime.utcnow() - last_run).total_seconds() < interval:
            # 返回缓存的结果
            return self.last_results.get(
                name,
                HealthCheckResult(
                    service=name, status="unknown", error="No cached result available"
                ),
            )

        # 运行检查
        if asyncio.iscoroutinefunction(check_func):
            result = await check_func()
        else:
            result = check_func()

        check_config["last_run"] = datetime.utcnow()
        return result

    def get_overall_status(self, results: dict[str, HealthCheckResult]) -> str:
        """获取整体健康状态"""
        if not results:
            return "unknown"

        statuses = [result.status for result in results.values()]

        if all(status == "healthy" for status in statuses):
            return "healthy"
        elif any(status == "unhealthy" for status in statuses):
            return "unhealthy"
        else:
            return "degraded"


# 全局健康检查器
health_checker = HealthChecker()


async def check_database_health() -> HealthCheckResult:
    """检查数据库健康状态"""
    try:
        with get_db_session() as db:
            # 执行简单查询
            result = db.execute(text("SELECT 1")).fetchone()

            if result:
                # 检查最近的任务状态
                recent_tasks = (
                    db.query(CrawlTask)
                    .filter(
                        CrawlTask.created_at >= datetime.utcnow() - timedelta(hours=1)
                    )
                    .count()
                )

                running_tasks = (
                    db.query(CrawlTask)
                    .filter(CrawlTask.status == TaskStatus.RUNNING)
                    .count()
                )

                return HealthCheckResult(
                    service="database",
                    status="healthy",
                    details={
                        "connection": "ok",
                        "recent_tasks_1h": recent_tasks,
                        "running_tasks": running_tasks,
                    },
                )
            else:
                return HealthCheckResult(
                    service="database",
                    status="unhealthy",
                    error="Query returned no result",
                )

    except Exception as e:
        return HealthCheckResult(service="database", status="unhealthy", error=str(e))


async def check_apify_health() -> HealthCheckResult:
    """检查Apify服务健康状态"""
    try:
        scraper = ApifyAmazonScraper()
        is_healthy = await scraper.health_check()

        if is_healthy:
            return HealthCheckResult(
                service="apify", status="healthy", details={"connection": "ok"}
            )
        else:
            return HealthCheckResult(
                service="apify", status="unhealthy", error="Apify health check failed"
            )

    except Exception as e:
        return HealthCheckResult(service="apify", status="unhealthy", error=str(e))


async def check_redis_health() -> HealthCheckResult:
    """检查Redis健康状态"""
    try:
        import redis

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)

        # 执行简单的ping命令
        pong = r.ping()

        if pong:
            # 获取Redis信息
            info = r.info()

            return HealthCheckResult(
                service="redis",
                status="healthy",
                details={
                    "connection": "ok",
                    "memory_usage": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "uptime": info.get("uptime_in_seconds"),
                },
            )
        else:
            return HealthCheckResult(
                service="redis", status="unhealthy", error="Redis ping failed"
            )

    except Exception as e:
        return HealthCheckResult(service="redis", status="unhealthy", error=str(e))


async def check_celery_health() -> HealthCheckResult:
    """检查Celery健康状态"""
    try:
        from ..task_queue.celery_app import celery_app

        # 检查活跃的worker
        inspect = celery_app.control.inspect()
        stats = inspect.stats()

        if stats:
            active_workers = len(stats)

            # 检查队列状态
            active_queues = inspect.active_queues()
            reserved_tasks = inspect.reserved()

            total_reserved = 0
            if reserved_tasks:
                for worker_tasks in reserved_tasks.values():
                    total_reserved += len(worker_tasks)

            return HealthCheckResult(
                service="celery",
                status="healthy",
                details={
                    "active_workers": active_workers,
                    "reserved_tasks": total_reserved,
                    "workers": list(stats.keys()) if stats else [],
                },
            )
        else:
            return HealthCheckResult(
                service="celery",
                status="unhealthy",
                error="No active Celery workers found",
            )

    except Exception as e:
        return HealthCheckResult(service="celery", status="unhealthy", error=str(e))


async def check_queue_health() -> HealthCheckResult:
    """检查任务队列健康状态"""
    try:
        with get_db_session() as db:
            # 检查待处理任务数量
            pending_tasks = (
                db.query(CrawlTask)
                .filter(CrawlTask.status == TaskStatus.PENDING)
                .count()
            )

            # 检查长时间运行的任务
            long_running_threshold = datetime.utcnow() - timedelta(hours=2)
            long_running_tasks = (
                db.query(CrawlTask)
                .filter(
                    CrawlTask.status == TaskStatus.RUNNING,
                    CrawlTask.started_at < long_running_threshold,
                )
                .count()
            )

            # 检查失败率
            recent_threshold = datetime.utcnow() - timedelta(hours=24)
            recent_tasks = db.query(CrawlTask).filter(
                CrawlTask.created_at >= recent_threshold
            )

            total_recent = recent_tasks.count()
            failed_recent = recent_tasks.filter(
                CrawlTask.status == TaskStatus.FAILED
            ).count()

            failure_rate = (
                (failed_recent / total_recent * 100) if total_recent > 0 else 0
            )

            # 判断健康状态
            status = "healthy"
            if pending_tasks > 1000:  # 待处理任务过多
                status = "degraded"
            if long_running_tasks > 10:  # 长时间运行任务过多
                status = "degraded"
            if failure_rate > 20:  # 失败率过高
                status = "unhealthy"

            return HealthCheckResult(
                service="task_queue",
                status=status,
                details={
                    "pending_tasks": pending_tasks,
                    "long_running_tasks": long_running_tasks,
                    "failure_rate_24h": round(failure_rate, 2),
                    "total_tasks_24h": total_recent,
                },
            )

    except Exception as e:
        return HealthCheckResult(service="task_queue", status="unhealthy", error=str(e))


# 注册健康检查
health_checker.register_check("database", check_database_health, interval=30)
health_checker.register_check("apify", check_apify_health, interval=120)
health_checker.register_check("redis", check_redis_health, interval=60)
health_checker.register_check("celery", check_celery_health, interval=60)
health_checker.register_check("task_queue", check_queue_health, interval=60)


async def get_health_status() -> dict[str, Any]:
    """获取完整的健康状态"""
    results = await health_checker.run_all_checks()
    overall_status = health_checker.get_overall_status(results)

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {name: result.to_dict() for name, result in results.items()},
    }
