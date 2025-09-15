#!/usr/bin/env python3
"""
持续生成监控数据脚本
为所有Grafana仪表板提供丰富的测试数据
"""

import asyncio
import random
import time
from typing import List

import httpx


class ContinuousMonitoringData:
    """持续监控数据生成器"""

    def __init__(self):
        self.base_url = "http://localhost:9080"
        self.endpoints = [
            "/health",
            "/api/v1/auth/login",
            "/api/v1/users/me",
            "/api/v1/users/me/api-keys",
            "/api/v1/tenants/current",
            "/api/v1/products",
            "/api/v1/products/123/data",
            "/api/v1/products/456/data",
            "/api/v1/products/789/data",
            "/api/v1/competitors/456",
            "/api/v1/competitors/789",
            "/api/v1/crawl/manual",
            "/api/v1/reports/daily",
            "/api/v1/reports/weekly",
            "/api/v1/analytics/trends"
        ]

        # 不同的用户行为模式
        self.user_patterns = [
            {
                "name": "heavy_user",
                "request_rate": 0.2,  # 每秒5个请求
                "burst_probability": 0.3,
                "burst_size": 10
            },
            {
                "name": "normal_user",
                "request_rate": 1.0,  # 每秒1个请求
                "burst_probability": 0.1,
                "burst_size": 5
            },
            {
                "name": "light_user",
                "request_rate": 3.0,  # 每3秒1个请求
                "burst_probability": 0.05,
                "burst_size": 3
            }
        ]

    async def generate_request_burst(self, client: httpx.AsyncClient, burst_size: int):
        """生成请求突发"""
        print(f"🚀 生成请求突发: {burst_size} 个请求")

        tasks = []
        for _ in range(burst_size):
            endpoint = random.choice(self.endpoints)
            task = self.make_single_request(client, endpoint)
            tasks.append(task)

        # 并发执行所有请求
        await asyncio.gather(*tasks, return_exceptions=True)

    async def make_single_request(self, client: httpx.AsyncClient, endpoint: str):
        """发送单个请求"""
        try:
            headers = {
                "Authorization": f"Bearer test-token-{random.randint(1000, 9999)}",
                "X-API-Key": f"api-key-{random.randint(10000, 99999)}",
                "User-Agent": f"monitoring-client-{random.choice(['web', 'mobile', 'api'])}"
            }

            # 添加一些查询参数以增加多样性
            params = self.get_random_params(endpoint)

            response = await client.get(
                f"{self.base_url}{endpoint}",
                headers=headers,
                params=params,
                timeout=10.0
            )

            print(f"  📊 {endpoint} -> {response.status_code}")

        except Exception as e:
            print(f"  ❌ {endpoint} -> Error: {e}")

    def get_random_params(self, endpoint: str) -> dict:
        """为不同端点生成随机参数"""
        if "/products" in endpoint and "/data" not in endpoint:
            return {
                "page": random.randint(1, 20),
                "limit": random.choice([10, 20, 50, 100]),
                "category": random.choice(["electronics", "headphones", "smartphones", "tablets"]),
                "sort": random.choice(["price", "rating", "bsr", "date"])
            }
        elif "/data" in endpoint:
            return {
                "days": random.choice([1, 7, 30, 90]),
                "metrics": random.choice(["price", "bsr", "rating", "reviews", "all"]),
                "format": random.choice(["json", "csv"])
            }
        elif "/competitors" in endpoint:
            return {
                "analysis_type": random.choice(["quick", "full", "deep"]),
                "include_pricing": random.choice(["true", "false"])
            }
        elif "/reports" in endpoint:
            return {
                "format": random.choice(["pdf", "excel", "json"]),
                "email": random.choice(["true", "false"])
            }
        return {}

    async def simulate_user_pattern(self, client: httpx.AsyncClient, pattern: dict, duration: int):
        """模拟特定用户行为模式"""
        pattern_name = pattern["name"]
        print(f"👤 开始模拟 {pattern_name} 行为模式，持续 {duration} 秒...")

        end_time = time.time() + duration
        request_count = 0

        while time.time() < end_time:
            # 检查是否应该生成突发请求
            if random.random() < pattern["burst_probability"]:
                await self.generate_request_burst(client, pattern["burst_size"])
                request_count += pattern["burst_size"]
            else:
                # 正常单个请求
                endpoint = random.choice(self.endpoints)
                await self.make_single_request(client, endpoint)
                request_count += 1

            # 根据模式调整请求频率
            await asyncio.sleep(pattern["request_rate"])

        print(f"✅ {pattern_name} 模式完成，共发送 {request_count} 个请求")

    async def run_mixed_load_test(self, duration_minutes: int = 10):
        """运行混合负载测试"""
        print(f"🎯 开始 {duration_minutes} 分钟的混合负载测试...")
        print("=" * 60)

        duration_seconds = duration_minutes * 60

        async with httpx.AsyncClient() as client:
            # 并发运行不同的用户模式
            tasks = []
            for pattern in self.user_patterns:
                task = self.simulate_user_pattern(client, pattern, duration_seconds)
                tasks.append(task)

            # 等待所有模式完成
            await asyncio.gather(*tasks)

        print("\n" + "=" * 60)
        print("✅ 混合负载测试完成!")

    async def run_realistic_traffic(self, duration_minutes: int = 15):
        """生成更真实的流量模式"""
        print(f"🌐 开始生成 {duration_minutes} 分钟的真实流量...")

        end_time = time.time() + (duration_minutes * 60)
        total_requests = 0

        async with httpx.AsyncClient() as client:
            while time.time() < end_time:
                # 模拟一天中不同时间段的流量变化
                current_minute = int((time.time() % 3600) / 60)

                # 高峰期（每小时的前15分钟）- 更多请求
                if current_minute < 15:
                    request_interval = random.uniform(0.1, 0.5)
                    burst_chance = 0.4
                # 正常期
                elif current_minute < 45:
                    request_interval = random.uniform(0.5, 1.5)
                    burst_chance = 0.2
                # 低峰期
                else:
                    request_interval = random.uniform(1.0, 3.0)
                    burst_chance = 0.1

                # 决定是否生成突发请求
                if random.random() < burst_chance:
                    burst_size = random.randint(3, 8)
                    await self.generate_request_burst(client, burst_size)
                    total_requests += burst_size
                else:
                    endpoint = random.choice(self.endpoints)
                    await self.make_single_request(client, endpoint)
                    total_requests += 1

                await asyncio.sleep(request_interval)

                # 每100个请求报告一次进度
                if total_requests % 100 == 0:
                    print(f"📈 已生成 {total_requests} 个请求...")

        print(f"✅ 真实流量生成完成! 总计 {total_requests} 个请求")

    async def generate_dashboard_data(self, minutes: int = 20):
        """为所有仪表板生成丰富的数据"""
        print("🎨 为Grafana仪表板生成丰富的监控数据...")
        print("=" * 60)
        print("📊 目标仪表板:")
        print("  • APISIX Gateway - Prometheus Metrics")
        print("  • APISIX Gateway Monitoring")
        print("  • Amazon Tracker Application Monitoring")
        print("=" * 60)

        # 分阶段生成不同类型的数据

        # 阶段1: 突发流量测试 (5分钟)
        print("\n🚀 阶段1: 突发流量测试...")
        await self.run_mixed_load_test(duration_minutes=5)

        # 短暂休息
        print("\n⏸️ 休息30秒...")
        await asyncio.sleep(30)

        # 阶段2: 真实流量模拟 (15分钟)
        print("\n🌐 阶段2: 真实流量模拟...")
        await self.run_realistic_traffic(duration_minutes=15)

        print("\n" + "=" * 60)
        print("✅ 所有仪表板数据生成完成!")
        print("\n📈 现在可以在Grafana中查看丰富的监控数据:")
        print("  🔗 Grafana: http://localhost:3000")
        print("  📊 各种图表应该显示丰富的指标变化")
        print("  🔍 Jaeger: http://localhost:16686")
        print("=" * 60)


async def main():
    """主函数"""
    generator = ContinuousMonitoringData()

    # 生成20分钟的综合监控数据
    await generator.generate_dashboard_data(minutes=20)


if __name__ == "__main__":
    asyncio.run(main())