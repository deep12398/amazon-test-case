-- Amazon Tracker 数据库初始化脚本
-- 创建开发环境的基础数据库结构

-- 确保数据库存在
\c amazon_tracker_dev;

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 创建schema
CREATE SCHEMA IF NOT EXISTS amazon_tracker;
CREATE SCHEMA IF NOT EXISTS logs;
CREATE SCHEMA IF NOT EXISTS monitoring;

-- 设置默认搜索路径
ALTER DATABASE amazon_tracker_dev SET search_path TO amazon_tracker, public;

-- 创建序列用于ID生成
CREATE SEQUENCE IF NOT EXISTS amazon_tracker.global_id_seq;

-- 创建枚举类型
DO $$ BEGIN
    CREATE TYPE amazon_tracker.user_status AS ENUM ('active', 'inactive', 'suspended');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE amazon_tracker.subscription_status AS ENUM ('trial', 'active', 'expired', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE amazon_tracker.product_status AS ENUM ('active', 'inactive', 'deleted');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE amazon_tracker.tracking_status AS ENUM ('active', 'paused', 'stopped');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 创建基础函数
CREATE OR REPLACE FUNCTION amazon_tracker.updated_at_trigger()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION amazon_tracker.generate_tenant_id()
RETURNS TEXT AS $$
BEGIN
    RETURN 'tenant_' || encode(gen_random_bytes(8), 'hex');
END;
$$ LANGUAGE plpgsql;

-- 创建日志记录函数
CREATE OR REPLACE FUNCTION logs.log_table_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO logs.audit_log (table_name, operation, old_data, user_id, tenant_id)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(OLD), current_setting('app.current_user_id', true), current_setting('app.current_tenant_id', true));
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO logs.audit_log (table_name, operation, old_data, new_data, user_id, tenant_id)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(OLD), row_to_json(NEW), current_setting('app.current_user_id', true), current_setting('app.current_tenant_id', true));
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO logs.audit_log (table_name, operation, new_data, user_id, tenant_id)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(NEW), current_setting('app.current_user_id', true), current_setting('app.current_tenant_id', true));
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 创建监控表
CREATE TABLE IF NOT EXISTS monitoring.health_check (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    response_time_ms INTEGER,
    error_message TEXT,
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_health_check_service_status ON monitoring.health_check(service_name, status);
CREATE INDEX IF NOT EXISTS idx_health_check_checked_at ON monitoring.health_check(checked_at);

-- 创建开发用户 (仅开发环境)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'amazon_tracker_dev_user') THEN
        CREATE ROLE amazon_tracker_dev_user WITH LOGIN PASSWORD 'dev_password_123';
    END IF;
END
$$;

-- 授权
GRANT USAGE ON SCHEMA amazon_tracker TO amazon_tracker_dev_user;
GRANT USAGE ON SCHEMA logs TO amazon_tracker_dev_user;
GRANT USAGE ON SCHEMA monitoring TO amazon_tracker_dev_user;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA amazon_tracker TO amazon_tracker_dev_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA logs TO amazon_tracker_dev_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA monitoring TO amazon_tracker_dev_user;

GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA amazon_tracker TO amazon_tracker_dev_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA logs TO amazon_tracker_dev_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA monitoring TO amazon_tracker_dev_user;

-- 插入初始健康检查记录
INSERT INTO monitoring.health_check (service_name, status, response_time_ms, metadata)
VALUES
    ('database', 'healthy', 0, '{"version": "15", "environment": "development"}'),
    ('init-script', 'completed', 0, '{"timestamp": "' || CURRENT_TIMESTAMP || '"}')
ON CONFLICT DO NOTHING;

-- 显示初始化完成信息
\echo '数据库初始化完成！'
\echo '创建的Schema: amazon_tracker, logs, monitoring'
\echo '创建的用户: amazon_tracker_dev_user'
\echo '可用的函数: updated_at_trigger(), generate_tenant_id(), log_table_change()'
