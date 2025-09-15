#!/usr/bin/env python3
"""
竞品分析API端点测试脚本

测试新实现的竞品分析API端点，包括：
1. 设置主产品 API
2. 创建竞品集合 API
3. 获取竞品集合 API
4. 分析竞品集合 API
5. 管理竞品关系 API

使用方法：
    python scripts/test_competitor_api_endpoints.py

要求：
- Core Service 运行在 localhost:8003
- 有效的JWT令牌
- 测试用户和租户数据
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, List
import aiohttp
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# API测试配置
API_CONFIG = {
    "base_url": "http://localhost:8003/api/v1",
    "headers": {
        "Content-Type": "application/json",
        # 注意：实际使用时需要有效的JWT令牌
        "Authorization": "Bearer test-jwt-token"
    },
    
    # 测试数据
    "test_main_product": {
        "asin": "B09X7GTHXX",
        "title": "Apple AirPods Pro (2nd Generation)",
        "brand": "Apple",
        "category": "Electronics > Headphones",
        "marketplace": "amazon_us",
        "tracking_frequency": "daily"
    },
    
    "competitor_urls": [
        "https://amazon.com/dp/B0863TXGM3",  # Sony WF-1000XM4
        "https://amazon.com/dp/B08PZHYWJS",  # Bose QuietComfort Earbuds
        "https://amazon.com/dp/B07SJR6HL3",  # Jabra Elite 75t
    ],
    
    "raw_competitor_data": [
        {
            "asin": "B08C4KWM9T",
            "title": "Samsung Galaxy Buds Pro True Wireless Bluetooth Earbuds",
            "brand": "Samsung",
            "price.value": 149.99,
            "stars": 4.3,
            "reviewsCount": 12456,
            "url": "https://amazon.com/dp/B08C4KWM9T",
            "thumbnailImage": "https://m.media-amazon.com/images/I/61xyz.jpg",
            "breadCrumbs": "Electronics > Headphones > Earbud Headphones"
        }
    ]
}


class CompetitorAPITester:
    """竞品分析API测试器"""
    
    def __init__(self):
        self.base_url = API_CONFIG["base_url"]
        self.headers = API_CONFIG["headers"]
        self.session = None
        
        # 测试中使用的ID
        self.main_product_id = None
        self.competitor_set_id = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """发起HTTP请求"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.request(
                method, url, 
                headers=self.headers,
                json=data if data else None
            ) as response:
                
                # 记录请求
                logger.info(f"📤 {method} {endpoint} -> {response.status}")
                
                response_data = await response.json()
                
                if response.status >= 400:
                    logger.error(f"❌ API错误 {response.status}: {response_data}")
                    return {"error": response_data, "status": response.status}
                
                return {"data": response_data, "status": response.status}
                
        except Exception as e:
            logger.error(f"❌ 请求失败: {e}")
            return {"error": str(e), "status": 0}
    
    async def run_all_tests(self):
        """运行所有API测试"""
        logger.info("🚀 开始竞品分析API测试")
        
        try:
            # 1. 准备测试数据
            await self.prepare_test_product()
            
            # 2. 测试设置主产品API
            await self.test_set_main_product_api()
            
            # 3. 测试创建竞品集合API
            await self.test_create_competitor_set_api()
            
            # 4. 测试从原始数据创建竞品集合API
            await self.test_create_competitor_set_from_data_api()
            
            # 5. 测试获取竞品集合列表API
            await self.test_get_competitor_sets_api()
            
            # 6. 测试获取竞品集合详情API
            await self.test_get_competitor_set_detail_api()
            
            # 7. 测试分析竞品集合API
            await self.test_analyze_competitor_set_api()
            
            # 8. 测试添加竞品到集合API
            await self.test_add_competitors_to_set_api()
            
            # 9. 测试更新竞品集合API
            await self.test_update_competitor_set_api()
            
            # 10. 测试现有的分析API
            await self.test_existing_analysis_apis()
            
            logger.info("✅ 所有API测试完成！")
            
        except Exception as e:
            logger.error(f"❌ API测试失败: {e}")
            raise
    
    async def prepare_test_product(self):
        """准备测试产品"""
        logger.info("📝 准备测试产品...")
        
        # 创建产品
        product_data = API_CONFIG["test_main_product"]
        
        result = await self.make_request("POST", "/products", product_data)
        
        if result.get("status") == 201:
            self.main_product_id = result["data"]["id"]
            logger.info(f"✓ 测试产品创建成功 (ID: {self.main_product_id})")
        elif result.get("status") == 409:
            # 产品已存在，通过搜索获取ID
            search_result = await self.make_request("POST", "/products/search", {
                "asin": product_data["asin"]
            })
            if search_result.get("status") == 200 and search_result["data"]:
                self.main_product_id = search_result["data"][0]["id"]
                logger.info(f"✓ 使用现有测试产品 (ID: {self.main_product_id})")
            else:
                raise Exception("无法创建或找到测试产品")
        else:
            raise Exception(f"创建测试产品失败: {result}")
    
    async def test_set_main_product_api(self):
        """测试设置主产品API"""
        logger.info("🎯 测试设置主产品API...")
        
        if not self.main_product_id:
            logger.warning("⚠️ 没有可用的产品ID，跳过测试")
            return
        
        data = {"product_id": self.main_product_id}
        
        result = await self.make_request("POST", "/competitors/set-main-product", data)
        
        if result.get("status") == 200:
            response_data = result["data"]
            logger.info(f"✓ 主产品设置成功: {response_data['asin']}")
            logger.info(f"  - 产品ID: {response_data['product_id']}")
        else:
            logger.error(f"❌ 设置主产品失败: {result}")
    
    async def test_create_competitor_set_api(self):
        """测试创建竞品集合API"""
        logger.info("🔗 测试创建竞品集合API...")
        
        if not self.main_product_id:
            logger.warning("⚠️ 没有可用的产品ID，跳过测试")
            return
        
        data = {
            "main_product_id": self.main_product_id,
            "name": "API测试竞品集合",
            "description": "通过API创建的测试竞品集合",
            "competitor_urls": API_CONFIG["competitor_urls"]
        }
        
        result = await self.make_request("POST", "/competitors/sets", data)
        
        if result.get("status") == 200:
            response_data = result["data"]
            if response_data.get("success"):
                self.competitor_set_id = response_data["competitor_set_id"]
                logger.info(f"✓ 竞品集合创建成功 (ID: {self.competitor_set_id})")
                logger.info(f"  - 竞品数量: {response_data['competitor_count']}")
                logger.info(f"  - 重复项: {response_data['duplicates_found']}")
                if response_data.get('errors'):
                    logger.warning(f"  - 错误: {response_data['errors']}")
            else:
                logger.error(f"❌ 竞品集合创建失败: {response_data.get('error', '未知错误')}")
        else:
            logger.error(f"❌ 创建竞品集合API调用失败: {result}")
    
    async def test_create_competitor_set_from_data_api(self):
        """测试从原始数据创建竞品集合API"""
        logger.info("📊 测试从原始数据创建竞品集合API...")
        
        if not self.main_product_id:
            logger.warning("⚠️ 没有可用的产品ID，跳过测试")
            return
        
        data = {
            "main_product_id": self.main_product_id,
            "name": "API测试竞品集合-原始数据",
            "description": "通过API从原始数据创建的测试竞品集合",
            "competitor_data": API_CONFIG["raw_competitor_data"]
        }
        
        result = await self.make_request("POST", "/competitors/sets/from-data", data)
        
        if result.get("status") == 200:
            response_data = result["data"]
            if response_data.get("success"):
                logger.info(f"✓ 从原始数据创建竞品集合成功 (ID: {response_data['competitor_set_id']})")
                logger.info(f"  - 处理项目: {response_data.get('processed_items', 0)}")
                logger.info(f"  - 竞品数量: {response_data['competitor_count']}")
            else:
                logger.error(f"❌ 从原始数据创建竞品集合失败: {response_data.get('error', '未知错误')}")
        else:
            logger.error(f"❌ 从原始数据创建竞品集合API调用失败: {result}")
    
    async def test_get_competitor_sets_api(self):
        """测试获取竞品集合列表API"""
        logger.info("📋 测试获取竞品集合列表API...")
        
        if not self.main_product_id:
            logger.warning("⚠️ 没有可用的产品ID，跳过测试")
            return
        
        result = await self.make_request("GET", f"/competitors/sets/product/{self.main_product_id}")
        
        if result.get("status") == 200:
            response_data = result["data"]
            logger.info(f"✓ 获取竞品集合列表成功:")
            logger.info(f"  - 产品: {response_data['asin']} - {response_data['title']}")
            logger.info(f"  - 竞品集合数量: {len(response_data['competitor_sets'])}")
            
            for cs in response_data['competitor_sets']:
                logger.info(f"    • {cs['name']}: {cs['competitor_count']} 个竞品 (状态: {cs['status']})")
        else:
            logger.error(f"❌ 获取竞品集合列表失败: {result}")
    
    async def test_get_competitor_set_detail_api(self):
        """测试获取竞品集合详情API"""
        logger.info("🔍 测试获取竞品集合详情API...")
        
        if not self.competitor_set_id:
            logger.warning("⚠️ 没有可用的竞品集合ID，跳过测试")
            return
        
        result = await self.make_request("GET", f"/competitors/sets/{self.competitor_set_id}")
        
        if result.get("status") == 200:
            response_data = result["data"]
            logger.info(f"✓ 获取竞品集合详情成功:")
            logger.info(f"  - 集合名称: {response_data['name']}")
            logger.info(f"  - 主产品: {response_data['main_product']['asin']}")
            logger.info(f"  - 竞品数量: {len(response_data['competitors'])}")
            logger.info(f"  - 分析频率: {response_data['analysis_frequency']}")
            
            # 显示竞品信息
            for comp in response_data['competitors'][:3]:  # 只显示前3个
                logger.info(f"    • {comp['asin']}: {comp['title'][:50]}...")
        else:
            logger.error(f"❌ 获取竞品集合详情失败: {result}")
    
    async def test_analyze_competitor_set_api(self):
        """测试分析竞品集合API"""
        logger.info("🔬 测试分析竞品集合API...")
        
        if not self.competitor_set_id:
            logger.warning("⚠️ 没有可用的竞品集合ID，跳过测试")
            return
        
        data = {
            "competitor_set_id": self.competitor_set_id,
            "analysis_type": "comprehensive"
        }
        
        result = await self.make_request("POST", f"/competitors/sets/{self.competitor_set_id}/analyze", data)
        
        if result.get("status") == 200:
            response_data = result["data"]
            if response_data.get("success"):
                logger.info(f"✓ 竞品集合分析成功:")
                logger.info(f"  - 分析ID: {response_data['analysis_id']}")
                logger.info(f"  - 竞品数量: {response_data['competitor_count']}")
                logger.info(f"  - 市场定位: {response_data.get('market_position', 'N/A')}")
                
                # 显示建议
                recommendations = response_data.get("recommendations", [])
                if recommendations:
                    logger.info(f"  💡 前3条建议:")
                    for i, rec in enumerate(recommendations[:3], 1):
                        logger.info(f"    {i}. {rec}")
            else:
                logger.error(f"❌ 竞品集合分析失败: {response_data.get('error', '未知错误')}")
        else:
            logger.error(f"❌ 分析竞品集合API调用失败: {result}")
    
    async def test_add_competitors_to_set_api(self):
        """测试添加竞品到集合API"""
        logger.info("➕ 测试添加竞品到集合API...")
        
        if not self.competitor_set_id:
            logger.warning("⚠️ 没有可用的竞品集合ID，跳过测试")
            return
        
        data = {
            "competitor_set_id": self.competitor_set_id,
            "competitor_urls": ["https://amazon.com/dp/B07PXGQC1Q"]  # Echo Buds
        }
        
        result = await self.make_request("POST", f"/competitors/sets/{self.competitor_set_id}/competitors", data)
        
        if result.get("status") == 200:
            response_data = result["data"]
            if response_data.get("success"):
                logger.info(f"✓ 添加竞品成功:")
                logger.info(f"  - 添加数量: {response_data['added_count']}")
                logger.info(f"  - 跳过数量: {response_data['skipped_count']}")
                if response_data.get('errors'):
                    logger.warning(f"  - 错误: {response_data['errors']}")
            else:
                logger.error(f"❌ 添加竞品失败")
        else:
            logger.error(f"❌ 添加竞品API调用失败: {result}")
    
    async def test_update_competitor_set_api(self):
        """测试更新竞品集合API"""
        logger.info("✏️ 测试更新竞品集合API...")
        
        if not self.competitor_set_id:
            logger.warning("⚠️ 没有可用的竞品集合ID，跳过测试")
            return
        
        data = {
            "name": "API测试竞品集合-已更新",
            "description": "通过API更新的测试竞品集合描述",
            "max_competitors": 15
        }
        
        result = await self.make_request("PUT", f"/competitors/sets/{self.competitor_set_id}", data)
        
        if result.get("status") == 200:
            response_data = result["data"]
            if response_data.get("success"):
                logger.info(f"✓ 竞品集合更新成功 (ID: {response_data['competitor_set_id']})")
            else:
                logger.error(f"❌ 竞品集合更新失败: {response_data.get('error', '未知错误')}")
        else:
            logger.error(f"❌ 更新竞品集合API调用失败: {result}")
    
    async def test_existing_analysis_apis(self):
        """测试现有的分析API"""
        logger.info("🔍 测试现有的分析API...")
        
        if not self.main_product_id:
            logger.warning("⚠️ 没有可用的产品ID，跳过测试")
            return
        
        # 测试传统的竞品分析API
        data = {
            "product_id": self.main_product_id,
            "analysis_type": "comprehensive",
            "auto_discover": True,
            "max_competitors": 5
        }
        
        result = await self.make_request("POST", "/competitors/analyze", data)
        
        if result.get("status") == 200:
            response_data = result["data"]
            logger.info(f"✓ 传统竞品分析成功:")
            logger.info(f"  - 分析ID: {response_data['analysis_id']}")
            logger.info(f"  - 分析类型: {response_data['analysis_type']}")
            logger.info(f"  - 竞品数量: {len(response_data['competitors'])}")
            logger.info(f"  - 市场定位: {response_data['market_position']}")
        else:
            logger.error(f"❌ 传统竞品分析失败: {result}")
        
        # 测试竞品发现API
        result = await self.make_request("GET", f"/competitors/discover/{self.main_product_id}?max_competitors=5")
        
        if result.get("status") == 200:
            response_data = result["data"]
            logger.info(f"✓ 竞品发现成功:")
            logger.info(f"  - 发现竞品数量: {response_data['competitor_count']}")
            logger.info(f"  - 竞品ASINs: {response_data['discovered_competitors']}")
        else:
            logger.error(f"❌ 竞品发现失败: {result}")


async def main():
    """主函数"""
    print("=" * 80)
    print("🧪 Amazon 竞品分析API测试")
    print("=" * 80)
    
    async with CompetitorAPITester() as tester:
        await tester.run_all_tests()
    
    print("=" * 80)
    print("✅ API测试完成！检查日志了解详细结果。")
    print("💡 注意：某些测试可能因为缺少有效的JWT令牌而失败。")
    print("💡 在实际环境中使用时，请确保提供正确的认证令牌。")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())