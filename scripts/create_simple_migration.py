#!/usr/bin/env python3
"""创建简单的数据库迁移脚本"""

import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_initial_migration():
    """创建初始数据库迁移"""

    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 迁移文件内容
    migration_content = f'''"""Initial database schema with multi-tenant support

Revision ID: {timestamp}
Revises:
Create Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")}

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '{timestamp}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create UUID extension if not exists
    op.execute("CREATE EXTENSION IF NOT EXISTS \\\"uuid-ossp\\\"")

    # Create tenants table
    op.create_table('tenants',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=100), nullable=True),
        sa.Column('subscription_plan', sa.Enum('FREE_TRIAL', 'BASIC', 'PROFESSIONAL', 'ENTERPRISE', name='subscriptionplan'), nullable=True),
        sa.Column('subscription_status', sa.Enum('TRIAL', 'ACTIVE', 'EXPIRED', 'CANCELLED', 'SUSPENDED', name='subscriptionstatus'), nullable=True),
        sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('subscription_ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('max_users', sa.Integer(), nullable=True),
        sa.Column('max_products', sa.Integer(), nullable=True),
        sa.Column('max_api_calls_per_day', sa.Integer(), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('domain'),
        sa.UniqueConstraint('tenant_id')
    )
    op.create_index('ix_tenants_is_deleted', 'tenants', ['is_deleted'], unique=False)
    op.create_index('ix_tenants_tenant_id', 'tenants', ['tenant_id'], unique=False)

    # Create users table
    op.create_table('users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('salt', sa.String(length=32), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', 'SUSPENDED', 'PENDING_VERIFICATION', name='userstatus'), nullable=True),
        sa.Column('is_email_verified', sa.Boolean(), nullable=True),
        sa.Column('is_super_admin', sa.Boolean(), nullable=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_ip', sa.String(length=45), nullable=True),
        sa.Column('login_count', sa.Integer(), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=True),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('email_verification_token', sa.String(length=255), nullable=True),
        sa.Column('email_verification_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_reset_token', sa.String(length=255), nullable=True),
        sa.Column('password_reset_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('avatar_url', sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', 'tenant_id', name='uq_user_email_tenant'),
        sa.UniqueConstraint('username', 'tenant_id', name='uq_user_username_tenant')
    )
    op.create_index('ix_user_tenant_status', 'users', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=False)
    op.create_index('ix_users_is_deleted', 'users', ['is_deleted'], unique=False)
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'], unique=False)
    op.create_index('ix_users_username', 'users', ['username'], unique=False)

    # Create user_sessions table
    op.create_table('user_sessions',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('jwt_jti', sa.String(length=255), nullable=False),
        sa.Column('refresh_token', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jwt_jti'),
        sa.UniqueConstraint('refresh_token'),
        sa.UniqueConstraint('session_id')
    )
    op.create_index('ix_session_expires', 'user_sessions', ['expires_at'], unique=False)
    op.create_index('ix_session_user_active', 'user_sessions', ['user_id', 'is_active'], unique=False)
    op.create_index('ix_user_sessions_is_deleted', 'user_sessions', ['is_deleted'], unique=False)
    op.create_index('ix_user_sessions_session_id', 'user_sessions', ['session_id'], unique=False)

    print("✅ 初始数据库架构创建完成!")


def downgrade() -> None:
    op.drop_table('user_sessions')
    op.drop_table('users')
    op.drop_table('tenants')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS subscriptionplan")
    op.execute("DROP TYPE IF EXISTS subscriptionstatus")
    op.execute("DROP TYPE IF EXISTS userstatus")

    print("✅ 数据库架构已回滚!")
'''

    # 创建迁移文件
    migrations_dir = "alembic/versions"
    os.makedirs(migrations_dir, exist_ok=True)

    filename = f"{timestamp}_initial_schema.py"
    filepath = os.path.join(migrations_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(migration_content)

    print(f"✅ 创建迁移文件: {filepath}")
    return filepath


if __name__ == "__main__":
    create_initial_migration()
