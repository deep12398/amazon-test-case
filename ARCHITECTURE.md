# Amazon产品追踪与分析系统 - 技术架构文档

## 项目概述

为Amazon卖家提供产品表现追踪、竞品分析和优化建议的后端系统，支持1000+产品监控，具备高可用、可扩展的架构设计。

## 技术栈选型

### 核心技术栈

#### 编程语言与框架
- **Python 3.11+** - 主要编程语言
- **FastAPI** - 现代化的异步Web框架
  - 自动API文档生成 (Swagger/ReDoc)
  - 高性能异步支持
  - 类型提示和数据验证
  - 内置CORS支持

#### 数据库与存储
- **Supabase (PostgreSQL)** - 主数据库
  - 托管PostgreSQL服务
  - 内置认证和实时订阅
  - 自动备份和扩展
- **Redis** - 缓存和会话存储
  - 数据缓存（24-48小时）
  - Celery消息代理
  - 限流计数器

#### 任务队列与调度
- **Celery** - 分布式任务队列
  - 异步任务执行
  - 定时任务调度
  - 失败重试机制
- **AWS SQS** - 消息队列服务
  - 可靠的消息传递
  - 自动扩展
  - 与Celery深度集成
- **Redis** - 结果存储和缓存

#### 数据库迁移
- **Alembic** - 数据库迁移工具
  - 版本化数据库结构
  - 自动迁移脚本生成

#### AI/LLM集成
- **LangChain** - LLM应用框架
  - OpenAI API集成
  - Prompt模板管理
  - 链式推理支持

#### 网页抓取
- **Apify** - 网页抓取服务
  - Amazon Product Details爬虫
  - 蓝牙耳机品类专用配置
  - 反爬虫机制处理
  - API调用优化

#### API网关与安全
- **APISIX** - 高性能云原生API网关
  - 身份认证与鉴权
  - 流量控制与限流
  - SSL/TLS加密
  - 负载均衡
  - 请求/响应转换
  - 原生Prometheus和OpenTelemetry支持
  - etcd配置同步（1ms级）

### 监控与运维
- **Prometheus** - 指标收集 ✅
- **Grafana** - 数据可视化 ✅
- **Jaeger** - 分布式追踪 ✅
- **OpenTelemetry** - 分布式追踪标准 ✅
- **CloudWatch** - AWS云监控

### CI/CD与版本控制
- **GitHub** - 代码版本控制
- **GitHub Actions** - 自动化工作流
- **Docker** - 容器化部署

### 补充技术组件

#### 数据验证与序列化
- **Pydantic V2** - 数据验证和设置管理
- **SQLAlchemy** - ORM层，与Alembic配合
- **Marshmallow** - 复杂数据序列化

#### 测试框架
- **Pytest** - 单元测试和集成测试
- **Pytest-asyncio** - 异步测试支持
- **Faker** - 测试数据生成
- **Locust** - 性能测试和负载测试

#### 日志与追踪
- **Loguru** - 简化的Python日志库
- **Structlog** - 结构化日志记录

#### HTTP客户端与工具
- **HTTPx** - 异步HTTP客户端
- **Tenacity** - 智能重试机制
- **APScheduler** - 轻量级任务调度补充

#### 数据处理
- **Pandas** - 数据分析和处理
- **NumPy** - 数值计算支持
- **Arrow** - 现代化时间处理

#### 安全组件
- **Python-jose[cryptography]** - JWT令牌处理
- **Passlib[bcrypt]** - 密码哈希加密
- **Python-multipart** - 文件上传支持

#### API文档与开发工具
- **Swagger/OpenAPI** - API文档自动生成
  - FastAPI内置支持
  - 交互式API测试界面
  - 自动生成客户端SDK
  - ReDoc美观文档展示

#### 代码质量工具链
- **Ruff** - 超快Python代码检查器 (Linter)
  - 替代Flake8 + isort + pyupgrade等多个工具
  - Rust实现，速度提升10-100倍
  - 支持600+检查规则
- **Black** - 代码格式化器 (Formatter)
  - 零配置的代码格式化
  - 确保代码风格一致性
- **MyPy** - 静态类型检查器
  - 捕获类型相关错误
  - 提高代码可维护性
- **Pre-commit** - Git提交钩子
  - 自动运行代码质量检查
  - 防止低质量代码提交
- **Bandit** - 安全漏洞检查器
  - 扫描常见安全问题
  - Python安全最佳实践

#### 包管理和环境
- **UV** - 极速Python包管理器
  - 比Poetry快10-100倍
  - 统一的项目管理
  - 兼容pyproject.toml

## 多租户架构设计

### 多租户策略
- **数据隔离**: 共享数据库，独立Schema，通过tenant_id字段隔离
- **网关识别**: APISIX根据子域名或API Key识别租户
- **应用隔离**: 所有业务操作都带上租户上下文

### 微服务拆分策略

#### 服务划分
1. **API Gateway (APISIX)** - 独立部署
2. **User Management Service** - 独立服务 (用户认证、租户管理)
3. **Core Business Service** - 主服务 (产品管理、竞品分析)
4. **Crawler Service** - 独立服务 (Apify集成、数据抓取)

