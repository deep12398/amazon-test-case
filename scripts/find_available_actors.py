#!/usr/bin/env python3
"""查找可用的Amazon爬虫Actor"""

import asyncio
import os
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

# 加载环境变量
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env.local")


async def find_amazon_actors():
    """查找可用的Amazon爬虫"""

    token = os.getenv("APIFY_API_TOKEN")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            print("🔍 搜索Amazon相关的公开Actor...")

            # 搜索Amazon相关的Actor
            search_params = {"q": "amazon", "category": "ECOMMERCE", "limit": 20}

            async with session.get(
                "https://api.apify.com/v2/store", headers=headers, params=search_params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    actors = data.get("data", {}).get("items", [])

                    print(f"找到 {len(actors)} 个相关Actor:")
                    for actor in actors:
                        name = actor.get("name", "")
                        username = actor.get("username", "")
                        title = actor.get("title", "")
                        if "amazon" in name.lower() or "amazon" in title.lower():
                            print(f"  - {username}/{name} - {title}")

                            # 测试这个actor是否可以访问
                            actor_url = (
                                f"https://api.apify.com/v2/acts/{username}~{name}"
                            )
                            async with session.get(
                                actor_url, headers=headers
                            ) as actor_response:
                                status = "✅" if actor_response.status == 200 else "❌"
                                print(f"    状态: {status} ({actor_response.status})")
                else:
                    print(f"搜索失败: {response.status}")
                    print(await response.text())

    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(find_amazon_actors())
