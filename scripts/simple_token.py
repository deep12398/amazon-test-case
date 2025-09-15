#!/usr/bin/env python3
"""生成简单测试令牌"""

import base64
import json
from datetime import datetime, timedelta


def create_simple_token():
    """创建简单的测试令牌"""

    # 模拟JWT payload
    payload = {
        "user_id": 1,
        "email": "test@crawler.com",
        "tenant_id": "demo-tenant",
        "is_super_admin": False,
        "exp": int((datetime.utcnow() + timedelta(days=30)).timestamp()),
    }

    # 简单的base64编码（不是真正的JWT，但可以用于测试）
    token_data = json.dumps(payload)
    token = base64.b64encode(token_data.encode()).decode()

    print("🔑 生成的测试令牌:")
    print(f"Bearer {token}")
    print(f"\n令牌数据: {payload}")

    return token


if __name__ == "__main__":
    create_simple_token()
