# Amazon产品追踪系统 API设计文档

## 系统概述

Amazon产品追踪系统是一个多租户SaaS平台，提供Amazon产品数据抓取、监控和分析功能。系统采用微服务架构，通过APISIX网关进行路由和认证管理。

## 服务架构

- **用户服务 (User Service)** - 端口 8001：用户认证、授权、租户管理
- **核心服务 (Core Service)** - 端口 8002：产品管理、数据分析、报表生成
- **爬虫服务 (Crawler Service)** - 端口 8003：数据抓取、调度管理、监控

## 1. RESTful API 端点设计

### 用户服务端点

#### 认证管理
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/refresh` - 刷新令牌
- `POST /api/v1/auth/logout` - 用户登出
- `POST /api/v1/auth/verify-email` - 邮箱验证
- `POST /api/v1/auth/forgot-password` - 忘记密码
- `POST /api/v1/auth/reset-password` - 重置密码

#### 用户管理
- `GET /api/v1/users/me` - 获取当前用户信息
- `PUT /api/v1/users/me` - 更新用户资料
- `GET /api/v1/users` - 获取用户列表（管理员）
- `GET /api/v1/users/{user_id}` - 获取指定用户信息
- `DELETE /api/v1/users/{user_id}` - 删除用户

#### API密钥管理
- `GET /api/v1/users/me/api-keys` - 获取API密钥列表
- `POST /api/v1/users/me/api-keys` - 创建API密钥
- `DELETE /api/v1/users/me/api-keys/{key_id}` - 撤销API密钥

#### 租户管理
- `GET /api/v1/tenants/me` - 获取当前租户信息
- `PUT /api/v1/tenants/me` - 更新租户信息
- `GET /api/v1/tenants/me/usage` - 获取使用统计
- `POST /api/v1/tenants/me/upgrade` - 升级订阅计划

### 核心服务端点

#### 产品管理
- `GET /api/v1/products` - 获取产品列表
- `POST /api/v1/products` - 创建产品
- `GET /api/v1/products/{product_id}` - 获取产品详情
- `PUT /api/v1/products/{product_id}` - 更新产品
- `DELETE /api/v1/products/{product_id}` - 删除产品
- `POST /api/v1/products/search` - 搜索产品
- `POST /api/v1/products/batch-operation` - 批量操作

#### 数据分析
- `GET /api/v1/products/{product_id}/price-history` - 价格历史
- `GET /api/v1/products/{product_id}/rank-history` - 排名历史
- `GET /api/v1/products/stats/overview` - 产品统计概览

#### 报表管理
- `GET /api/v1/reports` - 获取报表列表
- `POST /api/v1/reports/generate` - 生成报表
- `GET /api/v1/reports/{report_id}` - 获取报表详情
- `DELETE /api/v1/reports/{report_id}` - 删除报表

#### 告警管理
- `GET /api/v1/alerts` - 获取告警列表
- `POST /api/v1/alerts` - 创建告警规则
- `PUT /api/v1/alerts/{alert_id}` - 更新告警规则
- `DELETE /api/v1/alerts/{alert_id}` - 删除告警规则

### 爬虫服务端点

#### 爬取任务
- `POST /api/v1/products/crawl` - 单个产品爬取
- `POST /api/v1/products/batch-crawl` - 批量产品爬取
- `POST /api/v1/products/category-crawl` - 分类产品爬取

#### 调度管理
- `GET /api/v1/schedules` - 获取调度列表
- `POST /api/v1/schedules` - 创建调度
- `GET /api/v1/schedules/{schedule_id}` - 获取调度详情
- `PUT /api/v1/schedules/{schedule_id}` - 更新调度
- `DELETE /api/v1/schedules/{schedule_id}` - 删除调度
- `POST /api/v1/schedules/{schedule_id}/run-now` - 立即执行

#### 监控管理
- `GET /api/v1/monitoring/health` - 健康检查
- `GET /api/v1/monitoring/metrics` - 性能指标
- `GET /api/v1/monitoring/stats/crawler` - 爬虫统计
- `GET /api/v1/monitoring/stats/tasks` - 任务统计

## 2. Request/Response 格式定义

### 标准请求格式

```json
{
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer <token>",
    "X-Request-ID": "uuid"
  },
  "body": {
    "field1": "value1",
    "field2": "value2",
    "nested": {
      "field3": "value3"
    }
  }
}
```

### 标准响应格式

#### 成功响应
```json
{
  "success": true,
  "data": {
    "id": 1,
    "type": "product",
    "attributes": {
      "asin": "B08N5WRWNW",
      "title": "产品标题",
      "price": 99.99
    },
    "relationships": {
      "category": {
        "id": 5,
        "name": "Electronics"
      }
    }
  },
  "meta": {
    "timestamp": "2024-01-01T00:00:00Z",
    "version": "v1"
  }
}
```

#### 列表响应（带分页）
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "attributes": {}
    }
  ],
  "pagination": {
    "total": 100,
    "limit": 20,
    "offset": 0,
    "has_next": true,
    "has_prev": false
  },
  "meta": {
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### 请求参数规范

#### 查询参数
- 分页：`?limit=50&offset=0`
- 排序：`?sort_by=created_at&sort_order=desc`
- 过滤：`?status=active&category=electronics`
- 搜索：`?q=search_term`

#### 请求体示例
```json
{
  "asin": "B08N5WRWNW",
  "marketplace": "amazon_us",
  "tracking_frequency": "daily",
  "tags": ["electronics", "headphones"],
  "config": {
    "proxy": "http://proxy.example.com",
    "retry_count": 3
  }
}
```

## 3. 认证与授权机制

### JWT令牌认证

#### 令牌结构
```json
{
  "sub": "user_id",
  "tenant_id": "uuid",
  "session_id": "uuid",
  "roles": ["user", "admin"],
  "permissions": ["product_read", "product_write"],
  "exp": 1640995200,
  "iat": 1640908800,
  "jti": "unique_token_id"
}
```

#### 令牌使用
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 令牌生命周期
- 访问令牌：30天有效期
- 刷新令牌：可配置（7-30天）
- 自动刷新：支持无感刷新机制

### API密钥认证

#### 密钥格式
```
at_<32位随机字符串>
```

#### 密钥配置
```json
{
  "key_id": "uuid",
  "name": "生产环境密钥",
  "scopes": ["product_read", "crawler_create"],
  "allowed_ips": ["192.168.1.0/24"],
  "rate_limit_per_minute": 60,
  "expires_at": "2025-01-01T00:00:00Z"
}
```

### 权限模型 (RBAC)

#### 角色定义
- **superadmin**: 超级管理员，全系统权限
- **tenant_admin**: 租户管理员，租户内全权限
- **user**: 普通用户，标准操作权限
- **viewer**: 只读用户，仅查看权限

#### 权限范围
```
product_read    - 读取产品数据
product_write   - 创建/更新产品
product_delete  - 删除产品
crawler_create  - 创建爬虫任务
crawler_manage  - 管理爬虫调度
report_generate - 生成报表
admin_users     - 管理用户
admin_tenant    - 管理租户
```

### 多租户隔离

#### 租户识别
- 通过JWT中的`tenant_id`字段
- API密钥绑定租户
- 子域名路由：`tenant-a.api.example.com`

#### 数据隔离
- 所有数据模型包含`tenant_id`字段
- 自动过滤查询结果
- 跨租户访问拦截

## 4. 错误处理规范

### 错误响应格式

```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "请求的产品不存在",
    "details": {
      "product_id": 123,
      "tenant_id": "uuid"
    },
    "suggestion": "请检查产品ID是否正确"
  },
  "request_id": "req_abc123",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 错误码定义

