#!/usr/bin/env python3
"""
创建专门的APISIX Prometheus监控仪表板
"""

import json
import requests


def create_apisix_prometheus_dashboard():
    """创建详细的APISIX Prometheus仪表板"""
    grafana_url = "http://localhost:3000"
    grafana_user = "admin"
    grafana_password = "admin123"

    dashboard_config = {
        "dashboard": {
            "id": None,
            "title": "APISIX Gateway - Prometheus Metrics",
            "tags": ["apisix", "prometheus", "gateway", "api"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "Total HTTP Requests",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "apisix_http_requests_total",
                            "refId": "A",
                            "legendFormat": "Total Requests"
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
                                    {"color": "yellow", "value": 100},
                                    {"color": "red", "value": 500}
                                ]
                            },
                            "unit": "short"
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
                        "graphMode": "area",
                        "justifyMode": "auto"
                    }
                },
                {
                    "id": 2,
                    "title": "HTTP Request Rate (per second)",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "rate(apisix_http_requests_total[1m])",
                            "refId": "A",
                            "legendFormat": "Requests/sec"
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
                                    {"color": "yellow", "value": 5},
                                    {"color": "red", "value": 20}
                                ]
                            },
                            "unit": "reqps"
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
                        "graphMode": "area",
                        "justifyMode": "auto"
                    }
                },
                {
                    "id": 3,
                    "title": "Active Connections",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "apisix_nginx_http_current_connections",
                            "refId": "A",
                            "legendFormat": "Active Connections"
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
                                    {"color": "yellow", "value": 50},
                                    {"color": "red", "value": 100}
                                ]
                            },
                            "unit": "short"
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
                        "graphMode": "area",
                        "justifyMode": "auto"
                    }
                },
                {
                    "id": 4,
                    "title": "Bandwidth Usage",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "rate(apisix_bandwidth[1m])",
                            "refId": "A",
                            "legendFormat": "Bandwidth Rate"
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
                                    {"color": "yellow", "value": 1000000},
                                    {"color": "red", "value": 10000000}
                                ]
                            },
                            "unit": "Bps"
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
                        "graphMode": "area",
                        "justifyMode": "auto"
                    }
                },
                {
                    "id": 5,
                    "title": "HTTP Requests Over Time",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "rate(apisix_http_requests_total[1m])",
                            "refId": "A",
                            "legendFormat": "Request Rate"
                        },
                        {
                            "expr": "apisix_http_requests_total",
                            "refId": "B",
                            "legendFormat": "Total Requests"
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
                                "lineWidth": 2,
                                "fillOpacity": 10,
                                "gradientMode": "none",
                                "spanNulls": False,
                                "insertNulls": False,
                                "showPoints": "never",
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
                            "unit": "short"
                        },
                        "overrides": [
                            {
                                "matcher": {"id": "byName", "options": "Request Rate"},
                                "properties": [
                                    {"id": "unit", "value": "reqps"},
                                    {"id": "custom.axisPlacement", "value": "left"}
                                ]
                            },
                            {
                                "matcher": {"id": "byName", "options": "Total Requests"},
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
                    "title": "Connection Status",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "apisix_nginx_http_current_connections",
                            "refId": "A",
                            "legendFormat": "Active Connections"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "palette-classic"},
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "linear",
                                "barAlignment": 0,
                                "lineWidth": 2,
                                "fillOpacity": 10,
                                "gradientMode": "none",
                                "spanNulls": False,
                                "insertNulls": False,
                                "showPoints": "never",
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
                            "unit": "short",
                            "min": 0
                        }
                    },
                    "options": {
                        "tooltip": {"mode": "single", "sort": "none"},
                        "legend": {"calcs": [], "displayMode": "list", "placement": "bottom"}
                    }
                },
                {
                    "id": 7,
                    "title": "Bandwidth Usage Over Time",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "rate(apisix_bandwidth[1m])",
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
                                "lineWidth": 2,
                                "fillOpacity": 10,
                                "gradientMode": "hue",
                                "spanNulls": False,
                                "insertNulls": False,
                                "showPoints": "never",
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
                            "unit": "Bps",
                            "min": 0
                        }
                    },
                    "options": {
                        "tooltip": {"mode": "single", "sort": "none"},
                        "legend": {"calcs": [], "displayMode": "list", "placement": "bottom"}
                    }
                },
                {
                    "id": 8,
                    "title": "APISIX Etcd Metrics",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "apisix_etcd_modify_indexes",
                            "refId": "A",
                            "legendFormat": "Etcd Modify Index"
                        },
                        {
                            "expr": "apisix_etcd_reachable",
                            "refId": "B",
                            "legendFormat": "Etcd Reachable"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 24, "x": 0, "y": 24},
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "palette-classic"},
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "linear",
                                "barAlignment": 0,
                                "lineWidth": 2,
                                "fillOpacity": 0,
                                "gradientMode": "none",
                                "spanNulls": False,
                                "insertNulls": False,
                                "showPoints": "never",
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
                            "unit": "short"
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
                "refresh_intervals": ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h"],
                "time_options": ["5m", "15m", "1h", "6h", "12h", "24h", "2d", "7d", "30d"]
            },
            "templating": {"list": []},
            "annotations": {"list": []},
            "refresh": "5s",
            "schemaVersion": 37,
            "version": 0,
            "links": [],
            "description": "APISIX API网关的详细Prometheus监控指标，包括请求率、连接状态、带宽使用和etcd健康状况"
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
            dashboard_url = f"{grafana_url}/d/{result['uid']}/apisix-gateway-prometheus-metrics"
            print(f"✅ APISIX Prometheus仪表板创建成功")
            print(f"🔗 访问链接: {dashboard_url}")
            return True
        else:
            print(f"❌ 仪表板创建失败: {response.status_code} - {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ 创建仪表板失败: {e}")
        return False


if __name__ == "__main__":
    print("📊 创建APISIX Prometheus监控仪表板...")
    create_apisix_prometheus_dashboard()