### 整体架构

```mermaid
graph TB
    subgraph "外部用户"
        U1[租户A用户<br/>tenant-a.domain.com]
        U2[租户B用户<br/>tenant-b.domain.com]
        U3[租户C用户<br/>API Key: abc123]
    end

    subgraph "API网关层"
        U1 --> G[APISIX Gateway<br/>租户路由 + JWT认证<br/>:80/443]
        U2 --> G
        U3 --> G
    end

    subgraph "微服务层"
        G --> US[User Service<br/>认证 + 租户管理<br/>:8001]
        G --> CS[Core Service<br/>产品 + 分析<br/>:8002]
        G --> CRS[Crawler Service<br/>Apify集成<br/>:8003]
    end

    subgraph "消息队列层"
        CRS --> SQS[AWS SQS<br/>消息队列]
        CS --> SQS
        SQS --> CW[Celery Workers<br/>数据抓取]
        SQS --> CAW[Celery Workers<br/>AI分析]
        SQS --> CTW[Celery Beat<br/>定时任务]
    end

    subgraph "外部API层"
        CW --> AP[Apify API<br/>Amazon Product Details]
        CAW --> LC[LangChain + OpenAI<br/>竞品分析 + 优化建议]
    end

    subgraph "数据存储层"
        US --> DB[(Supabase PostgreSQL<br/>多租户Schema + 分区)]
        CS --> DB
        CRS --> DB
        CW --> DB
        CAW --> DB

        CS --> R[Redis<br/>缓存 + 会话]
        CRS --> R
        CW --> R
    end

    subgraph "监控观测层"
        G --> OT[OpenTelemetry<br/>分布式追踪]
        US --> OT
        CS --> OT
        CRS --> OT
        CW --> OT

        OT --> P[Prometheus<br/>指标收集]
        P --> GR[Grafana<br/>可视化面板]

        US --> CW2[CloudWatch<br/>AWS云监控]
        CS --> CW2
        SQS --> CW2
    end
```

### 数据流设计

```mermaid
sequenceDiagram
    participant U as 用户
    participant G as APISIX网关
    participant F as FastAPI
    participant C as Celery
    participant R as Redis
    participant D as 数据库
    participant A as Apify
    participant O as OpenAI

    U->>G: API请求
    G->>F: 验证通过的请求
    F->>R: 检查缓存
    alt 缓存命中
        R->>F: 返回缓存数据
    else 缓存未命中
        F->>C: 创建异步任务
        C->>A: 抓取产品数据
        A->>C: 返回数据
        C->>D: 存储数据
        C->>R: 缓存数据
        C->>O: AI分析请求
        O->>C: 分析结果
        C->>D: 存储分析结果
    end
    F->>U: 返回响应
```

## 核心服务设计

### 1. API网关层 (APISIX)
- **功能**：
  - JWT身份验证
  - API限流和熔断
  - 请求/响应加密解密
  - 路由转发和负载均衡
  - API版本管理
  - 实时配置更新（etcd）

### 2. 应用服务层 (FastAPI)
- **产品追踪服务**
  - 产品数据管理API
  - 价格历史追踪
  - BSR趋势分析
  - 评价变化监控

- **竞品分析服务**
  - 竞品关系管理
  - 多维对比分析
  - LLM报告生成
  - 数据标准化处理

### 3. 异步任务层 (Celery)
- **数据抓取任务**
  - 定时产品数据抓取
  - 批量处理优化
  - 失败重试机制

- **AI分析任务**
  - LangChain集成处理
  - Prompt模板管理
  - 结果缓存优化

## 数据库设计

### 多租户架构表结构

#### 1. 租户与用户管理

```sql
-- 租户表
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    subdomain VARCHAR(100) UNIQUE,
    api_key VARCHAR(255) UNIQUE,
    plan_type VARCHAR(50) DEFAULT 'basic', -- 'basic', 'premium', 'enterprise'
    max_products INTEGER DEFAULT 100,
    max_users INTEGER DEFAULT 5,
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'suspended', 'cancelled'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_subdomain (subdomain),
    INDEX idx_api_key (api_key)
);

-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user', -- 'admin', 'user', 'viewer'
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'inactive', 'pending'
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, email),
    INDEX idx_tenant_email (tenant_id, email),
    INDEX idx_email (email)
);
```

#### 2. 产品管理核心表

```sql
-- 产品表
CREATE TABLE products (
    product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    asin VARCHAR(10) NOT NULL,
    product_url TEXT NOT NULL,
    title TEXT,
    brand VARCHAR(255),
    category VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'inactive', 'paused'
    crawl_frequency VARCHAR(50) DEFAULT 'daily', -- 'hourly', 'daily', 'weekly'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, asin),
    INDEX idx_tenant_asin (tenant_id, asin),
    INDEX idx_user_products (user_id),
    INDEX idx_tenant_category (tenant_id, category),
    INDEX idx_status (status)
);

-- 品类管理表
CREATE TABLE categories (
    category_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    keywords TEXT[], -- 关键词数组
    auto_crawl BOOLEAN DEFAULT true,
    crawl_schedule VARCHAR(50) DEFAULT 'daily',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, name),
    INDEX idx_tenant_category (tenant_id, name)
);
```

