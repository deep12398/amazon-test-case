# 数据库设计文档

## 项目概述

Amazon产品追踪系统 - 多租户SaaS平台，用于亚马逊产品跟踪和分析。

## 技术栈

- **数据库**: PostgreSQL
- **ORM**: SQLAlchemy 2.0
- **迁移工具**: Alembic

## 设计原则

- **多租户**: 所有表通过 `tenant_id` 实现数据隔离
- **软删除**: `is_deleted` 字段标记删除状态
- **时间戳**: `created_at` 和 `updated_at` 记录数据变更时间

## 数据库表结构

### PostgreSQL扩展

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### tenants (租户表)

```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    subdomain VARCHAR(100) UNIQUE,
    api_key VARCHAR(255) UNIQUE,
    plan_type VARCHAR(50) NOT NULL DEFAULT 'basic',
    max_products INTEGER NOT NULL DEFAULT 100,
    max_users INTEGER NOT NULL DEFAULT 5,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_tenants_status ON tenants (status);
CREATE INDEX idx_tenants_subdomain ON tenants (subdomain);
```

### users (用户表)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    email VARCHAR(320) NOT NULL,
    username VARCHAR(50),
    full_name VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    is_email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_super_admin BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_users_tenant_id ON users (tenant_id);
CREATE INDEX idx_users_email ON users (email);
CREATE UNIQUE INDEX uq_users_email_tenant ON users (email, tenant_id);
```

### user_sessions (用户会话表)

```sql
CREATE TABLE user_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    jwt_jti VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_user_sessions_user_id ON user_sessions (user_id);
CREATE INDEX idx_user_sessions_jwt_jti ON user_sessions (jwt_jti);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions (expires_at);
```

### api_keys (API密钥表)

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    key_id VARCHAR(32) UNIQUE NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(8) NOT NULL,
    user_id UUID NOT NULL,
    scopes JSONB DEFAULT '[]',
    status VARCHAR(20) DEFAULT 'ACTIVE',
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_api_keys_key_id ON api_keys (key_id);
CREATE INDEX idx_api_keys_user_id ON api_keys (user_id);
```

### products (产品表)

```sql
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    asin VARCHAR(20) NOT NULL,
    title VARCHAR(500) NOT NULL,
    brand VARCHAR(200),
    category VARCHAR(200),
    marketplace VARCHAR(20) DEFAULT 'AMAZON_US',
    product_url TEXT NOT NULL,
    image_url TEXT,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    tracking_frequency VARCHAR(20) DEFAULT 'DAILY',
    is_competitor BOOLEAN DEFAULT FALSE,
    current_price DECIMAL(10,2),
    buy_box_price DECIMAL(10,2),
    current_rank INTEGER,
    current_rating DECIMAL(3,2),
    current_review_count INTEGER DEFAULT 0,
    current_availability VARCHAR(50),
    product_data JSONB DEFAULT '{}',
    bullet_points JSONB DEFAULT '[]',
    description TEXT,
    last_scraped_at TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    tags JSONB DEFAULT '[]',
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_products_tenant_id ON products (tenant_id);
CREATE INDEX idx_products_asin ON products (asin);
CREATE INDEX idx_products_status ON products (status);
CREATE UNIQUE INDEX uq_product_asin_marketplace_tenant ON products (asin, marketplace, tenant_id);
```

### product_tracking_data (产品跟踪数据表)

```sql
CREATE TABLE product_tracking_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL,
    price DECIMAL(10,2),
    list_price DECIMAL(10,2),
    buy_box_price DECIMAL(10,2),
    rank INTEGER,
    rating DECIMAL(3,2),
    review_count INTEGER,
    availability VARCHAR(50),
    scraped_data JSONB DEFAULT '{}',
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_product_tracking_data_product_id ON product_tracking_data (product_id);
CREATE INDEX idx_product_tracking_data_recorded_at ON product_tracking_data (recorded_at);
```


### product_alerts (产品预警表)

```sql
CREATE TABLE product_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    product_id UUID NOT NULL,
    user_id UUID,
    alert_type VARCHAR(50) NOT NULL,
    target_value DECIMAL(10,2),
    threshold_percentage DECIMAL(5,2),
    is_active BOOLEAN DEFAULT TRUE,
    last_triggered_at TIMESTAMP WITH TIME ZONE,
    trigger_count INTEGER DEFAULT 0,
    notification_methods JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_product_alerts_tenant_id ON product_alerts (tenant_id);
CREATE INDEX idx_product_alerts_product_id ON product_alerts (product_id);
```

### crawl_tasks (爬虫任务表)

```sql
CREATE TABLE crawl_tasks (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    product_id UUID NOT NULL,
    crawler_type VARCHAR(50) NOT NULL,
    task_name VARCHAR(200) NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING',
    priority VARCHAR(10) DEFAULT 'NORMAL',
    scheduled_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    result_data JSONB DEFAULT '{}',
    error_message TEXT,
    external_task_id VARCHAR(200),
    items_processed INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_crawl_tasks_tenant_id ON crawl_tasks (tenant_id);
CREATE INDEX idx_crawl_tasks_status ON crawl_tasks (status);
CREATE INDEX idx_crawl_tasks_scheduled_at ON crawl_tasks (scheduled_at);
```


## 总结

本数据库设计提供了Amazon产品追踪系统的核心表结构，包括：

- **多租户支持**: 通过 `tenant_id` 实现数据隔离
- **用户管理**: 用户、会话、API密钥管理
- **产品跟踪**: 产品信息、历史数据、预警机制
- **任务管理**: 爬虫任务调度和执行状态跟踪

设计特点：
- 简洁的表结构，易于理解和维护
- 基础索引优化查询性能
- 软删除支持数据恢复
- JSONB字段支持灵活的数据存储