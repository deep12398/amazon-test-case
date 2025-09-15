#!/usr/bin/env python3
"""
创建带有mock数据的Grafana仪表板
使用TestData数据源直接显示模拟的监控数据
"""

import json
import requests
import time
from datetime import datetime


def create_mock_data_dashboard():
    """创建包含mock数据的仪表板"""
    grafana_url = "http://localhost:3000"
    grafana_user = "admin"
    grafana_password = "admin123"

    # 创建TestData数据源（如果不存在）
    testdata_source = {
        "name": "TestData",
        "type": "testdata",
        "access": "proxy",
        "isDefault": False
    }

    try:
        # 尝试创建TestData数据源
        requests.post(
            f"{grafana_url}/api/datasources",
            json=testdata_source,
            auth=(grafana_user, grafana_password)
        )
    except:
        pass  # 可能已存在

    # 创建mock数据仪表板
    dashboard_config = {
        "dashboard": {
            "id": None,
            "title": "Amazon Tracker - Mock Monitoring Data",
            "tags": ["mock", "demo", "amazon-tracker"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "API Request Rate (Mock)",
                    "type": "timeseries",
                    "targets": [
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "A",
                            "alias": "API Requests/sec",
                            "min": 0,
                            "max": 50,
                            "startValue": 10,
                            "noise": 5
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "palette-classic"},
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth",
                                "lineWidth": 2,
                                "fillOpacity": 10,
                                "gradientMode": "opacity",
                                "showPoints": "never",
                                "pointSize": 5
                            },
                            "mappings": [],
                            "unit": "reqps",
                            "min": 0,
                            "displayName": "请求率"
                        }
                    },
                    "options": {
                        "tooltip": {"mode": "multi", "sort": "none"},
                        "legend": {"calcs": [], "displayMode": "list", "placement": "bottom"}
                    }
                },
                {
                    "id": 2,
                    "title": "Response Time (Mock)",
                    "type": "timeseries",
                    "targets": [
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "A",
                            "alias": "Avg Response Time",
                            "min": 50,
                            "max": 500,
                            "startValue": 150,
                            "noise": 30
                        },
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "B",
                            "alias": "95th Percentile",
                            "min": 100,
                            "max": 800,
                            "startValue": 300,
                            "noise": 50
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "palette-classic"},
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth",
                                "lineWidth": 2,
                                "fillOpacity": 0,
                                "showPoints": "never"
                            },
                            "mappings": [],
                            "unit": "ms",
                            "min": 0,
                            "displayName": "响应时间"
                        }
                    },
                    "options": {
                        "tooltip": {"mode": "multi", "sort": "none"},
                        "legend": {"calcs": [], "displayMode": "list", "placement": "bottom"}
                    }
                },
                {
                    "id": 3,
                    "title": "Current Metrics Summary",
                    "type": "stat",
                    "targets": [
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "A",
                            "alias": "Total Requests",
                            "min": 1000,
                            "max": 10000,
                            "startValue": 5000,
                            "noise": 100
                        },
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "B",
                            "alias": "Active Connections",
                            "min": 10,
                            "max": 100,
                            "startValue": 45,
                            "noise": 8
                        },
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "C",
                            "alias": "Error Rate %",
                            "min": 0,
                            "max": 5,
                            "startValue": 1.2,
                            "noise": 0.5
                        }
                    ],
                    "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8},
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "thresholds"},
                            "mappings": [],
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"color": "green", "value": None},
                                    {"color": "yellow", "value": 3},
                                    {"color": "red", "value": 5}
                                ]
                            },
                            "unit": "short"
                        },
                        "overrides": [
                            {
                                "matcher": {"id": "byName", "options": "Total Requests"},
                                "properties": [
                                    {"id": "unit", "value": "short"},
                                    {"id": "displayName", "value": "总请求数"}
                                ]
                            },
                            {
                                "matcher": {"id": "byName", "options": "Active Connections"},
                                "properties": [
                                    {"id": "unit", "value": "short"},
                                    {"id": "displayName", "value": "活跃连接"}
                                ]
                            },
                            {
                                "matcher": {"id": "byName", "options": "Error Rate %"},
                                "properties": [
                                    {"id": "unit", "value": "percent"},
                                    {"id": "displayName", "value": "错误率"}
                                ]
                            }
                        ]
                    },
                    "options": {
                        "reduceOptions": {
                            "values": False,
                            "calcs": ["lastNotNull"],
                            "fields": ""
                        },
                        "orientation": "auto",
                        "textMode": "value_and_name",
                        "colorMode": "background",
                        "graphMode": "area",
                        "justifyMode": "center"
                    }
                },
                {
                    "id": 4,
                    "title": "Service Health Status",
                    "type": "timeseries",
                    "targets": [
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "A",
                            "alias": "User Service",
                            "min": 0.95,
                            "max": 1.0,
                            "startValue": 0.99,
                            "noise": 0.02
                        },
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "B",
                            "alias": "Core Service",
                            "min": 0.90,
                            "max": 1.0,
                            "startValue": 0.97,
                            "noise": 0.03
                        },
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "C",
                            "alias": "Crawler Service",
                            "min": 0.85,
                            "max": 1.0,
                            "startValue": 0.94,
                            "noise": 0.04
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "palette-classic"},
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "linear",
                                "lineWidth": 2,
                                "fillOpacity": 20,
                                "showPoints": "never"
                            },
                            "mappings": [],
                            "unit": "percentunit",
                            "min": 0.8,
                            "max": 1.0,
                            "displayName": "服务可用性"
                        }
                    },
                    "options": {
                        "tooltip": {"mode": "multi", "sort": "none"},
                        "legend": {"calcs": [], "displayMode": "list", "placement": "bottom"}
                    }
                },
                {
                    "id": 5,
                    "title": "Database Performance",
                    "type": "timeseries",
                    "targets": [
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "A",
                            "alias": "Query Time",
                            "min": 20,
                            "max": 200,
                            "startValue": 80,
                            "noise": 15
                        },
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "B",
                            "alias": "Active Connections",
                            "min": 5,
                            "max": 50,
                            "startValue": 20,
                            "noise": 5
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "palette-classic"},
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth",
                                "lineWidth": 2,
                                "fillOpacity": 10,
                                "showPoints": "never"
                            },
                            "mappings": [],
                            "unit": "ms",
                            "min": 0,
                            "displayName": "数据库性能"
                        },
                        "overrides": [
                            {
                                "matcher": {"id": "byName", "options": "Active Connections"},
                                "properties": [
                                    {"id": "unit", "value": "short"},
                                    {"id": "custom.axisPlacement", "value": "right"}
                                ]
                            }
                        ]
                    },
                    "options": {
                        "tooltip": {"mode": "multi", "sort": "none"},
                        "legend": {"calcs": [], "displayMode": "list", "placement": "bottom"}
                    }
                },
                {
                    "id": 6,
                    "title": "Traffic Distribution by Endpoint",
                    "type": "piechart",
                    "targets": [
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "A",
                            "alias": "/api/v1/products",
                            "min": 100,
                            "max": 500,
                            "startValue": 300,
                            "noise": 20
                        },
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "B",
                            "alias": "/api/v1/auth/login",
                            "min": 50,
                            "max": 200,
                            "startValue": 120,
                            "noise": 15
                        },
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "C",
                            "alias": "/api/v1/users/me",
                            "min": 80,
                            "max": 300,
                            "startValue": 180,
                            "noise": 25
                        },
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "D",
                            "alias": "/health",
                            "min": 200,
                            "max": 400,
                            "startValue": 280,
                            "noise": 10
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 24},
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "palette-classic"},
                            "custom": {
                                "hideFrom": {"legend": False, "tooltip": False, "vis": False}
                            },
                            "mappings": [],
                            "unit": "short",
                            "displayName": "请求分布"
                        }
                    },
                    "options": {
                        "reduceOptions": {
                            "values": False,
                            "calcs": ["lastNotNull"],
                            "fields": ""
                        },
                        "pieType": "pie",
                        "tooltip": {"mode": "single", "sort": "none"},
                        "legend": {"displayMode": "list", "placement": "right", "values": ["value"]}
                    }
                },
                {
                    "id": 7,
                    "title": "System Resources",
                    "type": "timeseries",
                    "targets": [
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "A",
                            "alias": "CPU Usage %",
                            "min": 20,
                            "max": 80,
                            "startValue": 45,
                            "noise": 8
                        },
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "B",
                            "alias": "Memory Usage %",
                            "min": 40,
                            "max": 85,
                            "startValue": 65,
                            "noise": 5
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 24},
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "palette-classic"},
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth",
                                "lineWidth": 2,
                                "fillOpacity": 15,
                                "showPoints": "never"
                            },
                            "mappings": [],
                            "unit": "percent",
                            "min": 0,
                            "max": 100,
                            "displayName": "系统资源"
                        }
                    },
                    "options": {
                        "tooltip": {"mode": "multi", "sort": "none"},
                        "legend": {"calcs": [], "displayMode": "list", "placement": "bottom"}
                    }
                }
            ],
            "time": {"from": "now-1h", "to": "now"},
            "timepicker": {
                "refresh_intervals": ["5s", "10s", "30s", "1m", "5m"],
                "time_options": ["5m", "15m", "1h", "6h", "12h", "24h"]
            },
            "templating": {"list": []},
            "annotations": {"list": []},
            "refresh": "5s",
            "schemaVersion": 37,
            "version": 0,
            "links": [],
            "description": "Amazon产品追踪系统的模拟监控数据仪表板，展示各种实时性能指标和系统状态"
        },
        "overwrite": True
    }

    try:
        response = requests.post(
            f"{grafana_url}/api/dashboards/db",
            json=dashboard_config,
            auth=(grafana_user, grafana_password)
        )

        if response.status_code == 200:
            result = response.json()
            dashboard_url = f"{grafana_url}/d/{result['uid']}/amazon-tracker-mock-monitoring-data"
            print(f"✅ Mock数据仪表板创建成功")
            print(f"🔗 访问链接: {dashboard_url}")
            return True
        else:
            print(f"❌ 仪表板创建失败: {response.status_code} - {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ 创建仪表板失败: {e}")
        return False


