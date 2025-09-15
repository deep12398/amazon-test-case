"""Prometheus监控指标配置"""

import functools
import logging
import time

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, Summary
from prometheus_client.exposition import generate_latest

logger = logging.getLogger(__name__)

# 创建注册表
registry = CollectorRegistry()

# 业务指标
# 用户相关指标
user_registrations_total = Counter(
    "amazon_tracker_user_registrations_total",
    "Total number of user registrations",
    ["tenant_id"],
    registry=registry,
)

user_logins_total = Counter(
    "amazon_tracker_user_logins_total",
    "Total number of user logins",
    ["tenant_id", "status"],
    registry=registry,
)

active_users = Gauge(
    "amazon_tracker_active_users",
    "Number of currently active users",
    ["tenant_id"],
    registry=registry,
)

# 产品相关指标
products_total = Gauge(
    "amazon_tracker_products_total",
    "Total number of products being tracked",
    ["tenant_id", "status"],
    registry=registry,
)

products_created_total = Counter(
    "amazon_tracker_products_created_total",
    "Total number of products created",
    ["tenant_id"],
    registry=registry,
)

# 爬虫相关指标
crawl_tasks_total = Counter(
    "amazon_tracker_crawl_tasks_total",
    "Total number of crawl tasks",
    ["tenant_id", "status", "trigger_type"],
    registry=registry,
)

crawl_duration_seconds = Histogram(
    "amazon_tracker_crawl_duration_seconds",
    "Time spent on crawl tasks",
    ["tenant_id", "task_type"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1200],
    registry=registry,
)

crawl_success_rate = Gauge(
    "amazon_tracker_crawl_success_rate",
    "Success rate of crawl tasks",
    ["tenant_id"],
    registry=registry,
)

data_points_collected_total = Counter(
    "amazon_tracker_data_points_collected_total",
    "Total number of data points collected",
    ["tenant_id", "data_type"],
    registry=registry,
)


# 爬虫指标集合
class CrawlerMetrics:
    """爬虫监控指标集合"""

    def __init__(self):
        self.tasks_total = crawl_tasks_total
        self.duration_seconds = crawl_duration_seconds
        self.success_rate = crawl_success_rate
        self.data_points_collected = data_points_collected_total


crawler_metrics = CrawlerMetrics()

# API相关指标
api_requests_total = Counter(
    "amazon_tracker_api_requests_total",
    "Total number of API requests",
    ["service", "method", "endpoint", "status_code"],
    registry=registry,
)