#### 3. 产品追踪数据表（时序数据）

```sql
-- 产品追踪数据表 (分区表，最大数据量)
CREATE TABLE product_tracking_data (
    data_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(product_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    price NUMERIC(10, 2),
    bsr INTEGER, -- Best Seller Rank
    rating NUMERIC(3, 2),
    review_count INTEGER,
    buy_box_price NUMERIC(10, 2),
    availability VARCHAR(100),
    seller_name VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    INDEX idx_product_date (product_id, date DESC),
    INDEX idx_tenant_date (tenant_id, date DESC),
    INDEX idx_created_at (created_at),
    UNIQUE(product_id, date)
) PARTITION BY RANGE (date);

-- 创建分区 (按月分区)
CREATE TABLE product_tracking_data_2024_01 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE product_tracking_data_2024_02 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
-- ... 继续创建更多分区
```

#### 4. 竞品分析相关表

```sql
-- 竞品数据表
CREATE TABLE competitor_data (
    competitor_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_product_id UUID REFERENCES products(product_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    competitor_asin VARCHAR(10) NOT NULL,
    competitor_url TEXT NOT NULL,
    relationship_type VARCHAR(50) DEFAULT 'category', -- 'direct', 'category', 'brand'
    data JSONB NOT NULL, -- 存储多维度比较数据
    similarity_score NUMERIC(3,2),
    analysis_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'completed', 'failed'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_parent_product (parent_product_id),
    INDEX idx_tenant_competitor (tenant_id, competitor_asin),
    INDEX idx_analysis_status (analysis_status),
    INDEX gin_data (data) -- GIN索引用于JSONB查询
);

-- 分析报告表
CREATE TABLE analysis_reports (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(product_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    report_type VARCHAR(50) NOT NULL, -- 'competitor_analysis', 'market_trend'
    title VARCHAR(255) NOT NULL,
    content JSONB NOT NULL,
    ai_model VARCHAR(100), -- 'gpt-4', 'gpt-3.5-turbo'
    tokens_used INTEGER,
    generation_time_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    INDEX idx_product_type (product_id, report_type),
    INDEX idx_tenant_reports (tenant_id, created_at DESC),
    INDEX idx_created_at (created_at DESC)
);
```

#### 5. 优化建议表

```sql
-- 优化建议表
CREATE TABLE optimization_suggestions (
    suggestion_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(product_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    suggestion_type VARCHAR(50) NOT NULL, -- 'price', 'title', 'description', 'images', 'keywords'
    suggestion_text TEXT NOT NULL,
    reason TEXT NOT NULL,
    priority INTEGER NOT NULL CHECK (priority >= 1 AND priority <= 5), -- 1=highest, 5=lowest
    estimated_impact VARCHAR(50), -- 'high', 'medium', 'low'
    implementation_difficulty VARCHAR(50), -- 'easy', 'medium', 'hard'
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'implemented', 'dismissed'
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_product_suggestions (product_id, priority),
    INDEX idx_tenant_suggestions (tenant_id, generated_at DESC),
    INDEX idx_type_priority (suggestion_type, priority)
);
```

#### 6. 任务管理表

```sql
-- 任务表
CREATE TABLE tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    task_type VARCHAR(50) NOT NULL, -- 'crawl', 'analysis', 'suggestion'
    task_name VARCHAR(255) NOT NULL,
    parameters JSONB,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    priority INTEGER DEFAULT 3, -- 1=highest, 5=lowest
    progress INTEGER DEFAULT 0, -- 0-100
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_tenant_tasks (tenant_id, created_at DESC),
    INDEX idx_status_priority (status, priority),
    INDEX idx_task_type (task_type)
);
```

### 数据分区策略
- **product_tracking_data表**: 按时间分区（月度分区）
- **analysis_reports表**: 按创建时间分区
- **索引优化**: 覆盖索引用于常见查询模式
- **JSONB优化**: 使用GIN索引支持复杂查询

## API接口设计

### 接口规范
- **版本控制**: /api/v1/
- **认证方式**: JWT Bearer Token
- **响应格式**: JSON
- **状态码**: 标准HTTP状态码
- **错误格式**: `{"error": "message", "code": "ERROR_CODE"}`

### API文档集成
- **Swagger UI**: `/docs` - 交互式API文档
- **ReDoc**: `/redoc` - 美观的API文档展示
- **OpenAPI Schema**: `/openapi.json` - API规范下载

