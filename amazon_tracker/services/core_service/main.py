"""核心业务服务主应用"""

import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer

from amazon_tracker.common.auth.jwt_auth import get_current_user
from amazon_tracker.common.config import get_settings
from amazon_tracker.common.logging import configure_logging
from amazon_tracker.common.monitoring import setup_monitoring
from amazon_tracker.common.tracing import setup_tracing, setup_tracing_middleware

from .api.v1 import (
    alerts,
    bulk_import,
    market_trends,
    products,
    reports,
)

# 配置日志
configure_logging("core-service")

logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Amazon Tracker - Core Service",
    description="Amazon产品追踪核心业务服务API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 安全认证
security = HTTPBearer()

# 设置分布式追踪
setup_tracing(
    service_name="core-service", jaeger_endpoint="localhost:6832", console_export=True
)

# 设置监控
setup_monitoring(app, service_name="core-service")

# 设置追踪中间件
setup_tracing_middleware(app, service_name="core-service")

# 包含路由
app.include_router(products.router, prefix="/api/v1", dependencies=[Depends(security)])

app.include_router(alerts.router, prefix="/api/v1", dependencies=[Depends(security)])

app.include_router(
    market_trends.router, prefix="/api/v1", dependencies=[Depends(security)]
)

app.include_router(reports.router, prefix="/api/v1", dependencies=[Depends(security)])

app.include_router(
    bulk_import.router, prefix="/api/v1", dependencies=[Depends(security)]
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "Amazon Tracker - Core Service",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/api/v1/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "user_id": current_user["user_id"],
        "tenant_id": current_user["tenant_id"],
        "permissions": current_user.get("permissions", []),
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info",  # 核心服务端口
    )
