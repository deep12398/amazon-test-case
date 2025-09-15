#!/usr/bin/env python3
"""
环境变量检查脚本
检查.env.example文件中是否包含敏感信息
"""

import re
import sys
from pathlib import Path


def check_env_file():
    """检查环境变量文件是否包含真实的敏感信息"""
    env_file = Path(".env.example")

    if not env_file.exists():
        print("✅ .env.example 文件不存在，跳过检查")
        return True

    content = env_file.read_text()
    errors = []

    # 检查是否包含真实的API密钥模式
    sensitive_patterns = [
        (r"sk-[a-zA-Z0-9]{48,}", "OpenAI API密钥"),
        (r"apify_api_[a-zA-Z0-9]{32,}", "Apify API Token"),
        (r"postgresql://[^:]+:[^@]+@[^/]+", "数据库连接字符串"),
        (r"redis://[^:]*:[^@]*@", "Redis连接字符串"),
        (r"https://[a-zA-Z0-9\-]+\.supabase\.co", "Supabase URL"),
        (r"eyJ[a-zA-Z0-9\-_=]+\.[a-zA-Z0-9\-_=]+", "JWT Token"),
        (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    ]

    line_number = 0
    for line in content.split("\n"):
        line_number += 1

        # 跳过注释行和示例值
        if line.strip().startswith("#") or "=your-" in line or "=sk-your-" in line:
            continue

        for pattern, description in sensitive_patterns:
            if re.search(pattern, line):
                errors.append(
                    f"第{line_number}行包含真实的{description}: {line.strip()}"
                )

    if errors:
        print("❌ 发现敏感信息泄露:")
        for error in errors:
            print(f"  {error}")
        print("\n建议:")
        print("  1. 将真实配置移动到.env文件")
        print("  2. 在.env.example中使用占位符值")
        print("  3. 确保.env文件在.gitignore中")
        return False

    print("✅ 环境变量文件检查通过")
    return True


if __name__ == "__main__":
    success = check_env_file()
    sys.exit(0 if success else 1)
