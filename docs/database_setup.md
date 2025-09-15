# 数据库设计与迁移指南

本文档介绍Amazon产品追踪分析系统的数据库设计和迁移使用方法。

## 📁 文件结构

```
amazon_tracker/
├── common/
│   ├── config/
│   │   ├── settings.py              # 应用程序配置
│   │   └── __init__.py
│   └── database/
│       ├── base.py                  # 数据库基础配置
│       ├── models/                  # 数据模型
│       │   ├── __init__.py
│       │   ├── tenant.py           # 租户模型
│       │   ├── user.py             # 用户模型
│       │   ├── product.py          # 产品模型
│       │   ├── competitor.py       # 竞品模型
│       │   ├── analysis.py         # 分析报告模型
│       │   ├── suggestion.py       # 优化建议模型
│       │   └── task.py             # 任务模型
│       └── __init__.py
├── migrations/                      # Alembic迁移文件
│   ├── versions/                   # 迁移版本
│   ├── env.py                      # Alembic环境配置
│   └── script.py.mako              # 迁移模板
├── scripts/
│   ├── db_manager.py               # 数据库管理工具
│   ├── seed_data.py                # 种子数据脚本
│   └── database_partitions.sql     # 分区和优化脚本
├── alembic.ini                     # Alembic配置文件
└── .env.example                    # 环境变量示例
```

## 🗄️ 数据库架构

### 核心表结构

1. **多租户基础**
   - `tenants` - 租户表
   - `users` - 用户表

2. **产品管理**
   - `categories` - 品类管理表
   - `products` - 产品表
   - `product_tracking_data` - 产品追踪数据表(分区表)

3. **分析功能**
   - `competitor_data` - 竞品数据表
   - `analysis_reports` - 分析报告表
   - `optimization_suggestions` - 优化建议表

4. **任务管理**
   - `tasks` - 任务表

### 关键特性

- ✅ **多租户支持**: 通过tenant_id实现数据隔离
- ✅ **时序数据分区**: product_tracking_data表按月分区
- ✅ **JSONB存储**: 灵活的数据存储结构
- ✅ **完整索引**: 针对查询模式优化的索引策略
- ✅ **外键约束**: 保证数据完整性

## 🚀 快速开始

### 1. 环境配置

复制环境变量模板并配置：
```bash
cp .env.example .env
# 编辑.env文件，配置数据库连接等参数
```

### 2. 安装依赖

```bash
# 使用UV安装依赖
uv pip install -r requirements.txt

# 或使用pip
pip install -r requirements.txt
```

### 3. 数据库初始化

使用管理工具一键初始化：

```bash
# 完整初始化(包含迁移、优化、种子数据)
python scripts/db_manager.py init

# 仅迁移，不创建种子数据
python scripts/db_manager.py init --no-seed

# 强制重建(危险操作)
python scripts/db_manager.py init --force
```

或手动执行：

```bash
# 1. 运行数据库迁移
alembic upgrade head

# 2. 应用分区和索引优化
psql -d amazon_tracker < scripts/database_partitions.sql

# 3. 创建种子数据
python scripts/seed_data.py
```

### 4. 验证安装

```bash
# 检查数据库状态
python scripts/db_manager.py status

# 查看迁移历史
alembic history
```

## 🛠️ 开发工作流

### 创建新的数据库迁移

```bash
# 自动生成迁移文件
python scripts/db_manager.py migrate -m "添加新功能"

# 或直接使用Alembic
alembic revision --autogenerate -m "添加新功能"
```

### 应用迁移

```bash
# 应用所有未执行的迁移
python scripts/db_manager.py migrate

# 或直接使用Alembic
alembic upgrade head
```

### 重置数据库

```bash
# 重置数据库(会删除所有数据)
python scripts/db_manager.py reset --yes
```

### 创建种子数据

```bash
# 创建种子数据
python scripts/db_manager.py seed

# 重置种子数据
python scripts/db_manager.py seed --reset
```

### 应用性能优化

```bash
# 应用分区和索引优化
python scripts/db_manager.py optimize
```

