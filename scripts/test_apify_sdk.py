#!/usr/bin/env python3
"""测试Apify SDK集成"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env.local")
load_dotenv(project_root / ".env")

from amazon_tracker.common.crawlers.apify_client import ApifyAmazonScraper


async def test_asin_scraper():
    """测试ASIN爬虫功能"""

    print("🔧 测试Apify SDK集成")
    print("=" * 50)

    try:
        # 初始化爬虫
        scraper = ApifyAmazonScraper()

        # 测试输入数据 - 一些热门蓝牙耳机的ASIN
        test_input = {
            "asins": ["B09JQMJHXY", "B08PZHYWJS"]  # Sony WH-1000XM4, Bose QuietComfort
        }

        print("📤 测试ASIN爬取...")
        print(f"   输入ASIN: {test_input['asins']}")

        # 执行爬取
        result = await scraper.crawl(test_input)

        if result.success:
            print("   ✅ 爬取成功!")
            print(f"   爬取到 {result.data.get('total_items', 0)} 个产品")

            # 显示产品信息
            products = result.data.get("products", [])
            for i, product in enumerate(products[:3], 1):  # 只显示前3个
                print(f"\n   产品 {i}:")
                print(f"      ASIN: {product.get('asin')}")
                print(f"      标题: {product.get('title', 'N/A')[:60]}...")
                print(f"      价格: ${product.get('price', 'N/A')}")
                print(f"      评分: {product.get('rating', 'N/A')}/5")
                print(f"      评价数: {product.get('review_count', 'N/A')}")

            # 显示元数据
            print("\n   运行信息:")
            print(f"      运行ID: {result.metadata.get('run_id')}")
            print(f"      状态: {result.metadata.get('status')}")
            print(f"      开始时间: {result.metadata.get('started_at')}")
            print(f"      结束时间: {result.metadata.get('finished_at')}")

        else:
            print(f"   ❌ 爬取失败: {result.error}")

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback

        traceback.print_exc()


async def test_health_check():
    """测试健康检查"""
    print("\n🩺 测试健康检查...")

    try:
        scraper = ApifyAmazonScraper()
        is_healthy = await scraper.health_check()

        if is_healthy:
            print("   ✅ Apify服务正常")
        else:
            print("   ❌ Apify服务异常")

    except Exception as e:
        print(f"   ❌ 健康检查失败: {e}")


if __name__ == "__main__":

    async def main():
        await test_health_check()
        await test_asin_scraper()

    asyncio.run(main())