#### FastAPI Swagger配置
```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="Amazon产品追踪分析系统",
    description="多租户SaaS平台，提供Amazon产品数据追踪、竞品分析和优化建议",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json"
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Amazon Tracker API",
        version="1.0.0",
        description="Amazon产品追踪分析系统API文档",
        routes=app.routes,
    )
    # 添加JWT认证Schema
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

#### API标签分组
```python
tags_metadata = [
    {
        "name": "认证",
        "description": "用户认证和授权相关接口",
    },
    {
        "name": "用户管理",
        "description": "用户信息管理接口",
    },
    {
        "name": "租户管理",
        "description": "多租户管理接口",
    },
    {
        "name": "产品追踪",
        "description": "Amazon产品数据追踪接口",
    },
    {
        "name": "竞品分析",
        "description": "竞品分析和对比接口",
    },
    {
        "name": "优化建议",
        "description": "AI生成的产品优化建议接口",
    },
    {
        "name": "任务管理",
        "description": "异步任务管理接口",
    },
    {
        "name": "系统管理",
        "description": "系统监控和管理接口",
    }
]

app = FastAPI(openapi_tags=tags_metadata)
```

### 1. 认证与用户管理 API

#### 认证接口
```bash
POST /api/v1/auth/register      # 用户注册
POST /api/v1/auth/login         # 用户登录
POST /api/v1/auth/refresh       # 刷新Token
POST /api/v1/auth/logout        # 用户登出
POST /api/v1/auth/forgot-password  # 忘记密码
POST /api/v1/auth/reset-password   # 重置密码
```

**示例请求/响应:**
```json
// POST /api/v1/auth/register
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "securePassword123",
  "tenant_code": "company-abc" // 可选，加入现有租户
}

// Response
{
  "message": "User created successfully",
  "user_id": "uuid-here",
  "tenant_id": "uuid-here"
}

// POST /api/v1/auth/login
{
  "email": "john@example.com",
  "password": "securePassword123"
}

// Response
{
  "access_token": "jwt-token-here",
  "refresh_token": "refresh-token-here",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid-here",
    "email": "john@example.com",
    "role": "user",
    "tenant_id": "uuid-here"
  }
}
```

#### 用户管理接口
```bash
GET /api/v1/users/profile       # 获取当前用户信息
PUT /api/v1/users/profile       # 更新用户信息
PUT /api/v1/users/password      # 修改密码
GET /api/v1/users               # 获取用户列表（管理员）
GET /api/v1/users/{user_id}     # 获取用户详情（管理员）
PUT /api/v1/users/{user_id}     # 更新用户（管理员）
DELETE /api/v1/users/{user_id}  # 删除用户（管理员）
```

### 2. 租户管理 API

```bash
GET /api/v1/tenants/current     # 获取当前租户信息
PUT /api/v1/tenants/current     # 更新当前租户信息
GET /api/v1/tenants             # 获取租户列表（超管）
POST /api/v1/tenants            # 创建租户（超管）
GET /api/v1/tenants/{tenant_id} # 获取租户详情（超管）
PUT /api/v1/tenants/{tenant_id} # 更新租户（超管）
DELETE /api/v1/tenants/{tenant_id} # 删除租户（超管）
GET /api/v1/tenants/current/users  # 获取租户用户列表
POST /api/v1/tenants/current/users # 邀请用户加入租户
DELETE /api/v1/tenants/current/users/{user_id} # 移除租户用户
```

### 3. 产品追踪 API

```bash
GET /api/v1/products            # 获取产品列表
POST /api/v1/products           # 添加产品到监控
GET /api/v1/products/{product_id}       # 获取产品详情
PUT /api/v1/products/{product_id}       # 更新产品信息
DELETE /api/v1/products/{product_id}    # 删除产品
GET /api/v1/products/{product_id}/data  # 获取产品历史数据
POST /api/v1/products/batch             # 批量添加产品
POST /api/v1/products/{product_id}/crawl # 手动触发爬取
PUT /api/v1/products/{product_id}/status # 更新产品状态
```

**示例请求/响应:**
```json
// POST /api/v1/products
{
  "asin": "B08N5WRWNW",
  "product_url": "https://amazon.com/dp/B08N5WRWNW",
  "name": "Sony WH-1000XM4 Wireless Headphones",
  "category": "bluetooth-headphones",
  "crawl_frequency": "daily"
}

// Response
{
  "product_id": "uuid-here",
  "message": "Product added to tracking list",
  "estimated_first_crawl": "2024-01-15T10:00:00Z"
}

