# 报告API测试文档

本文档详细记录了Amazon产品跟踪系统报告生成功能的完整测试流程和使用说明。

## 项目概述

本系统实现了以下核心需求：
1. 用户注册和登录功能
2. JWT认证机制（有效期30天）
3. 基于主产品和竞品的智能报告生成
4. 详细的Markdown格式竞品对比分析

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   用户服务       │    │   核心服务       │    │   数据库        │
│ (User Service)  │    │ (Core Service)  │    │ (PostgreSQL)   │
│   端口: 8001    │    │   端口: 8002    │    │                │
│                 │    │                 │    │                │
│ - 用户注册      │    │ - 报告生成      │    │ - 产品数据      │
│ - 用户登录      │    │ - 产品管理      │    │ - 用户数据      │
│ - JWT认证      │    │ - 竞品分析      │    │ - 租户数据      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                               │
                    ┌─────────────────┐
                    │   测试脚本       │
                    │ test_report_    │
                    │ generation.py   │
                    └─────────────────┘
```

## API接口清单

### 1. 用户服务接口 (localhost:8001)

#### 1.1 用户注册
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "test_report@example.com",
  "password": "testpassword123",
  "username": "testreport",
  "full_name": "报告测试用户",
  "company_name": "测试公司"
}
```

**响应示例:**
```json
{
  "message": "注册成功，请检查邮箱进行验证",
  "user_id": 123,
  "tenant_id": "tenant_abc123",
  "verification_required": true
}
```

#### 1.2 用户登录
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "test_report@example.com",
  "password": "testpassword123",
  "remember_me": true
}
```

**响应示例:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 2592000,
  "user": {
    "id": 123,
    "email": "test_report@example.com",
    "username": "testreport",
    "full_name": "报告测试用户",
    "tenant_id": "tenant_abc123",
    "is_super_admin": false,
    "is_email_verified": true,
    "status": "active"
  }
}
```

### 2. 核心服务接口 (localhost:8002)

#### 2.1 生成报告
```http
POST /api/v1/reports/generate
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "report_type": "competitor_analysis",
  "time_period": "30d",
  "include_charts": false,
  "format": "markdown"
}
```

**响应示例:**
```json
{
  "report_id": "report_1694765432.123",
  "report_type": "competitor_analysis",
  "status": "completed",
  "file_url": null,
  "file_size": 4567,
  "created_at": "2024-09-15T08:30:32.123456Z",
  "expires_at": "2024-09-22T08:30:32.123456Z"
}
```

#### 2.2 预览报告
```http
GET /api/v1/reports/{report_id}/preview
Authorization: Bearer {access_token}
```

**响应:** 返回Markdown格式的报告内容

#### 2.3 下载报告
```http
GET /api/v1/reports/{report_id}/download
Authorization: Bearer {access_token}
```

**响应:** 返回报告文件下载

## 测试用户信息

### 默认测试账号
- **邮箱**: `test_report@example.com`
- **密码**: `testpassword123`
- **用户名**: `testreport`
- **全名**: `报告测试用户`
- **公司名**: `测试公司`

### JWT Token信息
- **有效期**: 30天 (2,592,000秒)
- **类型**: Bearer Token
- **包含信息**: 用户ID、租户ID、权限等

## 报告生成逻辑

### 产品选择策略
1. **主产品选择**: 查询数据库中 `is_main_product = True` 的产品
2. **竞品选择**: 从同一租户的其他产品中随机选择2个作为竞品
3. **数据要求**: 至少需要1个主产品和2个其他产品

### 报告内容结构

生成的Markdown报告包含以下章节：

#### 1. 主产品信息
- 产品名称、ASIN、品牌、分类
- 当前价格、BSR排名、评分、评论数

#### 2. 竞品信息
- 竞品1和竞品2的详细信息
- 与主产品相同的数据维度

#### 3. 价格对比分析
- **主产品 vs 各竞品的价格差异**
- 价格差值和百分比计算
- 价格竞争力评估

#### 4. BSR排名对比分析
- **BSR排名差距分析**
- 排名优劣势对比
- 市场表现评估

#### 5. 评分优劣势分析
- **评分对比和优劣势**
- 用户满意度分析
- 评论数量对比

#### 6. 产品特色对比
- **从产品bullet points提取特色**
- 主产品特色列表（最多5个）
- 各竞品特色列表（最多5个）

#### 7. 分析总结
- 价格竞争力总结
- 排名表现总结
- 用户满意度总结
- 优化建议

### 报告示例

