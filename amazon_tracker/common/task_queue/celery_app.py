"""Celery应用配置"""

import os
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(project_root / ".env.local")
load_dotenv(project_root / ".env")

from celery import Celery
from kombu import Queue

from .celery_beat_config import (
    CELERY_BEAT_SCHEDULE,
    CELERY_TASK_ACKS_LATE,
    CELERY_TASK_ANNOTATIONS,
    CELERY_TASK_DEFAULT_QUEUE,
    CELERY_TASK_QUEUES,
    CELERY_TASK_ROUTES,
    CELERY_TIMEZONE,
    CELERY_WORKER_PREFETCH_MULTIPLIER,
)


class CeleryConfig:
    """Celery配置类"""

    # Broker配置
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # 任务路由（从配置文件导入）
    task_routes = CELERY_TASK_ROUTES

    # 队列配置（从配置文件导入）
    task_default_queue = CELERY_TASK_DEFAULT_QUEUE
    task_queues = tuple(
        Queue(name, routing_key=config["routing_key"])
        for name, config in CELERY_TASK_QUEUES.items()
    )

    # 任务序列化
    task_serializer = "json"
    result_serializer = "json"
    accept_content = ["json"]

    # 时区配置（从配置文件导入）
    timezone = CELERY_TIMEZONE
    enable_utc = True

    # 任务执行配置（从配置文件导入）
    task_acks_late = CELERY_TASK_ACKS_LATE
    worker_prefetch_multiplier = CELERY_WORKER_PREFETCH_MULTIPLIER
    task_reject_on_worker_lost = True

    # 任务注解配置（从配置文件导入）
    task_annotations = CELERY_TASK_ANNOTATIONS

    # 任务重试配置
    task_default_retry_delay = 60  # 默认重试延迟60秒
    task_max_retries = 3

    # 任务超时配置
    task_soft_time_limit = 300  # 软限制5分钟
    task_time_limit = 600  # 硬限制10分钟

    # 结果过期时间
    result_expires = 3600  # 结果1小时后过期

    # Worker配置
    worker_disable_rate_limits = False
    worker_pool_restarts = True

    # 监控配置
    worker_send_task_events = True
    task_send_sent_event = True

    # 日志配置
    worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
    worker_task_log_format = "[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s"

    # Beat调度配置（从配置文件导入）
    beat_schedule = CELERY_BEAT_SCHEDULE


# 创建Celery应用实例
celery_app = Celery("amazon_tracker")

# 加载配置
celery_app.config_from_object(CeleryConfig)

# 自动发现任务
celery_app.autodiscover_tasks(
    [
        "amazon_tracker.common.task_queue",
    ]
)

# 确保导入所有任务模块
try:
    import amazon_tracker.common.task_queue.crawler_tasks
    import amazon_tracker.common.task_queue.monitoring_tasks
except ImportError as e:
    print(f"Warning: Could not import task modules: {e}")


@celery_app.task(bind=True)
def debug_task(self):
    """调试任务"""
    print(f"Request: {self.request!r}")
    return "Debug task completed"
