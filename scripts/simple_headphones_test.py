#!/usr/bin/env python3
"""
简化的蓝牙耳机测试 - 直接使用ApifyClient
避免包装器的问题，直接验证爬虫功能
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
from dotenv import load_dotenv
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env.local")

from apify_client import ApifyClient


def test_headphones_crawl():
    """直接测试蓝牙耳机爬取"""
    print("=" * 60)
    print("🎧 蓝牙耳机数据直接测试")
    print("=" * 60)
    
    # 5个核心产品
    test_asins = [
        "B0D1XD1ZV3",  # Apple AirPods Pro 2
        "B0863TXGM3",  # Sony WH-1000XM4
        "B0756CYWWD",  # Bose QuietComfort 35 II
        # 减少到3个以免超时
    ]
    
    try:
        client = ApifyClient(os.getenv("APIFY_API_TOKEN"))
        
        run_input = {
            "asins": test_asins,
            "amazonDomain": "amazon.com",
            "proxyCountry": "AUTO_SELECT_PROXY_COUNTRY",
            "useCaptchaSolver": False,
        }
        
        print(f"📤 测试 {len(test_asins)} 个核心蓝牙耳机产品...")
        for i, asin in enumerate(test_asins, 1):
            print(f"  {i}. {asin}")
        
        # 运行爬虫
        run = client.actor("ZhSGsaq9MHRnWtStl").call(run_input=run_input)
        
        print(f"\n✅ Actor运行完成: {run['id']}")
        print(f"   状态: {run.get('status')}")
        print(f"   运行时间: {run.get('stats', {}).get('runTimeSecs', 0):.1f}秒")
        
        # 获取数据
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        print(f"📊 获取到 {len(items)} 个产品数据")
        
        # 分析数据质量
        results = analyze_data_quality(items)
        
        # 保存结果
        save_results(results, items)
        
        return results
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def analyze_data_quality(items):
    """分析数据质量"""
    results = {
        'total_products': len(items),
        'with_bsr': 0,
        'with_price': 0,
        'with_rating': 0,
        'product_details': []
    }
    
    print(f"\n🔍 数据质量分析:")
    
    for item in items:
        asin = item.get('asin', 'Unknown')
        title = item.get('title', 'Unknown')[:50]
        
        # 检查BSR数据
        bsr_data = item.get('bestsellerRanks', [])
        has_bsr = bool(bsr_data and isinstance(bsr_data, list) and len(bsr_data) > 0)
        if has_bsr:
            results['with_bsr'] += 1
            
        # 检查价格数据
        price = item.get('price', {})
        has_price = bool(price and price.get('value'))
        if has_price:
            results['with_price'] += 1
            
        # 检查评分数据
        rating = item.get('stars')
        has_rating = bool(rating)
        if has_rating:
            results['with_rating'] += 1
        
        # 记录产品详情
        product_detail = {
            'asin': asin,
            'title': title,
            'has_bsr': has_bsr,
            'has_price': has_price,  
            'has_rating': has_rating,
            'bsr_sample': bsr_data[0] if bsr_data else None,
            'price_sample': price.get('value') if isinstance(price, dict) else price,
            'rating_sample': rating
        }
        results['product_details'].append(product_detail)
        
        # 输出单个产品状态
        bsr_status = f"BSR: ✅" if has_bsr else "BSR: ❌"
        price_status = f"Price: ✅" if has_price else "Price: ❌"
        rating_status = f"Rating: ✅" if has_rating else "Rating: ❌"
        
        print(f"  {asin}: {bsr_status} | {price_status} | {rating_status}")
        if has_bsr and bsr_data:
            bsr_sample = bsr_data[0]
            print(f"    └─ BSR示例: #{bsr_sample.get('rank')} in {bsr_sample.get('category')}")
    
    # 计算成功率
    total = len(items)
    results['bsr_success_rate'] = (results['with_bsr'] / total * 100) if total > 0 else 0
    results['price_success_rate'] = (results['with_price'] / total * 100) if total > 0 else 0  
    results['rating_success_rate'] = (results['with_rating'] / total * 100) if total > 0 else 0
    
    print(f"\n📊 总体数据质量:")
    print(f"   BSR数据可用率: {results['bsr_success_rate']:.1f}% ({results['with_bsr']}/{total})")
    print(f"   价格数据可用率: {results['price_success_rate']:.1f}% ({results['with_price']}/{total})")
    print(f"   评分数据可用率: {results['rating_success_rate']:.1f}% ({results['with_rating']}/{total})")
    
    return results


def save_results(results, raw_items):
    """保存结果到文件"""
    output_file = "/Users/elias/code/amazon-test-case/logs/simple_headphones_test.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    full_report = {
        'test_timestamp': '2025-09-13T02:50:00',
        'summary': results,
        'raw_sample': raw_items[0] if raw_items else None,
        'all_products': results['product_details']
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(full_report, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n📄 详细报告已保存至: {output_file}")


if __name__ == "__main__":
    print("🚀 开始简化蓝牙耳机测试...")
    results = test_headphones_crawl()
    
    if results and results['bsr_success_rate'] >= 80:
        print("\n🎉 验证成功！BSR数据可用性良好，可以继续实施Demo。")
    else:
        print("\n⚠️  验证发现问题，需要进一步调查。")