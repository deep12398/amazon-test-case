# Amazon产品追踪分析系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

多租户SaaS平台，提供Amazon产品数据追踪、竞品分析和AI驱动的优化建议。

## ✨ 功能特性

- 🏢 **多租户架构** - 支持多个组织独立使用
- 📊 **产品追踪** - 实时监控1000+产品的价格、BSR、评价变化
- 🤖 **AI分析** - LangChain+OpenAI驱动的竞品分析和优化建议
- 🕷️ **智能爬虫** - 基于Apify的高效数据抓取
- 📈 **可视化监控** - Prometheus+Grafana完整监控体系
- 🚀 **高性能** - 异步架构+多级缓存+分布式任务队列

## 🛠️ 技术栈

- **后端框架**: FastAPI + Python 3.11
- **数据库**: Supabase (PostgreSQL) + Redis
- **任务队列**: Celery + AWS SQS
- **网关**: APISIX + etcd
- **AI**: LangChain + OpenAI
- **监控**: OpenTelemetry + Prometheus + Grafana
- **部署**: Docker + Docker Compose

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Docker & Docker Compose
- UV (推荐) 或 Poetry

### ⚡ 一键启动开发环境

```bash
# 克隆项目
git clone <repository-url>
cd amazon-test-case

# 一键启动完整开发环境
python scripts/start_dev_env.py
```

这个脚本会自动：
- 🔍 检查依赖项
- 🐳 启动Docker服务 (PostgreSQL, Redis, APISIX等)
- 🗄️ 初始化数据库和种子数据
- 👥 启动用户服务
- 🌐 配置APISIX网关路由
- 🧪 运行认证系统测试

### 手动启动

```bash
# 完整环境设置
make dev-setup

# 检查环境状态
make dev-check
```

### 手动安装

```bash
# 1. 创建虚拟环境
make install
source .venv/bin/activate

# 2. 安装依赖
make install-deps

# 3. 安装开发工具
make install-hooks

# 4. 启动基础设施
make docker-up

# 5. 运行数据库迁移
make db-migrate
```

## 📁 项目结构

```
amazon-tracker/
├── amazon_tracker/           # 主项目包
│   ├── services/            # 微服务
│   │   ├── user_service/    # 用户管理服务
│   │   ├── core_service/    # 核心业务服务
│   │   └── crawler_service/ # 爬虫服务
│   ├── common/             # 共享组件
│   │   ├── database/       # 数据库相关
│   │   ├── auth/           # 认证相关
│   │   ├── cache/          # 缓存相关
│   │   └── utils/          # 工具函数
│   └── config/             # 配置文件
├── migrations/             # 数据库迁移
├── tests/                  # 测试文件
├── config/                 # 外部配置
├── scripts/                # 脚本文件
└── docs/                   # 文档
```

## 🔧 开发命令

```bash
# 代码质量
make format         # 代码格式化
make lint          # 代码检查
make type-check    # 类型检查
make check         # 所有检查

# 测试
make test          # 运行所有测试
make test-unit     # 单元测试
make test-integration # 集成测试

# 开发服务
make dev-user      # 启动用户服务 (port: 8001)
make dev-core      # 启动核心服务 (port: 8002)
make dev-crawler   # 启动爬虫服务 (port: 8003)

# Docker操作
make docker-up     # 启动开发环境
make docker-down   # 停止服务
make docker-logs   # 查看日志

# 数据库
make db-migrate    # 运行迁移
make db-migration  # 创建新迁移
make db-seed       # 填充种子数据
```

## 📊 服务端点

| 服务 | 端口 | 描述 | 文档 |
|------|------|------|------|
| APISIX网关 | 9080 | API网关 | - |
| 用户服务 | 8001 | 认证管理 | http://localhost:8001/docs |
| 核心服务 | 8002 | 产品分析 | http://localhost:8002/docs |
| 爬虫服务 | 8003 | 数据抓取 | http://localhost:8003/docs |
| PostgreSQL | 5432 | 主数据库 | - |
| Redis | 6379 | 缓存存储 | - |
| Prometheus | 9090 | 监控指标 | http://localhost:9090 |
| Grafana | 3000 | 监控面板 | http://localhost:3000 |

## 🔐 环境配置

复制 `.env.example` 到 `.env` 并填写以下关键配置：