// GET /api/v1/products/{product_id}/data
// Response
[
  {
    "date": "2024-01-14",
    "price": 279.99,
    "buy_box_price": 279.99,
    "bsr": 1234,
    "rating": 4.4,
    "review_count": 89234,
    "availability": "In Stock"
  }
]
```

### 4. 品类管理 API

```bash
GET /api/v1/categories          # 获取品类列表
POST /api/v1/categories         # 添加品类
GET /api/v1/categories/{category_id}        # 获取品类详情
PUT /api/v1/categories/{category_id}        # 更新品类
DELETE /api/v1/categories/{category_id}     # 删除品类
GET /api/v1/categories/{category_id}/products # 获取品类产品
POST /api/v1/categories/{category_id}/crawl   # 触发品类爬取
```

### 5. 竞品分析 API

```bash
POST /api/v1/competitors/{product_id}       # 添加竞品分析任务
GET /api/v1/competitors/tasks/{task_id}     # 查询分析任务状态
GET /api/v1/competitors/reports/{product_id} # 获取竞品分析报告
GET /api/v1/competitors/{product_id}        # 获取产品竞品列表
DELETE /api/v1/competitors/{competitor_id}   # 删除竞品关系
POST /api/v1/competitors/{product_id}/compare # 生成对比报告
```

**示例请求/响应:**
```json
// POST /api/v1/competitors/{product_id}
{
  "competitor_urls": [
    "https://amazon.com/dp/B08XXXXX",
    "https://amazon.com/dp/B09XXXXX"
  ],
  "analysis_type": "full", // 'quick', 'full', 'deep'
  "priority": "high"
}

// Response
{
  "task_id": "uuid-here",
  "message": "Competitor analysis task started",
  "estimated_completion": "2024-01-15T10:05:00Z"
}

// GET /api/v1/competitors/tasks/{task_id}
// Response
{
  "task_id": "uuid-here",
  "status": "completed", // 'pending', 'running', 'completed', 'failed'
  "progress": 100,
  "started_at": "2024-01-15T10:00:00Z",
  "completed_at": "2024-01-15T10:04:32Z",
  "report_id": "uuid-here"
}
```

### 6. 优化建议 API

```bash
POST /api/v1/suggestions/{product_id}       # 生成优化建议
GET /api/v1/suggestions/tasks/{task_id}     # 查询建议生成状态
GET /api/v1/suggestions/{product_id}        # 获取产品建议列表
PUT /api/v1/suggestions/{suggestion_id}/status # 更新建议状态
DELETE /api/v1/suggestions/{suggestion_id}   # 删除建议
POST /api/v1/suggestions/{product_id}/regenerate # 重新生成建议
```

**示例请求/响应:**
```json
// POST /api/v1/suggestions/{product_id}
{
  "suggestion_types": ["price", "title", "description"],
  "analysis_depth": "comprehensive", // 'quick', 'standard', 'comprehensive'
  "include_competitor_data": true
}

// Response
{
  "task_id": "uuid-here",
  "message": "Optimization suggestion task started"
}

// GET /api/v1/suggestions/{product_id}
// Response
{
  "product_id": "uuid-here",
  "suggestions": [
    {
      "suggestion_id": "uuid-here",
      "type": "price_adjustment",
      "suggestion_text": "Consider reducing price to $249.99",
      "reason": "Competitors average $245, your current price is 14% higher",
      "priority": 1,
      "estimated_impact": "high",
      "implementation_difficulty": "easy",
      "status": "pending"
    }
  ],
  "generated_at": "2024-01-15T10:00:00Z"
}
```

### 7. 任务管理 API

```bash
GET /api/v1/tasks               # 获取任务列表
GET /api/v1/tasks/{task_id}     # 获取任务详情
POST /api/v1/tasks/{task_id}/cancel   # 取消任务
POST /api/v1/tasks/{task_id}/retry    # 重试失败任务
DELETE /api/v1/tasks/{task_id}  # 删除任务记录
```

### 8. 系统管理 API

```bash
GET /api/v1/health              # 健康检查
GET /api/v1/health/detailed     # 详细健康检查
GET /api/v1/metrics             # 系统指标
GET /api/v1/settings            # 获取系统设置
PUT /api/v1/settings            # 更新系统设置
GET /api/v1/stats               # 获取使用统计
POST /api/v1/webhooks           # 配置Webhook
GET /api/v1/logs                # 获取日志（管理员）
```

### API响应格式规范

#### 成功响应
```json
{
  "data": {...},
  "message": "Success message",
  "timestamp": "2024-01-15T10:00:00Z"
}
```

#### 错误响应
```json
{
  "error": "Detailed error message",
  "code": "VALIDATION_ERROR",
  "field": "asin", // 字段级错误
  "timestamp": "2024-01-15T10:00:00Z"
}
```

#### 分页响应
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 156,
    "pages": 8
  }
}
```

## 缓存策略

### Redis缓存层次
```
Level 1: API响应缓存 (30分钟)
├── 产品基本信息
├── 价格趋势数据
└── 竞品分析报告

Level 2: 计算结果缓存 (6小时)
├── 聚合统计数据
├── BSR趋势计算
└── AI分析结果

Level 3: 会话缓存 (24小时)
├── 用户认证信息
├── API限流计数
└── 任务状态跟踪
```

## 安全架构

### 多层安全防护
1. **网关层安全 (APISIX)**
   - TLS/SSL加密传输
   - JWT令牌验证
   - API限流保护
   - IP白名单/黑名单

2. **应用层安全 (FastAPI)**
   - 输入数据验证 (Pydantic)
   - SQL注入防护 (SQLAlchemy)
   - 敏感数据脱敏

3. **数据层安全**
   - 数据库连接加密
   - 敏感字段加密存储
   - 定期数据备份

