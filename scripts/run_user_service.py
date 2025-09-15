"""用户服务启动脚本"""

import os
import sys
from pathlib import Path

import uvicorn

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from amazon_tracker.services.user_service.main import app

if __name__ == "__main__":
    # 设置环境变量
    os.environ.setdefault("JWT_SECRET_KEY", "your-jwt-secret-key-change-in-production")
    os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")

    # 启动用户服务
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",  # 开发环境启用热重载
    )
