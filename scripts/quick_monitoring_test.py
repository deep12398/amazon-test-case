#!/usr/bin/env python3
"""
快速监控测试脚本 - 生成短期测试数据
"""

import asyncio
import random
import time

import httpx


async def generate_quick_test_data():
    """生成快速测试数据"""
    print("🚀 开始生成监控测试数据...")

    base_url = "http://localhost:9080"
    endpoints = [
        "/health",
        "/api/v1/auth/login",
        "/api/v1/users/me",
        "/api/v1/products",
        "/api/v1/products/123/data",
    ]

    async with httpx.AsyncClient(timeout=10.0) as client:
        for i in range(100):  # 生成100个请求
            endpoint = random.choice(endpoints)

            try:
                print(f"📊 请求 {i+1}/100: {endpoint}")

                headers = {
                    "Authorization": "Bearer test-token",
                    "X-API-Key": f"test-key-{random.randint(1000, 9999)}",
                    "User-Agent": "monitoring-test-client"
                }

                # 发送请求到APISIX
                response = await client.get(
                    f"{base_url}{endpoint}",
                    headers=headers,
                    follow_redirects=True
                )

                print(f"    Status: {response.status_code}")

            except Exception as e:
                print(f"    Error: {e}")

            # 控制请求频率
            await asyncio.sleep(0.5)

    print("✅ 测试数据生成完成!")


if __name__ == "__main__":
    asyncio.run(generate_quick_test_data())