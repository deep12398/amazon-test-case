#!/usr/bin/env python3
"""
简化版Jaeger测试 - 使用OTLP导出器
"""

import asyncio
import random
import time

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_otlp_tracing():
    """使用OTLP设置追踪"""
    print("🔧 配置OTLP追踪...")

    # 创建资源
    resource = Resource.create({
        "service.name": "amazon-tracker-test",
        "service.version": "1.0.0",
        "environment": "development"
    })

    # 创建TracerProvider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    # 配置OTLP导出器 (Jaeger支持OTLP协议)
    otlp_exporter = OTLPSpanExporter(
        endpoint="http://localhost:4317",  # Jaeger OTLP GRPC端点
        insecure=True
    )

    # 添加span处理器
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

    return trace.get_tracer(__name__)


async def create_sample_traces():
    """创建示例追踪"""
    tracer = setup_otlp_tracing()

    print("🚀 开始生成示例追踪...")

    for i in range(10):
        with tracer.start_as_current_span("api_request") as span:
            span.set_attribute("request.id", f"req_{i}")
            span.set_attribute("user.type", random.choice(["normal", "premium", "admin"]))

            # 模拟子操作
            with tracer.start_as_current_span("database_query") as db_span:
                db_span.set_attribute("db.table", "products")
                await asyncio.sleep(random.uniform(0.01, 0.1))

            with tracer.start_as_current_span("cache_operation") as cache_span:
                cache_span.set_attribute("cache.hit", random.choice([True, False]))
                await asyncio.sleep(random.uniform(0.001, 0.01))

            print(f"✅ 生成追踪 {i + 1}/10")

        await asyncio.sleep(0.5)

    # 等待数据发送
    print("⏳ 等待数据发送...")
    await asyncio.sleep(2)

    print("✅ 完成!")


if __name__ == "__main__":
    asyncio.run(create_sample_traces())