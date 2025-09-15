"""APISIX路由和认证配置脚本"""

import json
import os
from typing import Any

import requests


class APISIXConfig:
    """APISIX配置管理器"""

    def __init__(
        self,
        admin_url: str = "http://localhost:9180",
        api_key: str = "dev-admin-key-123",
    ):
        self.admin_url = admin_url
        self.headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    def create_upstream(self, upstream_id: str, name: str, nodes: dict[str, int]):
        """创建上游服务"""
        upstream_config = {
            "name": name,
            "type": "roundrobin",
            "nodes": nodes,
            "retries": 2,
            "retry_timeout": 2,
            "timeout": {"connect": 6, "send": 6, "read": 6},
            "keepalive_pool": {"size": 320, "idle_timeout": 60, "requests": 1000},
        }

        response = requests.put(
            f"{self.admin_url}/apisix/admin/upstreams/{upstream_id}",
            headers=self.headers,
            data=json.dumps(upstream_config),
        )

        if response.status_code in [200, 201]:
            print(f"✓ 创建上游服务: {name}")
            return response.json()
        else:
            print(f"❌ 创建上游服务失败: {response.text}")
            return None

    def create_jwt_auth_plugin_config(self):
        """创建JWT认证插件配置"""
        jwt_secret = os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key")

        return {
            "jwt-auth": {
                "key": "user_key",
                "secret": jwt_secret,
                "algorithm": "HS256",
                "exp": 86400,  # 24小时
                "header": "Authorization",
                "query": "token",
            }
        }

    def create_route(self, route_id: str, route_config: dict[str, Any]):
        """创建路由"""
        response = requests.put(
            f"{self.admin_url}/apisix/admin/routes/{route_id}",
            headers=self.headers,
            data=json.dumps(route_config),
        )

        if response.status_code in [200, 201]:
            print(f"✓ 创建路由: {route_config.get('name', route_id)}")
            return response.json()
        else:
            print(f"❌ 创建路由失败: {response.text}")
            return None

    def create_consumer(self, consumer_config: dict[str, Any]):
        """创建消费者"""
        username = consumer_config["username"]
        response = requests.put(
            f"{self.admin_url}/apisix/admin/consumers/{username}",
            headers=self.headers,
            data=json.dumps(consumer_config),
        )

        if response.status_code in [200, 201]:
            print(f"✓ 创建消费者: {username}")
            return response.json()
        else:
            print(f"❌ 创建消费者失败: {response.text}")
            return None


def setup_user_service_routes():
    """设置用户服务路由"""

    apisix = APISIXConfig()

    # 1. 创建用户服务上游
    apisix.create_upstream(
        "user-service",
        "用户服务",
        {"127.0.0.1:8001": 1},  # 假设用户服务运行在8001端口
    )

    # 2. 创建公开路由（不需要认证）
    public_routes = [
        {
            "id": "user-service-public",
            "name": "用户服务公开接口",
            "uri": "/api/v1/auth/*",
            "methods": ["GET", "POST"],
            "upstream_id": "user-service",
            "plugins": {
                "cors": {
                    "allow_origins": "*",
                    "allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
                    "allow_headers": "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization",
                    "max_age": 1728000,
                },
                "prometheus": {"prefer_name": True},
            },
        }
    ]

    # 3. 创建需要认证的路由
    protected_routes = [
        {
            "id": "user-service-protected",
            "name": "用户服务受保护接口",
            "uri": "/api/v1/users/*",
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "upstream_id": "user-service",
            "plugins": {
                "jwt-auth": {"header": "Authorization", "query": "token"},
                "cors": {
                    "allow_origins": "*",
                    "allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
                    "allow_headers": "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization",
                    "max_age": 1728000,
                },
                "prometheus": {"prefer_name": True},
            },
        },
        {
            "id": "tenant-service-protected",
            "name": "租户服务受保护接口",
            "uri": "/api/v1/tenants/*",
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "upstream_id": "user-service",
            "plugins": {
                "jwt-auth": {"header": "Authorization", "query": "token"},
                "cors": {
                    "allow_origins": "*",
                    "allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
                    "allow_headers": "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization",
                    "max_age": 1728000,
                },
                "prometheus": {"prefer_name": True},
            },
        },
    ]

    # 创建所有路由
    all_routes = public_routes + protected_routes
    for route in all_routes:
        route_id = route.pop("id")
        apisix.create_route(route_id, route)

    print(f"✓ 用户服务路由配置完成，共创建 {len(all_routes)} 个路由")


