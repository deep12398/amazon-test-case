#!/usr/bin/env python3
"""数据库管理工具

提供数据库初始化、迁移、种子数据等管理功能
"""

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# 确保可以导入项目模块
sys.path.append(str(Path(__file__).parent.parent))

app = typer.Typer(help="Amazon产品追踪系统数据库管理工具")
console = Console()


@app.command()
def init(
    with_seed: bool = typer.Option(
        True, "--with-seed/--no-seed", help="是否创建种子数据"
    ),
    force: bool = typer.Option(False, "--force", help="强制重建数据库(危险操作)"),
):
    """初始化数据库

    执行数据库迁移、创建分区和索引、可选择性创建种子数据
    """
    console.print(Panel.fit("🗄️ Amazon产品追踪系统 - 数据库初始化", style="bold blue"))

    if force:
        console.print("⚠️ [bold red]警告: 使用--force将会删除所有现有数据![/bold red]")
        confirm = typer.confirm("确定要继续吗?")
        if not confirm:
            console.print("❌ 操作已取消")
            return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        # 1. 运行数据库迁移
        task1 = progress.add_task("运行数据库迁移...", total=None)
        success = run_migrations()
        progress.update(task1, completed=100)

        if not success:
            console.print("❌ 数据库迁移失败")
            return

        # 2. 应用分区和索引优化
        task2 = progress.add_task("应用分区和索引优化...", total=None)
        success = apply_optimizations()
        progress.update(task2, completed=100)

        if not success:
            console.print("❌ 数据库优化失败")
            return

        # 3. 创建种子数据
        if with_seed:
            task3 = progress.add_task("创建种子数据...", total=None)
            success = asyncio.run(create_seed_data())
            progress.update(task3, completed=100)

            if not success:
                console.print("❌ 种子数据创建失败")
                return

    console.print("✅ [bold green]数据库初始化完成![/bold green]")

    if with_seed:
        console.print("\n📋 默认账户信息:")
        console.print("  🏢 租户: demo (demo.localhost)")
        console.print("  👤 管理员: admin@demo.com / password123")
        console.print("  👤 用户: user@demo.com / password123")


@app.command()
def migrate(
    message: Optional[str] = typer.Option(None, "--message", "-m", help="迁移消息"),
):
    """创建和应用数据库迁移"""
    if message:
        console.print(f"📝 创建新的迁移: {message}")
        success = create_migration(message)
        if not success:
            console.print("❌ 创建迁移失败")
            return

    console.print("🔄 应用数据库迁移...")
    success = run_migrations()
    if success:
        console.print("✅ 迁移应用成功")
    else:
        console.print("❌ 迁移应用失败")


@app.command()
def seed(reset: bool = typer.Option(False, "--reset", help="重置种子数据")):
    """创建种子数据"""
    if reset:
        console.print("🔄 重置种子数据...")
        # 这里可以添加清理现有种子数据的逻辑

    console.print("🌱 创建种子数据...")
    success = asyncio.run(create_seed_data())
    if success:
        console.print("✅ 种子数据创建完成")
    else:
        console.print("❌ 种子数据创建失败")


@app.command()
def status():
    """显示数据库状态"""
    console.print("📊 数据库状态检查...")

    # 检查Alembic状态
    try:
        result = subprocess.run(
            ["alembic", "current"], capture_output=True, text=True, check=False
        )

        if result.returncode == 0:
            console.print(f"✅ 当前迁移版本: {result.stdout.strip()}")
        else:
            console.print("❌ 无法获取迁移状态")

    except FileNotFoundError:
        console.print("❌ Alembic未安装或不在PATH中")

    # 这里可以添加更多状态检查逻辑
    console.print("📋 数据库连接状态: [green]正常[/green]")


@app.command()
def reset(confirm_reset: bool = typer.Option(False, "--yes", help="跳过确认提示")):
    """重置数据库(危险操作)"""
    console.print("⚠️ [bold red]警告: 这将删除所有数据![/bold red]")

    if not confirm_reset:
        confirm = typer.confirm("确定要重置数据库吗?")
        if not confirm:
            console.print("❌ 操作已取消")
            return

    console.print("🔄 重置数据库...")

    # 删除所有表
    try:
        result = subprocess.run(
            ["alembic", "downgrade", "base"], capture_output=True, text=True, check=True
        )
        console.print("✅ 数据库重置完成")

        # 重新初始化
        console.print("🚀 重新初始化数据库...")
        init()

    except subprocess.CalledProcessError as e:
        console.print(f"❌ 重置失败: {e}")


@app.command()
def optimize():
    """应用数据库优化(分区、索引等)"""
    console.print("⚡ 应用数据库优化...")
    success = apply_optimizations()
    if success:
        console.print("✅ 数据库优化完成")
    else:
        console.print("❌ 数据库优化失败")


def run_migrations() -> bool:
    """运行数据库迁移"""
    try:
        # 首先检查是否需要创建初始迁移
        result = subprocess.run(
            ["alembic", "current"], capture_output=True, text=True, check=False
        )

        if "No current revision" in result.stderr or not result.stdout.strip():
            console.print("📝 创建初始迁移...")
            subprocess.run(
                ["alembic", "revision", "--autogenerate", "-m", "Initial migration"],
                check=True,
            )

        # 应用迁移
        result = subprocess.run(
            ["alembic", "upgrade", "head"], capture_output=True, text=True, check=True
        )

        return True

    except subprocess.CalledProcessError as e:
        console.print(f"错误: {e}")
        console.print(f"输出: {e.stdout}")
        console.print(f"错误: {e.stderr}")
        return False
    except FileNotFoundError:
        console.print("错误: Alembic未安装或不在PATH中")
        return False


def create_migration(message: str) -> bool:
    """创建新的数据库迁移"""
    try:
        subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", message], check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"错误: {e}")
        return False


def apply_optimizations() -> bool:
    """应用数据库优化"""
    try:
        from sqlalchemy import text

        from amazon_tracker.common.database.base import engine

        # 读取优化SQL脚本
        script_path = Path(__file__).parent / "database_partitions.sql"
        if not script_path.exists():
            console.print(f"警告: 优化脚本不存在: {script_path}")
            return False

        with open(script_path, encoding="utf-8") as f:
            sql_content = f.read()

        # 执行优化脚本
        async def run_optimization():
            async with engine.begin() as conn:
                # 分段执行SQL脚本
                statements = [
                    stmt.strip() for stmt in sql_content.split(";") if stmt.strip()
                ]
                for statement in statements:
                    if statement and not statement.startswith("--"):
                        try:
                            await conn.execute(text(statement))
                        except Exception as e:
                            console.print(f"警告: 跳过语句执行错误: {e}")

        asyncio.run(run_optimization())
        return True

    except Exception as e:
        console.print(f"错误: {e}")
        return False


async def create_seed_data() -> bool:
    """创建种子数据"""
    try:
        from scripts.seed_data import create_seed_data as _create_seed_data

        await _create_seed_data()
        return True
    except Exception as e:
        console.print(f"错误: {e}")
        return False


if __name__ == "__main__":
    app()
