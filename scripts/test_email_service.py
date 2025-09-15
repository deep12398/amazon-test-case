#!/usr/bin/env python3
"""测试邮件通知服务"""

import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from amazon_tracker.common.notification.email_service import EmailNotifier


def test_basic_email():
    """测试基础邮件发送功能"""
    print("🧪 测试基础邮件发送...")

    notifier = EmailNotifier()

    # 检查配置
    if not notifier.smtp_user or not notifier.smtp_password:
        print("❌ 邮件配置未设置，请在 .env.local 中配置 SMTP_USER 和 SMTP_PASSWORD")
        return False

    print(f"📧 SMTP服务器: {notifier.smtp_host}:{notifier.smtp_port}")
    print(f"📧 发件人: {notifier.from_email}")
    print(f"📧 收件人: {notifier.notification_email}")

    # 发送测试邮件
    subject = "🧪 Amazon产品追踪系统 - 邮件服务测试"
    html_body = """
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
            <h2 style="color: #28a745; margin-top: 0;">✅ 邮件服务测试成功</h2>

            <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
                <h3 style="color: #333; margin-top: 0;">系统信息</h3>
                <p><strong>系统名称:</strong> Amazon产品追踪分析系统</p>
                <p><strong>版本:</strong> 1.0.0</p>
                <p><strong>测试时间:</strong> {}</p>
                <p><strong>邮件服务:</strong> 正常运行</p>
            </div>

            <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; margin: 15px 0;">
                <h3 style="color: #333; margin-top: 0;">功能特性</h3>
                <ul>
                    <li>✅ SMTP连接测试通过</li>
                    <li>✅ HTML邮件格式支持</li>
                    <li>✅ 价格异常预警通知</li>
                    <li>✅ BSR排名异常预警通知</li>
                    <li>✅ 自动化邮件发送</li>
                </ul>
            </div>

            <div style="text-align: center; margin-top: 20px; color: #6c757d; font-size: 12px;">
                <p>如果您收到此邮件，说明邮件通知服务配置正确！</p>
                <p>本邮件由Amazon产品追踪系统自动发送</p>
            </div>
        </div>
    </body>
    </html>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    text_body = """
Amazon产品追踪系统 - 邮件服务测试

系统信息:
- 系统名称: Amazon产品追踪分析系统
- 版本: 1.0.0
- 测试时间: {}
- 邮件服务: 正常运行

如果您收到此邮件，说明邮件通知服务配置正确！
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    success = notifier.send_email(
        to_email=notifier.notification_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )

    if success:
        print("✅ 测试邮件发送成功！")
        print(f"📬 请检查邮箱: {notifier.notification_email}")
        return True
    else:
        print("❌ 测试邮件发送失败")
        return False


def test_price_alert():
    """测试价格预警邮件"""
    print("\n🧪 测试价格预警邮件...")

    notifier = EmailNotifier()

    # 模拟价格异常数据
    anomaly_data = {
        "is_anomaly": True,
        "product_asin": "B09XS7JWHH",
        "product_title": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
        "current_price": 299.99,
        "average_price": 349.99,
        "change_percent": 14.3,
        "direction": "decrease",
        "check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "threshold": 10.0,
    }

    success = notifier.send_price_alert(anomaly_data)

    if success:
        print("✅ 价格预警邮件发送成功！")
        return True
    else:
        print("❌ 价格预警邮件发送失败")
        return False


def test_bsr_alert():
    """测试BSR排名预警邮件"""
    print("\n🧪 测试BSR排名预警邮件...")

    notifier = EmailNotifier()

    # 模拟BSR异常数据
    anomaly_data = {
        "is_anomaly": True,
        "product_asin": "B0BDHWDR12",
        "product_title": "Apple AirPods Pro (2nd Generation)",
        "current_rank": 15,
        "average_rank": 45,
        "change_percent": 66.7,
        "direction": "better",
        "check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "threshold": 30.0,
    }

    success = notifier.send_bsr_alert(anomaly_data)

    if success:
        print("✅ BSR预警邮件发送成功！")
        return True
    else:
        print("❌ BSR预警邮件发送失败")
        return False


def main():
    """主测试函数"""
    print("🚀 Amazon产品追踪系统 - 邮件服务测试")
    print("=" * 50)

    tests = [
        ("基础邮件发送", test_basic_email),
        ("价格预警邮件", test_price_alert),
        ("BSR排名预警邮件", test_bsr_alert),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results.append((test_name, False))

    # 输出测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总")
    print("=" * 50)

    total_tests = len(results)
    passed_tests = sum(1 for _, result in results if result)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")

    print(f"\n总计: {passed_tests}/{total_tests} 测试通过")

    if passed_tests == total_tests:
        print("🎉 所有邮件服务测试通过！")
        return True
    else:
        print("⚠️ 部分测试失败，请检查配置")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
