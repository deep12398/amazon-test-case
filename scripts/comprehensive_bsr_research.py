#!/usr/bin/env python3
"""全面调研BSR数据获取能力"""

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


def test_more_products_with_current_actor():
    """测试更多产品看BSR字段是否都为null"""
    print("\n" + "=" * 60)
    print("🔍 测试更多产品的BSR数据 - 当前Actor: ZhSGsaq9MHRnWtStl")
    print("=" * 60)
    
    # 选择不同类别的热门产品
    test_products = [
        "B08N5WRWNW",  # Echo Dot (4th Gen) - Electronics/Smart Home
        "B0C1SJBM48",  # Stanley Tumbler - Home & Kitchen  
        "B09G9FPHY6",  # Apple AirTags - Electronics
        "B08L5NP6NG",  # YETI Rambler - Sports & Outdoors
        "B0BT9CZNPX",  # Ninja Creami - Kitchen Appliances
        "B07ZPKN6YR",  # Anker Portable Charger - Electronics/Accessories
        "B0D3J9XDSL",  # Hydro Flask - Sports
        "B0756CYWWD",  # Fire TV Stick - Electronics/Streaming
    ]
    
    try:
        client = ApifyClient(os.getenv("APIFY_API_TOKEN"))
        
        run_input = {
            "asins": test_products,
            "amazonDomain": "amazon.com",
            "proxyCountry": "AUTO_SELECT_PROXY_COUNTRY", 
            "useCaptchaSolver": False,
        }
        
        print(f"📤 测试 {len(test_products)} 个不同类别的热门产品...")
        print("产品列表:")
        for i, asin in enumerate(test_products, 1):
            print(f"  {i}. {asin}")
        
        run = client.actor("ZhSGsaq9MHRnWtStl").call(run_input=run_input)
        
        print(f"\n✅ Actor运行完成: {run['id']}")
        print(f"   状态: {run.get('status')}")
        
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        print(f"📊 获取到 {len(items)} 个产品数据")
        
        # 分析BSR数据
        bsr_results = {}
        products_with_bsr = 0
        products_without_bsr = 0
        
        for item in items:
            asin = item.get('asin', 'Unknown')
            bsr_data = item.get('bestsellerRanks')
            title = item.get('title', 'Unknown')[:50]
            
            bsr_results[asin] = {
                'title': title,
                'bsr_field_exists': 'bestsellerRanks' in item,
                'bsr_data': bsr_data,
                'bsr_is_null': bsr_data is None,
                'bsr_is_empty': bsr_data == [] if isinstance(bsr_data, list) else False
            }
            
            if bsr_data and bsr_data != []:
                products_with_bsr += 1
            else:
                products_without_bsr += 1
            
            print(f"\n产品: {asin}")
            print(f"  标题: {title}...")
            print(f"  BSR字段存在: {'✅' if 'bestsellerRanks' in item else '❌'}")
            print(f"  BSR数据: {bsr_data}")
            
            # 如果有BSR数据，详细显示
            if bsr_data and bsr_data != []:
                print(f"  🎯 发现BSR数据！")
                if isinstance(bsr_data, list):
                    for i, rank_info in enumerate(bsr_data):
                        print(f"    排名 {i+1}: {rank_info}")
                else:
                    print(f"    BSR值: {bsr_data}")
        
        # 保存详细结果
        with open("bsr_research_results.json", "w", encoding="utf-8") as f:
            json.dump({
                'summary': {
                    'total_products': len(items),
                    'products_with_bsr': products_with_bsr,
                    'products_without_bsr': products_without_bsr,
                    'bsr_availability_rate': products_with_bsr / len(items) * 100 if items else 0
                },
                'detailed_results': bsr_results,
                'raw_sample': items[0] if items else None
            }, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n📊 BSR数据统计:")
        print(f"   总产品数: {len(items)}")
        print(f"   有BSR数据: {products_with_bsr}")
        print(f"   无BSR数据: {products_without_bsr}")
        print(f"   BSR可用率: {products_with_bsr / len(items) * 100:.1f}%" if items else "0%")
        
        return bsr_results
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return None


def research_alternative_actors():
    """调研其他可能有BSR数据的Actor"""
    print("\n" + "=" * 60)
    print("🌐 调研其他Amazon爬虫Actor")
    print("=" * 60)
    
    # 要测试的其他Actor
    alternative_actors = [
        {
            "id": "junglee~amazon-product-details",
            "name": "Amazon Product Details",
            "input_format": "productUrls"
        },
        {
            "id": "epctex~amazon-product-scraper", 
            "name": "Epctex Amazon Product Scraper",
            "input_format": "productUrls"
        },
        {
            "id": "misceres~amazon-product-scraper",
            "name": "Misceres Amazon Scraper", 
            "input_format": "productUrls"
        }
    ]
    
    test_url = "https://www.amazon.com/dp/B08N5WRWNW"  # Echo Dot
    
    client = ApifyClient(os.getenv("APIFY_API_TOKEN"))
    
    for actor_info in alternative_actors:
        print(f"\n🔍 测试 {actor_info['name']} ({actor_info['id']})")
        
        try:
            # 准备输入
            if actor_info['input_format'] == 'productUrls':
                run_input = {
                    "productUrls": [test_url],
                    "maxProducts": 1,
                    "scrapeReviews": False
                }
            else:
                run_input = {"urls": [test_url]}
            
            print(f"   📤 发送测试请求...")
            
            # 运行Actor
            run = client.actor(actor_info['id']).call(run_input=run_input)
            
            print(f"   ✅ 运行完成: {run['id']}")
            print(f"   状态: {run.get('status')}")
            
            # 获取结果
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            
            if items:
                item = items[0]
                print(f"   📊 获取到数据，检查BSR字段...")
                
                # 检查所有可能的BSR相关字段
                bsr_fields = []
                for key in item.keys():
                    if any(keyword in key.lower() for keyword in ['rank', 'bsr', 'bestseller', 'best_seller']):
                        bsr_fields.append({
                            'field': key,
                            'value': item[key]
                        })
                
                if bsr_fields:
                    print(f"   🎯 发现BSR相关字段:")
                    for field_info in bsr_fields:
                        print(f"     - {field_info['field']}: {field_info['value']}")
                else:
                    print(f"   ❌ 未发现BSR相关字段")
                
                # 保存样本数据
                sample_file = f"actor_sample_{actor_info['id'].replace('~', '_').replace('/', '_')}.json"
                with open(sample_file, "w", encoding="utf-8") as f:
                    json.dump(item, f, indent=2, ensure_ascii=False, default=str)
                print(f"   💾 样本数据已保存到 {sample_file}")
                
            else:
                print(f"   ❌ 未获取到数据")
                
        except Exception as e:
            print(f"   ❌ 测试失败: {e}")


def main():
    """主函数"""
    print("🚀 开始全面BSR数据调研")
    print("   这将测试多个产品和多个Actor以找到BSR数据源")
    
    # 1. 测试当前Actor的更多产品
    bsr_results = test_more_products_with_current_actor()
    
    # 2. 调研其他Actor
    research_alternative_actors()
    
    print("\n" + "=" * 60)
    print("📋 调研总结")
    print("=" * 60)
    print("1. 当前Actor (ZhSGsaq9MHRnWtStl) 在多个产品上的BSR数据表现")
    print("2. 其他Amazon爬虫Actor的BSR数据能力")
    print("3. 所有测试结果和样本数据已保存到JSON文件")
    print("\n💡 建议查看生成的JSON文件了解详细结果")


if __name__ == "__main__":
    main()