def create_apisix_mock_dashboard():
    """创建APISIX专用的mock数据仪表板"""
    grafana_url = "http://localhost:3000"
    grafana_user = "admin"
    grafana_password = "admin123"

    dashboard_config = {
        "dashboard": {
            "id": None,
            "title": "APISIX Gateway - Mock Data",
            "tags": ["apisix", "mock", "gateway"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "HTTP Requests/sec",
                    "type": "stat",
                    "targets": [
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "A",
                            "alias": "Requests/sec",
                            "min": 5,
                            "max": 100,
                            "startValue": 25,
                            "noise": 8
                        }
                    ],
                    "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "thresholds"},
                            "mappings": [],
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"color": "green", "value": None},
                                    {"color": "yellow", "value": 50},
                                    {"color": "red", "value": 80}
                                ]
                            },
                            "unit": "reqps",
                            "displayName": "请求率"
                        }
                    },
                    "options": {
                        "reduceOptions": {
                            "values": False,
                            "calcs": ["lastNotNull"],
                            "fields": ""
                        },
                        "orientation": "auto",
                        "textMode": "value_and_name",
                        "colorMode": "background",
                        "graphMode": "area"
                    }
                },
                {
                    "id": 2,
                    "title": "Total Requests",
                    "type": "stat",
                    "targets": [
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "A",
                            "alias": "Total",
                            "min": 10000,
                            "max": 50000,
                            "startValue": 25000,
                            "noise": 500
                        }
                    ],
                    "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "thresholds"},
                            "mappings": [],
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"color": "green", "value": None},
                                    {"color": "yellow", "value": 30000},
                                    {"color": "red", "value": 45000}
                                ]
                            },
                            "unit": "short",
                            "displayName": "总请求数"
                        }
                    },
                    "options": {
                        "reduceOptions": {
                            "values": False,
                            "calcs": ["lastNotNull"],
                            "fields": ""
                        },
                        "orientation": "auto",
                        "textMode": "value_and_name",
                        "colorMode": "background",
                        "graphMode": "area"
                    }
                },
                {
                    "id": 3,
                    "title": "Active Connections",
                    "type": "stat",
                    "targets": [
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "A",
                            "alias": "Active",
                            "min": 10,
                            "max": 200,
                            "startValue": 80,
                            "noise": 15
                        }
                    ],
                    "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "thresholds"},
                            "mappings": [],
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"color": "green", "value": None},
                                    {"color": "yellow", "value": 150},
                                    {"color": "red", "value": 180}
                                ]
                            },
                            "unit": "short",
                            "displayName": "活跃连接"
                        }
                    },
                    "options": {
                        "reduceOptions": {
                            "values": False,
                            "calcs": ["lastNotNull"],
                            "fields": ""
                        },
                        "orientation": "auto",
                        "textMode": "value_and_name",
                        "colorMode": "background",
                        "graphMode": "area"
                    }
                },
                {
                    "id": 4,
                    "title": "Response Time",
                    "type": "stat",
                    "targets": [
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "A",
                            "alias": "Avg Response",
                            "min": 50,
                            "max": 500,
                            "startValue": 150,
                            "noise": 25
                        }
                    ],
                    "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "thresholds"},
                            "mappings": [],
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"color": "green", "value": None},
                                    {"color": "yellow", "value": 300},
                                    {"color": "red", "value": 450}
                                ]
                            },
                            "unit": "ms",
                            "displayName": "响应时间"
                        }
                    },
                    "options": {
                        "reduceOptions": {
                            "values": False,
                            "calcs": ["lastNotNull"],
                            "fields": ""
                        },
                        "orientation": "auto",
                        "textMode": "value_and_name",
                        "colorMode": "background",
                        "graphMode": "area"
                    }
                },
                {
                    "id": 5,
                    "title": "APISIX Request Timeline",
                    "type": "timeseries",
                    "targets": [
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "A",
                            "alias": "Requests/sec",
                            "min": 5,
                            "max": 100,
                            "startValue": 35,
                            "noise": 12
                        },
                        {
                            "datasource": {"type": "testdata", "uid": "testdata"},
                            "scenarioId": "random_walk",
                            "refId": "B",
                            "alias": "Error Rate/sec",
                            "min": 0,
                            "max": 5,
                            "startValue": 1,
                            "noise": 0.5
                        }
                    ],
                    "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8},
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "palette-classic"},
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth",
                                "lineWidth": 2,
                                "fillOpacity": 10,
                                "showPoints": "never"
                            },
                            "mappings": [],
                            "unit": "reqps",
                            "min": 0,
                            "displayName": "APISIX请求时序"
                        }
                    },
                    "options": {
                        "tooltip": {"mode": "multi", "sort": "none"},
                        "legend": {"calcs": [], "displayMode": "list", "placement": "bottom"}
                    }
                }
            ],
            "time": {"from": "now-30m", "to": "now"},
            "timepicker": {
                "refresh_intervals": ["5s", "10s", "30s", "1m"],
                "time_options": ["5m", "15m", "1h", "6h", "12h", "24h"]
            },
            "templating": {"list": []},
            "annotations": {"list": []},
            "refresh": "5s",
            "schemaVersion": 37,
            "version": 0,
            "links": [],
            "description": "APISIX网关的模拟监控数据，实时显示网关性能指标"
        },
        "overwrite": True
    }

    try:
        response = requests.post(
            f"{grafana_url}/api/dashboards/db",
            json=dashboard_config,
            auth=(grafana_user, grafana_password)
        )

        if response.status_code == 200:
            result = response.json()
            dashboard_url = f"{grafana_url}/d/{result['uid']}/apisix-gateway-mock-data"
            print(f"✅ APISIX Mock数据仪表板创建成功")
            print(f"🔗 访问链接: {dashboard_url}")
            return True
        else:
            print(f"❌ 仪表板创建失败: {response.status_code} - {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ 创建仪表板失败: {e}")
        return False


def main():
    """主函数"""
    print("🎯 创建Amazon追踪系统Mock监控仪表板...")
    print("=" * 60)

    # 创建综合监控仪表板
    success1 = create_mock_data_dashboard()

    # 创建APISIX专用仪表板
    success2 = create_apisix_mock_dashboard()

    print("\n" + "=" * 60)
    if success1 and success2:
        print("✅ 所有Mock数据仪表板创建成功!")
        print(f"\n📊 访问Grafana: http://localhost:3000")
        print(f"👤 用户名: admin")
        print(f"🔑 密码: admin123")
        print(f"\n📈 新增仪表板:")
        print(f"  • Amazon Tracker - Mock Monitoring Data")
        print(f"  • APISIX Gateway - Mock Data")
        print(f"\n🔄 仪表板每5秒自动刷新，显示实时变化的模拟数据")
    else:
        print("⚠️ 部分仪表板创建可能有问题")

    print("=" * 60)


if __name__ == "__main__":
    main()