def setup_core_service_routes():
    """设置核心服务路由（为将来准备）"""

    apisix = APISIXConfig()

    # 创建核心服务上游
    apisix.create_upstream(
        "core-service",
        "核心服务",
        {"127.0.0.1:8002": 1},  # 假设核心服务运行在8002端口
    )

    # 创建需要认证的路由
    core_routes = [
        {
            "id": "core-service-products",
            "name": "产品管理接口",
            "uri": "/api/v1/products/*",
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "upstream_id": "core-service",
            "plugins": {
                "jwt-auth": {"header": "Authorization", "query": "token"},
                "cors": {
                    "allow_origins": "*",
                    "allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
                    "allow_headers": "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization",
                    "max_age": 1728000,
                },
                "limit-req": {
                    "rate": 100,
                    "burst": 200,
                    "rejected_code": 429,
                    "key": "remote_addr",
                },
                "prometheus": {"prefer_name": True},
            },
        },
        {
            "id": "core-service-analytics",
            "name": "分析报告接口",
            "uri": "/api/v1/analytics/*",
            "methods": ["GET", "POST"],
            "upstream_id": "core-service",
            "plugins": {
                "jwt-auth": {"header": "Authorization", "query": "token"},
                "cors": {
                    "allow_origins": "*",
                    "allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
                    "allow_headers": "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization",
                    "max_age": 1728000,
                },
                "prometheus": {"prefer_name": True},
            },
        },
    ]

    # 创建路由
    for route in core_routes:
        route_id = route.pop("id")
        apisix.create_route(route_id, route)

    print(f"✓ 核心服务路由配置完成，共创建 {len(core_routes)} 个路由")


def setup_api_key_auth():
    """设置API Key认证"""

    apisix = APISIXConfig()

    # 创建API Key认证路由
    api_routes = [
        {
            "id": "api-products",
            "name": "产品API接口",
            "uri": "/api/products/*",
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "upstream_id": "core-service",
            "plugins": {
                "key-auth": {"header": "X-API-Key"},
                "limit-req": {
                    "rate": 60,
                    "burst": 120,
                    "rejected_code": 429,
                    "key": "consumer_name",
                },
                "prometheus": {"prefer_name": True},
            },
        },
        {
            "id": "api-analytics",
            "name": "分析API接口",
            "uri": "/api/analytics/*",
            "methods": ["GET", "POST"],
            "upstream_id": "core-service",
            "plugins": {
                "key-auth": {"header": "X-API-Key"},
                "limit-req": {
                    "rate": 30,
                    "burst": 60,
                    "rejected_code": 429,
                    "key": "consumer_name",
                },
                "prometheus": {"prefer_name": True},
            },
        },
    ]

    # 创建路由
    for route in api_routes:
        route_id = route.pop("id")
        apisix.create_route(route_id, route)

    print(f"✓ API Key认证路由配置完成，共创建 {len(api_routes)} 个路由")


def setup_global_plugins():
    """设置全局插件"""

    apisix = APISIXConfig()

    global_plugins = {
        "prometheus": {
            "prefer_name": True,
            "export_addr": {"ip": "0.0.0.0", "port": 9091},
        },
        "http-logger": {
            "uri": "http://localhost:8080/logs",
            "timeout": 3000,
            "name": "http-logger",
            "batch_max_size": 1000,
            "inactive_timeout": 5,
        },
    }

    response = requests.put(
        f"{apisix.admin_url}/apisix/admin/global_rules/1",
        headers=apisix.headers,
        data=json.dumps({"plugins": global_plugins}),
    )

    if response.status_code in [200, 201]:
        print("✓ 全局插件配置完成")
    else:
        print(f"❌ 全局插件配置失败: {response.text}")


def setup_health_check():
    """设置健康检查路由"""

    apisix = APISIXConfig()

    health_route = {
        "name": "健康检查",
        "uri": "/health",
        "methods": ["GET"],
        "plugins": {
            "mocking": {
                "response_status": 200,
                "content_type": "application/json",
                "response_example": json.dumps(
                    {
                        "status": "healthy",
                        "timestamp": "2023-01-01T00:00:00Z",
                        "services": {
                            "user_service": "healthy",
                            "core_service": "healthy",
                            "crawler_service": "healthy",
                        },
                    }
                ),
            }
        },
    }

    apisix.create_route("health-check", health_route)
    print("✓ 健康检查路由配置完成")


def main():
    """主函数"""
    print("开始配置APISIX网关认证和路由...")

    try:
        # 1. 设置用户服务路由
        print("\n1. 配置用户服务路由...")
        setup_user_service_routes()

        # 2. 设置核心服务路由
        print("\n2. 配置核心服务路由...")
        setup_core_service_routes()

        # 3. 设置API Key认证
        print("\n3. 配置API Key认证...")
        setup_api_key_auth()

        # 4. 设置全局插件
        print("\n4. 配置全局插件...")
        setup_global_plugins()

        # 5. 设置健康检查
        print("\n5. 配置健康检查...")
        setup_health_check()

        print("\n✓ APISIX网关配置完成!")
        print("\n路由配置:")
        print("- /api/v1/auth/* - 用户认证（公开）")
        print("- /api/v1/users/* - 用户管理（需JWT认证）")
        print("- /api/v1/tenants/* - 租户管理（需JWT认证）")
        print("- /api/v1/products/* - 产品管理（需JWT认证）")
        print("- /api/v1/analytics/* - 分析报告（需JWT认证）")
        print("- /api/products/* - 产品API（需API Key认证）")
        print("- /api/analytics/* - 分析API（需API Key认证）")
        print("- /health - 健康检查")

    except Exception as e:
        print(f"❌ 配置过程中发生错误: {e}")
        raise


if __name__ == "__main__":
    main()
