"""爬虫服务主应用"""

import logging
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(project_root / ".env.local")
load_dotenv(project_root / ".env")

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer

from amazon_tracker.common.auth.jwt_auth import get_current_user
from amazon_tracker.common.config import get_settings

from .api.v1 import monitoring, products, schedules, tasks

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Amazon Tracker - Crawler Service",
    description="Amazon产品爬虫服务API",
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

# 包含路由
app.include_router(products.router, prefix="/api/v1", dependencies=[Depends(security)])

app.include_router(tasks.router, prefix="/api/v1", dependencies=[Depends(security)])

app.include_router(schedules.router, prefix="/api/v1", dependencies=[Depends(security)])

app.include_router(
    monitoring.router,
    prefix="/api/v1",
    # 监控端点不需要全局安全依赖，因为有些端点是公开的
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "Amazon Tracker - Crawler Service",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "crawler-service"}


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
        port=8002,
        reload=True,
        log_level="info",  # 爬虫服务端口
    )
