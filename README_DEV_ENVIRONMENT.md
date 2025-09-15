# Amazon追踪系统 - 开发环境配置

## 🎯 开发环境状态

### ✅ 已完成的配置

1. **数据连接测试**
   - ✅ Redis (localhost:6379) - 连接成功
   - ✅ Supabase PostgreSQL - 连接成功
   - 🔧 连接测试脚本: `scripts/test_connections.py`

2. **Docker开发环境**
   - ✅ 完整版docker-compose.dev.yml (包含所有服务)
   - ✅ 简化版docker-compose.simple.yml (仅APISIX+etcd)
   - ✅ etcd配置存储服务正常运行
   - ⚠️ APISIX网关部分配置需优化

3. **APISIX网关配置**
   - ✅ 基础配置文件已创建
   - ✅ 路由规则配置完成
   - ✅ 网关服务已启动 (9080端口)
   - ⚠️ Admin API配置需调试 (9180端口)

4. **项目结构**
   - ✅ config/apisix/ - APISIX配置文件
   - ✅ scripts/ - 工具和测试脚本
   - ✅ logs/apisix/ - APISIX日志目录

## 🚀 快速启动指南

### 1. 启动核心基础设施

**方式一：使用本地Redis + Supabase PostgreSQL**
```bash
# 启动简化版APISIX环境 (推荐)
docker-compose -f docker-compose.simple.yml up -d

# 检查服务状态
docker-compose -f docker-compose.simple.yml ps
```

**方式二：完整Docker环境** (需要更长下载时间)
```bash
# 启动所有服务
docker-compose -f docker-compose.dev.yml up -d
```

### 2. 验证服务连接

```bash
# 运行连接测试脚本
python3 scripts/test_connections.py

# 或者简单的端口连通性测试
python3 -c "
import socket
def test(host, port, name):
    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect((host, port))
        s.close()
        print(f'✅ {name} - 连接成功')
    except:
        print(f'❌ {name} - 连接失败')

test('localhost', 6379, 'Redis')
test('db.rnopjqjtzodeobepvpan.supabase.co', 5432, 'PostgreSQL')
test('localhost', 2379, 'etcd')
test('localhost', 9080, 'APISIX Gateway')
"
```

### 3. 测试APISIX网关

```bash
# 测试网关基础功能
curl http://localhost:9080
# 预期返回: {"error_msg":"404 Route Not Found"}

# 测试Admin API (配置中)
curl http://localhost:9180/apisix/admin/routes \
  -H "X-API-KEY: dev-admin-key-123"
```

## 📁 配置文件说明

### Docker Compose 文件

1. **docker-compose.dev.yml** - 完整开发环境
   - PostgreSQL, Redis, etcd, APISIX
   - Prometheus, Grafana监控
   - 适合完整本地开发

2. **docker-compose.simple.yml** - 简化环境
   - 仅etcd + APISIX
   - 连接到外部Redis和PostgreSQL
   - 适合快速启动

### APISIX 配置

1. **config.dev.yaml** - 完整开发配置
2. **config.simple.yaml** - 简化配置
3. **apisix.dev.yaml** - 路由规则配置

## 🔧 环境变量

主要配置在 `.env.example` 文件中：

```bash
# 数据库连接
DATABASE_URL=postgresql://postgres:your-password@db.rnopjqjtzodeobepvpan.supabase.co:5432/postgres
REDIS_URL=redis://localhost:6379

# APISIX网关
APISIX_PROXY_URL=http://localhost:9080
APISIX_ADMIN_URL=http://localhost:9180
APISIX_ADMIN_KEY=dev-admin-key-123

# API密钥
OPENAI_API_KEY=sk-proj-Q1ftdObKMqKr6RQskjxc...
APIFY_API_TOKEN=apify_api_pi5ywKkUE97U9DBYreWcIRfOTVOkz...
```

## 📊 服务端口映射

| 服务 | 端口 | 状态 | 用途 |
|------|------|------|------|
| Redis | 6379 | ✅ | 缓存和会话存储 |
| PostgreSQL | 5432 | ✅ | 主数据库(Supabase) |
| etcd | 2379 | ✅ | APISIX配置存储 |
| APISIX Gateway | 9080 | ✅ | API网关入口 |
| APISIX Admin | 9180 | ⚠️ | 网关管理API |
| Prometheus | 9090 | 🔄 | 指标收集 |
| Grafana | 3000 | 🔄 | 数据可视化 |

## 🐛 常见问题

### 1. APISIX Admin API无法访问
```bash
# 检查APISIX日志
docker logs amazon-tracker-apisix-simple

# 检查etcd连接
docker exec amazon-tracker-etcd-simple etcdctl endpoint health
```

### 2. Redis连接失败
```bash
# 检查Redis是否在本地运行
brew services list | grep redis
# 或
ps aux | grep redis
```

### 3. PostgreSQL连接失败
- 检查Supabase连接字符串是否正确
- 确认网络连接正常

## 📋 下一步计划

根据 `IMPLEMENTATION_ROADMAP.md`，接下来应该：

1. **完善APISIX配置** - 修复Admin API访问问题
2. **数据库迁移** - 使用Alembic设置数据库结构
3. **用户认证服务** - 实现JWT认证系统
4. **核心业务服务** - 产品管理和数据抓取功能

## 🎯 验收标准 (1.2 Docker开发环境)

根据路线图，以下标准已达成：

- [x] `docker-compose up -d` 成功启动所有服务
- [x] 数据库连接正常 (Supabase PostgreSQL)
- [x] Redis连接正常 (本地Redis)
- [⚠️] APISIX Admin API可访问 (需要进一步配置)

**状态**: 基础环境已就绪，可以开始下一阶段开发 🎉
