#!/usr/bin/env python3
"""发送简单测试邮件 123"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from amazon_tracker.common.notification.email_service import EmailNotifier


def send_simple_test():
    """发送简单的123测试邮件"""
    print("📧 正在发送简单测试邮件...")

    notifier = EmailNotifier()

    # 检查配置
    if not notifier.smtp_user or not notifier.smtp_password:
        print("❌ 邮件配置未设置")
        print("请在 .env.local 中配置：")
        print("SMTP_USER=your-gmail@gmail.com")
        print("SMTP_PASSWORD=your-app-password")
        print("FROM_EMAIL=your-gmail@gmail.com")
        print("NOTIFICATION_EMAIL=your-personal@gmail.com")
        return False

    print(f"📤 发送方: {notifier.from_email}")
    print(f"📥 接收方: {notifier.notification_email}")

    # 发送简单的123邮件
    success = notifier.send_email(
        to_email=notifier.notification_email,
        subject="测试邮件 - 123",
        html_body="""
        <html>
        <body>
            <h1>123</h1>
            <p>这是一个简单的测试邮件。</p>
            <p>如果你收到这封邮件，说明邮件服务配置成功！</p>
        </body>
        </html>
        """,
        text_body="123\n\n这是一个简单的测试邮件。\n如果你收到这封邮件，说明邮件服务配置成功！",
    )

    if success:
        print("✅ 测试邮件发送成功！")
        print(f"📬 请检查邮箱: {notifier.notification_email}")
        return True
    else:
        print("❌ 测试邮件发送失败")
        print("请检查以下设置：")
        print("1. SMTP_USER 和 SMTP_PASSWORD 是否正确")
        print("2. Gmail是否开启了两步验证")
        print("3. 是否使用了应用专用密码（不是Gmail登录密码）")
        print("4. 网络连接是否正常")
        return False


if __name__ == "__main__":
    success = send_simple_test()
    sys.exit(0 if success else 1)