## 📊 数据模型说明

### 租户模型 (Tenant)

```python
class Tenant(Base):
    id: UUID                    # 租户ID
    name: str                  # 租户名称
    subdomain: str             # 子域名 (可选)
    api_key: str              # API密钥 (可选)
    plan_type: str            # 套餐类型
    max_products: int         # 最大产品数
    max_users: int           # 最大用户数
    status: str              # 状态
```

### 用户模型 (User)

```python
class User(Base):
    id: UUID                 # 用户ID
    tenant_id: UUID         # 所属租户
    email: str              # 邮箱
    username: str           # 用户名
    password_hash: str      # 密码哈希
    role: str              # 角色
    status: str            # 状态
```

### 产品模型 (Product)

```python
class Product(Base):
    product_id: UUID        # 产品ID
    tenant_id: UUID        # 所属租户
    user_id: UUID          # 创建用户
    asin: str              # Amazon ASIN
    product_url: str       # 产品URL
    title: str             # 产品标题
    brand: str             # 品牌
    category: str          # 类别
    status: str            # 状态
    crawl_frequency: str   # 爬取频率
```

### 产品追踪数据 (ProductTrackingData)

```python
class ProductTrackingData(Base):
    data_id: UUID           # 数据ID
    product_id: UUID        # 产品ID
    tenant_id: UUID         # 租户ID
    date: date              # 数据日期
    price: Decimal          # 价格
    bsr: int                # BSR排名
    rating: Decimal         # 评分
    review_count: int       # 评价数量
    # ... 其他追踪字段
```

## 🔍 性能优化

### 分区策略

- `product_tracking_data`表按月分区
- 自动创建新分区的存储过程
- 自动清理旧分区的维护脚本

### 索引优化

- 复合索引用于多租户查询
- 覆盖索引避免回表操作
- 部分索引仅为活跃数据建索引
- JSONB字段的GIN索引

### 查询优化

- 统计信息目标设置
- 表填充因子调优
- 连接池配置

## 🎯 默认测试数据

初始化完成后，系统会创建以下测试账户：

**Demo Company 租户**
- 管理员: `admin@demo.com` / `password123`
- 用户: `user@demo.com` / `password123`
- 子域名: `demo.localhost`

**Test Enterprise 租户**
- 管理员: `admin@testent.com` / `password123`
- 分析师: `analyst@testent.com` / `password123`

**Basic Startup 租户**
- 创始人: `founder@startup.com` / `password123`

## 📈 监控和维护

### 分区维护

```sql
-- 创建下个月的分区
SELECT create_next_month_partition();

-- 删除12个月前的旧分区
SELECT drop_old_partitions(12);
```

### 性能监控

```sql
-- 查看分区大小
SELECT * FROM partition_sizes;

-- 查看慢查询
SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
```

### 备份建议

- 使用pg_dump进行逻辑备份
- 配置WAL归档进行增量备份
- 定期测试备份恢复流程

## ⚠️ 注意事项

1. **生产环境配置**
   - 修改默认密码
   - 配置SSL连接
   - 设置适当的连接池大小

2. **安全建议**
   - 使用强密码策略
   - 启用审计日志
   - 定期更新依赖包

3. **性能建议**
   - 定期ANALYZE表统计信息
   - 监控慢查询并优化
   - 根据数据增长调整分区策略

## 🆘 故障排除

### 常见问题

1. **迁移失败**
   ```bash
   # 查看迁移状态
   alembic current

   # 查看迁移历史
   alembic history

   # 手动标记迁移版本
   alembic stamp head
   ```

2. **分区创建失败**
   - 检查PostgreSQL版本(>=10)
   - 确认分区键类型匹配
   - 检查分区边界值

3. **索引创建失败**
   - 检查并发索引创建权限
   - 监控磁盘空间使用
   - 分批创建大索引

### 联系支持

如果遇到问题，请检查：
- [ ] 环境变量配置
- [ ] 数据库连接权限
- [ ] PostgreSQL版本兼容性
- [ ] 日志文件错误信息

---

*本文档随着系统演进持续更新*
