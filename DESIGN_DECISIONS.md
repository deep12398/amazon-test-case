# Amazon产品追踪系统 - 技术决策文档

本文档记录了Amazon产品追踪分析系统开发过程中的关键技术决策，包括决策背景、考量因素和预期效果。

## 架构决策

### 1. 微服务架构 vs 单体架构

**决策**: 采用微服务架构

**背景**:
- 系统需要支持多租户SaaS模式
- 不同功能模块具有不同的扩展需求
- 团队希望实现独立部署和技术栈灵活性

**考量因素**:
- ✅ **优势**:
  - 服务独立部署和扩展
  - 技术栈选择灵活
  - 故障隔离，提高系统可用性
  - 团队可以并行开发不同服务
- ❌ **挑战**:
  - 分布式系统复杂性
  - 服务间通信开销
  - 数据一致性问题

**实施方案**:
```
User Service (8001)     → 用户认证、租户管理
Core Service (8003)     → 产品管理、竞品分析
Crawler Service (8002)  → 数据抓取、Apify集成
```

**结果**: 成功实现了服务的独立开发和部署，支持按需扩展不同服务。

---

### 2. API网关选择: APISIX vs Nginx vs Kong

**决策**: 选择Apache APISIX

**背景**: 需要一个高性能、功能丰富的API网关来处理多租户路由、认证和流量控制。

**对比分析**:

| 特性 | APISIX | Kong | Nginx |
|------|--------|------|-------|
| 性能 | 高 (基于OpenResty) | 中等 | 高 |
| 动态配置 | ✅ (etcd, 毫秒级) | ✅ (数据库) | ❌ (需要重启) |
| 插件生态 | ✅ 丰富 | ✅ 丰富 | ⚠️ 有限 |
| 云原生 | ✅ K8s原生支持 | ✅ 支持 | ⚠️ 需要额外配置 |
| 多租户 | ✅ 原生支持 | ⚠️ 需要自定义 | ❌ 复杂配置 |
| 可观测性 | ✅ Prometheus集成 | ✅ 支持 | ⚠️ 需要配置 |
| 学习成本 | 低 | 中等 | 高 |

**决策理由**:
1. **动态配置**: etcd支持毫秒级配置更新，无需重启
2. **多租户友好**: 原生支持基于域名/API Key的租户隔离
3. **可观测性**: 内置Prometheus metrics和OpenTelemetry集成
4. **插件系统**: 丰富的认证、限流、安全插件
5. **云原生**: 与Kubernetes深度集成

**实施配置**:
```yaml
# 认证插件
- jwt-auth      # JWT令牌验证
- key-auth      # API Key认证
- basic-auth    # Basic认证

# 流量控制
- limit-req     # 请求限流
- limit-conn    # 连接限流
- limit-count   # 计数限流

# 安全防护
- cors          # 跨域支持
- ip-restriction # IP控制
```

---

### 3. 消息队列选择: Redis vs AWS SQS vs RabbitMQ

**决策**: 使用Redis作为Celery消息代理

**初始方案**: 计划使用AWS SQS + Celery
**最终方案**: Redis + Celery

**变更原因**:

| 考量因素 | AWS SQS | Redis | RabbitMQ |
|----------|---------|-------|----------|
| **成本** | 按使用付费 | 免费(自托管) | 免费(自托管) |
| **延迟** | 较高(网络) | 极低(内存) | 低 |
| **可靠性** | 99.9% SLA | 需要自己保证 | 需要自己保证 |
| **部署复杂度** | 简单 | 简单 | 复杂 |
| **功能丰富度** | 基础 | 丰富 | 非常丰富 |
| **Celery集成** | 支持 | 原生支持 | 原生支持 |

**决策理由**:
1. **统一架构**: Redis既用作缓存又用作消息队列，减少组件复杂性
2. **成本考量**: 开发和小规模部署阶段，Redis成本更低
3. **性能优势**: 内存存储，延迟极低
4. **开发便利**: 本地开发环境配置简单
5. **功能足够**: 支持Celery所需的所有功能

**实施配置**:
```python
# Celery配置
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"

# 任务队列设计
CELERY_TASK_ROUTES = {
    'crawler.tasks.*': {'queue': 'crawler'},
    'analysis.tasks.*': {'queue': 'analysis'},
    'notifications.*': {'queue': 'notifications'},
}
```

**扩展计划**: 生产环境高负载时可考虑Redis Cluster或迁移到RabbitMQ。

---

### 4. 数据库选择: Supabase vs 自托管PostgreSQL

