#!/usr/bin/env python3
"""
生成APISIX演示指标数据的脚本
由于APISIX配置复杂，我们使用Python脚本生成模拟指标数据
"""

import time
import random
import requests
import json
from prometheus_client import CollectorRegistry, Gauge, Counter, Histogram, start_http_server
import threading

class APISIXMetricsSimulator:
    def __init__(self, port=8090):
        self.registry = CollectorRegistry()
        self.port = port

        # 创建指标
        self.http_requests_total = Counter(
            'apisix_http_requests_total',
            'Total HTTP requests',
            ['method', 'status', 'route'],
            registry=self.registry
        )

        self.http_request_duration = Histogram(
            'apisix_http_latency_histogram',
            'HTTP request duration',
            ['method', 'route'],
            registry=self.registry,
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
        )

        self.http_status = Counter(
            'apisix_http_status',
            'HTTP status codes',
            ['code', 'route'],
            registry=self.registry
        )

        self.current_connections = Gauge(
            'apisix_nginx_http_current_connections',
            'Current connections',
            registry=self.registry
        )

        self.bandwidth = Counter(
            'apisix_bandwidth',
            'Bandwidth usage',
            ['type'],
            registry=self.registry
        )

    def generate_metrics(self):
        """生成模拟的指标数据"""
        while True:
            try:
                # 模拟不同的路由和状态码
                routes = ['99', '10', '20', '30']  # 对应不同的APISIX路由ID
                methods = ['GET', 'POST', 'PUT', 'DELETE']
                status_codes = ['200', '404', '500', '201', '400']

                for _ in range(random.randint(5, 15)):
                    route = random.choice(routes)
                    method = random.choice(methods)
                    status = random.choice(status_codes)

                    # 大部分请求是成功的
                    if random.random() < 0.8:
                        status = '200'
                    elif random.random() < 0.9:
                        status = '404'

                    # 增加请求计数
                    self.http_requests_total.labels(
                        method=method,
                        status=status,
                        route=route
                    ).inc()

                    # 记录状态码
                    self.http_status.labels(
                        code=status,
                        route=route
                    ).inc()

                    # 记录请求延迟
                    latency = random.uniform(0.01, 0.5)
                    if random.random() < 0.05:  # 5%的慢请求
                        latency = random.uniform(1.0, 3.0)

                    self.http_request_duration.labels(
                        method=method,
                        route=route
                    ).observe(latency)

                # 更新连接数
                connections = random.randint(10, 100)
                self.current_connections.set(connections)

                # 更新带宽使用
                self.bandwidth.labels(type='in').inc(random.randint(1000, 10000))
                self.bandwidth.labels(type='out').inc(random.randint(500, 5000))

                time.sleep(random.uniform(1, 3))

            except Exception as e:
                print(f"生成指标时出错: {e}")
                time.sleep(5)

    def start_server(self):
        """启动指标服务器"""
        start_http_server(self.port, registry=self.registry)
        print(f"APISIX指标模拟服务器启动在端口 {self.port}")
        print(f"指标端点: http://localhost:{self.port}/metrics")

        # 在后台线程中生成指标
        metrics_thread = threading.Thread(target=self.generate_metrics, daemon=True)
        metrics_thread.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n停止指标生成服务器...")

def main():
    print("启动APISIX指标模拟器...")
    simulator = APISIXMetricsSimulator(port=8090)
    simulator.start_server()

if __name__ == "__main__":
    main()