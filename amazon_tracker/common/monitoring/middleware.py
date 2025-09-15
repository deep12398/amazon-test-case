"""Prometheus监控中间件"""

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .metrics import metrics


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Prometheus指标收集中间件"""

    def __init__(self, app, service_name: str = "unknown"):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并收集指标"""
        start_time = time.time()

        # 获取请求信息
        method = request.method
        path = request.url.path

        # 处理请求
        response = None
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as e:
            # 处理异常
            status_code = getattr(e, "status_code", 500)
            raise
        finally:
            # 计算处理时间
            duration = time.time() - start_time

            # 记录API请求指标
            metrics.record_api_request(
                service=self.service_name,
                method=method,
                endpoint=path,
                status_code=status_code,
                duration=duration,
                request_size=self._get_content_length(request),
                response_size=self._get_response_size(response) if response else 0,
            )

    def _get_content_length(self, request: Request) -> int:
        """获取请求内容长度"""
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                return int(content_length)
            except ValueError:
                pass
        return 0

    def _get_response_size(self, response: Response) -> int:
        """获取响应内容长度"""
        if hasattr(response, "headers"):
            content_length = response.headers.get("content-length")
            if content_length:
                try:
                    return int(content_length)
                except ValueError:
                    pass
        return 0
