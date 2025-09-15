# Amazon产品追踪系统 - 部署架构

## 基础Docker镜像

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装UV包管理器
RUN pip install uv

# 复制依赖文件
COPY pyproject.toml ./

# 安装Python依赖
RUN uv pip install --system -e ".[dev]"

# 复制应用代码
COPY . .

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Docker Compose配置

### 生产环境 (docker-compose.prod.yml)
```yaml
version: "3.8"

networks:
  app-network:
    driver: bridge

services:
  # 用户服务
  user-service:
    build: ./services/user-service
    ports:
      - "8001:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - postgres
      - redis
    networks:
      - app-network
    restart: unless-stopped

  # 核心服务
  core-service:
    build: ./services/core-service
    ports:
      - "8003:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis
    networks:
      - app-network
    restart: unless-stopped

  # 爬虫服务
  crawler-service:
    build: ./services/crawler-service
    ports:
      - "8002:8000"
    environment:
      - APIFY_API_TOKEN=${APIFY_API_TOKEN}
      - REDIS_URL=${REDIS_URL}
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - redis
      - postgres
    networks:
      - app-network
    restart: unless-stopped

  # Celery Worker
  celery-worker:
    build: ./services/crawler-service
    command: celery -A app.celery worker --loglevel=info
    environment:
      - REDIS_URL=${REDIS_URL}
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - redis
    networks:
      - app-network
    restart: unless-stopped

  # Celery Beat
  celery-beat:
    build: ./services/crawler-service
    command: celery -A app.celery beat --loglevel=info
    environment:
      - REDIS_URL=${REDIS_URL}
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - redis
    networks:
      - app-network
    restart: unless-stopped

  # PostgreSQL
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    networks:
      - app-network
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - app-network
    volumes:
      - redis_data:/data
    restart: unless-stopped

  # APISIX Gateway
  apisix:
    image: apache/apisix:latest
    environment:
      APISIX_ETCD_HOST: etcd
    ports:
      - "9080:9080"
    depends_on:
      - etcd
    networks:
      - app-network
    restart: unless-stopped

  # etcd
  etcd:
    image: bitnami/etcd:latest
    environment:
      ETCD_ENABLE_V2: "true"
      ALLOW_NONE_AUTHENTICATION: "yes"
    ports:
      - "2379:2379"
    networks:
      - app-network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

## Makefile部署命令

### 环境管理
```bash
# 生产环境设置
make setup          # 安装依赖和初始化
make restart        # 重启生产环境
make status         # 查看服务状态
```

### 生产部署操作
```bash
make deploy-prod    # 部署到生产环境
make deploy-check   # 检查部署状态
```

### 数据库操作
```bash
make db-migrate     # 运行数据库迁移
make db-migration   # 创建新迁移文件
make db-seed        # 填充种子数据
```

### 部署操作
```bash
make deploy-prod    # 部署到生产环境
make deploy-check   # 检查部署状态
```

## 水平扩展

### 服务扩展
```bash
# 使用Docker Compose扩展服务实例
docker-compose -f docker-compose.prod.yml up -d --scale user-service=3
docker-compose -f docker-compose.prod.yml up -d --scale core-service=2
docker-compose -f docker-compose.prod.yml up -d --scale crawler-service=2

# 扩展Celery Worker
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=4
```

### 负载均衡
通过APISIX网关自动实现负载均衡，支持多个服务实例。

### 数据库扩展
```bash
# 读写分离配置
# 主数据库: postgres-primary (写操作)
# 从数据库: postgres-replica (读操作)

# Redis集群模式
# redis-1, redis-2, redis-3 (集群配置)
```

### 监控扩展状态
```bash
# 查看扩展后的服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看资源使用情况
docker stats

# 查看服务健康状态
make dev-check
```

## Kubernetes部署

### Kustomize配置结构
```
k8s/
├── base/
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── hpa.yaml
└── overlays/
    └── prod/
        ├── kustomization.yaml
        └── patches/
```

### 基础配置 (base/kustomization.yaml)
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: amazon-tracker

resources:
  - deployment.yaml
  - service.yaml
  - hpa.yaml

commonLabels:
  app: amazon-tracker
  version: v1
```

### Deployment配置 (base/deployment.yaml)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
spec:
  replicas: 3
  selector:
    matchLabels:
      service: user-service
  template:
    metadata:
      labels:
        service: user-service
    spec:
      containers:
      - name: user-service
        image: amazon-tracker/user-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

### 生产环境配置 (overlays/prod/kustomization.yaml)
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

replicas:
  - name: user-service
    count: 5

images:
  - name: amazon-tracker/user-service
    newTag: v1.0.0

patchesStrategicMerge:
  - patches/resources.yaml
```

### 部署命令
```bash
# 生产环境部署
kubectl apply -k k8s/overlays/prod

# 查看状态
kubectl get pods -n amazon-tracker

# 滚动更新
kubectl rollout restart deployment/user-service -n amazon-tracker
```

## CI/CD工作流

### GitHub Actions配置 (.github/workflows/deploy.yml)
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install UV
        run: pip install uv

      - name: Install dependencies
        run: uv pip install --system -e ".[dev]"

      - name: Run tests
        env:
          DATABASE_URL: postgresql://test_user:test_pass@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379
        run: |
          uv run pytest --cov=. --cov-report=xml
          uv run ruff check .
          uv run black --check .
          uv run mypy .

  build:
    needs: test
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ${{ steps.meta.outputs.tags }}

  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to production
        run: |
          kubectl apply -k k8s/overlays/prod
          kubectl rollout status deployment/user-service -n amazon-tracker
```