### 环境变量配置
```bash
# API Keys
OPENAI_API_KEY=sk-xxx
APIFY_API_TOKEN=xxx
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_KEY=xxx

# Database & Cache
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://user:password@localhost:5432/amazon_tracker
SUPABASE_DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres

# AWS Services
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_REGION=us-east-1
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/xxx/amazon-tracker-queue
SQS_DLQ_URL=https://sqs.us-east-1.amazonaws.com/xxx/amazon-tracker-dlq

# APISIX Gateway
APISIX_ADMIN_KEY=apisix_admin_key_here
APISIX_PROXY_URL=http://localhost:9080
APISIX_ADMIN_URL=http://localhost:9180
ETCD_HOST=localhost
ETCD_PORT=2379

# Security
JWT_SECRET=your-super-secret-jwt-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24
JWT_REFRESH_EXPIRE_DAYS=7
BCRYPT_ROUNDS=12

# API Configuration
API_V1_PREFIX=/api/v1
API_RATE_LIMIT=100/hour
API_BURST_LIMIT=20/minute
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Celery Configuration
CELERY_BROKER_URL=sqs://${AWS_ACCESS_KEY_ID}:${AWS_SECRET_ACCESS_KEY}@sqs.${AWS_REGION}.amazonaws.com
CELERY_RESULT_BACKEND=redis://localhost:6379/1
CELERY_TASK_SERIALIZER=json
CELERY_RESULT_SERIALIZER=json
CELERY_TIMEZONE=UTC

# Monitoring & Observability
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
LOG_LEVEL=INFO
ENVIRONMENT=production
OPENTELEMETRY_ENDPOINT=http://localhost:4317
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# External APIs
APIFY_TIMEOUT=300
APIFY_MAX_RETRIES=3
OPENAI_TIMEOUT=60
OPENAI_MAX_TOKENS=4000
OPENAI_MODEL=gpt-4o-mini

# Application Settings
MAX_PRODUCTS_PER_TENANT=1000
MAX_CONCURRENT_CRAWLS=5
DATA_RETENTION_DAYS=365
CACHE_TTL_SECONDS=3600

# Development Settings (开发环境)
DEBUG=false
RELOAD=false
WORKERS=4
```

## 监控与观测性 ✅

### 指标收集 (Prometheus) ✅
- APISIX网关指标 (HTTP请求数、延迟、状态码)
- 系统资源指标 (CPU、内存、网络)
- 业务指标收集能力

### 数据可视化 (Grafana) ✅
- APISIX监控仪表板
- 实时指标图表展示
- 告警规则配置

### 分布式追踪 (Jaeger + OpenTelemetry) ✅
- HTTP请求完整追踪链路
- 性能瓶颈识别
- 跨服务调用分析

### 日志记录 ✅
- 结构化访问日志
- 错误日志收集
- Docker日志统一管理

## CI/CD工作流

### GitHub Actions工作流
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: poetry install
      - name: Run tests
        run: |
          poetry run pytest --cov=.
          poetry run ruff check .
          poetry run black --check .

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t amazon-tracker .
      - name: Push to registry
        run: docker push amazon-tracker:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: |
          # 部署脚本
          docker-compose -f docker-compose.prod.yml up -d
```

## 部署架构

### 容器化部署
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose部署
- **FastAPI**: 多实例部署
- **Celery Workers**: 基于队列长度手动扩展
- **Redis**: 单机高可用模式
- **负载均衡**: APISIX网关

## 性能优化策略

### 应用层优化
- 异步I/O操作 (FastAPI + asyncio)
- 连接池管理 (数据库/Redis)
- 批量处理优化
- 查询优化和索引策略

### 缓存优化
- 多级缓存策略
- 缓存预热机制
- 智能缓存失效

### 数据库优化
- 读写分离
- 数据分区
- 索引优化
- 查询缓存

## 可扩展性设计

### 水平扩展
- **应用层**: 无状态设计，支持多实例
- **任务队列**: Celery分布式workers
- **数据库**: 读副本扩展
- **缓存**: Redis集群

### 垂直扩展
- 资源监控和自动扩容
- 性能瓶颈识别
- 容量规划

## 开发工作流

### 本地开发环境

#### UV环境管理
```bash
# 安装UV (推荐使用官方安装脚本)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 项目初始化
git clone <repository>
cd amazon-tracker

# 创建虚拟环境并安装依赖
uv venv
uv pip install -r requirements.txt

# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows
```

#### 开发服务启动
```bash
# 启动基础设施服务
docker-compose -f docker-compose.dev.yml up -d

# 数据库迁移
uv run alembic upgrade head

# 启动各个服务 (多终端)
# Terminal 1: 用户服务
cd services/user-service
uv run uvicorn app.main:app --reload --port 8001

# Terminal 2: 核心服务
cd services/core-service
uv run uvicorn app.main:app --reload --port 8002

# Terminal 3: 爬虫服务
cd services/crawler-service
uv run uvicorn app.main:app --reload --port 8003

# Terminal 4: Celery Worker
uv run celery -A app.celery worker --loglevel=info

