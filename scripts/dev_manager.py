#!/usr/bin/env python3
"""Amazon Tracker 开发环境管理器 - 统一启动/关闭脚本"""

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path


class ServiceManager:
    """服务管理器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.env_file = self.project_root / ".env.local"
        self.docker_processes: list[subprocess.Popen] = []
        self.python_services: dict[str, subprocess.Popen] = {}
        self.shutdown_event = threading.Event()

    def load_env_vars(self) -> dict[str, str]:
        """加载环境变量"""
        env_vars = os.environ.copy()

        if self.env_file.exists():
            print(f"✓ 加载环境变量: {self.env_file}")
            with open(self.env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()
        else:
            print("⚠️ .env.local文件不存在，使用默认配置")

        return env_vars

    def start_docker_services(self) -> bool:
        """启动所有Docker服务"""
        print("\n🐳 启动Docker服务...")

        compose_file = self.project_root / "docker-compose.dev.yml"
        if not compose_file.exists():
            print("❌ docker-compose.dev.yml不存在")
            return False

        try:
            cmd = ["docker", "compose", "-f", str(compose_file), "up", "-d"]
            result = subprocess.run(cmd, cwd=self.project_root, check=True)

            print("⏳ 等待Docker服务就绪...")
            time.sleep(15)

            # 检查服务状态
            self.check_docker_services()
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Docker服务启动失败: {e}")
            return False

    def check_docker_services(self):
        """检查Docker服务状态"""
        print("\n📊 检查服务状态...")

        services = {
            "Redis": {"port": 6379, "container": "amazon-tracker-redis-dev"},
            "etcd": {"port": 2379, "container": "amazon-tracker-etcd-dev"},
            "APISIX": {"port": 9080, "container": "amazon-tracker-apisix-dev"},
            "Prometheus": {"port": 9090, "container": "amazon-tracker-prometheus-dev"},
            "Grafana": {"port": 3000, "container": "amazon-tracker-grafana-dev"},
            "Jaeger": {"port": 16686, "container": "amazon-tracker-jaeger-dev"},
        }

        for name, config in services.items():
            try:
                # 检查容器状态
                result = subprocess.run(
                    [
                        "docker",
                        "ps",
                        "--filter",
                        f"name={config['container']}",
                        "--format",
                        "{{.Status}}",
                    ],
                    capture_output=True,
                    text=True,
                )

                if result.stdout.strip() and "Up" in result.stdout:
                    # 检查端口连通性
                    import socket

                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    port_result = sock.connect_ex(("localhost", config["port"]))
                    sock.close()

                    if port_result == 0:
                        print(f"✓ {name} (端口 {config['port']}) - 运行中")
                    else:
                        print(f"⚠️ {name} - 容器运行但端口未就绪")
                else:
                    print(f"❌ {name} - 容器未运行")

            except Exception as e:
                print(f"❌ {name} - 检查失败: {e}")

    def start_python_service(
        self, service_name: str, port: int, module_path: str
    ) -> bool:
        """启动Python服务"""
        print(f"\n🚀 启动{service_name}...")

        env_vars = self.load_env_vars()

        try:
            cmd = [
                "uv",
                "run",
                "uvicorn",
                f"{module_path}:app",
                "--host",
                "0.0.0.0",
                "--port",
                str(port),
                "--reload",
            ]

            process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                env=env_vars,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            self.python_services[service_name] = process

            # 确保 logs 目录存在
            log_dir = os.path.join(self.project_root, "logs")
            os.makedirs(log_dir, exist_ok=True)

            log_file_path = os.path.join(log_dir, f"{service_name}.log")

            # 创建线程实时打印日志并写入文件
            def print_output():
                with open(log_file_path, "a", encoding="utf-8") as f:
                    for line in process.stdout:
                        # 打印到控制台
                        print(f"[{service_name}] {line}", end="")
                        # 写入文件
                        f.write(line)
                        f.flush()  # 实时刷新

            t = threading.Thread(target=print_output, daemon=True)
            t.start()
            print(f"{log_file_path}日志文件创建成功！")

            # 等待服务启动
            time.sleep(3)

            if process.poll() is None:
                print(f"✓ {service_name}启动成功 (端口 {port})")
                return True
            else:
                print(f"❌ {service_name}启动失败")
                return False

        except Exception as e:
            print(f"❌ {service_name}启动异常: {e}")
            return False

    def start_celery_service(self, service_name: str, celery_args: list[str]) -> bool:
        """启动Celery服务"""
        print(f"\n⚡ 启动{service_name}...")

        env_vars = self.load_env_vars()

        try:
            cmd = [
                "uv",
                "run",
                "celery",
                "-A",
                "amazon_tracker.common.task_queue.celery_app",
            ] + celery_args

            process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                env=env_vars,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            self.python_services[service_name] = process

            # 等待服务启动
            time.sleep(3)

            if process.poll() is None:
                print(f"✓ {service_name}启动成功")
                return True
            else:
                print(f"❌ {service_name}启动失败")
                return False

        except Exception as e:
            print(f"❌ {service_name}启动异常: {e}")
            return False

    def start_all_services(self) -> bool:
        """启动所有服务"""
        print("🚀 Amazon Tracker 开发环境启动器")
        print("=" * 50)

        # 1. 启动Docker服务
        if not self.start_docker_services():
            return False

        # 2. 启动Python服务
        services = [
            ("用户服务", 8001, "amazon_tracker.services.user_service.main"),
            ("爬虫服务", 8002, "amazon_tracker.services.crawler_service.main"),
            ("核心服务", 8003, "amazon_tracker.services.core_service.main"),
        ]

        for service_name, port, module_path in services:
            if not self.start_python_service(service_name, port, module_path):
                print(f"⚠️ {service_name}启动失败，继续启动其他服务...")

        # 3. 启动Celery服务
        celery_services = [
            ("Celery Worker", ["worker", "--loglevel=info"]),
            ("Celery Beat", ["beat", "--loglevel=info"]),
        ]

        for service_name, celery_args in celery_services:
            if not self.start_celery_service(service_name, celery_args):
                print(f"⚠️ {service_name}启动失败，继续启动其他服务...")

        return True

    def print_service_info(self):
        """打印服务信息"""
        print("\n" + "=" * 50)
        print("🌍 服务访问地址:")
        print("- 用户服务API文档: http://localhost:8001/docs")
        print("- 爬虫服务API文档: http://localhost:8002/docs")
        print("- 核心服务API文档: http://localhost:8003/docs")
        print("- APISIX网关: http://localhost:9080")
        print("- APISIX管理API: http://localhost:9180")
        print("- Prometheus监控: http://localhost:9090")
        print("- Grafana仪表盘: http://localhost:3000 (admin/admin123)")
        print("- Jaeger链路追踪: http://localhost:16686")
        print("- Redis: localhost:6379")

        print("\n⚡ 后台任务服务:")
        print("- Celery Worker: 处理异步任务")
        print("- Celery Beat: 定时任务调度器")

        print("\n📚 常用API端点:")
        print("- 用户注册: POST http://localhost:8001/api/v1/auth/register")
        print("- 用户登录: POST http://localhost:8001/api/v1/auth/login")
        print("- 获取用户信息: GET http://localhost:8001/api/v1/users/me")
        print("- 产品管理: http://localhost:8003/api/v1/products/")
        print("- 爬虫任务: http://localhost:8002/api/v1/crawl/")

        print("\n✅ 开发环境启动完成!")
        print("按 Ctrl+C 停止所有服务")

    def monitor_services(self):
        """监控服务状态"""
        while not self.shutdown_event.is_set():
            try:
                # 检查Python服务
                failed_services = []
                for name, process in self.python_services.items():
                    if process.poll() is not None:
                        failed_services.append(name)

                if failed_services:
                    print(f"\n⚠️ 检测到服务异常: {', '.join(failed_services)}")

                time.sleep(10)
            except Exception:
                break

    def stop_all_services(self):
        """停止所有服务"""
        print("\n🛑 正在关闭所有服务...")

        self.shutdown_event.set()

        # 1. 关闭Python服务
        for name, process in self.python_services.items():
            if process.poll() is None:
                print(f"🔄 关闭{name}...")
                process.terminate()
                try:
                    process.wait(timeout=10)
                    print(f"✓ {name}已关闭")
                except subprocess.TimeoutExpired:
                    process.kill()
                    print(f"🔪 强制关闭{name}")

        # 2. 关闭Docker服务
        try:
            print("🔄 关闭Docker服务...")
            compose_file = self.project_root / "docker-compose.dev.yml"
            cmd = ["docker", "compose", "-f", str(compose_file), "down"]
            subprocess.run(cmd, cwd=self.project_root, check=True)
            print("✓ Docker服务已关闭")
        except subprocess.CalledProcessError:
            print("⚠️ Docker服务关闭失败")

        print("👋 开发环境已完全关闭")

    def run(self):
        """运行开发环境"""

        def signal_handler(signum, frame):
            self.stop_all_services()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            if not self.start_all_services():
                self.stop_all_services()
                return 1

            self.print_service_info()

            # 启动监控线程
            monitor_thread = threading.Thread(target=self.monitor_services, daemon=True)
            monitor_thread.start()

            # 保持主线程运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

        except Exception as e:
            print(f"❌ 运行过程中出现错误: {e}")
            self.stop_all_services()
            return 1

        self.stop_all_services()
        return 0


def main():
    """主函数"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "stop":
            # 只停止服务
            manager = ServiceManager()
            manager.stop_all_services()
            return 0
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("用法:")
            print("  python dev_manager.py        # 启动所有服务")
            print("  python dev_manager.py stop   # 停止所有服务")
            return 0

    # 启动服务
    manager = ServiceManager()
    return manager.run()


if __name__ == "__main__":
    sys.exit(main())
