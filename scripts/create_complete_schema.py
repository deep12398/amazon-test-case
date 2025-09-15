#!/usr/bin/env python3
"""创建完整数据库架构脚本"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def create_complete_schema():
    """创建完整数据库架构"""

    DATABASE_URL = "postgresql+asyncpg://postgres:your-password@db.your-project.supabase.co:5432/postgres"

    print("🏗️ 开始创建完整数据库架构...")

    # 创建引擎
    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        async with engine.begin() as conn:
            # 1. 创建产品管理核心表
            print("📦 创建产品管理表...")

            # 产品表
            await conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS products (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                    product_id UUID NOT NULL DEFAULT gen_random_uuid(),
                    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                    tenant_id VARCHAR(64) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
                    asin VARCHAR(10) NOT NULL,
                    product_url TEXT NOT NULL,
                    title TEXT,
                    brand VARCHAR(255),
                    category VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'active',
                    crawl_frequency VARCHAR(50) DEFAULT 'daily',
                    UNIQUE(tenant_id, asin)
                )
            """
                )
            )

            # 索引
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_products_tenant_asin ON products (tenant_id, asin)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_products_user ON products (user_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_products_category ON products (tenant_id, category)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_products_status ON products (status)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_products_product_id ON products (product_id)"
                )
            )

            print("  ✓ products表创建完成")

            # 品类管理表
            await conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS categories (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                    category_id UUID NOT NULL DEFAULT gen_random_uuid(),
                    tenant_id VARCHAR(64) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    keywords TEXT[],
                    auto_crawl BOOLEAN DEFAULT TRUE,
                    crawl_schedule VARCHAR(50) DEFAULT 'daily',
                    UNIQUE(tenant_id, name)
                )
            """
                )
            )

            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_categories_tenant ON categories (tenant_id, name)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_categories_auto_crawl ON categories (auto_crawl) WHERE auto_crawl = TRUE"
                )
            )

            print("  ✓ categories表创建完成")

            # 2. 创建产品追踪数据表(时序数据)
            print("📊 创建产品追踪数据表...")

            # 主要产品追踪数据表
            await conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS product_tracking_data (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                    data_id UUID NOT NULL DEFAULT gen_random_uuid(),
                    product_id BIGINT REFERENCES products(id) ON DELETE CASCADE,
                    tenant_id VARCHAR(64) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
                    tracking_date DATE NOT NULL,
                    price NUMERIC(10, 2),
                    bsr INTEGER,
                    rating NUMERIC(3, 2),
                    review_count INTEGER,
                    buy_box_price NUMERIC(10, 2),
                    availability VARCHAR(100),
                    seller_name VARCHAR(255),
                    raw_data JSONB,
                    UNIQUE(product_id, tracking_date)
                )
            """
                )
            )

            # 索引
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_tracking_product_date ON product_tracking_data (product_id, tracking_date DESC)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_tracking_tenant_date ON product_tracking_data (tenant_id, tracking_date DESC)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_tracking_created_at ON product_tracking_data (created_at DESC)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_tracking_price ON product_tracking_data (price) WHERE price IS NOT NULL"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_tracking_bsr ON product_tracking_data (bsr) WHERE bsr IS NOT NULL"
                )
            )

            print("  ✓ product_tracking_data表创建完成")

            # 3. 创建竞品分析相关表
            print("🔍 创建竞品分析表...")

            # 竞品数据表
            await conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS competitor_data (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                    competitor_id UUID NOT NULL DEFAULT gen_random_uuid(),
                    parent_product_id BIGINT REFERENCES products(id) ON DELETE CASCADE,
                    tenant_id VARCHAR(64) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
                    competitor_asin VARCHAR(10) NOT NULL,
                    competitor_url TEXT NOT NULL,
                    relationship_type VARCHAR(50) DEFAULT 'category',
                    data JSONB NOT NULL,
                    similarity_score NUMERIC(3,2),
                    analysis_status VARCHAR(50) DEFAULT 'pending'
                )
            """
                )
            )

            # 索引
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_competitor_parent ON competitor_data (parent_product_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_competitor_tenant ON competitor_data (tenant_id, competitor_asin)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_competitor_status ON competitor_data (analysis_status)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_competitor_data ON competitor_data USING GIN (data)"
                )
            )

            print("  ✓ competitor_data表创建完成")

            # 分析报告表
            await conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS analysis_reports (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                    report_id UUID NOT NULL DEFAULT gen_random_uuid(),
                    product_id BIGINT REFERENCES products(id) ON DELETE CASCADE,
                    tenant_id VARCHAR(64) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
                    report_type VARCHAR(50) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    content JSONB NOT NULL,
                    ai_model VARCHAR(100),
                    tokens_used INTEGER,
                    generation_time_ms INTEGER
                )
            """
                )
            )

            # 索引
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_reports_product_type ON analysis_reports (product_id, report_type)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_reports_tenant ON analysis_reports (tenant_id, created_at DESC)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_reports_created ON analysis_reports (created_at DESC)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_reports_content ON analysis_reports USING GIN (content)"
                )
            )

            print("  ✓ analysis_reports表创建完成")

            # 4. 创建优化建议表
            print("💡 创建优化建议表...")

            await conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS optimization_suggestions (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                    suggestion_id UUID NOT NULL DEFAULT gen_random_uuid(),
                    product_id BIGINT REFERENCES products(id) ON DELETE CASCADE,
                    tenant_id VARCHAR(64) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
                    suggestion_type VARCHAR(50) NOT NULL,
                    suggestion_text TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    priority INTEGER NOT NULL CHECK (priority >= 1 AND priority <= 5),
                    estimated_impact VARCHAR(50),
                    implementation_difficulty VARCHAR(50),
                    status VARCHAR(50) DEFAULT 'pending',
                    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """
                )
            )

            # 索引
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_suggestions_product ON optimization_suggestions (product_id, priority)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_suggestions_tenant ON optimization_suggestions (tenant_id, generated_at DESC)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_suggestions_type_priority ON optimization_suggestions (suggestion_type, priority)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_suggestions_status ON optimization_suggestions (status)"
                )
            )

            print("  ✓ optimization_suggestions表创建完成")

            # 5. 创建任务管理表
            print("⚙️ 创建任务管理表...")

            await conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS tasks (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                    task_id UUID NOT NULL DEFAULT gen_random_uuid(),
                    tenant_id VARCHAR(64) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
                    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
                    task_type VARCHAR(50) NOT NULL,
                    task_name VARCHAR(255) NOT NULL,
                    parameters JSONB,
                    status VARCHAR(50) DEFAULT 'pending',
                    priority INTEGER DEFAULT 3,
                    progress INTEGER DEFAULT 0,
                    error_message TEXT,
                    started_at TIMESTAMPTZ,
                    completed_at TIMESTAMPTZ
                )
            """
                )
            )

            # 索引
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_tasks_tenant ON tasks (tenant_id, created_at DESC)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_tasks_status_priority ON tasks (status, priority)"
                )
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks (task_type)")
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks (user_id) WHERE user_id IS NOT NULL"
                )
            )

            print("  ✓ tasks表创建完成")

            # 6. 创建系统日志表
            print("📝 创建系统日志表...")

            await conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS system_logs (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    log_level VARCHAR(20) NOT NULL,
                    message TEXT NOT NULL,
                    module VARCHAR(100),
                    tenant_id VARCHAR(64),
                    user_id BIGINT,
                    metadata JSONB,
                    trace_id VARCHAR(100)
                )
            """
                )
            )

            # 索引
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_logs_created ON system_logs (created_at DESC)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs (log_level)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_logs_tenant ON system_logs (tenant_id) WHERE tenant_id IS NOT NULL"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_logs_trace ON system_logs (trace_id) WHERE trace_id IS NOT NULL"
                )
            )

            print("  ✓ system_logs表创建完成")

            # 7. 创建API密钥表
            print("🔑 创建API密钥表...")

            await conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS api_keys (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                    api_key_id UUID NOT NULL DEFAULT gen_random_uuid(),
                    tenant_id VARCHAR(64) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
                    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                    key_hash VARCHAR(255) NOT NULL,
                    key_prefix VARCHAR(20) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    permissions JSONB DEFAULT '[]',
                    rate_limit INTEGER DEFAULT 1000,
                    last_used_at TIMESTAMPTZ,
                    expires_at TIMESTAMPTZ,
                    is_active BOOLEAN DEFAULT TRUE,
                    usage_count BIGINT DEFAULT 0
                )
            """
                )
            )

            # 索引
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys (tenant_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys (user_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys (key_hash)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys (is_active) WHERE is_active = TRUE"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_api_keys_expires ON api_keys (expires_at) WHERE expires_at IS NOT NULL"
                )
            )

            print("  ✓ api_keys表创建完成")

            # 8. 创建触发器函数更新updated_at
            print("⏱️ 创建更新时间触发器...")

            await conn.execute(
                text(
                    """
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ language 'plpgsql'
            """
                )
            )

            # 为所有表添加触发器
            tables_with_updated_at = [
                "tenants",
                "users",
                "user_sessions",
                "products",
                "categories",
                "product_tracking_data",
                "competitor_data",
                "analysis_reports",
                "optimization_suggestions",
                "tasks",
                "api_keys",
            ]

            for table in tables_with_updated_at:
                trigger_name = f"update_{table}_updated_at"
                # 先删除已存在的触发器
                await conn.execute(
                    text(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table}")
                )
                # 再创建新触发器
                await conn.execute(
                    text(
                        f"""
                    CREATE TRIGGER {trigger_name}
                        BEFORE UPDATE ON {table}
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column()
                """
                    )
                )
                print(f"  ✓ {table}更新时间触发器")

        await engine.dispose()
        print("\n✅ 完整数据库架构创建完成!")
        return True

    except Exception as e:
        print(f"\n❌ 架构创建失败: {e}")
        await engine.dispose()
        return False


if __name__ == "__main__":
    success = asyncio.run(create_complete_schema())
    exit(0 if success else 1)
