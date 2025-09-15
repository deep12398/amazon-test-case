#!/usr/bin/env python3
"""简单的Demo数据导入脚本 - 通过API批量导入"""

import asyncio
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
env_files = [
    project_root / ".env.local",
    project_root / ".env",
]

for env_file in env_files:
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ 已加载环境配置: {env_file}")
        break

from amazon_tracker.common.crawlers.apify_client import ApifyAmazonScraper


class SimpleDemoImporter:
    """简单的Demo数据导入器"""

    def __init__(self):
        # 预选的蓝牙耳机产品ASIN列表（10个热门产品）
        self.demo_products = [
            {
                "asin": "B09XS7JWHH",
                "name": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
                "estimated_price": 300,
            },
            {
                "asin": "B0BDHWDR12",
                "name": "Apple AirPods Pro (2nd Generation)",
                "estimated_price": 250,
            },
            {
                "asin": "B098FKXT8L",
                "name": "Bose QuietComfort 45 Wireless Bluetooth Headphones",
                "estimated_price": 280,
            },
            {
                "asin": "B08WM3LMJF",
                "name": "JBL Tune 510BT Wireless On-Ear Headphones",
                "estimated_price": 40,
            },
            {
                "asin": "B07NM3RSRQ",
                "name": "Anker Soundcore Life Q20 Hybrid Active Noise Cancelling Headphones",
                "estimated_price": 60,
            },
            {
                "asin": "B075G56CDY",
                "name": "Beats Studio3 Wireless Noise Cancelling Over-Ear Headphones",
                "estimated_price": 200,
            },
            {
                "asin": "B0B8QZ9FYB",
                "name": "Sennheiser Momentum 4 Wireless Headphones",
                "estimated_price": 350,
            },
            {
                "asin": "B07RGZ5NKS",
                "name": "TOZO T6 True Wireless Earbuds",
                "estimated_price": 30,
            },
            {
                "asin": "B0B2SH4CN6",
                "name": "Samsung Galaxy Buds2 Pro True Wireless Bluetooth Earbuds",
                "estimated_price": 150,
            },
            {
                "asin": "B07Q2T2CKG",
                "name": "Bose Noise Cancelling Wireless Bluetooth Headphones 700",
                "estimated_price": 320,
            },
        ]

    async def test_apify_connection(self):
        """测试Apify连接和爬取功能"""
        print("🔧 测试Apify连接...")

        try:
            # 使用正确的Amazon Product Scraper
            config = {"actor_id": "BG3WDrGdteHgZgbPK"}
            scraper = ApifyAmazonScraper(config)

            # 测试单个产品爬取
            test_asin = "B09XS7JWHH"  # Sony WH-1000XM5
            print(f"🔄 测试爬取ASIN: {test_asin}")

            result = await scraper.scrape_single_product(test_asin, country="US")

            if result.success:
                products = result.data.get("products", [])
                if products:
                    product = products[0]
                    print("✅ 爬取成功!")
                    print(f"   标题: {product.get('title', 'N/A')[:50]}...")
                    print(f"   价格: ${product.get('price', 'N/A')}")
                    print(f"   评分: {product.get('rating', 'N/A')}")
                    print(f"   评论数: {product.get('review_count', 'N/A')}")
                    print(f"   BSR排名: {product.get('rank', 'N/A')}")
                    return True
                else:
                    print("❌ 未获取到产品数据")
                    return False
            else:
                print(f"❌ 爬取失败: {result.error}")
                return False

        except Exception as e:
            print(f"❌ 连接测试失败: {e}")
            return False

    async def crawl_all_demo_products(self):
        """爬取所有Demo产品数据"""
        print("🚀 开始爬取Demo产品数据...")
        print(f"📋 计划爬取 {len(self.demo_products)} 个蓝牙耳机产品")

        config = {"actor_id": "BG3WDrGdteHgZgbPK"}
        scraper = ApifyAmazonScraper(config)
        results = []

        for i, product_info in enumerate(self.demo_products, 1):
            print(
                f"\n📦 [{i}/{len(self.demo_products)}] 爬取: {product_info['name'][:40]}..."
            )

            try:
                # 爬取产品数据
                result = await scraper.scrape_single_product(
                    product_info["asin"], country="US"
                )

                if result.success:
                    products = result.data.get("products", [])
                    if products:
                        product_data = products[0]

                        # 整理数据
                        clean_data = {
                            "asin": product_info["asin"],
                            "title": product_data.get("title", product_info["name"]),
                            "brand": product_data.get("brand", "Unknown"),
                            "price": product_data.get("price"),
                            "rating": product_data.get("rating"),
                            "review_count": product_data.get("review_count", 0),
                            "rank": product_data.get("rank"),
                            "category": "bluetooth-headphones",
                            "availability": product_data.get("availability", "Unknown"),
                            "image_url": product_data.get("image_url"),
                            "features": product_data.get("features", []),
                            "estimated_price": product_info["estimated_price"],
                            "crawl_success": True,
                            "crawl_time": time.time(),
                        }

                        results.append(clean_data)

                        print(
                            f"✅ 爬取成功: {clean_data['brand']} - ${clean_data['price']} - ⭐{clean_data['rating']}"
                        )

                    else:
                        print(f"❌ 未获取到产品数据: {product_info['asin']}")
                        results.append(
                            {
                                "asin": product_info["asin"],
                                "name": product_info["name"],
                                "crawl_success": False,
                                "error": "No product data returned",
                            }
                        )
                else:
                    print(f"❌ 爬取失败: {product_info['asin']} - {result.error}")
                    results.append(
                        {
                            "asin": product_info["asin"],
                            "name": product_info["name"],
                            "crawl_success": False,
                            "error": result.error,
                        }
                    )

                # 添加延迟避免被限流
                print("   ⏳ 等待2秒...")
                await asyncio.sleep(2)

            except Exception as e:
                print(f"❌ 处理ASIN {product_info['asin']} 时发生错误: {e}")
                results.append(
                    {
                        "asin": product_info["asin"],
                        "name": product_info["name"],
                        "crawl_success": False,
                        "error": str(e),
                    }
                )

        return results

    def save_results_to_file(self, results, filename="demo_products_data.json"):
        """保存结果到文件"""

        output_file = project_root / filename

        # 统计信息
        successful = [r for r in results if r.get("crawl_success")]
        failed = [r for r in results if not r.get("crawl_success")]

        report = {
            "summary": {
                "total_products": len(results),
                "successful_crawls": len(successful),
                "failed_crawls": len(failed),
                "success_rate": len(successful) / len(results) * 100,
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "products": results,
        }

        # 保存到JSON文件
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📄 结果已保存到: {output_file}")
        return report

    def print_summary(self, report):
        """打印汇总报告"""

        summary = report["summary"]
        products = report["products"]

        print("\n🎉 Demo数据爬取完成!")
        print(f"📊 总计: {summary['total_products']} 个产品")
        print(f"✅ 成功: {summary['successful_crawls']} 个")
        print(f"❌ 失败: {summary['failed_crawls']} 个")
        print(f"📈 成功率: {summary['success_rate']:.1f}%")

        print("\n📦 成功爬取的产品:")
        successful_products = [p for p in products if p.get("crawl_success")]

        for product in successful_products:
            print(
                f"  • {product.get('brand', 'Unknown')} - {product.get('title', 'Unknown')[:40]}..."
            )
            print(
                f"    ASIN: {product.get('asin')} | 价格: ${product.get('price', 'N/A')} | 评分: {product.get('rating', 'N/A')}"
            )

        if summary["failed_crawls"] > 0:
            print("\n❌ 失败的产品:")
            failed_products = [p for p in products if not p.get("crawl_success")]
            for product in failed_products:
                print(
                    f"  • {product.get('name', product.get('asin'))}: {product.get('error', 'Unknown error')}"
                )


async def main():
    """主函数"""

    print("🚀 Amazon蓝牙耳机Demo数据爬取工具")
    print("=" * 50)

    importer = SimpleDemoImporter()

    # 测试连接
    if not await importer.test_apify_connection():
        print("❌ Apify连接测试失败，请检查API密钥配置")
        return

    print("\n" + "=" * 50)

    # 爬取所有产品
    results = await importer.crawl_all_demo_products()

    # 保存结果
    report = importer.save_results_to_file(results)

    # 打印汇总
    importer.print_summary(report)

    print("\n💡 提示:")
    print("   - 可以使用这些数据作为Demo演示")
    print("   - 数据文件: demo_products_data.json")
    print("   - 可以通过API批量导入这些产品到系统中")


if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容）
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 运行主函数
    asyncio.run(main())