api_request_duration_seconds = Histogram(
    "amazon_tracker_api_request_duration_seconds",
    "Time spent processing API requests",
    ["service", "method", "endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 60.0],
    registry=registry,
)

api_request_size_bytes = Summary(
    "amazon_tracker_api_request_size_bytes",
    "Size of API requests",
    ["service", "endpoint"],
    registry=registry,
)

api_response_size_bytes = Summary(
    "amazon_tracker_api_response_size_bytes",
    "Size of API responses",
    ["service", "endpoint"],
    registry=registry,
)

# 数据库相关指标
db_connections_active = Gauge(
    "amazon_tracker_db_connections_active",
    "Number of active database connections",
    registry=registry,
)

db_query_duration_seconds = Histogram(
    "amazon_tracker_db_query_duration_seconds",
    "Time spent on database queries",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
    registry=registry,
)

db_queries_total = Counter(
    "amazon_tracker_db_queries_total",
    "Total number of database queries",
    ["operation", "table", "status"],
    registry=registry,
)

# 缓存相关指标
cache_hits_total = Counter(
    "amazon_tracker_cache_hits_total",
    "Total number of cache hits",
    ["cache_type"],
    registry=registry,
)

cache_misses_total = Counter(
    "amazon_tracker_cache_misses_total",
    "Total number of cache misses",
    ["cache_type"],
    registry=registry,
)

cache_operations_duration_seconds = Histogram(
    "amazon_tracker_cache_operations_duration_seconds",
    "Time spent on cache operations",
    ["cache_type", "operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
    registry=registry,
)

# 队列相关指标
queue_size = Gauge(
    "amazon_tracker_queue_size",
    "Number of items in queues",
    ["queue_name"],
    registry=registry,
)

queue_processing_duration_seconds = Histogram(
    "amazon_tracker_queue_processing_duration_seconds",
    "Time spent processing queue items",
    ["queue_name", "task_type"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1200, 1800],
    registry=registry,
)

queue_items_processed_total = Counter(
    "amazon_tracker_queue_items_processed_total",
    "Total number of queue items processed",
    ["queue_name", "task_type", "status"],
    registry=registry,
)

# AI分析相关指标
ai_analysis_requests_total = Counter(
    "amazon_tracker_ai_analysis_requests_total",
    "Total number of AI analysis requests",
    ["tenant_id", "analysis_type"],
    registry=registry,
)

ai_analysis_duration_seconds = Histogram(
    "amazon_tracker_ai_analysis_duration_seconds",
    "Time spent on AI analysis",
    ["analysis_type"],
    buckets=[5, 10, 30, 60, 120, 300, 600, 1200],
    registry=registry,
)

ai_tokens_used_total = Counter(
    "amazon_tracker_ai_tokens_used_total",
    "Total number of AI tokens used",
    ["tenant_id", "model", "token_type"],
    registry=registry,
)

# 报告相关指标
reports_generated_total = Counter(
    "amazon_tracker_reports_generated_total",
    "Total number of reports generated",
    ["tenant_id", "report_type", "format"],
    registry=registry,
)

report_generation_duration_seconds = Histogram(
    "amazon_tracker_report_generation_duration_seconds",
    "Time spent generating reports",
    ["report_type", "format"],
    buckets=[10, 30, 60, 120, 300, 600, 1200, 1800],
    registry=registry,
)

# 系统资源指标
memory_usage_bytes = Gauge(
    "amazon_tracker_memory_usage_bytes",
    "Memory usage in bytes",
    ["service"],
    registry=registry,
)

cpu_usage_percent = Gauge(
    "amazon_tracker_cpu_usage_percent",
    "CPU usage percentage",
    ["service"],
    registry=registry,
)


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self.registry = registry

    def record_user_registration(self, tenant_id: str):
        """记录用户注册"""
        user_registrations_total.labels(tenant_id=tenant_id).inc()

    def record_user_login(self, tenant_id: str, success: bool):
        """记录用户登录"""
        status = "success" if success else "failure"
        user_logins_total.labels(tenant_id=tenant_id, status=status).inc()

    def update_active_users(self, tenant_id: str, count: int):
        """更新活跃用户数"""
        active_users.labels(tenant_id=tenant_id).set(count)

    def record_product_created(self, tenant_id: str):
        """记录产品创建"""
        products_created_total.labels(tenant_id=tenant_id).inc()

    def update_product_count(self, tenant_id: str, status: str, count: int):
        """更新产品数量"""
        products_total.labels(tenant_id=tenant_id, status=status).set(count)

    def record_crawl_task(
        self, tenant_id: str, status: str, trigger_type: str, duration: float = None
    ):
        """记录爬虫任务"""
        crawl_tasks_total.labels(
            tenant_id=tenant_id, status=status, trigger_type=trigger_type
        ).inc()

        if duration is not None:
            crawl_duration_seconds.labels(
                tenant_id=tenant_id, task_type=trigger_type
            ).observe(duration)

    def update_crawl_success_rate(self, tenant_id: str, rate: float):
        """更新爬虫成功率"""
        crawl_success_rate.labels(tenant_id=tenant_id).set(rate)

    def record_data_point(self, tenant_id: str, data_type: str):
        """记录数据点收集"""
        data_points_collected_total.labels(
            tenant_id=tenant_id, data_type=data_type
        ).inc()

    def record_api_request(
        self,
        service: str,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        request_size: int = None,
        response_size: int = None,
    ):
        """记录API请求"""
        api_requests_total.labels(
            service=service,
            method=method,
            endpoint=endpoint,
            status_code=str(status_code),
        ).inc()

        api_request_duration_seconds.labels(
            service=service, method=method, endpoint=endpoint
        ).observe(duration)

        if request_size is not None:
            api_request_size_bytes.labels(service=service, endpoint=endpoint).observe(
                request_size
            )

        if response_size is not None:
            api_response_size_bytes.labels(service=service, endpoint=endpoint).observe(
                response_size
            )

    def record_db_query(
        self, operation: str, table: str, duration: float, success: bool
    ):
        """记录数据库查询"""
        status = "success" if success else "error"
        db_queries_total.labels(operation=operation, table=table, status=status).inc()

        db_query_duration_seconds.labels(operation=operation, table=table).observe(
            duration
        )

    def update_db_connections(self, count: int):
        """更新数据库连接数"""
        db_connections_active.set(count)

    def record_cache_operation(
        self, cache_type: str, operation: str, hit: bool, duration: float
    ):
        """记录缓存操作"""
        if hit:
            cache_hits_total.labels(cache_type=cache_type).inc()
        else:
            cache_misses_total.labels(cache_type=cache_type).inc()

        cache_operations_duration_seconds.labels(
            cache_type=cache_type, operation=operation
        ).observe(duration)

    def update_queue_size(self, queue_name: str, size: int):
        """更新队列大小"""
        queue_size.labels(queue_name=queue_name).set(size)

    def record_queue_processing(
        self, queue_name: str, task_type: str, duration: float, success: bool
    ):
        """记录队列处理"""
        status = "success" if success else "error"
        queue_items_processed_total.labels(
            queue_name=queue_name, task_type=task_type, status=status
        ).inc()

        queue_processing_duration_seconds.labels(
            queue_name=queue_name, task_type=task_type
        ).observe(duration)

    def record_ai_analysis(self, tenant_id: str, analysis_type: str, duration: float):
        """记录AI分析"""
        ai_analysis_requests_total.labels(
            tenant_id=tenant_id, analysis_type=analysis_type
        ).inc()

        ai_analysis_duration_seconds.labels(analysis_type=analysis_type).observe(
            duration
        )

    def record_ai_tokens(self, tenant_id: str, model: str, token_type: str, count: int):
        """记录AI token使用"""
        ai_tokens_used_total.labels(
            tenant_id=tenant_id, model=model, token_type=token_type
        ).inc(count)

    def record_report_generation(
        self, tenant_id: str, report_type: str, format: str, duration: float
    ):
        """记录报告生成"""
        reports_generated_total.labels(
            tenant_id=tenant_id, report_type=report_type, format=format
        ).inc()

        report_generation_duration_seconds.labels(
            report_type=report_type, format=format
        ).observe(duration)

    def update_system_metrics(
        self, service: str, memory_bytes: int, cpu_percent: float
    ):
        """更新系统资源指标"""
        memory_usage_bytes.labels(service=service).set(memory_bytes)
        cpu_usage_percent.labels(service=service).set(cpu_percent)

    def get_metrics(self) -> str:
        """获取所有指标的Prometheus格式输出"""
        return generate_latest(self.registry)


# 全局指标收集器实例
metrics = MetricsCollector()


def track_api_calls(service: str):
    """API调用跟踪装饰器"""

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = 200
            error = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                status_code = getattr(e, "status_code", 500)
                raise
            finally:
                duration = time.time() - start_time
                endpoint = func.__name__
                method = "GET"  # 可以从request中获取

                metrics.record_api_request(
                    service=service,
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                    duration=duration,
                )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = 200
            error = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                status_code = getattr(e, "status_code", 500)
                raise
            finally:
                duration = time.time() - start_time
                endpoint = func.__name__
                method = "GET"  # 可以从request中获取

                metrics.record_api_request(
                    service=service,
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                    duration=duration,
                )

        # 检查函数是否为协程
        if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def track_db_queries(operation: str, table: str):
    """数据库查询跟踪装饰器"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True

            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                metrics.record_db_query(operation, table, duration, success)

        return wrapper

    return decorator


def track_cache_operations(cache_type: str, operation: str):
    """缓存操作跟踪装饰器"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            hit = False

            try:
                result = func(*args, **kwargs)
                # 假设结果不为None表示缓存命中
                hit = result is not None
                return result
            finally:
                duration = time.time() - start_time
                metrics.record_cache_operation(cache_type, operation, hit, duration)

        return wrapper

    return decorator