# Terminal 5: Celery Beat (定时任务)
uv run celery -A app.celery beat --loglevel=info
```

#### 开发环境Docker Compose
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  # 开发环境PostgreSQL
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: amazon_tracker_dev
      POSTGRES_USER: dev_user
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data

  # 开发环境Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_dev_data:/data

  # APISIX开发环境
  apisix-dev:
    image: apache/apisix:latest
    environment:
      APISIX_ETCD_HOST: etcd-dev
    ports:
      - "9080:9080"
      - "9180:9180"
    volumes:
      - ./config/apisix/config.dev.yaml:/usr/local/apisix/conf/config.yaml
    depends_on:
      - etcd-dev

  # etcd开发环境
  etcd-dev:
    image: bitnami/etcd:latest
    environment:
      ETCD_ENABLE_V2: "true"
      ALLOW_NONE_AUTHENTICATION: "yes"
      ETCD_ADVERTISE_CLIENT_URLS: "http://0.0.0.0:2379"
      ETCD_LISTEN_CLIENT_URLS: "http://0.0.0.0:2379"
    ports:
      - "2379:2379"

volumes:
  postgres_dev_data:
  redis_dev_data:
```

### 代码质量保证
- Pre-commit钩子自动检查
- 单元测试覆盖率 >80%
- 集成测试和端到端测试
- 性能回归测试

## Apify触发机制设计

### 三种触发方式

#### 1. 手动触发
```python
# API: POST /api/v1/crawl/manual
{
  "product_ids": ["B07ABC123", "B08DEF456"],
  "priority": "high"
}
```

#### 2. 品类添加触发
```python
# API: POST /api/v1/categories
{
  "name": "Electronics",
  "keywords": ["smartphone", "laptop"],
  "auto_crawl": true
}
# 自动触发该品类产品抓取
```

#### 3. 定时触发
```python
# Celery Beat配置
CELERY_BEAT_SCHEDULE = {
    'daily-crawl-all-tenants': {
        'task': 'crawler.tasks.daily_crawl_scheduler',
        'schedule': crontab(hour=2, minute=0),  # 每天凌晨2点
    },
}
```

### 触发优先级管理
- **手动触发**: 高优先级，立即执行
- **品类添加**: 中优先级，5分钟内执行
- **定时触发**: 低优先级，批量执行

## Docker部署架构

### 服务器部署拓扑
```
Production Server (单机Docker部署)
├── APISIX Gateway     :9080/9443
├── etcd               :2379
├── User Service       :8001
├── Core Service       :8002
├── Crawler Service    :8003
├── Application DB     :5432 (Supabase PostgreSQL)
├── Redis             :6379
├── Celery Workers    (内部通信)
├── Prometheus        :9090
└── Grafana           :3000
```

### Docker Compose部署配置
```yaml
version: '3.8'

networks:
  apisix-net:
    driver: bridge

services:
  # etcd
  etcd:
    image: bitnami/etcd:latest
    environment:
      ETCD_ENABLE_V2: "true"
      ALLOW_NONE_AUTHENTICATION: "yes"
      ETCD_ADVERTISE_CLIENT_URLS: "http://0.0.0.0:2379"
      ETCD_LISTEN_CLIENT_URLS: "http://0.0.0.0:2379"
    ports:
      - "2379:2379"
      - "2380:2380"
    networks:
      - apisix-net
    volumes:
      - etcd_data:/bitnami/etcd

  # APISIX Gateway
  apisix:
    image: apache/apisix:latest
    environment:
      APISIX_ETCD_HOST: etcd
    ports:
      - "9080:9080"
      - "9180:9180"
      - "9443:9443"
    depends_on:
      - etcd
    networks:
      - apisix-net
    volumes:
      - ./config/apisix/config.yaml:/usr/local/apisix/conf/config.yaml
      - ./config/apisix/apisix.yaml:/usr/local/apisix/conf/apisix.yaml
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9080/apisix/status"]
      interval: 10s
      timeout: 5s
      retries: 5

  # 用户管理服务
  user-service:
    build: ./services/user-service
    ports:
      - "8001:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - postgres
      - redis

  # 核心业务服务
  core-service:
    build: ./services/core-service
    ports:
      - "8002:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis

  # 爬虫服务
  crawler-service:
    build: ./services/crawler-service
    ports:
      - "8003:8000"
    environment:
      - APIFY_API_TOKEN=${APIFY_API_TOKEN}
      - REDIS_URL=${REDIS_URL}
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - redis
      - postgres

  # Celery Workers
  celery-worker:
    build: ./services/crawler-service
    command: celery -A app.celery worker --loglevel=info
    environment:
      - APIFY_API_TOKEN=${APIFY_API_TOKEN}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - redis

  celery-beat:
    build: ./services/crawler-service
    command: celery -A app.celery beat --loglevel=info
    environment:
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - redis
```

