#!/usr/bin/env python3
"""启动爬虫服务脚本"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


class CrawlerServiceManager:
    """爬虫服务管理器"""

    def __init__(self):
        self.processes = {}
        self.project_root = project_root

    def start_crawler_service(self):
        """启动爬虫服务"""
        print("🚀 Starting Crawler Service...")

        # 设置环境变量
        env = os.environ.copy()
        env.update(
            {
                "PYTHONPATH": str(self.project_root),
                "DATABASE_URL": env.get(
                    "DATABASE_URL",
                    "postgresql://postgres:postgres@localhost:5432/amazon_tracker",
                ),
                "REDIS_URL": env.get("REDIS_URL", "redis://localhost:6379/0"),
                "CELERY_BROKER_URL": env.get(
                    "CELERY_BROKER_URL", "redis://localhost:6379/0"
                ),
                "CELERY_RESULT_BACKEND": env.get(
                    "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
                ),
            }
        )

        # 启动FastAPI服务
        service_cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "amazon_tracker.services.crawler_service.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8002",
            "--reload",
            "--log-level",
            "info",
        ]

        try:
            service_process = subprocess.Popen(
                service_cmd,
                cwd=self.project_root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )

            self.processes["crawler_service"] = service_process
            print("✅ Crawler Service started on http://localhost:8002")

            return service_process

        except Exception as e:
            print(f"❌ Failed to start Crawler Service: {e}")
            return None

    def start_celery_worker(self):
        """启动Celery worker"""
        print("🔄 Starting Celery Worker...")

        env = os.environ.copy()
        env.update(
            {
                "PYTHONPATH": str(self.project_root),
                "DATABASE_URL": env.get(
                    "DATABASE_URL",
                    "postgresql://postgres:postgres@localhost:5432/amazon_tracker",
                ),
                "REDIS_URL": env.get("REDIS_URL", "redis://localhost:6379/0"),
                "CELERY_BROKER_URL": env.get(
                    "CELERY_BROKER_URL", "redis://localhost:6379/0"
                ),
                "CELERY_RESULT_BACKEND": env.get(
                    "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
                ),
            }
        )

        worker_cmd = [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "amazon_tracker.common.task_queue.celery_app",
            "worker",
            "--loglevel=info",
            "--concurrency=4",
            "--queues=default,crawler,scheduler",
        ]

        try:
            worker_process = subprocess.Popen(
                worker_cmd,
                cwd=self.project_root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )

            self.processes["celery_worker"] = worker_process
            print("✅ Celery Worker started")

            return worker_process

        except Exception as e:
            print(f"❌ Failed to start Celery Worker: {e}")
            return None

    def start_celery_beat(self):
        """启动Celery Beat调度器"""
        print("⏰ Starting Celery Beat Scheduler...")

        env = os.environ.copy()
        env.update(
            {
                "PYTHONPATH": str(self.project_root),
                "DATABASE_URL": env.get(
                    "DATABASE_URL",
                    "postgresql://postgres:postgres@localhost:5432/amazon_tracker",
                ),
                "REDIS_URL": env.get("REDIS_URL", "redis://localhost:6379/0"),
                "CELERY_BROKER_URL": env.get(
                    "CELERY_BROKER_URL", "redis://localhost:6379/0"
                ),
                "CELERY_RESULT_BACKEND": env.get(
                    "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
                ),
            }
        )

        beat_cmd = [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "amazon_tracker.common.task_queue.celery_app",
            "beat",
            "--loglevel=info",
            "--schedule=/tmp/celerybeat-schedule",
        ]

        try:
            beat_process = subprocess.Popen(
                beat_cmd,
                cwd=self.project_root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )

            self.processes["celery_beat"] = beat_process
            print("✅ Celery Beat Scheduler started")

            return beat_process

        except Exception as e:
            print(f"❌ Failed to start Celery Beat: {e}")
            return None

    def start_flower_monitor(self):
        """启动Flower监控"""
        print("🌸 Starting Flower Monitor...")

        env = os.environ.copy()
        env.update(
            {
                "PYTHONPATH": str(self.project_root),
                "CELERY_BROKER_URL": env.get(
                    "CELERY_BROKER_URL", "redis://localhost:6379/0"
                ),
            }
        )

        flower_cmd = [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "amazon_tracker.common.task_queue.celery_app",
            "flower",
            "--port=5555",
            "--broker=redis://localhost:6379/0",
        ]

        try:
            flower_process = subprocess.Popen(
                flower_cmd,
                cwd=self.project_root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )

            self.processes["flower"] = flower_process
            print("✅ Flower Monitor started on http://localhost:5555")

            return flower_process

        except Exception as e:
            print(f"❌ Failed to start Flower Monitor: {e}")
            return None

    def check_dependencies(self):
        """检查依赖服务"""
        print("🔍 Checking dependencies...")

        # 检查Redis
        try:
            import redis

            r = redis.Redis(host="localhost", port=6379, db=0)
            r.ping()
            print("✅ Redis is running")
        except Exception as e:
            print(f"❌ Redis is not available: {e}")
            return False

        # 检查PostgreSQL
        try:
            import psycopg2

            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="amazon_tracker",
                user="postgres",
                password="postgres",
            )
            conn.close()
            print("✅ PostgreSQL is running")
        except Exception as e:
            print(f"❌ PostgreSQL is not available: {e}")
            return False

        return True

    def wait_for_service(self, url: str, timeout: int = 30):
        """等待服务启动"""
        import requests

        print(f"⏳ Waiting for service at {url}...")

        for i in range(timeout):
            try:
                response = requests.get(url, timeout=1)
                if response.status_code == 200:
                    print(f"✅ Service is ready at {url}")
                    return True
            except:
                pass

            time.sleep(1)

        print(f"❌ Service not ready at {url} after {timeout}s")
        return False

    def stop_all(self):
        """停止所有进程"""
        print("\n🛑 Stopping all services...")

        for name, process in self.processes.items():
            if process and process.poll() is None:
                print(f"Stopping {name}...")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                except Exception as e:
                    print(f"Error stopping {name}: {e}")

        print("✅ All services stopped")

    def show_status(self):
        """显示服务状态"""
        print("\n📊 Service Status:")
        print("=" * 50)

        for name, process in self.processes.items():
            if process:
                status = "Running" if process.poll() is None else "Stopped"
                pid = process.pid if process.poll() is None else "N/A"
                print(f"  {name}: {status} (PID: {pid})")
            else:
                print(f"  {name}: Not started")

        print("\n🔗 Service URLs:")
        print("  Crawler Service: http://localhost:8002")
        print("  Crawler API Docs: http://localhost:8002/docs")
        print("  Flower Monitor: http://localhost:5555")
        print("  Health Check: http://localhost:8002/health")
        print("  Metrics: http://localhost:8002/api/v1/monitoring/metrics")

    def run(self, components: list = None):
        """运行服务"""
        if components is None:
            components = ["service", "worker", "beat", "flower"]

        print("🚀 Starting Amazon Tracker - Crawler Service")
        print("=" * 50)

        # 检查依赖
        if not self.check_dependencies():
            print("❌ Dependencies not available. Please start Docker services first.")
            return False

        # 设置信号处理
        def signal_handler(sig, frame):
            self.stop_all()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            # 启动服务
            if "service" in components:
                service = self.start_crawler_service()
                if not service:
                    return False

                # 等待服务启动
                if not self.wait_for_service("http://localhost:8002/health"):
                    return False

            if "worker" in components:
                self.start_celery_worker()

            if "beat" in components:
                self.start_celery_beat()

            if "flower" in components:
                self.start_flower_monitor()

            # 显示状态
            self.show_status()

            print("\n✅ All services started successfully!")
            print("Press Ctrl+C to stop all services")

            # 保持运行
            while True:
                time.sleep(1)

                # 检查进程是否还在运行
                for name, process in list(self.processes.items()):
                    if process and process.poll() is not None:
                        print(f"\n⚠️  {name} has stopped unexpectedly")
                        # 可以在这里添加自动重启逻辑

        except KeyboardInterrupt:
            self.stop_all()
        except Exception as e:
            print(f"❌ Error: {e}")
            self.stop_all()
            return False

        return True


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Start Crawler Service")
    parser.add_argument(
        "--components",
        nargs="+",
        choices=["service", "worker", "beat", "flower"],
        default=["service", "worker", "beat", "flower"],
        help="Components to start",
    )
    parser.add_argument(
        "--check-deps", action="store_true", help="Only check dependencies"
    )

    args = parser.parse_args()

    manager = CrawlerServiceManager()

    if args.check_deps:
        success = manager.check_dependencies()
        sys.exit(0 if success else 1)

    success = manager.run(args.components)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
