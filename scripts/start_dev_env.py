"""开发环境启动脚本"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class DevEnvironmentManager:
    """开发环境管理器"""

    def __init__(self):
        self.project_root = project_root
        self.processes: list[subprocess.Popen] = []

    def check_dependencies(self) -> bool:
        """检查依赖项"""
        print("🔍 检查依赖项...")

        # 检查Python虚拟环境
        venv_path = self.project_root / ".venv"
        if not venv_path.exists():
            print("❌ 虚拟环境不存在，请先运行: uv venv")
            return False

        # 检查Docker Compose
        try:
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            print(f"✓ Docker Compose: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Docker Compose未安装或不可用")
            return False

        # 检查环境变量文件
        env_file = self.project_root / ".env"
        if not env_file.exists():
            print("⚠️ .env文件不存在，将使用默认配置")
        else:
            print("✓ 找到.env配置文件")

        print("✅ 依赖项检查完成")
        return True

    def start_docker_services(self) -> bool:
        """启动Docker服务"""
        print("\n🐳 启动Docker服务...")

        compose_file = self.project_root / "docker-compose.dev.yml"
        if not compose_file.exists():
            print("❌ docker-compose.dev.yml文件不存在")
            return False

        try:
            # 启动Docker服务
            cmd = ["docker-compose", "-f", str(compose_file), "up", "-d"]
            result = subprocess.run(
                cmd, cwd=self.project_root, check=True, capture_output=True, text=True
            )
            print("✓ Docker服务启动成功")

            # 等待服务就绪
            print("⏳ 等待服务就绪...")
            time.sleep(10)

            # 检查服务状态
            self.check_docker_services()
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Docker服务启动失败: {e}")
            print(f"错误输出: {e.stderr}")
            return False

    def check_docker_services(self):
        """检查Docker服务状态"""
        print("\n📊 检查Docker服务状态...")

        services = {
            "postgres": "5432",
            "redis": "6379",
            "etcd": "2379",
            "apisix": "9080",
            "prometheus": "9090",
            "grafana": "3000",
        }

        for service, port in services.items():
            try:
                import socket

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(("localhost", int(port)))
                sock.close()

                if result == 0:
                    print(f"✓ {service} (端口 {port}) - 运行中")
                else:
                    print(f"❌ {service} (端口 {port}) - 未响应")
            except Exception as e:
                print(f"❌ {service} - 检查失败: {e}")

    def init_database(self) -> bool:
        """初始化数据库"""
        print("\n🗄️ 初始化数据库...")

        try:
            # 运行Alembic迁移
            print("📝 运行数据库迁移...")
            alembic_cmd = [
                str(self.project_root / ".venv" / "bin" / "python"),
                "-m",
                "alembic",
                "upgrade",
                "head",
            ]

            result = subprocess.run(
                alembic_cmd,
                cwd=self.project_root,
                check=False,  # 不强制检查，因为可能没有迁移文件
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print("✓ 数据库迁移完成")
            else:
                print(f"⚠️ 数据库迁移警告: {result.stderr}")

            # 运行种子数据脚本
            print("🌱 初始化种子数据...")
            seed_cmd = [
                str(self.project_root / ".venv" / "bin" / "python"),
                str(self.project_root / "scripts" / "seed_data.py"),
            ]

            result = subprocess.run(
                seed_cmd,
                cwd=self.project_root,
                check=True,
                capture_output=True,
                text=True,
            )

            print("✓ 种子数据初始化完成")
            print(result.stdout)
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ 数据库初始化失败: {e}")
            print(f"错误输出: {e.stderr}")
            return False

    def start_user_service(self) -> bool:
        """启动用户服务"""
        print("\n👥 启动用户服务...")

        try:
            # 设置环境变量
            env = os.environ.copy()
            env.update(
                {
                    "JWT_SECRET_KEY": "dev-jwt-secret-key-change-in-production",
                    "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
                    "REFRESH_TOKEN_EXPIRE_DAYS": "7",
                    "DATABASE_URL": "postgresql://dev_user:dev_password@localhost:5432/amazon_tracker_dev",
                }
            )

            # 启动用户服务
            cmd = [
                str(self.project_root / ".venv" / "bin" / "python"),
                str(self.project_root / "scripts" / "run_user_service.py"),
            ]

            process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            self.processes.append(process)

            # 等待服务启动
            time.sleep(3)

            if process.poll() is None:
                print("✓ 用户服务启动成功 (端口 8001)")
                return True
            else:
                print("❌ 用户服务启动失败")
                return False

        except Exception as e:
            print(f"❌ 用户服务启动异常: {e}")
            return False

    def configure_apisix(self) -> bool:
        """配置APISIX网关"""
        print("\n🌐 配置APISIX网关...")

        try:
            # 等待APISIX完全启动
            time.sleep(5)

            cmd = [
                str(self.project_root / ".venv" / "bin" / "python"),
                str(self.project_root / "scripts" / "setup_apisix_routes.py"),
            ]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )

            print("✓ APISIX网关配置完成")
            print(result.stdout)
            return True

        except subprocess.TimeoutExpired:
            print("❌ APISIX配置超时")
            return False
        except subprocess.CalledProcessError as e:
            print(f"❌ APISIX配置失败: {e}")
            print(f"错误输出: {e.stderr}")
            return False

    def run_tests(self) -> bool:
        """运行认证系统测试"""
        print("\n🧪 运行认证系统测试...")

        # 等待服务完全就绪
        time.sleep(5)

        try:
            cmd = [
                str(self.project_root / ".venv" / "bin" / "python"),
                str(self.project_root / "scripts" / "test_auth_system.py"),
            ]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )

            print("✓ 认证系统测试完成")
            print(result.stdout)
            return True

        except subprocess.TimeoutExpired:
            print("❌ 测试超时")
            return False
        except subprocess.CalledProcessError as e:
            print(f"❌ 测试失败: {e}")
            print(f"输出: {e.stdout}")
            return False

    def print_service_urls(self):
        """打印服务URL"""
        print("\n🌍 服务访问地址:")
        print("- 用户服务API文档: http://localhost:8001/docs")
        print("- APISIX网关: http://localhost:9080")
        print("- APISIX管理界面: http://localhost:9180")
        print("- Prometheus: http://localhost:9090")
        print("- Grafana: http://localhost:3000 (admin/admin)")
        print("\n📖 API端点:")
        print("- 用户注册: POST http://localhost:8001/api/v1/auth/register")
        print("- 用户登录: POST http://localhost:8001/api/v1/auth/login")
        print("- 用户信息: GET http://localhost:8001/api/v1/users/me")
        print("- 租户信息: GET http://localhost:8001/api/v1/tenants/me")
        print("\n👤 演示账户:")
        print("- 管理员: admin@demo.com / admin123456")

    def wait_for_shutdown(self):
        """等待关闭信号"""
        print("\n✅ 开发环境启动完成！")
        print("按 Ctrl+C 停止所有服务")

        try:
            # 监控进程输出
            for process in self.processes:
                if process.poll() is None:
                    print("\n📡 用户服务日志:")
                    while True:
                        line = process.stdout.readline()
                        if line:
                            print(f"[用户服务] {line.strip()}")
                        elif process.poll() is not None:
                            break
                        time.sleep(0.1)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        """关闭所有服务"""
        print("\n🛑 正在关闭服务...")

        # 关闭Python进程
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                    print("✓ Python服务已关闭")
                except subprocess.TimeoutExpired:
                    process.kill()
                    print("🔪 强制关闭Python服务")

        # 关闭Docker服务
        try:
            compose_file = self.project_root / "docker-compose.dev.yml"
            cmd = ["docker-compose", "-f", str(compose_file), "down"]
            subprocess.run(cmd, cwd=self.project_root, check=True)
            print("✓ Docker服务已关闭")
        except subprocess.CalledProcessError:
            print("⚠️ Docker服务关闭失败")

        print("👋 开发环境已关闭")


def main():
    """主函数"""
    print("🚀 Amazon Tracker 开发环境启动器")
    print("=" * 50)

    manager = DevEnvironmentManager()

    # 注册信号处理器
    def signal_handler(signum, frame):
        manager.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 1. 检查依赖项
        if not manager.check_dependencies():
            return 1

        # 2. 启动Docker服务
        if not manager.start_docker_services():
            return 1

        # 3. 初始化数据库
        if not manager.init_database():
            return 1

        # 4. 启动用户服务
        if not manager.start_user_service():
            return 1

        # 5. 配置APISIX
        if not manager.configure_apisix():
            print("⚠️ APISIX配置失败，但继续运行")

        # 6. 运行测试
        if not manager.run_tests():
            print("⚠️ 测试失败，但服务正在运行")

        # 7. 显示服务信息
        manager.print_service_urls()

        # 8. 等待关闭信号
        manager.wait_for_shutdown()

    except KeyboardInterrupt:
        manager.shutdown()
    except Exception as e:
        print(f"❌ 启动过程中出现错误: {e}")
        manager.shutdown()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
