"""分布式追踪模块"""

from fastapi import FastAPI


def setup_tracing(
    service_name: str, jaeger_endpoint: str = None, console_export: bool = False
):
    """设置分布式追踪

    Args:
        service_name: 服务名称
        jaeger_endpoint: Jaeger端点
        console_export: 是否输出到控制台
    """
    # 目前简化实现，仅打印配置信息
    print(
        f"设置追踪: {service_name}, Jaeger: {jaeger_endpoint}, Console: {console_export}"
    )


def setup_tracing_middleware(app: FastAPI, service_name: str):
    """设置追踪中间件

    Args:
        app: FastAPI应用实例
        service_name: 服务名称
    """
    # 目前简化实现
    print(f"设置追踪中间件: {service_name}")


__all__ = ["setup_tracing", "setup_tracing_middleware"]