## APISIX网关配置

### APISIX配置 (config/apisix/config.yaml)
```yaml
apisix:
  node_listen: 9080
  enable_ipv6: false

  enable_control: true
  control:
    ip: "0.0.0.0"
    port: 9092

deployment:
  role: traditional
  role_traditional:
    config_provider: etcd

  etcd:
    host:
      - "http://etcd:2379"
    prefix: "/apisix"
    timeout: 30

plugin_attr:
  prometheus:
    export_addr:
      ip: "0.0.0.0"
      port: 9091
```

### 路由配置 (config/apisix/apisix.yaml)
```yaml
routes:
  - id: user-service
    uri: /api/v1/users/*
    upstream:
      type: roundrobin
      nodes:
        "user-service:8000": 1
    plugins:
      jwt-auth: {}
      limit-req:
        rate: 200
        burst: 100
      prometheus:
        prefer_name: true

  - id: core-service
    uri: /api/v1/products/*
    upstream:
      type: roundrobin
      nodes:
        "core-service:8000": 1
    plugins:
      jwt-auth: {}
      limit-req:
        rate: 500
        burst: 200
      prometheus:
        prefer_name: true

  - id: crawler-service
    uri: /api/v1/crawl/*
    upstream:
      type: roundrobin
      nodes:
        "crawler-service:8000": 1
    plugins:
      jwt-auth: {}
      limit-req:
        rate: 100
        burst: 50
      prometheus:
        prefer_name: true

consumers:
  - username: api-user
    plugins:
      jwt-auth:
        key: user-key
        secret: your-secret-key

upstreams:
  - id: user-service-upstream
    type: roundrobin
    nodes:
      "user-service:8000": 1
    health_check:
      active:
        http_path: "/health"
        host: "user-service"
        healthy:
          interval: 5
          successes: 2
        unhealthy:
          interval: 5
          http_failures: 3

  - id: core-service-upstream
    type: roundrobin
    nodes:
      "core-service:8000": 1
    health_check:
      active:
        http_path: "/health"
        host: "core-service"
        healthy:
          interval: 5
          successes: 2
        unhealthy:
          interval: 5
          http_failures: 3

  - id: crawler-service-upstream
    type: roundrobin
    nodes:
      "crawler-service:8000": 1
    health_check:
      active:
        http_path: "/health"
        host: "crawler-service"
        healthy:
          interval: 5
          successes: 2
        unhealthy:
          interval: 5
          http_failures: 3

global_rules:
  - id: global-cors
    plugins:
      cors:
        allow_origins: "*"
        allow_methods: "GET,POST,PUT,DELETE,OPTIONS"
        allow_headers: "Content-Type,Authorization"

  - id: global-prometheus
    plugins:
      prometheus:
        prefer_name: true

plugin_metadata:
  - id: prometheus
    prefer_name: true
    export_addr:
      ip: 0.0.0.0
      port: 9091
```

### SSL配置 (生产环境)
```yaml
# config/apisix/ssl.yaml
ssl:
  - id: 1
    cert: |
      -----BEGIN CERTIFICATE-----
      # Your SSL certificate
      -----END CERTIFICATE-----
    key: |
      -----BEGIN PRIVATE KEY-----
      # Your private key
      -----END PRIVATE KEY-----
    snis:
      - "*.yourdomain.com"
      - "yourdomain.com"
```

## 监控配置

### Prometheus配置 (config/prometheus/prometheus.yml)
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'apisix'
    static_configs:
      - targets: ['apisix:9080']
    metrics_path: '/apisix/prometheus/metrics'

  - job_name: 'user-service'
    static_configs:
      - targets: ['user-service:8000']
    metrics_path: '/metrics'

  - job_name: 'core-service'
    static_configs:
      - targets: ['core-service:8000']
    metrics_path: '/metrics'

  - job_name: 'crawler-service'
    static_configs:
      - targets: ['crawler-service:8000']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### Grafana Dashboard配置
```json
{
  "dashboard": {
    "title": "Amazon Tracker Monitoring",
    "panels": [
      {
        "title": "API请求量",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(apisix_http_requests_total[5m])",
            "legendFormat": "{{service}}"
          }
        ]
      },
      {
        "title": "响应时间",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, apisix_http_latency_bucket)",
            "legendFormat": "95th percentile"
          }
        ]
      }
    ]
  }
}
```

### 监控告警规则 (config/prometheus/alerts.yml)
```yaml
groups:
  - name: amazon-tracker-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(apisix_http_status{code=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "高错误率告警"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, apisix_http_latency_bucket) > 1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "响应时间过高"

      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "数据库服务不可用"
```

## 生产环境部署步骤

### Docker Compose部署
```bash
# 1. 设置环境变量
cp .env.example .env.production

# 2. 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 3. 数据库迁移
make db-migrate

# 4. 健康检查
curl http://localhost:9080/health
```

### Kubernetes部署
```bash
# 1. 应用配置
kubectl apply -k k8s/overlays/prod

# 2. 等待部署完成
kubectl rollout status deployment/user-service -n amazon-tracker

# 3. 验证部署
kubectl get pods -n amazon-tracker
```