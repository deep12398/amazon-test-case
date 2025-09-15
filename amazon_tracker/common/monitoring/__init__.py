"""监控模块"""

from fastapi import FastAPI, Response

from .metrics import MetricsCollector, metrics
from .middleware import PrometheusMiddleware


def setup_monitoring(app: FastAPI, service_name: str = "unknown"):
    """设置应用监控

    Args:
        app: FastAPI应用实例
        service_name: 服务名称
    """
    # 添加Prometheus监控中间件
    app.add_middleware(PrometheusMiddleware, service_name=service_name)

    # 添加metrics端点
    @app.get("/metrics")
    async def get_metrics():
        """Prometheus metrics端点"""
        return Response(content=metrics.get_metrics(), media_type="text/plain")


__all__ = ["metrics", "MetricsCollector", "PrometheusMiddleware", "setup_monitoring"]
