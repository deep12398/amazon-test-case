#!/usr/bin/env python3
"""
测试Jaeger分布式追踪
"""

import asyncio
import random
import time

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_jaeger_tracing():
    """设置Jaeger追踪"""
    print("🔧 配置Jaeger追踪...")

    # 创建资源
    resource = Resource.create({
        "service.name": "amazon-tracker-test",
        "service.version": "1.0.0",
        "environment": "development"
    })

    # 创建TracerProvider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    # 配置Jaeger导出器
    jaeger_exporter = JaegerExporter(
        agent_host_name="localhost",
        agent_port=6832,
        collector_endpoint="http://localhost:14268/api/traces",
    )

    # 添加span处理器
    span_processor = BatchSpanProcessor(jaeger_exporter)
    tracer_provider.add_span_processor(span_processor)

    return trace.get_tracer(__name__)


async def simulate_user_request(tracer, user_id: str):
    """模拟用户请求的完整链路"""

    with tracer.start_as_current_span("user_request") as root_span:
        # 设置根span属性
        root_span.set_attribute("user.id", user_id)
        root_span.set_attribute("request.type", "product_analysis")
        root_span.set_attribute("tenant.id", f"tenant_{random.randint(100, 999)}")

        print(f"🔍 开始追踪用户请求: {user_id}")

        # 1. 认证验证
        with tracer.start_as_current_span("authentication") as auth_span:
            auth_span.set_attribute("service.name", "user-service")
            auth_span.set_attribute("operation", "validate_jwt")
            auth_span.set_attribute("auth.method", "jwt")

            # 模拟认证时间
            auth_time = random.uniform(0.01, 0.05)
            await asyncio.sleep(auth_time)
            auth_span.set_attribute("auth.duration_ms", int(auth_time * 1000))

            print(f"  ✅ 认证完成 ({int(auth_time * 1000)}ms)")

        # 2. 权限检查
        with tracer.start_as_current_span("authorization") as authz_span:
            authz_span.set_attribute("operation", "check_permissions")
            authz_span.set_attribute("resource", "products")
            authz_span.set_attribute("action", "read")

            await asyncio.sleep(0.01)
            print(f"  ✅ 权限检查完成")

        # 3. 缓存查询
        with tracer.start_as_current_span("cache_lookup") as cache_span:
            cache_span.set_attribute("cache.type", "redis")
            cache_span.set_attribute("cache.operation", "get")

            cache_key = f"product_data_{random.randint(1, 1000)}"
            cache_span.set_attribute("cache.key", cache_key)

            # 70%的概率缓存命中
            cache_hit = random.random() < 0.7
            cache_span.set_attribute("cache.hit", cache_hit)

            if cache_hit:
                await asyncio.sleep(0.001)
                print(f"  ✅ 缓存命中: {cache_key}")
                return
            else:
                await asyncio.sleep(0.01)
                print(f"  ❌ 缓存未命中: {cache_key}")

        # 4. 数据库查询 (缓存未命中时)
        with tracer.start_as_current_span("database_query") as db_span:
            db_span.set_attribute("db.system", "postgresql")
            db_span.set_attribute("db.operation", "SELECT")
            db_span.set_attribute("db.table", "products")

            # 模拟复杂查询
            query_time = random.uniform(0.05, 0.2)
            await asyncio.sleep(query_time)

            rows_returned = random.randint(1, 50)
            db_span.set_attribute("db.rows_returned", rows_returned)
            db_span.set_attribute("db.duration_ms", int(query_time * 1000))

            print(f"  ✅ 数据库查询完成 ({rows_returned} rows, {int(query_time * 1000)}ms)")

        # 5. 外部API调用 (30%概率)
        if random.random() < 0.3:
            with tracer.start_as_current_span("external_api_call") as api_span:
                service_type = random.choice(["apify", "openai"])
                api_span.set_attribute("external.service", service_type)

                if service_type == "apify":
                    api_span.set_attribute("external.operation", "crawl_product")
                    api_span.set_attribute("external.url", "https://api.apify.com/v2/acts/...")
                    api_time = random.uniform(1.0, 3.0)
                else:
                    api_span.set_attribute("external.operation", "analyze_text")
                    api_span.set_attribute("external.url", "https://api.openai.com/v1/chat/completions")
                    api_time = random.uniform(0.5, 1.5)

                await asyncio.sleep(api_time)

                api_span.set_attribute("external.duration_ms", int(api_time * 1000))
                api_span.set_attribute("external.response_size", random.randint(1000, 10000))

                print(f"  ✅ {service_type.upper()} API调用完成 ({int(api_time * 1000)}ms)")

        # 6. 业务逻辑处理
        with tracer.start_as_current_span("business_logic") as logic_span:
            logic_span.set_attribute("operation", "process_product_data")

            processing_steps = random.randint(3, 8)
            logic_span.set_attribute("processing.steps", processing_steps)

            for step in range(processing_steps):
                with tracer.start_as_current_span(f"processing_step_{step + 1}") as step_span:
                    step_span.set_attribute("step.name", f"data_transformation_{step + 1}")
                    await asyncio.sleep(random.uniform(0.01, 0.05))

            logic_time = random.uniform(0.1, 0.5)
            await asyncio.sleep(logic_time)

            logic_span.set_attribute("business.duration_ms", int(logic_time * 1000))

            print(f"  ✅ 业务逻辑处理完成 ({processing_steps} steps, {int(logic_time * 1000)}ms)")

        # 7. 缓存写入
        with tracer.start_as_current_span("cache_write") as cache_write_span:
            cache_write_span.set_attribute("cache.type", "redis")
            cache_write_span.set_attribute("cache.operation", "set")
            cache_write_span.set_attribute("cache.key", cache_key)
            cache_write_span.set_attribute("cache.ttl", 3600)

            await asyncio.sleep(0.005)
            print(f"  ✅ 缓存写入完成")

        # 设置最终结果
        total_duration = time.time() - root_span.start_time / 1_000_000_000
        root_span.set_attribute("request.duration_ms", int(total_duration * 1000))
        root_span.set_attribute("request.status", "success")

        print(f"  🎉 请求完成! 总耗时: {int(total_duration * 1000)}ms")


async def generate_jaeger_test_data():
    """生成Jaeger测试数据"""
    tracer = setup_jaeger_tracing()

    print("🚀 开始生成Jaeger追踪数据...")

    # 生成不同类型的用户请求
    user_types = ["normal_user", "power_user", "api_client", "admin_user"]

    for i in range(20):  # 生成20个追踪
        user_type = random.choice(user_types)
        user_id = f"{user_type}_{random.randint(1000, 9999)}"

        await simulate_user_request(tracer, user_id)

        # 控制频率
        await asyncio.sleep(random.uniform(0.5, 2.0))

        if (i + 1) % 5 == 0:
            print(f"📊 已生成 {i + 1}/20 个追踪...")

    # 等待数据发送到Jaeger
    print("⏳ 等待数据发送到Jaeger...")
    await asyncio.sleep(3)

    print("✅ Jaeger测试数据生成完成!")
    print(f"🔍 查看Jaeger UI: http://localhost:16686")


if __name__ == "__main__":
    asyncio.run(generate_jaeger_test_data())