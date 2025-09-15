#!/usr/bin/env python3
"""
调试爬虫返回结果结构
"""

import asyncio
import os
import sys
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from amazon_tracker.common.crawlers.apify_client import ApifyAmazonScraper


async def debug_crawler():
    """调试爬虫返回结果"""
    
    scraper = ApifyAmazonScraper()
    
    # 测试单个产品
    test_asins = ["B0D1XD1ZV3"]  # Apple AirPods Pro 2
    
    print("🔍 调试爬虫返回结果...")
    
    try:
        result = await scraper.scrape_multiple_products(test_asins)
        
        print(f"Success: {result.success}")
        print(f"Error: {result.error}")
        print(f"Data type: {type(result.data)}")
        
        if result.data:
            print(f"Data keys: {list(result.data.keys()) if isinstance(result.data, dict) else 'Not dict'}")
            
            # 保存完整结果到文件以便分析
            with open('/Users/elias/code/amazon-test-case/logs/debug_crawler_result.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'success': result.success,
                    'error': result.error,
                    'metadata': result.metadata,
                    'data': result.data
                }, f, indent=2, ensure_ascii=False, default=str)
            
            print("📄 完整结果已保存到 logs/debug_crawler_result.json")
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_crawler())