**决策**: 使用Supabase托管PostgreSQL

**背景**: 需要一个可靠的PostgreSQL数据库，同时希望减少运维复杂度。

**对比分析**:

| 方面 | Supabase | 自托管PostgreSQL |
|------|----------|------------------|
| **运维负担** | 低 | 高 |
| **成本** | 付费(有免费额度) | 基础设施成本 |
| **扩展性** | 自动扩展 | 需要手动管理 |
| **备份恢复** | 自动 | 需要自己实现 |
| **高可用** | 内置 | 需要自己搭建 |
| **监控** | 内置仪表板 | 需要自己配置 |
| **实时功能** | 内置Realtime | 需要额外组件 |
| **认证集成** | 内置Auth | 需要自己实现 |

**决策理由**:
1. **快速启动**: 专注业务逻辑，而非数据库运维
2. **内置功能**: Realtime订阅、Row Level Security等
3. **成本效益**: 早期阶段免费额度足够使用
4. **可靠性**: 99.9%可用性保证
5. **扩展便利**: 支持读副本、连接池等

**实施方案**:
```python
# 数据库连接配置
DATABASE_URL = "postgresql+asyncpg://postgres:password@db.supabase.co:5432/postgres"

# 多租户隔离
class TenantMixin:
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))

    @classmethod
    def tenant_query(cls, tenant_id: UUID):
        return select(cls).where(cls.tenant_id == tenant_id)
```

---

### 5. 分布式追踪: Jaeger vs Zipkin

**决策**: 选择Jaeger + OpenTelemetry

**背景**: 微服务架构需要分布式追踪来诊断性能问题和调用链路。

**对比分析**:

| 特性 | Jaeger | Zipkin |
|------|--------|--------|
| **CNCF成熟度** | 毕业项目 | 孵化项目 |
| **存储后端** | 多种(ES/Cassandra/Memory) | 多种(ES/MySQL/Memory) |
| **UI体验** | 现代化，功能丰富 | 简洁，基础功能 |
| **OpenTelemetry** | 原生支持 | 支持 |
| **性能** | 高 | 高 |
| **社区活跃度** | 高 | 中等 |
| **部署复杂度** | 中等 | 低 |

**决策理由**:
1. **标准化**: CNCF毕业项目，行业标准
2. **功能丰富**: 强大的查询和分析功能
3. **OpenTelemetry**: 与标准追踪协议完美集成
4. **可扩展**: 支持多种存储后端
5. **社区支持**: 活跃的社区和完善的文档

**实施配置**:
```python
# OpenTelemetry配置
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

def setup_tracing(service_name: str):
    jaeger_exporter = JaegerExporter(
        agent_host_name="localhost",
        agent_port=6832,
    )

    tracer = trace.get_tracer(service_name)
    return tracer
```

---

### 6. 包管理器: UV vs Poetry vs Pip

**决策**: 选择UV作为主要包管理器

**背景**: 需要快速、可靠的Python包管理解决方案。

**性能对比**:
```
安装速度测试(相同依赖):
- pip:    45.2s
- poetry: 22.8s
- uv:     3.1s   (14x faster)
```

**功能对比**:

| 特性 | UV | Poetry | Pip |
|------|----|----|-----|
| **安装速度** | 极快 | 中等 | 慢 |
| **依赖解析** | 快速 | 准确 | 基础 |
| **虚拟环境** | 集成 | 集成 | 需要venv |
| **锁文件** | ✅ | ✅ | ❌ |
| **跨平台** | ✅ | ✅ | ✅ |
| **生态成熟度** | 新兴 | 成熟 | 传统 |
| **学习成本** | 低 | 中等 | 低 |

**决策理由**:
1. **性能卓越**: Rust实现，速度提升10-100倍
2. **兼容性好**: 支持pyproject.toml标准
3. **开发体验**: 统一的项目管理命令
4. **未来趋势**: Astral团队(Ruff作者)出品，发展前景好

**实施方案**:
```bash
# 项目配置
pip install uv

# 虚拟环境管理
uv venv
uv pip install -e ".[dev]"

# 依赖管理
uv add fastapi
uv add --dev pytest
```

---

### 7. 代码质量工具链

**决策**: Ruff + Black + MyPy + Pre-commit

**背景**: 需要统一的代码质量标准和自动化检查。

**工具组合**:

| 工具 | 作用 | 选择理由 |
|------|------|----------|
| **Ruff** | Linting | Rust实现，极快速度，集成多种规则 |
| **Black** | 格式化 | 零配置，社区标准 |
| **MyPy** | 类型检查 | Python类型检查标准 |
| **Pre-commit** | Git钩子 | 自动化质量检查 |

