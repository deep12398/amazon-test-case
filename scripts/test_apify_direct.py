#!/usr/bin/env python3
"""直接测试Apify API连接"""

import asyncio
import os
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

# 加载环境变量
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env.local")
load_dotenv(project_root / ".env")


async def test_apify_connection():
    """测试Apify API连接"""

    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        print("❌ APIFY_API_TOKEN not found")
        return

    print("🔑 Apify API连接测试")
    print("=" * 40)
    print(f"Token: {token[:15]}...")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            # 测试用户信息
            print("\n📤 测试用户信息...")
            async with session.get(
                "https://api.apify.com/v2/users/me", headers=headers
            ) as response:
                print(f"   状态码: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"   用户ID: {data['data']['id']}")
                    print(f"   用户名: {data['data']['username']}")
                    print("   ✅ API认证成功!")
                else:
                    text = await response.text()
                    print(f"   ❌ 认证失败: {text}")
                    return

            # 测试可用的actors
            print("\n📤 测试Amazon scraper actors...")
            test_actors = [
                "junglee~Amazon-crawler",
                "junglee~amazon-asins-scraper",
                "junglee~free-amazon-product-scraper",
            ]

            for actor_id in test_actors:
                async with session.get(
                    f"https://api.apify.com/v2/acts/{actor_id}", headers=headers
                ) as response:
                    print(f"   {actor_id}: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print(f"      名称: {data['data']['name']}")
                        print(
                            f"      版本: {data['data']['taggedBuilds']['latest']['buildNumber']}"
                        )
                        print("      ✅ 可用")

                        # 如果找到可用的actor，尝试一个简单的运行测试
                        if actor_id == "junglee~amazon-asins-scraper":
                            print(f"\n📤 测试运行 {actor_id}...")
                            test_input = {
                                "asins": ["B09JQMJHXY", "B08PZHYWJS"],
                                "country": "US",
                            }

                            async with session.post(
                                f"https://api.apify.com/v2/acts/{actor_id}/runs",
                                headers=headers,
                                json=test_input,
                            ) as run_response:
                                print(f"      运行状态: {run_response.status}")
                                if run_response.status == 201:
                                    run_data = await run_response.json()
                                    run_id = run_data["data"]["id"]
                                    print(f"      运行ID: {run_id}")
                                    print("      ✅ Actor运行测试成功!")
                                    break
                                else:
                                    run_text = await run_response.text()
                                    print(f"      ❌ 运行失败: {run_text}")
                    else:
                        print("      ❌ 不可用")

    except Exception as e:
        print(f"❌ 连接异常: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_apify_connection())
