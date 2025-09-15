#!/usr/bin/env python3
"""测试真实品类爬取 - 使用ASIN列表"""

import time
from datetime import datetime

import requests


def test_category_crawl_with_asins():
    """使用ASIN列表测试品类爬取"""

    print("🕷️ 测试真实Amazon品类数据爬取 (使用ASIN)")
    print("=" * 60)

    # 测试令牌
    token = "eyJ1c2VyX2lkIjogMSwgImVtYWlsIjogInRlc3RAY3Jhd2xlci5jb20iLCAidGVuYW50X2lkIjogImRlbW8tdGVuYW50IiwgImlzX3N1cGVyX2FkbWluIjogZmFsc2UsICJleHAiOiAxNzYwMjU4NDE1fQ=="

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 热门蓝牙耳机ASIN列表
    bluetooth_headphones_asins = [
        "B09JQMJHXY",  # Sony WH-1000XM4
        "B08PZHYWJS",  # Apple AirPods Max
        "B0863TXGM3",  # Jabra Elite 45h
        "B08MVGF24M",  # Anker Soundcore Q30
        "B0851C8B55",  # Audio-Technica ATH-M40x
        "B07G4YX39M",  # Sennheiser HD 450BT
        "B08YRM5D7X",  # Bose QuietComfort Earbuds
        "B0856BFBXZ",  # JBL Tune 750BTNC
        "B08QJ2KGSP",  # Plantronics BackBeat Go 810
        "B08T7BQMGG",  # Skullcandy Crusher ANC
    ]

    # 爬取请求 - 使用BatchCrawlRequest格式，但要保持原有的包装格式
    crawl_request = {
        "request": {
            "asins": bluetooth_headphones_asins,  # ASIN列表
            "marketplace": "amazon_us",
            "tracking_frequency": "daily",
            "priority": "normal",
            "config": {"category_name": "蓝牙耳机"},  # 在config中包含分类信息
        },
        "token_data": {
            "user_id": 1,
            "email": "test@crawler.com",
            "tenant_id": "demo-tenant",
            "username": "test_crawler",
            "is_super_admin": False,
            "roles": ["user"],
            "permissions": ["crawler:create", "product:read"],
            "session_id": "test-session-123",
            "exp": "2025-10-13T16:40:15Z",
            "iat": "2025-09-13T16:40:15Z",
            "jti": "test-jti-123",
        },
    }

    print("📤 发起ASIN爬取请求...")
    print(f"   品类: {crawl_request['request']['config']['category_name']}")
    print(f"   ASIN数量: {len(crawl_request['request']['asins'])}")
    print(f"   ASIN列表: {', '.join(crawl_request['request']['asins'][:5])}...")

    try:
        # 发起爬取请求 - 使用批量爬取接口
        response = requests.post(
            "http://localhost:8002/api/v1/products/batch-crawl",  # 使用批量爬取端点
            headers=headers,
            json=crawl_request,
            timeout=30,
        )

        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.text}")

        if response.status_code == 200:
            result = response.json()
            task_id = result.get("task_id")
            print("   ✅ 爬取任务创建成功!")
            print(f"   任务ID: {task_id}")
            print(f"   处理的ASIN: {result.get('asins_processed', [])}")

            # 监控任务状态
            if task_id:
                monitor_task_status(task_id, headers)

        else:
            print(f"   ❌ 请求失败: {response.status_code}")
            print(f"   错误详情: {response.text}")

    except Exception as e:
        print(f"   ❌ 请求异常: {e}")
        import traceback

        traceback.print_exc()


def monitor_task_status(task_id, headers):
    """监控任务执行状态"""
    print(f"\n📊 监控任务执行状态 (任务ID: {task_id})")
    print("-" * 40)

    for i in range(15):  # 监控2.5分钟
        try:
            response = requests.get(
                f"http://localhost:8002/api/v1/tasks/{task_id}",
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                task = response.json()
                status = task.get("status", "unknown")
                progress = task.get("progress", 0)

                print(
                    f"   [{datetime.now().strftime('%H:%M:%S')}] 状态: {status} | 进度: {progress}%"
                )

                if status in ["completed", "failed", "cancelled"]:
                    if status == "completed":
                        print("   ✅ 任务完成!")
                        show_crawled_products(headers)
                    else:
                        print(
                            f"   ❌ 任务失败: {task.get('error_message', 'Unknown error')}"
                        )
                    break

            else:
                print(f"   ⚠️ 无法查询任务状态: {response.status_code}")

        except Exception as e:
            print(f"   ⚠️ 查询任务状态异常: {e}")

        time.sleep(10)

    print("   📝 监控结束")


def show_crawled_products(headers):
    """显示爬取到的产品"""
    print("\n📦 显示爬取到的产品")
    print("-" * 40)

    try:
        response = requests.get(
            "http://localhost:8002/api/v1/products/categories/蓝牙耳机/products?limit=20",
            headers=headers,
            timeout=10,
        )

        if response.status_code == 200:
            products = response.json()
            print(f"   找到 {len(products)} 个产品:")

            for i, product in enumerate(products[:10], 1):
                print(
                    f"   {i}. {product.get('asin')} - {product.get('title', 'Unknown')[:50]}..."
                )
                print(
                    f"      价格: ${product.get('current_price', 'N/A')} | 排名: #{product.get('current_rank', 'N/A')}"
                )
                print(
                    f"      评分: {product.get('current_rating', 'N/A')}/5 | 评价: {product.get('review_count', 'N/A')}"
                )

        else:
            print(f"   ⚠️ 无法获取产品列表: {response.status_code}")
            print(f"   响应: {response.text}")

    except Exception as e:
        print(f"   ⚠️ 获取产品列表异常: {e}")


if __name__ == "__main__":
    test_category_crawl_with_asins()
