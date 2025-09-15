#!/usr/bin/env python3
"""简单的Apify API测试脚本"""

import asyncio
import json
import os
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent

# 加载环境变量
env_file = project_root / ".env.local"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ 已加载环境配置: {env_file}")


async def test_apify_direct():
    """直接测试Apify API"""

    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        print("❌ 未找到APIFY_API_TOKEN")
        return

    print(f"🔧 使用API Token: {api_token[:20]}...")

    # 尝试几个不同的Amazon爬虫
    actors_to_test = [
        {
            "id": "BG3WDrGdteHgZgbPK",
            "name": "Amazon Product Scraper",
            "input": {
                "categoryOrProductUrls": ["https://www.amazon.com/dp/B09XS7JWHH"],
                "country": "US",
                "liveView": False,
            },
        },
        {
            "id": "ZhSGsaq9MHRnWtStl",
            "name": "Amazon ASINs Scraper",
            "input": {"asins": ["B09XS7JWHH"], "country": "US"},
        },
        {
            "id": "XVDTQc4a7MDTqSTMJ",
            "name": "Amazon Scraper",
            "input": {
                "categoryUrls": ["https://www.amazon.com/s?k=B09XS7JWHH"],
                "country": "US",
            },
        },
    ]

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        for actor in actors_to_test:
            print(f"\n🚀 测试 {actor['name']} (ID: {actor['id']})")

            try:
                # 启动Actor
                url = f"https://api.apify.com/v2/acts/{actor['id']}/runs"
                payload = {
                    "input": actor["input"],
                    "timeout": 300,
                    "memory": 1024,
                }

                async with session.post(url, json=payload, headers=headers) as response:
                    print(f"   状态码: {response.status}")

                    if response.status == 201:
                        run_data = await response.json()
                        run_id = run_data["data"]["id"]
                        print(f"   ✅ 成功启动运行: {run_id}")

                        # 等待一段时间看结果
                        await asyncio.sleep(10)

                        # 检查运行状态
                        status_url = f"https://api.apify.com/v2/actor-runs/{run_id}"
                        async with session.get(
                            status_url, headers=headers
                        ) as status_resp:
                            if status_resp.status == 200:
                                status_data = await status_resp.json()
                                status = status_data["data"]["status"]
                                print(f"   状态: {status}")

                                if status == "SUCCEEDED":
                                    # 获取数据
                                    dataset_id = status_data["data"].get(
                                        "defaultDatasetId"
                                    )
                                    if dataset_id:
                                        data_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?limit=1"
                                        async with session.get(
                                            data_url, headers=headers
                                        ) as data_resp:
                                            if data_resp.status == 200:
                                                data = await data_resp.json()
                                                print(f"   📦 获得 {len(data)} 条数据")
                                                if data:
                                                    print(
                                                        f"   示例数据: {list(data[0].keys())[:10]}"
                                                    )
                                                    return (
                                                        actor["id"],
                                                        data[0],
                                                    )  # 返回成功的actor和数据

                    else:
                        error_text = await response.text()
                        print(f"   ❌ 启动失败: {error_text[:200]}...")

            except Exception as e:
                print(f"   ❌ 错误: {e}")

    return None, None


if __name__ == "__main__":
    result = asyncio.run(test_apify_direct())
    if result[0]:
        print(f"\n🎉 找到可用的Actor: {result[0]}")
        print("示例数据结构:")
        print(json.dumps(result[1], indent=2, ensure_ascii=False)[:500] + "...")
    else:
        print("\n❌ 没有找到可用的Actor")