**配置示例**:
```toml
# pyproject.toml
[tool.ruff]
select = ["E", "F", "W", "C", "I", "N", "B", "A"]
line-length = 88
target-version = "py311"

[tool.black]
line-length = 88
target-version = ['py311']

[tool.mypy]
python_version = "3.11"
strict = true
```

---

## 性能优化决策

### 1. 缓存策略: 多级缓存设计

**决策**: Redis多级缓存 + 应用内存缓存

**缓存层次设计**:
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

**决策理由**:
1. **性能提升**: 减少数据库查询和API调用
2. **用户体验**: 快速响应常见请求
3. **成本控制**: 减少外部API(OpenAI/Apify)调用
4. **系统稳定**: 降低数据库负载

---

### 2. 数据库优化策略

**分区表设计**:
```sql
-- 产品追踪数据按月分区
CREATE TABLE product_tracking_data (
    data_id UUID PRIMARY KEY,
    product_id UUID,
    tenant_id UUID,
    date DATE NOT NULL,
    price NUMERIC(10, 2),
    -- 其他字段...
) PARTITION BY RANGE (date);

-- 创建分区
CREATE TABLE product_tracking_data_2024_01
PARTITION OF product_tracking_data
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

**索引策略**:
```sql
-- 复合索引优化常见查询
CREATE INDEX idx_tenant_product_date
ON product_tracking_data (tenant_id, product_id, date DESC);

-- JSONB字段GIN索引
CREATE INDEX gin_analysis_data
ON competitor_data USING GIN (data);
```

---

## 安全决策

### 1. 多层认证体系

**实施方案**:
```
外层: APISIX网关认证 (JWT/API Key)
  ↓
中层: FastAPI依赖注入验证
  ↓
内层: 数据库Row Level Security
```

**JWT设计**:
```python
# 双令牌机制
{
    "access_token": "短期令牌(1小时)",
    "refresh_token": "长期令牌(7天)",
    "token_type": "bearer"
}

# 令牌载荷
{
    "user_id": "uuid",
    "tenant_id": "uuid",
    "role": "admin|user|viewer",
    "scopes": ["products.read", "analytics.write"],
    "exp": 1640995200
}
```

### 2. API限流策略

**APISIX限流配置**:
```yaml
# 请求限流
limit-req:
  rate: 100
  burst: 20
  key: "remote_addr"

# API Key限流
limit-count:
  count: 1000
  time_window: 3600
  key: "header_x_api_key"
```

---

## 监控与观测性决策

### 1. 监控栈选择

**决策**: Prometheus + Grafana + Jaeger

**架构**:
```
应用指标 → Prometheus → Grafana
分布式追踪 → OpenTelemetry → Jaeger
日志聚合 → Docker Logs → 中央日志系统
```

**关键指标定义**:
```python
# 业务指标
- product_crawl_success_rate
- ai_analysis_completion_time
- user_active_sessions
- api_request_rate_per_tenant

# 系统指标
- service_response_time
- database_connection_pool_usage
- redis_cache_hit_rate
- celery_task_queue_length
```

---

## 部署决策

### 1. 容器化 vs 虚拟机

**决策**: Docker容器化部署

**优势**:
- 环境一致性
- 快速扩展
- 资源利用率高
- CI/CD友好

**实施方案**:
```dockerfile
# 多阶段构建优化镜像大小
FROM python:3.11-slim as builder
RUN pip install uv
COPY pyproject.toml ./
RUN uv pip install --system -e ".[dev]"

FROM python:3.11-slim as runtime
COPY --from=builder /usr/local /usr/local
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

### 2. 部署策略: Docker Compose vs Kubernetes

**当前**: Docker Compose (开发和小规模生产)
**未来**: Kubernetes (大规模生产)

**决策理由**:
1. **渐进式**: 先简单后复杂
2. **学习成本**: Docker Compose更容易上手
3. **运维复杂度**: K8s需要专业运维知识
4. **扩展预留**: 架构设计支持迁移到K8s

---

## 总结

本文档记录的技术决策基于以下原则：

1. **业务优先**: 技术服务于业务目标
2. **渐进演进**: 从简单到复杂，支持平滑升级
3. **成本效益**: 在功能和成本间找到平衡
4. **团队能力**: 考虑团队技术栈熟悉度
5. **社区生态**: 选择有活跃社区支持的技术

这些决策将随着项目发展和需求变化持续评估和调整。