```bash
# API密钥
OPENAI_API_KEY=sk-your-key-here
APIFY_API_TOKEN=your-token-here

# 数据库
DATABASE_URL=postgresql://...
REDIS_URL=redis://localhost:6379

# 安全
JWT_SECRET=your-secret-key
```

## 🏗️ 架构设计

系统采用微服务架构，支持多租户SaaS模式：

- **API网关层**: APISIX提供统一入口和租户路由
- **微服务层**: 用户管理、核心业务、爬虫服务
- **数据存储层**: PostgreSQL主数据库 + Redis缓存
- **任务队列层**: Celery + SQS处理异步任务
- **监控观测层**: 完整的监控和追踪体系

详细架构文档：[ARCHITECTURE.md](ARCHITECTURE.md)

## 🗺️ 开发进度

项目分为5个阶段，目前完成情况：

### ✅ **Phase 1: 项目基础设施** (已完成)
- ✅ 项目目录结构和开发环境
- ✅ UV虚拟环境和依赖管理
- ✅ Docker开发环境 (PostgreSQL, Redis, APISIX等)
- ✅ Git配置和代码质量工具
- ✅ Alembic数据库迁移

### ✅ **Phase 2: 用户认证系统** (已完成)
- ✅ 多租户用户数据模型
- ✅ JWT认证机制 (访问+刷新令牌)
- ✅ 用户注册、登录、权限管理API
- ✅ RBAC权限控制系统
- ✅ API Key认证
- ✅ APISIX网关认证配置
- ✅ 完整认证系统测试

### 🚧 **Phase 3: 数据抓取服务** (进行中)
- [ ] Apify爬虫集成
- [ ] Amazon产品数据抓取
- [ ] 数据清洗和验证
- [ ] 异步任务队列
- [ ] 爬虫调度和监控

### 📅 **Phase 4: 核心业务功能** (计划中)
- [ ] 产品管理系统
- [ ] 竞争对手分析
- [ ] AI优化建议
- [ ] 分析报告生成

### 📅 **Phase 5: 监控与部署** (计划中)
- [ ] 完整监控体系
- [ ] 生产环境部署
- [ ] 性能优化
- [ ] 文档完善

详细实施计划：[IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md)

## 🔐 认证系统使用

### 演示账户
- **管理员**: `admin@demo.com` / `admin123456` (拥有所有权限)

### 认证流程示例

```bash
# 1. 用户登录获取JWT令牌
curl -X POST "http://localhost:8001/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@demo.com",
    "password": "admin123456",
    "remember_me": true
  }'

# 2. 使用JWT令牌访问受保护资源
curl -X GET "http://localhost:8001/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 3. 创建API Key用于程序化访问
curl -X POST "http://localhost:8001/api/v1/users/me/api-keys" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "我的API Key",
    "scopes": ["products.read", "analytics.read"],
    "rate_limit_per_minute": 100
  }'

# 4. 使用API Key访问API
curl -X GET "http://localhost:9080/api/products" \
  -H "X-API-Key: YOUR_API_KEY"
```

### 权限系统

| 角色 | 描述 | 权限 |
|------|------|------|
| 超级管理员 | 系统级权限 | 所有权限 |
| 租户管理员 | 租户内管理员 | 用户管理、产品管理、分析报告 |
| 普通用户 | 基础用户 | 产品管理、分析查看 |
| 查看者 | 只读用户 | 仅查看权限 |

### 测试认证系统

```bash
# 运行完整的认证系统测试
python scripts/test_auth_system.py
```

## 🧪 测试

```bash
# 运行所有测试
make test

# 查看覆盖率报告
open htmlcov/index.html
```

## 📝 API文档

- **Swagger UI**: 交互式API文档和测试界面
- **ReDoc**: 美观的API文档展示
- **OpenAPI Schema**: 标准化API规范

每个服务的文档地址：
- 用户服务: http://localhost:8001/docs
- 核心服务: http://localhost:8002/docs
- 爬虫服务: http://localhost:8003/docs

## 🚀 部署

```bash
# 生产环境部署
make deploy-prod

# 检查部署状态
make deploy-check
```

## 📞 支持

- 📖 [完整文档](docs/)
- 🐛 [问题反馈](https://github.com/yourusername/amazon-tracker/issues)
- 💬 [讨论区](https://github.com/yourusername/amazon-tracker/discussions)

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件
