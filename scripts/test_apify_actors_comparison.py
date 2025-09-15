#!/usr/bin/env python3
"""测试不同的Apify Actor以找到最适合的爬虫"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(project_root / ".env.local")
load_dotenv(project_root / ".env")

from apify_client import ApifyClient


def test_actor_1():
    """测试第一个Actor: 7KgyOHHEiPEcilZXM (Amazon Scraper)"""
    print("\n" + "=" * 60)
    print("🔍 测试 Actor 1: 7KgyOHHEiPEcilZXM (Amazon Scraper)")
    print("=" * 60)
    
    try:
        # 初始化客户端
        client = ApifyClient(os.getenv("APIFY_API_TOKEN"))
        
        # 准备输入
        run_input = {
            "urls": [
                "https://www.amazon.com/dp/B09JQMJHXY",  # AirPods Pro
                "https://www.amazon.com/dp/B08PZHYWJS",  # AirPods Max
            ]
        }
        
        print("📤 发送请求...")
        print(f"   URLs: {run_input['urls']}")
        
        # 运行Actor
        run = client.actor("7KgyOHHEiPEcilZXM").call(run_input=run_input)
        
        print(f"✅ Actor运行完成，Run ID: {run['id']}")
        print(f"   状态: {run.get('status')}")
        
        # 获取结果
        print("\n📊 获取的数据字段：")
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if items:
            for i, item in enumerate(items, 1):
                print(f"\n产品 {i}: {item.get('title', 'N/A')[:50]}...")
                print(f"  ASIN: {item.get('asin', 'N/A')}")
                print(f"  价格: {item.get('price', 'N/A')}")
                print(f"  Buy Box价格: {item.get('buyBoxPrice', 'N/A')}")
                print(f"  BSR: {item.get('bestSellersRank', 'N/A')}")
                print(f"  评分: {item.get('stars', 'N/A')}")
                print(f"  评论数: {item.get('reviewsCount', 'N/A')}")
                print(f"  库存: {item.get('availability', 'N/A')}")
                
                # 显示所有可用字段
                print(f"\n  所有字段: {list(item.keys())}")
                
                # 保存一个样本到文件
                if i == 1:
                    with open("actor1_sample.json", "w", encoding="utf-8") as f:
                        json.dump(item, f, indent=2, ensure_ascii=False)
                    print("\n  💾 样本数据已保存到 actor1_sample.json")
        else:
            print("❌ 没有获取到数据")
            
        return items
        
    except Exception as e:
        print(f"❌ Actor 1 测试失败: {e}")
        return None


def test_actor_2():
    """测试第二个Actor: junglee~amazon-product-scraper"""
    print("\n" + "=" * 60)
    print("🔍 测试 Actor 2: junglee~amazon-product-scraper")
    print("=" * 60)
    
    try:
        # 初始化客户端
        client = ApifyClient(os.getenv("APIFY_API_TOKEN"))
        
        # 准备输入 - 这个Actor可能需要不同的输入格式
        run_input = {
            "productUrls": [
                "https://www.amazon.com/dp/B09JQMJHXY",  # AirPods Pro
                "https://www.amazon.com/dp/B08PZHYWJS",  # AirPods Max
            ],
            "maxProducts": 10,
            "scrapeReviews": False,
            "scrapeDescription": True,
            "scrapeFeatures": True,
        }
        
        print("📤 发送请求...")
        print(f"   URLs: {run_input['productUrls']}")
        
        # 运行Actor
        run = client.actor("junglee~amazon-product-scraper").call(run_input=run_input)
        
        print(f"✅ Actor运行完成，Run ID: {run['id']}")
        print(f"   状态: {run.get('status')}")
        
        # 获取结果
        print("\n📊 获取的数据字段：")
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if items:
            for i, item in enumerate(items, 1):
                print(f"\n产品 {i}: {item.get('title', 'N/A')[:50]}...")
                print(f"  ASIN: {item.get('asin', 'N/A')}")
                print(f"  价格: {item.get('price', 'N/A')}")
                print(f"  Buy Box价格: {item.get('buyBoxPrice', 'N/A')}")
                print(f"  BSR: {item.get('bestSellersRank', 'N/A')}")
                print(f"  评分: {item.get('stars', 'N/A')}")
                print(f"  评论数: {item.get('reviewsCount', 'N/A')}")
                print(f"  库存: {item.get('availability', 'N/A')}")
                
                # 显示所有可用字段
                print(f"\n  所有字段: {list(item.keys())}")
                
                # 保存一个样本到文件
                if i == 1:
                    with open("actor2_sample.json", "w", encoding="utf-8") as f:
                        json.dump(item, f, indent=2, ensure_ascii=False)
                    print("\n  💾 样本数据已保存到 actor2_sample.json")
        else:
            print("❌ 没有获取到数据")
            
        return items
        
    except Exception as e:
        print(f"❌ Actor 2 测试失败: {e}")
        return None


def test_current_actor():
    """测试当前使用的Actor: ZhSGsaq9MHRnWtStl"""
    print("\n" + "=" * 60)
    print("🔍 测试当前Actor: ZhSGsaq9MHRnWtStl (junglee/amazon-asins-scraper)")
    print("=" * 60)
    
    try:
        # 初始化客户端
        client = ApifyClient(os.getenv("APIFY_API_TOKEN"))
        
        # 准备输入
        run_input = {
            "asins": ["B09JQMJHXY", "B08PZHYWJS"],
            "amazonDomain": "amazon.com",
            "proxyCountry": "AUTO_SELECT_PROXY_COUNTRY",
            "useCaptchaSolver": False,
        }
        
        print("📤 发送请求...")
        print(f"   ASINs: {run_input['asins']}")
        
        # 运行Actor
        run = client.actor("ZhSGsaq9MHRnWtStl").call(run_input=run_input)
        
        print(f"✅ Actor运行完成，Run ID: {run['id']}")
        print(f"   状态: {run.get('status')}")
        
        # 获取结果
        print("\n📊 获取的数据字段：")
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if items:
            for i, item in enumerate(items, 1):
                print(f"\n产品 {i}: {item.get('title', 'N/A')[:50]}...")
                print(f"  ASIN: {item.get('asin', 'N/A')}")
                print(f"  价格: {item.get('price', 'N/A')}")
                print(f"  Buy Box价格: {item.get('buyBoxPrice', 'N/A')}")
                print(f"  BSR: {item.get('bestSellersRank', 'N/A')}")
                print(f"  评分: {item.get('stars', 'N/A')}")
                print(f"  评论数: {item.get('reviewsCount', 'N/A')}")
                print(f"  库存: {item.get('availability', 'N/A')}")
                
                # 显示所有可用字段
                print(f"\n  所有字段: {list(item.keys())}")
                
                # 保存一个样本到文件
                if i == 1:
                    with open("current_actor_sample.json", "w", encoding="utf-8") as f:
                        json.dump(item, f, indent=2, ensure_ascii=False)
                    print("\n  💾 样本数据已保存到 current_actor_sample.json")
        else:
            print("❌ 没有获取到数据")
            
        return items
        
    except Exception as e:
        print(f"❌ 当前Actor测试失败: {e}")
        return None


def compare_results():
    """比较不同Actor的结果"""
    print("\n" + "=" * 60)
    print("📊 Actor对比总结")
    print("=" * 60)
    
    # 测试所有Actor
    current_results = test_current_actor()
    actor1_results = test_actor_1()
    actor2_results = test_actor_2()
    
    print("\n🎯 结果对比：")
    
    def analyze_actor(name, results):
        if not results:
            print(f"\n{name}: ❌ 无法获取数据")
            return
        
        sample = results[0] if results else {}
        has_bsr = bool(sample.get('bestSellersRank'))
        has_buy_box = bool(sample.get('buyBoxPrice'))
        has_price = bool(sample.get('price'))
        has_rating = bool(sample.get('stars') or sample.get('rating'))
        
        print(f"\n{name}:")
        print(f"  ✅ 成功获取 {len(results)} 个产品")
        print(f"  {'✅' if has_price else '❌'} 价格信息")
        print(f"  {'✅' if has_buy_box else '❌'} Buy Box价格")
        print(f"  {'✅' if has_bsr else '❌'} BSR排名")
        print(f"  {'✅' if has_rating else '❌'} 评分信息")
    
    analyze_actor("当前Actor (ZhSGsaq9MHRnWtStl)", current_results)
    analyze_actor("Actor 1 (7KgyOHHEiPEcilZXM)", actor1_results)
    analyze_actor("Actor 2 (junglee~amazon-product-scraper)", actor2_results)
    
    print("\n💡 建议：")
    print("  根据测试结果选择数据最完整的Actor")
    print("  特别关注BSR排名和Buy Box价格的获取")


if __name__ == "__main__":
    print("🚀 开始测试不同的Apify Actor...")
    print("   这将测试3个不同的Actor并比较结果")
    print("   测试可能需要几分钟时间...")
    
    compare_results()
    
    print("\n✅ 测试完成！请查看生成的JSON文件了解详细数据结构")