### GitHub Actions CI/CD
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install Poetry
        run: pip install poetry
      - name: Install dependencies
        run: poetry install
      - name: Run tests
        run: |
          poetry run pytest --cov=.
          poetry run ruff check .
          poetry run black --check .

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3

      - name: Setup SSH
        uses: webfactory/ssh-agent@v0.7.0
        with:
          ssh-private-key: ${{ secrets.SSH_PRIVATE_KEY }}

      - name: Deploy to server
        run: |
          ssh -o StrictHostKeyChecking=no ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_HOST }} '
            cd /opt/amazon-tracker &&
            git pull origin main &&
            cp .env.production .env &&
            docker-compose -f docker-compose.prod.yml down &&
            docker-compose -f docker-compose.prod.yml build &&
            docker-compose -f docker-compose.prod.yml up -d &&
            docker system prune -f
          '

      - name: Health Check
        run: |
          sleep 30
          curl -f http://${{ secrets.SERVER_HOST }}/health || exit 1
```

## 开发流程规划

### Phase 1: 基础设施 (Days 1-2)
1. **项目初始化**
   - GitHub仓库创建
   - Poetry项目配置
   - Docker环境搭建
   - 代码规范配置 (Black, Ruff, Pre-commit)

2. **数据库设计**
   - 多租户Schema设计
   - Alembic迁移脚本
   - Supabase配置

### Phase 2: API网关与认证 (Days 3-4)
1. **APISIX网关配置**
   - 多租户路由规则
   - JWT认证插件
   - 限流熔断配置

2. **用户管理服务**
   - JWT认证实现
   - 租户CRUD API
   - 权限管理系统

### Phase 3: 爬虫服务 (Days 5-7)
1. **Apify集成**
   - 客户端封装
   - 三种触发机制
   - 数据标准化

2. **Celery任务系统**
   - 任务队列配置
   - 定时任务调度
   - 失败重试机制

### Phase 4: 核心业务 (Days 8-12)
1. **产品数据管理**
   - 产品CRUD API
   - 价格历史追踪
   - 数据变化通知

2. **竞品分析引擎**
   - LangChain集成
   - AI分析任务
   - 报告生成系统

### Phase 5: 测试与部署 (Days 13-14)
1. **测试完善**
   - 单元测试 (>80%覆盖率)
   - 集成测试
   - 性能测试

2. **生产部署**
   - 监控系统配置
   - 生产环境部署
   - 文档完善

### 开发优先级
```
网关认证 → 数据库 → 爬虫服务 → 核心业务 → 测试部署
```

**关键里程碑:**
- Day 4: 认证系统可用
- Day 7: 数据抓取可用
- Day 12: 核心功能完成
- Day 14: 生产就绪


## 总结

本架构设计基于现代云原生微服务和多租户SaaS架构原则，具备以下核心特点：

### 技术架构特色
1. **多租户SaaS架构**: 数据层隔离 + APISIX网关路由，支持子域名和API Key双模式
2. **微服务设计**: 用户服务、核心服务、爬虫服务合理拆分，职责清晰
3. **云原生消息队列**: AWS SQS + Celery分布式任务处理，可靠性高
4. **高性能网关**: APISIX Gateway提供毫秒级配置更新和原生监控集成
5. **现代化工具链**: UV包管理、FastAPI异步框架、LangChain AI集成

### 性能与扩展性
1. **高性能**: FastAPI异步处理 + Redis多级缓存 + PostgreSQL分区表
2. **高可扩展**: 水平扩展设计 + Docker容器化 + SQS自动伸缩
3. **智能调度**: 三种Apify触发机制（手动、品类、定时）+ 优先级管理
4. **数据优化**: 时序数据分区 + JSONB索引 + 连接池管理

### 开发与运维
1. **完整API设计**: 8大模块60+接口，RESTful规范 + JWT认证
2. **可观测性**: Jaeger分布式追踪 + Prometheus指标 + Grafana可视化 ✅
3. **开发体验**: UV快速环境管理 + 热重载 + Pre-commit代码检查
4. **生产就绪**: Docker部署 + GitHub Actions CI/CD + 健康检查

### 业务价值
1. **Amazon专业爬虫**: Apify Product Details专用爬虫，蓝牙耳机品类优化
2. **AI驱动分析**: LangChain + OpenAI生成竞品分析和优化建议
3. **企业级多租户**: 支持不同计划类型，灵活的用户和权限管理
4. **数据驱动决策**: 完整的产品追踪数据 + 历史趋势分析

### 部署与成本
1. **简化部署**: 单机Docker Compose部署，无需Kubernetes复杂性
2. **成本优化**: SQS按需付费 + Redis缓存减少API调用 + 智能任务调度
3. **监控完备**: APISIX原生Prometheus集成，性能开销极低
4. **安全保障**: JWT认证 + 多层防护 + 敏感数据加密

### 发展路径
该架构设计能够支持：
- **MVP阶段**: 快速启动，单机部署，基础功能验证
- **成长期**: 多租户扩展，性能优化，功能丰富
- **成熟期**: 大规模部署，企业级特性，国际化支持

**预期容量**: 支持1000+租户，每租户1000+产品监控，日处理百万级数据点。
