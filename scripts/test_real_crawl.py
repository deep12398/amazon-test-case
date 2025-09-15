#!/usr/bin/env python3
"""测试真实Amazon品类数据爬取"""

import time
from datetime import datetime

import requests


def test_category_crawl():
    """测试品类爬取功能"""

    print("🕷️ 测试真实Amazon品类数据爬取")
    print("=" * 60)

    # 测试令牌
    token = "eyJ1c2VyX2lkIjogMSwgImVtYWlsIjogInRlc3RAY3Jhd2xlci5jb20iLCAidGVuYW50X2lkIjogImRlbW8tdGVuYW50IiwgImlzX3N1cGVyX2FkbWluIjogZmFsc2UsICJleHAiOiAxNzYwMjU4NDE1fQ=="

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 爬取请求
    crawl_request = {
        "request": {
            "category_url": "https://www.amazon.com/s?k=bluetooth+headphones&ref=nb_sb_noss_2",
            "category_name": "蓝牙耳机",
            "product_limit": 10,
            "sort_by": "best_seller",
            "tracking_frequency": "daily",
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

    print("📤 发起品类爬取请求...")
    print(f"   URL: {crawl_request['request']['category_url']}")
    print(f"   品类: {crawl_request['request']['category_name']}")
    print(f"   产品数量: {crawl_request['request']['product_limit']}")

    try:
        # 发起爬取请求
        response = requests.post(
            "http://localhost:8002/api/v1/products/category-crawl",
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
            print(f"   找到的ASIN: {result.get('asins_found', [])}")

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

    for i in range(12):  # 监控2分钟
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

        else:
            print(f"   ⚠️ 无法获取产品列表: {response.status_code}")

    except Exception as e:
        print(f"   ⚠️ 获取产品列表异常: {e}")


if __name__ == "__main__":
    test_category_crawl()
