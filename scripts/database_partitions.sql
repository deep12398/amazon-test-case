-- 数据库分区和索引优化脚本
-- 适用于Amazon产品追踪分析系统

-- ================================================================
-- 1. 设置产品追踪数据表的时间分区
-- ================================================================

-- 首先，如果表已经存在且没有分区，需要重建为分区表
-- 注意：这个脚本假设在数据库迁移时运行，表还没有数据

-- 创建分区表 (如果还没有在模型中设置)
-- ALTER TABLE product_tracking_data PARTITION BY RANGE (date);

-- 创建2024年的月度分区
CREATE TABLE IF NOT EXISTS product_tracking_data_2024_01 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2024_02 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2024_03 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2024_04 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2024_05 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2024_06 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2024_07 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2024_08 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2024_09 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2024_10 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2024_11 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2024_12 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

-- 创建2025年的月度分区
CREATE TABLE IF NOT EXISTS product_tracking_data_2025_01 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2025_02 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2025_03 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2025_04 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2025_05 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2025_06 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2025_07 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2025_08 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2025_09 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2025_10 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2025_11 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE IF NOT EXISTS product_tracking_data_2025_12 PARTITION OF product_tracking_data
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- ================================================================
-- 2. 创建分析报告表的时间分区 (可选)
-- ================================================================

-- 如果分析报告数据量很大，也可以考虑分区
-- ALTER TABLE analysis_reports PARTITION BY RANGE (created_at);

-- ================================================================
-- 3. 优化索引策略
-- ================================================================

-- 3.1 复合索引优化 - 用于多租户查询优化
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_tenant_status_created
    ON products (tenant_id, status, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tracking_tenant_product_date_desc
    ON product_tracking_data (tenant_id, product_id, date DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_competitor_data_tenant_status_created
    ON competitor_data (tenant_id, analysis_status, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_tenant_status_priority_created
    ON tasks (tenant_id, status, priority, created_at DESC);

-- 3.2 覆盖索引 - 包含常用查询字段避免回表
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_asin_cover
    ON products (asin)
    INCLUDE (title, brand, category, status, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_cover
    ON users (email)
    INCLUDE (username, role, status, last_login_at);

-- 3.3 部分索引 - 只为活跃数据创建索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_active_only
    ON products (tenant_id, created_at DESC)
    WHERE status = 'active';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_pending_running_only
    ON tasks (priority, created_at)
    WHERE status IN ('pending', 'running');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_suggestions_pending_high_priority
    ON optimization_suggestions (product_id, generated_at DESC)
    WHERE status = 'pending' AND priority <= 2;

-- 3.4 表达式索引 - 用于特定查询模式
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_asin_upper
    ON products (UPPER(asin));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_title_trgm
    ON products USING gin (title gin_trgm_ops);

-- 3.5 JSONB字段的特定索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_competitor_data_price
    ON competitor_data USING gin ((data->'pricing'));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analysis_reports_summary
    ON analysis_reports USING gin ((content->'summary'));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_params_product_id
    ON tasks USING gin ((parameters->'product_id'));

-- ================================================================
-- 4. 设置表的统计信息目标 (提高查询计划准确性)
-- ================================================================

-- 对于高基数列设置更高的统计信息目标
ALTER TABLE products ALTER COLUMN asin SET STATISTICS 1000;
ALTER TABLE product_tracking_data ALTER COLUMN date SET STATISTICS 1000;
ALTER TABLE users ALTER COLUMN email SET STATISTICS 1000;
ALTER TABLE tenants ALTER COLUMN subdomain SET STATISTICS 1000;

-- ================================================================
-- 5. 设置表的填充因子 (为UPDATE预留空间)
-- ================================================================

-- 对于经常更新的表设置较低的填充因子
ALTER TABLE users SET (fillfactor = 85);
ALTER TABLE products SET (fillfactor = 90);
ALTER TABLE tasks SET (fillfactor = 80);

-- ================================================================
-- 6. 创建定期维护的存储过程
-- ================================================================

CREATE OR REPLACE FUNCTION create_next_month_partition()
RETURNS void AS $$
DECLARE
    next_month_start date;
    next_month_end date;
    partition_name text;
BEGIN
    -- 计算下个月的开始和结束日期
    next_month_start := date_trunc('month', CURRENT_DATE + interval '1 month');
    next_month_end := date_trunc('month', CURRENT_DATE + interval '2 months');

    -- 构建分区表名
    partition_name := 'product_tracking_data_' || to_char(next_month_start, 'YYYY_MM');

    -- 创建分区表
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF product_tracking_data
                    FOR VALUES FROM (%L) TO (%L)',
                   partition_name, next_month_start, next_month_end);

    RAISE NOTICE 'Created partition: %', partition_name;
END;
$$ LANGUAGE plpgsql;

-- 创建清理旧分区的存储过程
CREATE OR REPLACE FUNCTION drop_old_partitions(retention_months integer DEFAULT 12)
RETURNS void AS $$
DECLARE
    partition_name text;
    cutoff_date date;
BEGIN
    cutoff_date := date_trunc('month', CURRENT_DATE - (retention_months || ' months')::interval);

    FOR partition_name IN
        SELECT schemaname||'.'||tablename
        FROM pg_tables
        WHERE tablename LIKE 'product_tracking_data_%'
        AND tablename < 'product_tracking_data_' || to_char(cutoff_date, 'YYYY_MM')
    LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || partition_name;
        RAISE NOTICE 'Dropped old partition: %', partition_name;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- 7. 创建数据库维护提醒
-- ================================================================

COMMENT ON FUNCTION create_next_month_partition() IS
'每月运行以创建下个月的分区表。建议在cron job中设置自动运行。';

COMMENT ON FUNCTION drop_old_partitions(integer) IS
'删除超过指定月数的旧分区表。默认保留12个月的数据。';

-- ================================================================
-- 8. 启用一些有用的PostgreSQL扩展
-- ================================================================

-- 启用pg_trgm用于相似性搜索和模糊匹配
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 启用pg_stat_statements用于查询性能监控
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- 启用uuid-ossp用于UUID生成
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ================================================================
-- 9. 创建性能监控视图
-- ================================================================

CREATE OR REPLACE VIEW partition_sizes AS
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_stat_get_tuples_returned(oid) as tuples_returned,
    pg_stat_get_tuples_fetched(oid) as tuples_fetched
FROM pg_tables t
JOIN pg_class c ON c.relname = t.tablename
WHERE tablename LIKE 'product_tracking_data_%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

COMMENT ON VIEW partition_sizes IS '显示所有分区表的大小和访问统计';

-- 完成脚本
SELECT 'Database partitioning and indexing optimization completed successfully!' as status;
