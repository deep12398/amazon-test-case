"""Celery Beat定时任务配置"""

from celery.schedules import crontab

# Celery Beat调度配置
CELERY_BEAT_SCHEDULE = {
    # ===== 核心产品监控任务 =====
    # 每30分钟检查产品价格和BSR变化
    "product-price-monitor": {
        "task": "amazon_tracker.common.task_queue.monitoring_tasks.scan_all_product_anomalies",
        "schedule": crontab(minute="*/30"),  # 每30分钟
        "options": {"queue": "monitoring", "routing_key": "monitoring"},
    },
    # 每5分钟批量抓取产品数据
    "frequent-product-update": {
        "task": "amazon_tracker.common.task_queue.crawler_tasks.crawl_products_batch",
        "schedule": 3000.0,  # 每3000秒执行
        "options": {"queue": "crawler", "routing_key": "crawler"},
    },
}

# Celery Beat时区设置
CELERY_TIMEZONE = "UTC"

# 任务路由配置
CELERY_TASK_ROUTES = {
    # 爬虫任务
    "amazon_tracker.common.task_queue.crawler_tasks.*": {
        "queue": "crawler",
        "routing_key": "crawler",
    },
    # 监控任务
    "amazon_tracker.common.task_queue.monitoring_tasks.*": {
        "queue": "monitoring",
        "routing_key": "monitoring",
    },
    # 分析任务
    "amazon_tracker.common.task_queue.analysis_tasks.*": {
        "queue": "analysis",
        "routing_key": "analysis",
    },
    # 维护任务
    "amazon_tracker.common.task_queue.maintenance_tasks.*": {
        "queue": "maintenance",
        "routing_key": "maintenance",
    },
    # 报告任务
    "amazon_tracker.common.task_queue.report_tasks.*": {
        "queue": "reports",
        "routing_key": "reports",
    },
    # 调度任务
    "amazon_tracker.common.task_queue.scheduler_tasks.*": {
        "queue": "scheduler",
        "routing_key": "scheduler",
    },
}

# 队列配置
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_QUEUES = {
    "default": {"routing_key": "default"},
    "crawler": {"routing_key": "crawler"},
    "monitoring": {"routing_key": "monitoring"},
    "analysis": {"routing_key": "analysis"},
    "maintenance": {"routing_key": "maintenance"},
    "reports": {"routing_key": "reports"},
    "scheduler": {"routing_key": "scheduler"},
}

# 任务优先级配置
CELERY_TASK_DEFAULT_PRIORITY = 5
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_DISABLE_RATE_LIMITS = False

# 任务重试配置
CELERY_TASK_ANNOTATIONS = {
    "*": {
        "rate_limit": "10/s",
        "time_limit": 30 * 60,  # 30分钟超时
        "soft_time_limit": 25 * 60,  # 25分钟软超时
    },
    "amazon_tracker.common.task_queue.crawler_tasks.*": {
        "rate_limit": "5/s",  # 爬虫任务限速
        "max_retries": 3,
        "default_retry_delay": 60,  # 1分钟重试间隔
    },
    "amazon_tracker.common.task_queue.monitoring_tasks.*": {
        "rate_limit": "20/s",  # 监控任务可以更频繁
        "max_retries": 2,
        "default_retry_delay": 30,
    },
    "amazon_tracker.common.task_queue.analysis_tasks.*": {
        "rate_limit": "2/s",  # AI分析任务限速更严格
        "time_limit": 60 * 60,  # 1小时超时
        "soft_time_limit": 55 * 60,
        "max_retries": 2,
        "default_retry_delay": 120,  # 2分钟重试间隔
    },
}
