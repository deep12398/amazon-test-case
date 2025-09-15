#!/usr/bin/env python3
"""
Grafana仪表板配置脚本
为Amazon产品追踪系统创建监控仪表板
"""

import json
import requests
import time
from typing import Dict, Any


class GrafanaSetup:
    """Grafana配置管理器"""

    def __init__(self):
        self.grafana_url = "http://localhost:3000"
        self.grafana_user = "admin"
        self.grafana_password = "admin123"

    def wait_for_grafana(self, max_attempts: int = 30):
        """等待Grafana启动"""
        print("🔄 等待Grafana启动...")

        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{self.grafana_url}/api/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Grafana已启动")
                    return True
            except requests.exceptions.RequestException:
                pass

            time.sleep(2)
            print(f"  尝试 {attempt + 1}/{max_attempts}...")

        print("❌ Grafana启动超时")
        return False

    def create_prometheus_datasource(self):
        """创建Prometheus数据源"""
        print("🔧 配置Prometheus数据源...")

        datasource_config = {
            "name": "Prometheus",
            "type": "prometheus",
            "url": "http://localhost:9090",
            "access": "proxy",
            "isDefault": True,
            "jsonData": {
                "httpMethod": "POST",
                "timeInterval": "15s"
            }
        }

        try:
            response = requests.post(
                f"{self.grafana_url}/api/datasources",
                json=datasource_config,
                auth=(self.grafana_user, self.grafana_password)
            )

            if response.status_code in [200, 409]:  # 200=创建成功, 409=已存在
                print("✅ Prometheus数据源配置完成")
                return True
            else:
                print(f"❌ 数据源配置失败: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ 连接Grafana失败: {e}")
            return False

    def create_apisix_dashboard(self):
        """创建APISIX监控仪表板"""
        print("📊 创建APISIX监控仪表板...")

        dashboard_config = {
            "dashboard": {
                "id": None,
                "title": "APISIX Gateway Monitoring",
                "tags": ["apisix", "gateway", "monitoring"],
                "timezone": "browser",
                "panels": [
                    {
                        "id": 1,
                        "title": "API Request Rate",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "rate(apisix_http_requests_total[5m])",
                                "refId": "A"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "palette-classic"},
                                "custom": {"displayMode": "list", "showUnfilled": True},
                                "mappings": [],
                                "thresholds": {
                                    "mode": "absolute",
                                    "steps": [
                                        {"color": "green", "value": None},
                                        {"color": "red", "value": 80}
                                    ]
                                }
                            }
                        },
                        "options": {
                            "reduceOptions": {
                                "values": False,
                                "calcs": ["lastNotNull"],
                                "fields": ""
                            },
                            "orientation": "auto",
                            "textMode": "auto",
                            "colorMode": "value",
                            "graphMode": "area",
                            "justifyMode": "auto"
                        }
                    },
                    {
                        "id": 2,
                        "title": "Total HTTP Requests",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "apisix_http_requests_total",
                                "refId": "A"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "thresholds"},
                                "mappings": [],
                                "thresholds": {
                                    "mode": "absolute",
                                    "steps": [
                                        {"color": "green", "value": None},
                                        {"color": "red", "value": 80}
                                    ]
                                }
                            }
                        },
                        "options": {
                            "reduceOptions": {
                                "values": False,
                                "calcs": ["lastNotNull"],
                                "fields": ""
                            },
                            "orientation": "auto",
                            "textMode": "auto",
                            "colorMode": "value",
                            "graphMode": "area",
                            "justifyMode": "auto"
                        }
                    },
                    {
                        "id": 3,
                        "title": "HTTP Request Latency",
                        "type": "timeseries",
                        "targets": [
                            {
                                "expr": "histogram_quantile(0.50, rate(apisix_http_latency_bucket[5m]))",
                                "refId": "A",
                                "legendFormat": "50th percentile"
                            },
                            {
                                "expr": "histogram_quantile(0.95, rate(apisix_http_latency_bucket[5m]))",
                                "refId": "B",
                                "legendFormat": "95th percentile"
                            },
                            {
                                "expr": "histogram_quantile(0.99, rate(apisix_http_latency_bucket[5m]))",
                                "refId": "C",
                                "legendFormat": "99th percentile"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8},
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "palette-classic"},
                                "custom": {
                                    "drawStyle": "line",
                                    "lineInterpolation": "linear",
                                    "barAlignment": 0,
                                    "lineWidth": 1,
                                    "fillOpacity": 0,
                                    "gradientMode": "none",
                                    "spanNulls": False,
                                    "insertNulls": False,
                                    "showPoints": "auto",
                                    "pointSize": 5,
                                    "stacking": {"mode": "none", "group": "A"},
                                    "axisPlacement": "auto",
                                    "axisLabel": "",
                                    "axisColorMode": None,
                                    "scaleDistribution": {"type": "linear"},
                                    "axisCenteredZero": False,
                                    "hideFrom": {"legend": False, "tooltip": False, "vis": False},
                                    "thresholdsStyle": {"mode": "off"}
                                },
                                "mappings": [],
                                "unit": "ms"
                            }
                        },
                        "options": {
                            "tooltip": {"mode": "single", "sort": "none"},
                            "legend": {"calcs": [], "displayMode": "list", "placement": "bottom"}
                        }
                    },
                    {
                        "id": 4,
                        "title": "APISIX Bandwidth Usage",
                        "type": "timeseries",
                        "targets": [
                            {
                                "expr": "rate(apisix_bandwidth[5m])",
                                "refId": "A",
                                "legendFormat": "Bandwidth Rate"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 16},
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "palette-classic"},
                                "custom": {
                                    "drawStyle": "line",
                                    "lineInterpolation": "linear",
                                    "barAlignment": 0,
                                    "lineWidth": 1,
                                    "fillOpacity": 10,
                                    "gradientMode": "none",
                                    "spanNulls": False,
                                    "insertNulls": False,
                                    "showPoints": "auto",
                                    "pointSize": 5,
                                    "stacking": {"mode": "none", "group": "A"},
                                    "axisPlacement": "auto",
                                    "axisLabel": "",
                                    "axisColorMode": None,
                                    "scaleDistribution": {"type": "linear"},
                                    "axisCenteredZero": False,
                                    "hideFrom": {"legend": False, "tooltip": False, "vis": False},
                                    "thresholdsStyle": {"mode": "off"}
                                },
                                "mappings": [],
                                "unit": "bytes"
                            }
                        },
                        "options": {
                            "tooltip": {"mode": "single", "sort": "none"},
                            "legend": {"calcs": [], "displayMode": "list", "placement": "bottom"}
                        }
                    }
                ],
                "time": {"from": "now-15m", "to": "now"},
                "timepicker": {},
                "templating": {"list": []},
                "annotations": {"list": []},
                "refresh": "5s",
                "schemaVersion": 37,
                "version": 0,
                "links": []
            },
            "overwrite": True
        }

        try:
            response = requests.post(
                f"{self.grafana_url}/api/dashboards/db",
                json=dashboard_config,
                auth=(self.grafana_user, self.grafana_password)
            )

            if response.status_code == 200:
                result = response.json()
                dashboard_url = f"{self.grafana_url}/d/{result['uid']}/apisix-gateway-monitoring"
                print(f"✅ APISIX仪表板创建成功")
                print(f"🔗 访问链接: {dashboard_url}")
                return True
            else:
                print(f"❌ 仪表板创建失败: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ 创建仪表板失败: {e}")
            return False

    def create_application_dashboard(self):
        """创建应用程序监控仪表板"""
        print("🏗️ 创建应用程序监控仪表板...")

        dashboard_config = {
            "dashboard": {
                "id": None,
                "title": "Amazon Tracker Application Monitoring",
                "tags": ["application", "microservices", "amazon-tracker"],
                "timezone": "browser",
                "panels": [
                    {
                        "id": 1,
                        "title": "Service Health Overview",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "up{job=~\".*amazon.*\"}",
                                "refId": "A",
                                "legendFormat": "{{instance}}"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 0},
                        "fieldConfig": {
                            "defaults": {
                                "color": {
                                    "mode": "thresholds"
                                },
                                "mappings": [
                                    {
                                        "options": {
                                            "0": {"text": "DOWN", "color": "red"},
                                            "1": {"text": "UP", "color": "green"}
                                        },
                                        "type": "value"
                                    }
                                ],
                                "thresholds": {
                                    "mode": "absolute",
                                    "steps": [
                                        {"color": "red", "value": None},
                                        {"color": "green", "value": 1}
                                    ]
                                }
                            }
                        },
                        "options": {
                            "reduceOptions": {
                                "values": False,
                                "calcs": ["lastNotNull"],
                                "fields": ""
                            },
                            "orientation": "auto",
                            "textMode": "auto",
                            "colorMode": "background",
                            "graphMode": "none",
                            "justifyMode": "auto"
                        }
                    },
                    {
                        "id": 2,
                        "title": "Request Rate by Service",
                        "type": "timeseries",
                        "targets": [
                            {
                                "expr": "sum(rate(apisix_http_requests_total[5m])) by (route)",
                                "refId": "A",
                                "legendFormat": "{{route}}"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "palette-classic"},
                                "custom": {
                                    "drawStyle": "line",
                                    "lineInterpolation": "linear",
                                    "barAlignment": 0,
                                    "lineWidth": 1,
                                    "fillOpacity": 0,
                                    "gradientMode": "none",
                                    "spanNulls": False,
                                    "insertNulls": False,
                                    "showPoints": "auto",
                                    "pointSize": 5,
                                    "stacking": {"mode": "none", "group": "A"},
                                    "axisPlacement": "auto",
                                    "axisLabel": "",
                                    "axisColorMode": None,
                                    "scaleDistribution": {"type": "linear"},
                                    "axisCenteredZero": False,
                                    "hideFrom": {"legend": False, "tooltip": False, "vis": False},
                                    "thresholdsStyle": {"mode": "off"}
                                },
                                "mappings": [],
                                "unit": "reqps"
                            }
                        },
                        "options": {
                            "tooltip": {"mode": "single", "sort": "none"},
                            "legend": {"calcs": [], "displayMode": "list", "placement": "bottom"}
                        }
                    },
                    {
                        "id": 3,
                        "title": "HTTP Status Codes",
                        "type": "piechart",
                        "targets": [
                            {
                                "expr": "sum(apisix_http_requests_total) by (code)",
                                "refId": "A",
                                "legendFormat": "{{code}}"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "palette-classic"},
                                "custom": {
                                    "hideFrom": {"legend": False, "tooltip": False, "vis": False}
                                },
                                "mappings": []
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
                            "legend": {"displayMode": "list", "placement": "bottom"}
                        }
                    }
                ],
                "time": {"from": "now-15m", "to": "now"},
                "timepicker": {},
                "templating": {"list": []},
                "annotations": {"list": []},
                "refresh": "5s",
                "schemaVersion": 37,
                "version": 0,
                "links": []
            },
            "overwrite": True
        }

        try:
            response = requests.post(
                f"{self.grafana_url}/api/dashboards/db",
                json=dashboard_config,
                auth=(self.grafana_user, self.grafana_password)
            )

            if response.status_code == 200:
                result = response.json()
                dashboard_url = f"{self.grafana_url}/d/{result['uid']}/amazon-tracker-application-monitoring"
                print(f"✅ 应用程序仪表板创建成功")
                print(f"🔗 访问链接: {dashboard_url}")
                return True
            else:
                print(f"❌ 仪表板创建失败: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ 创建仪表板失败: {e}")
            return False

    def setup_all(self):
        """完整设置流程"""
        print("🚀 开始设置Grafana监控仪表板...")
        print("=" * 60)

        # 等待Grafana启动
        if not self.wait_for_grafana():
            return False

        # 配置数据源
        if not self.create_prometheus_datasource():
            return False

        # 创建仪表板
        apisix_success = self.create_apisix_dashboard()
        app_success = self.create_application_dashboard()

        print("\n" + "=" * 60)
        if apisix_success and app_success:
            print("✅ Grafana配置完成!")
            print(f"\n📊 访问Grafana: {self.grafana_url}")
            print(f"👤 用户名: {self.grafana_user}")
            print(f"🔑 密码: {self.grafana_password}")
            print("\n📈 仪表板:")
            print("  • APISIX Gateway Monitoring")
            print("  • Amazon Tracker Application Monitoring")
        else:
            print("⚠️ 部分配置可能需要手动完成")

        print("=" * 60)
        return True


if __name__ == "__main__":
    setup = GrafanaSetup()
    setup.setup_all()