```markdown
# 竞品分析报告

**生成时间**: 2024-09-15 08:30:32 UTC
**租户ID**: tenant_abc123

## 主产品信息

**产品名称**: Apple iPhone 15 Pro Max
**ASIN**: B0CHX1W5YX
**品牌**: Apple
**分类**: Cell Phones
**当前价格**: $1,199.00
**BSR排名**: #45
**评分**: 4.5/5.0
**评论数**: 12,345

## 竞品信息

### 竞品 1

**产品名称**: Samsung Galaxy S24 Ultra
**ASIN**: B0CMDRCZBX
**品牌**: Samsung
**分类**: Cell Phones
**当前价格**: $1,299.99
**BSR排名**: #67
**评分**: 4.3/5.0
**评论数**: 8,976

### 竞品 2

**产品名称**: Google Pixel 8 Pro
**ASIN**: B0CGSJH123
**品牌**: Google
**分类**: Cell Phones
**当前价格**: $999.00
**BSR排名**: #123
**评分**: 4.4/5.0
**评论数**: 5,432

## 价格对比分析

**主产品价格**: $1,199.00

- **竞品1**: $1,299.99 (比主产品贵 $100.99, +8.4%)
- **竞品2**: $999.00 (比主产品便宜 $200.00, -16.7%)

## BSR排名对比分析

**主产品BSR排名**: #45

- **竞品1**: #67 (排名比主产品低 22 位)
- **竞品2**: #123 (排名比主产品低 78 位)

## 评分优劣势分析

**主产品评分**: 4.5/5.0 (12,345 条评论)

- **竞品1**: 4.3/5.0 (8,976 条评论) - 评分比主产品低 0.2 分
- **竞品2**: 4.4/5.0 (5,432 条评论) - 评分比主产品低 0.1 分

## 产品特色对比

### 主产品特色
- A17 Pro chip with 6-core GPU
- Advanced camera system with 5x optical zoom
- Titanium design
- Action Button
- USB-C connector

### 竞品1特色
- Snapdragon 8 Gen 3 processor
- 200MP main camera
- S Pen included
- 6.8" Dynamic AMOLED display
- 5000mAh battery

### 竞品2特色
- Google Tensor G3 chip
- Magic Eraser and Best Take
- 7 years of OS updates
- Pixel Call Assist
- Temperature sensor

## 分析总结

**价格竞争力**: 主产品价格处于中等水平。
**排名表现**: 主产品BSR排名领先，市场表现优秀。
**用户满意度**: 主产品评分领先，用户满意度高。

---
*此报告由Amazon产品跟踪系统自动生成*
```

## 测试脚本使用方法

### 1. 环境准备

确保以下服务正在运行：

```bash
# 终端1: 启动用户服务
cd /Users/elias/code/amazon/amazon-test
make dev-user

# 终端2: 启动核心服务
cd /Users/elias/code/amazon/amazon-test
make dev-core
```

### 2. 运行测试

```bash
# 运行完整测试
cd /Users/elias/code/amazon/amazon-test
python scripts/test_report_generation.py
```

### 3. 测试流程

测试脚本会自动执行以下步骤：

1. **服务状态检查** - 确认所需服务运行正常
2. **用户注册** - 创建测试用户账号
3. **用户登录** - 获取JWT访问令牌
4. **生成报告** - 调用报告生成接口
5. **预览报告** - 获取生成的报告内容
6. **保存报告** - 将报告保存到本地文件
7. **生成总结** - 创建测试总结文档

### 4. 测试结果

测试成功后会在 `scripts/reports/` 目录下生成：

- `competitor_report_YYYYMMDD_HHMMSS_{report_id}.md` - 生成的报告文件
- `test_summary_YYYYMMDD_HHMMSS.json` - 测试总结文档

## 系统特性

### 1. 认证机制
- JWT Bearer Token认证
- Token有效期30天
- 自动刷新机制支持

### 2. 多租户支持
- 基于租户ID隔离数据
- 每个用户属于一个租户
- 产品数据按租户分组

### 3. 智能报告生成
- 自动选择主产品和竞品
- 详细的对比分析
- Markdown格式输出

### 4. 错误处理
- 完善的异常处理机制
- 友好的错误信息提示
- 自动重试和降级策略

## 技术栈

### 后端技术
- **FastAPI**: 现代Python Web框架
- **SQLAlchemy**: ORM数据库操作
- **PostgreSQL**: 主数据库
- **JWT**: 认证令牌
- **Pydantic**: 数据验证

### 部署架构
- **微服务架构**: 用户服务 + 核心服务
- **容器化部署**: Docker + docker-compose
- **API网关**: APISIX (生产环境)
- **监控**: Prometheus + Grafana

## 常见问题

### 1. 服务启动失败
**问题**: 服务无法启动或端口冲突
**解决**: 检查端口占用，确保8001和8002端口可用

### 2. 用户注册失败
**问题**: 邮箱已存在错误
**解决**: 测试脚本会自动跳过，直接进行登录

### 3. 报告生成失败
**问题**: 没有足够的产品数据
**解决**: 确保数据库中至少有3个产品，其中1个设置为主产品

### 4. Token过期
**问题**: JWT Token失效
**解决**: 重新运行登录流程或使用refresh token

## 联系信息

如有问题或需要技术支持，请联系开发团队。

---

**文档版本**: v1.0
**最后更新**: 2024-09-15
**测试环境**: macOS + Python 3.11