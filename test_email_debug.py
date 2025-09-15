#!/usr/bin/env python3
"""测试邮件发送功能的调试脚本"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# 添加项目路径
sys.path.insert(0, '/Users/elias/code/amazon/amazon-test')

# 加载环境变量
load_dotenv('/Users/elias/code/amazon/amazon-test/.env.local')

from amazon_tracker.common.notification.email_service import EmailNotifier

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_email_connection():
    """测试邮件连接和发送"""
    print("🔧 开始测试邮件服务...")

    try:
        # 初始化邮件服务
        notifier = EmailNotifier()

        print(f"SMTP主机: {notifier.smtp_host}")
        print(f"SMTP端口: {notifier.smtp_port}")
        print(f"SMTP用户: {notifier.smtp_user}")
        print(f"发件人: {notifier.from_email}")
        print(f"通知邮箱: {notifier.notification_email}")

        # 测试基本邮件发送
        print("\n📧 测试基本邮件发送...")
        success = notifier.send_email(
            to_email=notifier.notification_email,
            subject="测试邮件 - Amazon监控系统",
            html_body="""
            <html>
            <body>
                <h2>邮件测试成功!</h2>
                <p>这是一封测试邮件，用于验证邮件服务配置。</p>
                <p>发送时间: {}</p>
            </body>
            </html>
            """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            text_body="邮件测试成功! 发送时间: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )

        if success:
            print("✅ 基本邮件发送成功!")
        else:
            print("❌ 基本邮件发送失败!")

        # 测试价格变化通知
        print("\n💰 测试价格变化通知...")
        price_alert_data = {
            "asin": "B01EXAMPLE",
            "title": "测试产品 - Sony WH-1000XM4 无线降噪耳机",
            "old_price": 299.99,
            "new_price": 249.99,
            "change_percent": 16.67,
            "alert_type": "price_change",
            "timestamp": datetime.now().isoformat()
        }

        price_success = notifier.send_price_change_alert(price_alert_data)

        if price_success:
            print("✅ 价格变化通知发送成功!")
        else:
            print("❌ 价格变化通知发送失败!")

        # 测试BSR排名通知
        print("\n📊 测试BSR排名通知...")
        rank_alert_data = {
            "asin": "B01EXAMPLE",
            "title": "测试产品 - Sony WH-1000XM4 无线降噪耳机",
            "old_rank": 100,
            "new_rank": 150,
            "change_percent": 50.0,
            "alert_type": "bsr_change",
            "timestamp": datetime.now().isoformat()
        }

        rank_success = notifier.send_rank_alert(rank_alert_data)

        if rank_success:
            print("✅ BSR排名通知发送成功!")
        else:
            print("❌ BSR排名通知发送失败!")

        return success and price_success and rank_success

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Amazon监控系统 - 邮件服务测试")
    print("=" * 50)

    # 检查环境变量
    print("\n🔍 检查环境变量...")
    required_vars = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "FROM_EMAIL", "NOTIFICATION_EMAIL"]
    missing_vars = []

    for var in required_vars:
        value = os.getenv(var)
        if value:
            # 隐藏密码
            if "PASSWORD" in var:
                print(f"✅ {var}: {'*' * len(value)}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: 未设置")
            missing_vars.append(var)

    if missing_vars:
        print(f"\n⚠️  缺少环境变量: {', '.join(missing_vars)}")
        print("请检查 .env.local 文件配置")
        sys.exit(1)

    # 执行测试
    success = test_email_connection()

    print("\n" + "=" * 50)
    if success:
        print("🎉 所有邮件测试通过!")
    else:
        print("💥 邮件测试失败，请检查配置和网络连接")
    print("=" * 50)