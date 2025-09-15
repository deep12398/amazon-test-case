# Amazon Tracker 开发环境管理

## 快速启动

### 方式一：使用 Makefile (推荐)
```bash
# 启动完整开发环境
make dev

# 停止所有服务
make stop

# 重启开发环境
make restart

# 查看服务状态
make status
```

### 方式二：使用 dev.sh 脚本
```bash
# 启动开发环境
./dev.sh start

# 停止开发环境
./dev.sh stop

# 重启开发环境
./dev.sh restart

# 查看服务状态
./dev.sh status

# 查看日志
./dev.sh logs

# 完全清理环境
./dev.sh clean
```

### 方式三：使用 Python 管理器
```bash
# 启动开发环境
python scripts/dev_manager.py

# 停止开发环境
python scripts/dev_manager.py stop
```

## 服务架构

开发环境包含以下服务：

### Docker 服务
- **Redis** (端口 6379) - 缓存服务
- **etcd** (端口 2379) - APISIX 配置存储
- **APISIX** (端口 9080/9180) - API 网关
- **Prometheus** (端口 9090) - 监控指标收集
- **Grafana** (端口 3000) - 监控仪表盘
- **Jaeger** (端口 16686) - 分布式链路追踪

### Python 服务
- **用户服务** (端口 8001) - 用户管理和认证
- **爬虫服务** (端口 8002) - 数据爬取任务
- **核心服务** (端口 8003) - 产品管理和分析

## 服务访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 用户服务 API | http://localhost:8001/docs | Swagger API 文档 |
| 爬虫服务 API | http://localhost:8002/docs | Swagger API 文档 |
| 核心服务 API | http://localhost:8003/docs | Swagger API 文档 |
| APISIX 网关 | http://localhost:9080 | API 网关入口 |
| APISIX 管理 | http://localhost:9180 | 网关管理界面 |
| Prometheus | http://localhost:9090 | 监控指标查询 |
| Grafana | http://localhost:3000 | 监控仪表盘 (admin/admin123) |
| Jaeger | http://localhost:16686 | 链路追踪界面 |

## 环境配置

项目使用 `.env.local` 文件进行环境配置，包含：

- **数据库配置** - 使用远程 Supabase PostgreSQL
- **Redis 配置** - 本地 Redis 连接
- **JWT 配置** - 认证密钥和算法
- **API 密钥** - OpenAI、Apify 等服务
- **邮件配置** - SMTP 通知设置

## 常用命令

### 查看服务状态
```bash
# 查看 Docker 容器状态
docker ps --filter "name=amazon-tracker"

# 查看 Python 服务端口占用
lsof -i :8001 -i :8002 -i :8003

# 查看完整服务状态
./dev.sh status
```

### 查看日志
```bash
# 查看所有 Docker 服务日志
./dev.sh logs

# 查看特定服务日志
./dev.sh logs redis
./dev.sh logs grafana
```

### 重置环境
```bash
# 完全清理并重启
./dev.sh clean
./dev.sh start

# 或者使用 make
make clean-all
make dev
```

## 故障排除

### 端口占用问题
如果遇到端口占用，可以：
```bash
# 查找占用进程
lsof -i :3000  # 例如 Grafana 端口

# 杀死占用进程
kill -9 <PID>
```

### Docker 服务问题
```bash
# 重启 Docker 服务
docker compose -f docker-compose.dev.yml restart <服务名>

# 查看容器日志
docker logs amazon-tracker-<服务名>-dev
```

### Python 服务问题
Python 服务会自动重启，如有问题可以：
```bash
# 手动启动单个服务
uv run uvicorn amazon_tracker.services.user_service.main:app --host 0.0.0.0 --port 8001 --reload
```

## 开发建议

1. **首次启动**：使用 `make dev` 或 `./dev.sh start`
2. **日常开发**：服务支持热重载，修改代码后自动重启
3. **调试时**：可以单独启动需要的服务进行调试
4. **停止服务**：使用 `Ctrl+C` 或 `make stop`
5. **完全清理**：定期运行 `./dev.sh clean` 清理环境

## API 测试

启动服务后，可以通过以下方式测试：

1. **Swagger UI**：访问各服务的 `/docs` 端点
2. **curl 命令**：
   ```bash
   # 健康检查
   curl http://localhost:8001/health

   # 用户注册
   curl -X POST http://localhost:8001/api/v1/auth/register \
        -H "Content-Type: application/json" \
        -d '{"email":"test@example.com","password":"password123"}'
   ```

3. **API 网关访问**：通过 APISIX (端口 9080) 统一访问所有服务
