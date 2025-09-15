"""用户服务主应用"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ...common.database import close_db, init_db
from ...common.logging import configure_logging
from ...common.monitoring import setup_monitoring
from ...common.tracing import setup_tracing, setup_tracing_middleware
from .api.v1 import auth, tenants, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("用户服务启动中...")

    # 配置日志
    configure_logging("user-service")


    init_db()
    yield
    # 关闭时执行
    print("用户服务关闭中...")
    close_db()


# 创建FastAPI应用
app = FastAPI(
    title="Amazon Tracker - 用户服务",
    description="用户认证、授权和管理服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该设置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 设置分布式追踪
setup_tracing(
    service_name="user-service", jaeger_endpoint="localhost:6832", console_export=True
)

# 设置监控
setup_monitoring(app, service_name="user-service")

# 设置追踪中间件
setup_tracing_middleware(app, service_name="user-service")

# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/v1/users", tags=["用户"])
app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["租户"])


@app.get("/")
async def root():
    """根路径"""
    return {"service": "用户服务", "version": "1.0.0", "status": "running"}