#### 业务错误码
- `INVALID_INPUT` - 输入参数无效
- `RESOURCE_NOT_FOUND` - 资源不存在
- `RESOURCE_CONFLICT` - 资源冲突
- `PERMISSION_DENIED` - 权限不足
- `QUOTA_EXCEEDED` - 超出配额限制
- `OPERATION_FAILED` - 操作失败

#### HTTP状态码使用规范

**2xx 成功响应**
- `200 OK` - 请求成功
- `201 Created` - 资源创建成功
- `204 No Content` - 删除成功，无返回内容

**4xx 客户端错误**
- `400 Bad Request` - 请求参数错误
- `401 Unauthorized` - 未认证
- `403 Forbidden` - 无权限访问
- `404 Not Found` - 资源不存在
- `409 Conflict` - 资源状态冲突
- `422 Unprocessable Entity` - 数据验证失败

**5xx 服务器错误**
- `500 Internal Server Error` - 服务器内部错误
- `502 Bad Gateway` - 网关错误
- `503 Service Unavailable` - 服务暂时不可用
- `504 Gateway Timeout` - 网关超时

### 错误处理最佳实践

#### 输入验证
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "输入验证失败",
    "details": {
      "fields": [
        {
          "field": "asin",
          "message": "ASIN必须为10位字符",
          "value": "B123"
        },
        {
          "field": "price",
          "message": "价格必须大于0",
          "value": -10
        }
      ]
    }
  }
}
```

#### 异常处理链
1. 参数验证层 - 基础格式校验
2. 业务逻辑层 - 业务规则验证
3. 数据访问层 - 数据库异常处理
4. 全局异常处理 - 兜底处理

## 5. 数据格式规范

### 时间格式
- 统一使用ISO 8601格式：`2024-01-01T00:00:00Z`
- 时区：默认UTC，支持时区转换

### 货币格式
```json
{
  "price": 99.99,
  "currency": "USD",
  "formatted": "$99.99"
}
```

### 枚举值
- 使用小写下划线命名：`tracking_frequency`
- 提供可选值列表文档
- 支持向后兼容扩展

### 分页规范
- 默认限制：50条/页
- 最大限制：500条/页
- 偏移量方式：`limit` + `offset`

## 6. API版本管理

### 版本策略
- URL路径版本：`/api/v1/`, `/api/v2/`
- 主版本号表示不兼容变更
- 次版本号表示向后兼容新功能

### 弃用流程
1. 新版本发布，旧版本标记为弃用
2. 响应头添加：`Deprecation: true`
3. 提供6个月迁移期
4. 发送弃用通知邮件
5. 最终下线旧版本

### 版本兼容性
- 向后兼容：新增字段使用可选参数
- 破坏性变更：仅在主版本升级时进行
- 提供版本迁移指南和工具

---

*文档版本: 1.0*
*最后更新: 2024-01-01*
*适用API版本: v1*