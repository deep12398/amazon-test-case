#!/usr/bin/env python3
"""查找免费的Amazon Actor"""

import asyncio
import os
from pathlib import Path

from apify_client import ApifyClient
from dotenv import load_dotenv

# 加载环境变量
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env.local")


async def find_free_amazon_actors():
    """查找免费的Amazon Actor"""

    token = os.getenv("APIFY_API_TOKEN")
    client = ApifyClient(token)

    print("🔍 搜索免费Amazon Actor...")
    print("=" * 50)

    try:
        # 搜索Amazon相关Actor
        actors = client.store().list_actors(search="amazon", limit=30)

        for actor in actors["data"]["items"]:
            name = actor.get("name", "")
            username = actor.get("username", "")
            title = actor.get("title", "")
            pricing = actor.get("pricing", {})

            if "amazon" in name.lower() or "amazon" in title.lower():
                # 检查是否免费
                is_free = (
                    pricing.get("monthlyUsageBase", 0) == 0
                    or "free" in str(pricing).lower()
                    or actor.get("isFree", False)
                )

                print(f"📦 {username}/{name}")
                print(f"   标题: {title}")
                print(f"   定价: {pricing}")
                print(f"   免费: {'✅' if is_free else '❌'}")

                # 测试可访问性
                try:
                    actor_detail = client.actor(f"{username}~{name}").get()
                    print("   访问: ✅")
                except Exception as e:
                    print(f"   访问: ❌ ({str(e)[:50]}...)")

                print("-" * 30)

    except Exception as e:
        print(f"❌ 搜索失败: {e}")


if __name__ == "__main__":
    asyncio.run(find_free_amazon_actors())
