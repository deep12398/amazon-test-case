"""Add complete business tables

Revision ID: 2b02360f3de8
Revises: 20250912_010328
Create Date: 2025-09-12 01:22:41.607154

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2b02360f3de8'
down_revision: Union[str, None] = '20250912_010328'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add complete business tables."""
    
    # 1. 创建产品表
    op.create_table('products',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('asin', sa.String(length=10), nullable=False),
        sa.Column('product_url', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('brand', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='active'),
        sa.Column('crawl_frequency', sa.String(length=50), nullable=True, server_default='daily'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'asin')
    )
    
    # 产品表索引
    op.create_index('idx_products_tenant_asin', 'products', ['tenant_id', 'asin'], unique=False)
    op.create_index('idx_products_user', 'products', ['user_id'], unique=False)
    op.create_index('idx_products_category', 'products', ['tenant_id', 'category'], unique=False)
    op.create_index('idx_products_status', 'products', ['status'], unique=False)
    op.create_index('idx_products_product_id', 'products', ['product_id'], unique=False)
    
    # 2. 创建品类表
    op.create_table('categories',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('keywords', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('auto_crawl', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('crawl_schedule', sa.String(length=50), nullable=True, server_default='daily'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'name')
    )
    
    # 品类表索引
    op.create_index('idx_categories_tenant', 'categories', ['tenant_id', 'name'], unique=False)
    op.create_index('idx_categories_auto_crawl', 'categories', ['auto_crawl'], unique=False, 
                   postgresql_where=sa.text('auto_crawl = true'))
    
    # 3. 创建产品追踪数据表
    op.create_table('product_tracking_data',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('data_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_id', sa.BigInteger(), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('tracking_date', sa.Date(), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('bsr', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('review_count', sa.Integer(), nullable=True),
        sa.Column('buy_box_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('availability', sa.String(length=100), nullable=True),
        sa.Column('seller_name', sa.String(length=255), nullable=True),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id', 'tracking_date')
    )
    
    # 追踪数据表索引
    op.create_index('idx_tracking_product_date', 'product_tracking_data', ['product_id', sa.text('tracking_date DESC')], unique=False)
    op.create_index('idx_tracking_tenant_date', 'product_tracking_data', ['tenant_id', sa.text('tracking_date DESC')], unique=False)
    op.create_index('idx_tracking_created_at', 'product_tracking_data', [sa.text('created_at DESC')], unique=False)
    op.create_index('idx_tracking_price', 'product_tracking_data', ['price'], unique=False, 
                   postgresql_where=sa.text('price IS NOT NULL'))
    op.create_index('idx_tracking_bsr', 'product_tracking_data', ['bsr'], unique=False,
                   postgresql_where=sa.text('bsr IS NOT NULL'))
    
    # 4. 创建竞品数据表
    op.create_table('competitor_data',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('competitor_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('parent_product_id', sa.BigInteger(), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('competitor_asin', sa.String(length=10), nullable=False),
        sa.Column('competitor_url', sa.Text(), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=True, server_default='category'),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('similarity_score', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('analysis_status', sa.String(length=50), nullable=True, server_default='pending'),
        sa.ForeignKeyConstraint(['parent_product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 竞品数据表索引
    op.create_index('idx_competitor_parent', 'competitor_data', ['parent_product_id'], unique=False)
    op.create_index('idx_competitor_tenant', 'competitor_data', ['tenant_id', 'competitor_asin'], unique=False)
    op.create_index('idx_competitor_status', 'competitor_data', ['analysis_status'], unique=False)
    op.create_index('idx_competitor_data', 'competitor_data', ['data'], unique=False, postgresql_using='gin')
    
    # 5. 创建分析报告表
    op.create_table('analysis_reports',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_id', sa.BigInteger(), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('report_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('ai_model', sa.String(length=100), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('generation_time_ms', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 分析报告表索引
    op.create_index('idx_reports_product_type', 'analysis_reports', ['product_id', 'report_type'], unique=False)
    op.create_index('idx_reports_tenant', 'analysis_reports', ['tenant_id', sa.text('created_at DESC')], unique=False)
    op.create_index('idx_reports_created', 'analysis_reports', [sa.text('created_at DESC')], unique=False)
    op.create_index('idx_reports_content', 'analysis_reports', ['content'], unique=False, postgresql_using='gin')
    
    # 6. 创建优化建议表
    op.create_table('optimization_suggestions',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('suggestion_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_id', sa.BigInteger(), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('suggestion_type', sa.String(length=50), nullable=False),
        sa.Column('suggestion_text', sa.Text(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('estimated_impact', sa.String(length=50), nullable=True),
        sa.Column('implementation_difficulty', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='pending'),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('priority >= 1 AND priority <= 5'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 优化建议表索引
    op.create_index('idx_suggestions_product', 'optimization_suggestions', ['product_id', 'priority'], unique=False)
    op.create_index('idx_suggestions_tenant', 'optimization_suggestions', ['tenant_id', sa.text('generated_at DESC')], unique=False)
    op.create_index('idx_suggestions_type_priority', 'optimization_suggestions', ['suggestion_type', 'priority'], unique=False)
    op.create_index('idx_suggestions_status', 'optimization_suggestions', ['status'], unique=False)
    
    # 7. 创建任务管理表
    op.create_table('tasks',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('task_type', sa.String(length=50), nullable=False),
        sa.Column('task_name', sa.String(length=255), nullable=False),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='pending'),
        sa.Column('priority', sa.Integer(), nullable=True, server_default='3'),
        sa.Column('progress', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 任务管理表索引
    op.create_index('idx_tasks_tenant', 'tasks', ['tenant_id', sa.text('created_at DESC')], unique=False)
    op.create_index('idx_tasks_status_priority', 'tasks', ['status', 'priority'], unique=False)
    op.create_index('idx_tasks_type', 'tasks', ['task_type'], unique=False)
    op.create_index('idx_tasks_user', 'tasks', ['user_id'], unique=False, 
                   postgresql_where=sa.text('user_id IS NOT NULL'))
    
    # 8. 创建系统日志表
    op.create_table('system_logs',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('log_level', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('module', sa.String(length=100), nullable=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=True),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('trace_id', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 系统日志表索引
    op.create_index('idx_logs_created', 'system_logs', [sa.text('created_at DESC')], unique=False)
    op.create_index('idx_logs_level', 'system_logs', ['log_level'], unique=False)
    op.create_index('idx_logs_tenant', 'system_logs', ['tenant_id'], unique=False,
                   postgresql_where=sa.text('tenant_id IS NOT NULL'))
    op.create_index('idx_logs_trace', 'system_logs', ['trace_id'], unique=False,
                   postgresql_where=sa.text('trace_id IS NOT NULL'))
    
    # 9. 创建API密钥表
    op.create_table('api_keys',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('key_prefix', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('rate_limit', sa.Integer(), nullable=True, server_default='1000'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('usage_count', sa.BigInteger(), nullable=True, server_default='0'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # API密钥表索引
    op.create_index('idx_api_keys_tenant', 'api_keys', ['tenant_id'], unique=False)
    op.create_index('idx_api_keys_user', 'api_keys', ['user_id'], unique=False)
    op.create_index('idx_api_keys_hash', 'api_keys', ['key_hash'], unique=False)
    op.create_index('idx_api_keys_active', 'api_keys', ['is_active'], unique=False,
                   postgresql_where=sa.text('is_active = true'))
    op.create_index('idx_api_keys_expires', 'api_keys', ['expires_at'], unique=False,
                   postgresql_where=sa.text('expires_at IS NOT NULL'))
    
    # 10. 创建更新触发器
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql'
    """)
    
    # 为需要的表添加触发器
    tables_with_updated_at = [
        'products', 'categories', 'product_tracking_data', 'competitor_data', 
        'analysis_reports', 'optimization_suggestions', 'tasks', 'api_keys'
    ]
    
    for table in tables_with_updated_at:
        trigger_name = f"update_{table}_updated_at"
        op.execute(f"""
            CREATE TRIGGER {trigger_name}
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column()
        """)
    
    print("✅ 完整业务表结构创建完成!")


def downgrade() -> None:
    """Downgrade schema - Remove all business tables."""
    
    # 删除触发器
    tables_with_updated_at = [
        'products', 'categories', 'product_tracking_data', 'competitor_data', 
        'analysis_reports', 'optimization_suggestions', 'tasks', 'api_keys'
    ]
    
    for table in tables_with_updated_at:
        trigger_name = f"update_{table}_updated_at"
        op.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table}")
    
    # 删除触发器函数 (如果没有其他地方使用)
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    
    # 删除表 (按依赖关系倒序)
    op.drop_table('api_keys')
    op.drop_table('system_logs') 
    op.drop_table('tasks')
    op.drop_table('optimization_suggestions')
    op.drop_table('analysis_reports')
    op.drop_table('competitor_data')
    op.drop_table('product_tracking_data')
    op.drop_table('categories')
    op.drop_table('products')
    
    print("✅ 业务表结构已回滚!")
