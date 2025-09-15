# Amazon产品追踪分析系统 - Makefile
# 使用方法: make <target>

.PHONY: help install dev test lint format check clean docker-build docker-up docker-down

# 默认目标
.DEFAULT_GOAL := help

# 颜色定义
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[0;33m
BLUE = \033[0;34m
NC = \033[0m # No Color

help: ## 显示帮助信息
	@echo "$(BLUE)Amazon产品追踪分析系统 - 开发命令$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# ===== 环境设置 =====
install: ## 安装项目依赖
	@echo "$(YELLOW)📦 安装项目依赖...$(NC)"
	uv venv --python 3.11
	@echo "$(GREEN)✅ 虚拟环境创建完成$(NC)"
	@echo "$(YELLOW)激活环境: source .venv/bin/activate$(NC)"

install-deps: ## 安装所有依赖包
	@echo "$(YELLOW)📦 安装开发依赖...$(NC)"
	uv pip install -e ".[dev]"
	@echo "$(GREEN)✅ 依赖安装完成$(NC)"

install-hooks: ## 安装pre-commit钩子
	@echo "$(YELLOW)🪝 安装pre-commit钩子...$(NC)"
	pre-commit install
	@echo "$(GREEN)✅ Pre-commit钩子安装完成$(NC)"

setup: install install-deps install-hooks ## 完整项目设置
	@echo "$(GREEN)🚀 项目设置完成！$(NC)"
	@echo "下一步:"
	@echo "  1. 复制 .env.example 到 .env 并填写配置"
	@echo "  2. 运行 make docker-up 启动服务"
	@echo "  3. 运行 make test 执行测试"

# ===== 代码质量 =====
format: ## 格式化代码 (Black + Ruff)
	@echo "$(YELLOW)🎨 格式化代码...$(NC)"
	black .
	ruff format .
	@echo "$(GREEN)✅ 代码格式化完成$(NC)"

lint: ## 代码检查 (Ruff linter)
	@echo "$(YELLOW)🔍 运行代码检查...$(NC)"
	ruff check . --fix
	@echo "$(GREEN)✅ 代码检查完成$(NC)"

type-check: ## 类型检查 (MyPy)
	@echo "$(YELLOW)🔍 运行类型检查...$(NC)"
	mypy amazon_tracker/
	@echo "$(GREEN)✅ 类型检查完成$(NC)"

security-check: ## 安全检查 (Bandit)
	@echo "$(YELLOW)🛡️  运行安全检查...$(NC)"
	bandit -r . -x tests/
	@echo "$(GREEN)✅ 安全检查完成$(NC)"

check: lint type-check security-check ## 运行所有代码检查
	@echo "$(GREEN)✅ 所有检查完成$(NC)"

pre-commit: ## 运行pre-commit检查
	@echo "$(YELLOW)🪝 运行pre-commit检查...$(NC)"
	pre-commit run --all-files
	@echo "$(GREEN)✅ Pre-commit检查完成$(NC)"

# ===== 测试 =====
test: ## 运行测试
	@echo "$(YELLOW)🧪 运行测试...$(NC)"
	pytest -v --cov=amazon_tracker --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)✅ 测试完成$(NC)"
	@echo "$(BLUE)📊 覆盖率报告: htmlcov/index.html$(NC)"

test-unit: ## 运行单元测试
	@echo "$(YELLOW)🧪 运行单元测试...$(NC)"
	pytest tests/unit/ -v
	@echo "$(GREEN)✅ 单元测试完成$(NC)"

test-integration: ## 运行集成测试
	@echo "$(YELLOW)🧪 运行集成测试...$(NC)"
	pytest tests/integration/ -v
	@echo "$(GREEN)✅ 集成测试完成$(NC)"

test-watch: ## 监听文件变化并运行测试
	@echo "$(YELLOW)👀 监听测试模式...$(NC)"
	pytest-watch

# ===== 统一环境管理 =====
dev: ## 启动完整开发环境 (Docker + Python服务)
	@echo "$(YELLOW)🚀 启动完整开发环境...$(NC)"
	@chmod +x dev.sh
	@./dev.sh start

stop: ## 停止完整开发环境
	@echo "$(YELLOW)🛑 停止完整开发环境...$(NC)"
	@chmod +x dev.sh
	@./dev.sh stop

restart: ## 重启完整开发环境
	@echo "$(YELLOW)🔄 重启完整开发环境...$(NC)"
	@chmod +x dev.sh
	@./dev.sh restart

status: ## 查看服务状态
	@echo "$(YELLOW)📊 查看服务状态...$(NC)"
	@chmod +x dev.sh
	@./dev.sh status

# ===== Docker操作 =====
docker-build: ## 构建Docker镜像
	@echo "$(YELLOW)🐳 构建Docker镜像...$(NC)"
	docker compose -f docker-compose.dev.yml build
	@echo "$(GREEN)✅ Docker镜像构建完成$(NC)"

docker-up: ## 启动开发环境服务
	@echo "$(YELLOW)🚀 启动开发环境...$(NC)"
	docker compose -f docker-compose.dev.yml up -d
	@echo "$(GREEN)✅ 开发环境启动完成$(NC)"
	@echo "$(BLUE)📊 服务状态:$(NC)"
	@docker compose -f docker-compose.dev.yml ps

docker-down: ## 停止开发环境服务
	@echo "$(YELLOW)🛑 停止开发环境...$(NC)"
	docker compose -f docker-compose.dev.yml down
	@echo "$(GREEN)✅ 开发环境已停止$(NC)"

docker-logs: ## 查看服务日志
	@echo "$(YELLOW)📋 查看服务日志...$(NC)"
	docker-compose -f docker-compose.dev.yml logs -f

docker-clean: ## 清理Docker资源
	@echo "$(YELLOW)🧹 清理Docker资源...$(NC)"
	docker-compose -f docker-compose.dev.yml down -v --remove-orphans
	docker system prune -f
	@echo "$(GREEN)✅ Docker资源清理完成$(NC)"

# ===== 数据库操作 =====
db-migrate: ## 运行数据库迁移
	@echo "$(YELLOW)📊 运行数据库迁移...$(NC)"
	alembic upgrade head
	@echo "$(GREEN)✅ 数据库迁移完成$(NC)"

db-migration: ## 创建新的迁移文件
	@read -p "迁移文件描述: " desc; \
	alembic revision --autogenerate -m "$$desc"
	@echo "$(GREEN)✅ 迁移文件创建完成$(NC)"

db-seed: ## 填充种子数据
	@echo "$(YELLOW)🌱 填充种子数据...$(NC)"
	python scripts/seed_data.py
	@echo "$(GREEN)✅ 种子数据填充完成$(NC)"

# ===== 开发服务 =====
dev-user: ## 启动用户服务 (8001端口)
	@echo "$(YELLOW)👤 启动用户服务...$(NC)"
	uvicorn amazon_tracker.services.user_service.main:app --host 0.0.0.0 --port 8001 --reload

dev-core: ## 启动核心服务 (8003端口)
	@echo "$(YELLOW)⚙️  启动核心服务...$(NC)"
	uvicorn amazon_tracker.services.core_service.main:app --host 0.0.0.0 --port 8003 --reload

dev-crawler: ## 启动爬虫服务 (8002端口)
	@echo "$(YELLOW)🕷️  启动爬虫服务...$(NC)"
	uvicorn amazon_tracker.services.crawler_service.main:app --host 0.0.0.0 --port 8002 --reload

dev-worker: ## 启动Celery Worker
	@echo "$(YELLOW)⚡ 启动Celery Worker...$(NC)"
	celery -A amazon_tracker.celery worker --loglevel=info

dev-beat: ## 启动Celery Beat
	@echo "$(YELLOW)⏰ 启动Celery Beat...$(NC)"
	celery -A amazon_tracker.celery beat --loglevel=info

dev-celery: ## 同时启动Celery Worker和Beat
	@echo "$(YELLOW)⚡⏰ 启动Celery Worker和Beat...$(NC)"
	@trap 'kill 0' INT; \
	celery -A amazon_tracker.celery worker --loglevel=info & \
	celery -A amazon_tracker.celery beat --loglevel=info & \
	wait

# ===== 文档 =====
docs-build: ## 构建API文档
	@echo "$(YELLOW)📚 构建API文档...$(NC)"
	mkdocs build
	@echo "$(GREEN)✅ API文档构建完成$(NC)"

docs-serve: ## 启动文档服务器
	@echo "$(YELLOW)📚 启动文档服务器...$(NC)"
	mkdocs serve
	@echo "$(BLUE)📖 文档地址: http://localhost:8000$(NC)"

# ===== 部署 =====
deploy-prod: ## 部署到生产环境
	@echo "$(YELLOW)🚀 部署到生产环境...$(NC)"
	docker-compose -f docker-compose.prod.yml up -d --build
	@echo "$(GREEN)✅ 生产环境部署完成$(NC)"

deploy-check: ## 检查部署状态
	@echo "$(YELLOW)🔍 检查部署状态...$(NC)"
	docker-compose -f docker-compose.prod.yml ps
	@echo "$(BLUE)🌐 健康检查: curl http://localhost:9080/health$(NC)"

# ===== 清理 =====
clean: ## 清理临时文件
	@echo "$(YELLOW)🧹 清理临时文件...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ dist/ build/
	@echo "$(GREEN)✅ 临时文件清理完成$(NC)"

clean-all: clean docker-clean ## 清理所有文件和Docker资源
	@echo "$(GREEN)✅ 完全清理完成$(NC)"

# ===== 开发工作流 =====
dev-setup: setup docker-up db-migrate ## 完整开发环境设置
	@echo "$(GREEN)🎉 开发环境设置完成！$(NC)"
	@echo ""
	@echo "$(BLUE)🚀 快速开始:$(NC)"
	@echo "  make dev-user    # 启动用户服务 :8001 (终端1)"
	@echo "  make dev-core    # 启动核心服务 :8003 (终端2)"
	@echo "  make dev-crawler # 启动爬虫服务 :8002 (终端3)"
	@echo "  make dev-worker  # 启动Worker (终端4)"
	@echo ""
	@echo "$(BLUE)📊 监控面板:$(NC)"
	@echo "  用户服务API: http://localhost:8001/docs"
	@echo "  爬虫服务API: http://localhost:8002/docs"
	@echo "  核心服务API: http://localhost:8003/docs"
	@echo "  APISIX管理:  http://localhost:9180/apisix/admin"
	@echo "  Prometheus:  http://localhost:9090"
	@echo "  Grafana:     http://localhost:3000"

dev-check: ## 开发环境健康检查
	@echo "$(YELLOW)🔍 开发环境健康检查...$(NC)"
	@echo "$(BLUE)Docker服务状态:$(NC)"
	@docker-compose -f docker-compose.dev.yml ps
	@echo ""
	@echo "$(BLUE)端口检查:$(NC)"
	@echo "APISIX网关: $$(curl -s -o /dev/null -w '%{http_code}' http://localhost:9080/apisix/status || echo '❌ 不可用')"
	@echo "PostgreSQL: $$(nc -z localhost 5432 && echo '✅ 可用' || echo '❌ 不可用')"
	@echo "Redis: $$(nc -z localhost 6379 && echo '✅ 可用' || echo '❌ 不可用')"
	@echo "etcd: $$(nc -z localhost 2379 && echo '✅ 可用' || echo '❌ 不可用')"

# ===== 可观察性演示 =====
observability-demo: ## 启动可观察性演示环境
	@echo "$(YELLOW)🔭 启动可观察性演示环境...$(NC)"
	@echo "$(BLUE)1. 检查Docker服务...$(NC)"
	@docker-compose -f docker-compose.dev.yml ps | grep -E "(jaeger|prometheus|grafana|apisix)" || (echo "$(RED)请先运行 make docker-up$(NC)" && exit 1)
	@echo ""
	@echo "$(BLUE)2. 发送测试请求...$(NC)"
	@for i in 1 2 3 4 5; do \
		echo "发送请求 $$i/5..."; \
		curl -s -X GET http://localhost:9080/api/v1/demo/metrics \
			-H "Content-Type: application/json" \
			-H "X-Request-ID: demo-$$i-$$(date +%s)" \
			-w "\n状态码: %{http_code}, 耗时: %{time_total}s\n" \
			-o /dev/null; \
		sleep 0.5; \
	done
	@echo ""
	@echo "$(GREEN)✅ 测试请求发送完成！$(NC)"
	@echo ""
	@echo "$(BLUE)📊 查看监控数据:$(NC)"
	@echo "  Prometheus:  http://localhost:9090"
	@echo "  Grafana:     http://localhost:3000 (admin/admin123)"
	@echo "  Jaeger UI:   http://localhost:16686"
	@echo ""
	@echo "$(YELLOW)提示: 在Jaeger中选择服务'APISIX-Gateway'查看追踪$(NC)"

observability-test: ## 批量测试可观察性端点
	@echo "$(YELLOW)🔄 批量发送测试请求...$(NC)"
	@echo "将发送100个请求用于压力测试..."
	@for i in $$(seq 1 100); do \
		curl -s -X GET http://localhost:9080/api/v1/demo/metrics \
			-H "X-Request-ID: stress-test-$$i" \
			-o /dev/null & \
		if [ $$((i % 10)) -eq 0 ]; then \
			echo "已发送 $$i 个请求..."; \
			sleep 0.1; \
		fi; \
	done
	@wait
	@echo "$(GREEN)✅ 压力测试完成！$(NC)"

observability-urls: ## 显示可观察性UI地址
	@echo "$(BLUE)🔗 可观察性平台地址:$(NC)"
	@echo ""
	@echo "$(GREEN)Prometheus$(NC) (指标收集):"
	@echo "  http://localhost:9090"
	@echo "  查询: apisix_http_status, apisix_http_latency"
	@echo ""
	@echo "$(GREEN)Grafana$(NC) (可视化仪表板):"
	@echo "  http://localhost:3000"
	@echo "  账号: admin / admin123"
	@echo ""
	@echo "$(GREEN)Jaeger$(NC) (分布式追踪):"
	@echo "  http://localhost:16686"
	@echo "  服务名: APISIX-Gateway"
	@echo ""
	@echo "$(GREEN)APISIX Admin$(NC) (网关管理):"
	@echo "  http://localhost:9180/apisix/admin"
	@echo ""
	@echo "$(YELLOW)演示端点:$(NC)"
	@echo "  GET http://localhost:9080/api/v1/demo/metrics"
