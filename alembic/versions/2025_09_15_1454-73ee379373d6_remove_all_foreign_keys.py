"""remove_all_foreign_keys

Revision ID: 73ee379373d6
Revises: f1c26c9be646
Create Date: 2025-09-15 14:54:19.935101

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '73ee379373d6'
down_revision: Union[str, None] = 'f1c26c9be646'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove all foreign keys from database."""

    # 第1批 - 末端表的外键（避免依赖冲突）
    op.drop_constraint('crawl_logs_task_id_fkey', 'crawl_logs', type_='foreignkey')
    op.drop_constraint('competitor_analysis_snapshots_competitor_set_id_fkey', 'competitor_analysis_snapshots', type_='foreignkey')
    op.drop_constraint('competitor_relationships_competitor_product_id_fkey', 'competitor_relationships', type_='foreignkey')
    op.drop_constraint('competitor_relationships_competitor_set_id_fkey', 'competitor_relationships', type_='foreignkey')

    # 第2批 - 中间表的外键
    op.drop_constraint('crawl_tasks_product_id_fkey', 'crawl_tasks', type_='foreignkey')
    op.drop_constraint('competitor_sets_main_product_id_fkey', 'competitor_sets', type_='foreignkey')
    op.drop_constraint('product_alerts_product_id_fkey', 'product_alerts', type_='foreignkey')
    op.drop_constraint('product_alerts_user_id_fkey', 'product_alerts', type_='foreignkey')
    op.drop_constraint('product_price_history_product_id_fkey', 'product_price_history', type_='foreignkey')
    op.drop_constraint('product_rank_history_product_id_fkey', 'product_rank_history', type_='foreignkey')
    op.drop_constraint('api_keys_user_id_fkey', 'api_keys', type_='foreignkey')
    op.drop_constraint('user_sessions_user_id_fkey', 'user_sessions', type_='foreignkey')
    op.drop_constraint('role_permissions_permission_id_fkey', 'role_permissions', type_='foreignkey')
    op.drop_constraint('role_permissions_role_id_fkey', 'role_permissions', type_='foreignkey')
    op.drop_constraint('user_roles_granted_by_fkey', 'user_roles', type_='foreignkey')
    op.drop_constraint('user_roles_role_id_fkey', 'user_roles', type_='foreignkey')
    op.drop_constraint('user_roles_user_id_fkey', 'user_roles', type_='foreignkey')

    # 第3批 - 基础表的外键
    op.drop_constraint('users_tenant_id_fkey', 'users', type_='foreignkey')


def downgrade() -> None:
    """Recreate all foreign keys (for rollback)."""

    # 反向顺序重新创建外键
    # 第1批 - 基础表的外键
    op.create_foreign_key('users_tenant_id_fkey', 'users', 'tenants', ['tenant_id'], ['tenant_id'])

    # 第2批 - 中间表的外键
    op.create_foreign_key('user_roles_user_id_fkey', 'user_roles', 'users', ['user_id'], ['id'])
    op.create_foreign_key('user_roles_role_id_fkey', 'user_roles', 'roles', ['role_id'], ['id'])
    op.create_foreign_key('user_roles_granted_by_fkey', 'user_roles', 'users', ['granted_by'], ['id'])
    op.create_foreign_key('role_permissions_role_id_fkey', 'role_permissions', 'roles', ['role_id'], ['id'])
    op.create_foreign_key('role_permissions_permission_id_fkey', 'role_permissions', 'permissions', ['permission_id'], ['id'])
    op.create_foreign_key('user_sessions_user_id_fkey', 'user_sessions', 'users', ['user_id'], ['id'])
    op.create_foreign_key('api_keys_user_id_fkey', 'api_keys', 'users', ['user_id'], ['id'])
    op.create_foreign_key('product_rank_history_product_id_fkey', 'product_rank_history', 'products', ['product_id'], ['id'])
    op.create_foreign_key('product_price_history_product_id_fkey', 'product_price_history', 'products', ['product_id'], ['id'])
    op.create_foreign_key('product_alerts_user_id_fkey', 'product_alerts', 'users', ['user_id'], ['id'])
    op.create_foreign_key('product_alerts_product_id_fkey', 'product_alerts', 'products', ['product_id'], ['id'])
    op.create_foreign_key('competitor_sets_main_product_id_fkey', 'competitor_sets', 'products', ['main_product_id'], ['id'])
    op.create_foreign_key('crawl_tasks_product_id_fkey', 'crawl_tasks', 'products', ['product_id'], ['id'])

    # 第3批 - 末端表的外键
    op.create_foreign_key('competitor_relationships_competitor_set_id_fkey', 'competitor_relationships', 'competitor_sets', ['competitor_set_id'], ['id'])
    op.create_foreign_key('competitor_relationships_competitor_product_id_fkey', 'competitor_relationships', 'products', ['competitor_product_id'], ['id'])
    op.create_foreign_key('competitor_analysis_snapshots_competitor_set_id_fkey', 'competitor_analysis_snapshots', 'competitor_sets', ['competitor_set_id'], ['id'])
    op.create_foreign_key('crawl_logs_task_id_fkey', 'crawl_logs', 'crawl_tasks', ['task_id'], ['task_id'])
