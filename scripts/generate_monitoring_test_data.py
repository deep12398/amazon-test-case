#!/usr/bin/env python3
"""
生成监控测试数据脚本
为Prometheus和Jaeger生成模拟的API调用和追踪数据
"""

import asyncio
import json
import random
import time
from typing import List

import httpx
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


class MonitoringDataGenerator:
    """监控数据生成器"""

    def __init__(self):
        self.base_url = "http://localhost:9080"  # APISIX网关
        self.jaeger_endpoint = "http://localhost:14268/api/traces"
        self.setup_tracing()

        # 模拟的API端点
        self.endpoints = [
            "/api/v1/auth/login",
            "/api/v1/users/me",
            "/api/v1/users/me/api-keys",
            "/api/v1/tenants/current",
            "/api/v1/products",
            "/api/v1/products/123/data",
            "/api/v1/competitors/456",
            "/api/v1/crawl/manual",
            "/health"
        ]

        # 模拟用户场景
        self.user_scenarios = [
            {
                "name": "normal_user",
                "success_rate": 0.95,
                "avg_response_time": 200,
                "request_patterns": {
                    "/api/v1/auth/login": 10,
                    "/api/v1/users/me": 50,
                    "/api/v1/products": 100,
                    "/api/v1/products/123/data": 80,
                }
            },
            {
                "name": "power_user",
                "success_rate": 0.98,
                "avg_response_time": 150,
                "request_patterns": {
                    "/api/v1/auth/login": 5,
                    "/api/v1/users/me": 20,
                    "/api/v1/products": 200,
                    "/api/v1/competitors/456": 100,
                    "/api/v1/crawl/manual": 50,
                }
            },
            {
                "name": "api_client",
                "success_rate": 0.99,
                "avg_response_time": 100,
                "request_patterns": {
                    "/api/v1/products": 500,
                    "/api/v1/products/123/data": 300,
                    "/api/v1/competitors/456": 200,
                }
            }
        ]

    def setup_tracing(self):
        """设置OpenTelemetry追踪"""
        resource = Resource.create({"service.name": "test-data-generator"})

        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)

        # 配置Jaeger导出器
        jaeger_exporter = JaegerExporter(
            agent_host_name="localhost",
            agent_port=6832,
        )

        span_processor = BatchSpanProcessor(jaeger_exporter)
        tracer_provider.add_span_processor(span_processor)

        self.tracer = trace.get_tracer(__name__)

        # 自动化HTTP客户端追踪
        HTTPXClientInstrumentor().instrument()

    async def generate_api_requests(self, duration_minutes: int = 30):
        """生成API请求测试数据"""
        print(f"🚀 开始生成 {duration_minutes} 分钟的API测试数据...")

        end_time = time.time() + (duration_minutes * 60)
        request_count = 0

        async with httpx.AsyncClient() as client:
            while time.time() < end_time:
                # 随机选择用户场景
                scenario = random.choice(self.user_scenarios)

                # 根据场景生成请求
                await self._execute_user_scenario(client, scenario)

                request_count += 1

                # 控制请求频率 (每秒1-5个请求)
                await asyncio.sleep(random.uniform(0.2, 1.0))

                if request_count % 50 == 0:
                    print(f"📊 已生成 {request_count} 个请求...")

        print(f"✅ 完成! 总共生成了 {request_count} 个API请求")

    async def _execute_user_scenario(self, client: httpx.AsyncClient, scenario: dict):
        """执行用户场景"""
        scenario_name = scenario["name"]

        with self.tracer.start_as_current_span(f"user_scenario_{scenario_name}") as span:
            span.set_attribute("user.scenario", scenario_name)
            span.set_attribute("user.success_rate", scenario["success_rate"])

            # 根据场景权重选择端点
            endpoint = self._select_weighted_endpoint(scenario["request_patterns"])

            await self._make_api_request(client, endpoint, scenario)

    def _select_weighted_endpoint(self, patterns: dict) -> str:
        """根据权重选择端点"""
        endpoints = list(patterns.keys())
        weights = list(patterns.values())
        return random.choices(endpoints, weights=weights)[0]

    async def _make_api_request(self, client: httpx.AsyncClient, endpoint: str, scenario: dict):
        """执行API请求"""
        with self.tracer.start_as_current_span(f"api_request_{endpoint.replace('/', '_')}") as span:
            try:
                # 设置追踪属性
                span.set_attribute("http.method", "GET")
                span.set_attribute("http.url", f"{self.base_url}{endpoint}")
                span.set_attribute("user.scenario", scenario["name"])

                # 模拟认证头
                headers = {
                    "Authorization": "Bearer mock-jwt-token",
                    "X-API-Key": f"test-api-key-{random.randint(1000, 9999)}",
                    "User-Agent": f"test-client-{scenario['name']}"
                }

                # 模拟请求参数
                params = self._get_mock_params(endpoint)

                # 执行请求
                start_time = time.time()

                # 模拟成功/失败
                if random.random() < scenario["success_rate"]:
                    # 成功请求
                    response = await client.get(
                        f"{self.base_url}{endpoint}",
                        headers=headers,
                        params=params,
                        timeout=5.0
                    )
                    status_code = 200 if endpoint == "/health" else random.choice([200, 200, 200, 201, 304])
                else:
                    # 模拟失败
                    status_code = random.choice([400, 401, 403, 404, 429, 500, 502, 503])

                response_time = time.time() - start_time

                # 设置响应属性
                span.set_attribute("http.status_code", status_code)
                span.set_attribute("http.response_time_ms", int(response_time * 1000))

                if status_code >= 400:
                    span.set_status(trace.Status(trace.StatusCode.ERROR))

                # 模拟不同的响应时间
                base_time = scenario["avg_response_time"] / 1000
                variation = random.uniform(0.5, 2.0)
                await asyncio.sleep(base_time * variation)

            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))

    def _get_mock_params(self, endpoint: str) -> dict:
        """获取模拟请求参数"""
        if endpoint == "/api/v1/products":
            return {
                "page": random.randint(1, 10),
                "limit": random.choice([10, 20, 50, 100]),
                "category": random.choice(["electronics", "headphones", "smartphones"])
            }
        elif endpoint == "/api/v1/products/123/data":
            return {
                "days": random.choice([7, 30, 90]),
                "metrics": random.choice(["price", "bsr", "rating", "all"])
            }
        elif endpoint == "/api/v1/competitors/456":
            return {
                "analysis_type": random.choice(["quick", "full", "deep"])
            }
        return {}

    async def generate_jaeger_traces(self, duration_minutes: int = 15):
        """生成Jaeger追踪数据"""
        print(f"🔍 开始生成 {duration_minutes} 分钟的追踪数据...")

        end_time = time.time() + (duration_minutes * 60)
        trace_count = 0

        while time.time() < end_time:
            await self._create_complex_trace()
            trace_count += 1

            # 控制追踪频率
            await asyncio.sleep(random.uniform(1.0, 3.0))

            if trace_count % 20 == 0:
                print(f"🔗 已生成 {trace_count} 个追踪链路...")

        print(f"✅ 完成! 总共生成了 {trace_count} 个追踪链路")

    async def _create_complex_trace(self):
        """创建复杂的追踪链路"""
        with self.tracer.start_as_current_span("user_request") as root_span:
            # 模拟用户请求
            user_id = f"user_{random.randint(1000, 9999)}"
            tenant_id = f"tenant_{random.randint(100, 999)}"

            root_span.set_attribute("user.id", user_id)
            root_span.set_attribute("tenant.id", tenant_id)
            root_span.set_attribute("request.type", "product_analysis")

            # 认证服务调用
            with self.tracer.start_as_current_span("auth_service") as auth_span:
                auth_span.set_attribute("service.name", "user-service")
                auth_span.set_attribute("operation", "validate_jwt")
                await asyncio.sleep(random.uniform(0.01, 0.05))

            # 数据库查询
            with self.tracer.start_as_current_span("database_query") as db_span:
                db_span.set_attribute("db.type", "postgresql")
                db_span.set_attribute("db.table", "products")
                db_span.set_attribute("db.operation", "SELECT")
                await asyncio.sleep(random.uniform(0.05, 0.2))

            # 缓存操作
            with self.tracer.start_as_current_span("cache_operation") as cache_span:
                cache_span.set_attribute("cache.type", "redis")
                cache_span.set_attribute("cache.key", f"product_{random.randint(1, 1000)}")

                if random.random() < 0.7:  # 70% cache hit
                    cache_span.set_attribute("cache.hit", True)
                    await asyncio.sleep(0.001)
                else:
                    cache_span.set_attribute("cache.hit", False)
                    await asyncio.sleep(0.01)

            # 外部API调用
            if random.random() < 0.3:  # 30% 概率调用外部API
                with self.tracer.start_as_current_span("external_api") as api_span:
                    api_service = random.choice(["apify", "openai"])
                    api_span.set_attribute("external.service", api_service)

                    if api_service == "apify":
                        api_span.set_attribute("external.operation", "crawl_product")
                        await asyncio.sleep(random.uniform(1.0, 3.0))
                    else:
                        api_span.set_attribute("external.operation", "analyze_competitor")
                        await asyncio.sleep(random.uniform(0.5, 1.5))

            # 业务逻辑处理
            with self.tracer.start_as_current_span("business_logic") as logic_span:
                logic_span.set_attribute("operation", "calculate_metrics")
                logic_span.set_attribute("product.count", random.randint(1, 50))
                await asyncio.sleep(random.uniform(0.1, 0.5))

    def generate_prometheus_metrics(self):
        """生成Prometheus指标数据"""
        print("📊 生成Prometheus指标数据...")

        # 这里我们主要依赖APISIX自动生成的指标
        # 以及通过API调用产生的指标数据

        metrics_info = {
            "apisix_http_requests_total": "API请求总数",
            "apisix_http_latency": "API响应延迟",
            "apisix_bandwidth": "网络带宽使用",
            "apisix_etcd_modify_indexes": "etcd修改索引",
        }

        print("🎯 主要监控指标:")
        for metric, description in metrics_info.items():
            print(f"  - {metric}: {description}")

    async def run_full_test(self, duration_minutes: int = 30):
        """运行完整的测试数据生成"""
        print("=" * 60)
        print("🎯 Amazon产品追踪系统 - 监控测试数据生成器")
        print("=" * 60)

        self.generate_prometheus_metrics()

        # 并行生成API请求和追踪数据
        await asyncio.gather(
            self.generate_api_requests(duration_minutes),
            self.generate_jaeger_traces(duration_minutes // 2),
        )

        print("\n" + "=" * 60)
        print("✅ 监控测试数据生成完成!")
        print("\n📊 查看数据:")
        print(f"  • Prometheus: http://localhost:9090")
        print(f"  • Jaeger UI:  http://localhost:16686")
        print(f"  • APISIX Metrics: http://localhost:9091/apisix/prometheus/metrics")
        print("=" * 60)


async def main():
    """主函数"""
    generator = MonitoringDataGenerator()

    # 生成30分钟的测试数据
    await generator.run_full_test(duration_minutes=30)


if __name__ == "__main__":
    asyncio.run(main())