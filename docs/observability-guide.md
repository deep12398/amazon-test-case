# APISIX可观察性功能查看指南

## 快速开始

### 一键启动和测试
```bash
# 1. 启动基础设施（如果未启动）
make docker-up

# 2. 启动用户服务（新终端）
make dev-user

# 3. 运行可观察性演示
make observability-demo

# 4. 批量压力测试（可选）
make observability-test

# 5. 查看所有监控地址
make observability-urls
```

## 查看监控数据

### 1. Prometheus指标（http://localhost:9090）

#### 常用查询示例：
- **基础指标**：
  - `apisix_http_status{route="99"}` - 演示路由的HTTP状态码分布
  - `apisix_http_requests_total` - 总请求数
  - `apisix_http_latency_histogram` - 请求延迟分布

- **性能指标**：
  - `rate(apisix_http_requests_total[1m])` - 每分钟请求率
  - `histogram_quantile(0.95, apisix_http_latency_histogram)` - P95响应时间
  - `apisix_nginx_http_current_connections` - 当前连接数

- **错误监控**：
  - `rate(apisix_http_status{code=~"5.."}[5m])` - 5分钟内5xx错误率
  - `rate(apisix_http_status{code=~"4.."}[5m])` - 5分钟内4xx错误率

#### 查看步骤：
1. 访问 http://localhost:9090
2. 在查询框中输入上述PromQL查询
3. 点击"Execute"执行查询
4. 切换到"Graph"查看时序图

### 2. Grafana仪表板（http://localhost:3000）

#### 初始配置：
1. 登录账号：`admin` / `admin123`
2. 添加数据源：
   - 导航：Configuration → Data Sources → Add data source
   - 选择：Prometheus
   - URL：`http://prometheus:9090`
   - 点击"Save & Test"

#### 导入APISIX仪表板：
1. 导航：+ → Import
2. 输入Grafana仪表板ID：`11719`（APISIX官方模板）
3. 选择Prometheus数据源
4. 点击"Import"

#### 自定义面板：
- **请求速率面板**：查询 `sum(rate(apisix_http_requests_total[1m]))`
- **错误率面板**：查询 `sum(rate(apisix_http_status{code=~"5.."}[1m]))/sum(rate(apisix_http_requests_total[1m]))*100`
- **P95延迟面板**：查询 `histogram_quantile(0.95, apisix_http_latency_histogram)`

### 3. Jaeger分布式追踪（http://localhost:16686）

#### 查看步骤：
1. 访问 http://localhost:16686
2. 在左侧Service下拉框选择：`APISIX-Gateway`
3. Operation选择：`all` 或具体操作
4. 设置时间范围（默认1小时）
5. 点击"Find Traces"查找追踪

#### 分析trace：
1. **Trace列表**：显示所有匹配的请求链路
   - Duration：请求总耗时
   - Spans：操作数量
   - Services：涉及服务数

2. **Trace详情**：点击具体trace查看
   - **时序图**：显示各操作的时间关系
   - **Span信息**：每个操作的详细信息
   - **Tags**：包含route_id, http.method, http.status_code等元数据
   - **Logs**：操作过程中的日志事件

#### 关键字段说明：
- **trace.span_id**：Span的唯一标识
- **http.method**：HTTP请求方法
- **http.status_code**：HTTP状态码
- **route_id**：APISIX路由ID
- **upstream.host**：上游服务地址

## 监控指标详解

### Prometheus核心指标

| 指标名称 | 类型 | 描述 | 正常范围 |
|---------|------|------|----------|
| `apisix_http_requests_total` | Counter | 累计请求数 | 持续增长 |
| `apisix_http_latency_histogram` | Histogram | 请求延迟分布 | P95 < 100ms |
| `apisix_http_status` | Counter | 按状态码分类的请求数 | 2xx占主要部分 |
| `apisix_nginx_http_current_connections` | Gauge | 当前连接数 | < 1000 |
| `apisix_bandwidth` | Counter | 带宽使用统计 | 根据业务调整 |

### Jaeger追踪维度

| 维度 | 说明 | 关注点 |
|------|------|--------|
| **Duration** | 请求总耗时 | 是否存在异常慢请求 |
| **Spans数量** | 操作步骤数 | 调用链复杂度 |
| **Error Tags** | 错误标记 | 失败请求的根本原因 |
| **Service分布** | 服务调用关系 | 服务依赖和瓶颈 |

## 常见问题排查

### Jaeger无追踪数据

1. **检查Jaeger服务状态**：
   ```bash
   docker logs amazon-tracker-jaeger-dev
   ```

2. **验证APISIX配置**：
   ```bash
   curl http://localhost:9180/apisix/admin/plugin_metadata/opentelemetry \
     -H "X-API-KEY: dev-admin-key-123"
   ```

3. **检查OTLP端点连通性**：
   ```bash
   curl -X POST http://localhost:4318/v1/traces \
     -H "Content-Type: application/x-protobuf" \
     --data-binary @/dev/null
   ```

### Prometheus无指标数据

1. **检查采集目标**：
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

2. **验证APISIX metrics端点**：
   ```bash
   curl http://localhost:9091/apisix/prometheus/metrics
   ```

3. **检查路由配置**：
   ```bash
   curl http://localhost:9180/apisix/admin/routes/99 \
     -H "X-API-KEY: dev-admin-key-123"
   ```

### 演示路由无响应

1. **检查用户服务状态**：
   ```bash
   curl http://localhost:8001/health
   ```

2. **验证APISIX路由**：
   ```bash
   curl -v http://localhost:9080/api/v1/demo/metrics
   ```

3. **查看APISIX日志**：
   ```bash
   docker logs amazon-tracker-apisix-dev
   ```

## 性能调优建议

### Prometheus优化
- 合理设置`scrape_interval`，避免过于频繁的采集
- 使用recording rules预计算常用查询
- 定期清理历史数据，控制存储空间

### Jaeger优化
- 生产环境调整采样率，避免性能影响
- 设置合理的trace retention时间
- 考虑使用Elasticsearch后端存储大量数据

### APISIX优化
- 合理配置`batch_span_processor`参数
- 生产环境禁用不必要的插件
- 监控APISIX自身的内存和CPU使用情况

## 告警配置示例

### Prometheus告警规则
```yaml
groups:
  - name: apisix_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(apisix_http_status{code=~"5.."}[5m]) / rate(apisix_http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "APISIX high error rate detected"

      - alert: HighLatency
        expr: histogram_quantile(0.95, apisix_http_latency_histogram) > 1000
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "APISIX high latency detected"
```

## 参考资源

- [APISIX OpenTelemetry插件文档](https://apisix.apache.org/docs/apisix/plugins/opentelemetry/)
- [Prometheus查询语言PromQL](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Jaeger使用指南](https://www.jaegertracing.io/docs/1.21/getting-started/)
- [Grafana仪表板库](https://grafana.com/grafana/dashboards/)