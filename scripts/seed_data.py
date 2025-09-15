"""数据库种子数据脚本"""

import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from amazon_tracker.common.database.base import get_db_session, init_db
from amazon_tracker.common.database.models import (
    Permission,
    Role,
    SubscriptionPlan,
    SubscriptionStatus,
    Tenant,
    User,
    UserRole,
    UserStatus,
)


def create_default_permissions(db):
    """创建默认权限"""

    permissions_data = [
        # 用户管理权限
        {
            "name": "users.read",
            "display_name": "查看用户",
            "description": "查看用户列表和详情",
            "resource": "users",
            "action": "read",
            "scope": "tenant",
        },
        {
            "name": "users.write",
            "display_name": "管理用户",
            "description": "创建和编辑用户",
            "resource": "users",
            "action": "write",
            "scope": "tenant",
        },
        {
            "name": "users.delete",
            "display_name": "删除用户",
            "description": "删除用户账户",
            "resource": "users",
            "action": "delete",
            "scope": "tenant",
        },
        {
            "name": "users.admin",
            "display_name": "用户管理员",
            "description": "完全的用户管理权限",
            "resource": "users",
            "action": "admin",
            "scope": "tenant",
        },
        # 产品管理权限
        {
            "name": "products.read",
            "display_name": "查看产品",
            "description": "查看产品信息",
            "resource": "products",
            "action": "read",
            "scope": "tenant",
        },
        {
            "name": "products.write",
            "display_name": "管理产品",
            "description": "创建和编辑产品",
            "resource": "products",
            "action": "write",
            "scope": "tenant",
        },
        {
            "name": "products.delete",
            "display_name": "删除产品",
            "description": "删除产品",
            "resource": "products",
            "action": "delete",
            "scope": "tenant",
        },
        {
            "name": "products.admin",
            "display_name": "产品管理员",
            "description": "完全的产品管理权限",
            "resource": "products",
            "action": "admin",
            "scope": "tenant",
        },
        # 分析报告权限
        {
            "name": "analytics.read",
            "display_name": "查看分析",
            "description": "查看分析报告",
            "resource": "analytics",
            "action": "read",
            "scope": "tenant",
        },
        {
            "name": "analytics.export",
            "display_name": "导出报告",
            "description": "导出分析报告",
            "resource": "analytics",
            "action": "export",
            "scope": "tenant",
        },
        # API Key权限
        {
            "name": "api_keys.read",
            "display_name": "查看API Key",
            "description": "查看API Key列表",
            "resource": "api_keys",
            "action": "read",
            "scope": "tenant",
        },
        {
            "name": "api_keys.write",
            "display_name": "管理API Key",
            "description": "创建和管理API Key",
            "resource": "api_keys",
            "action": "write",
            "scope": "tenant",
        },
        {
            "name": "api_keys.delete",
            "display_name": "删除API Key",
            "description": "删除API Key",
            "resource": "api_keys",
            "action": "delete",
            "scope": "tenant",
        },
        # 租户权限
        {
            "name": "tenant.read",
            "display_name": "查看租户信息",
            "description": "查看租户配置",
            "resource": "tenant",
            "action": "read",
            "scope": "tenant",
        },
        {
            "name": "tenant.write",
            "display_name": "管理租户",
            "description": "修改租户配置",
            "resource": "tenant",
            "action": "write",
            "scope": "tenant",
        },
        {
            "name": "tenant.admin",
            "display_name": "租户管理员",
            "description": "完全的租户管理权限",
            "resource": "tenant",
            "action": "admin",
            "scope": "tenant",
        },
        # 系统权限
        {
            "name": "system.admin",
            "display_name": "系统管理员",
            "description": "系统管理权限",
            "resource": "system",
            "action": "admin",
            "scope": "global",
        },
        {
            "name": "system.settings",
            "display_name": "系统设置",
            "description": "修改系统设置",
            "resource": "system",
            "action": "write",
            "scope": "global",
        },
    ]

    created_permissions = []

    for perm_data in permissions_data:
        # 检查权限是否已存在
        existing = (
            db.query(Permission).filter(Permission.name == perm_data["name"]).first()
        )
        if not existing:
            permission = Permission(
                name=perm_data["name"],
                display_name=perm_data["display_name"],
                description=perm_data["description"],
                resource=perm_data["resource"],
                action=perm_data["action"],
                scope=perm_data["scope"],
                is_system=True,
            )
            db.add(permission)
            created_permissions.append(permission)
            print(f"✓ 创建权限: {perm_data['name']}")
        else:
            created_permissions.append(existing)

    db.commit()
    return created_permissions


def create_default_roles(db, permissions):
    """创建默认角色"""

    # 权限映射
    perm_dict = {p.name: p for p in permissions}

    roles_data = [
        {
            "name": "super_admin",
            "display_name": "超级管理员",
            "description": "系统超级管理员，拥有所有权限",
            "tenant_id": None,  # 全局角色
            "is_system": True,
            "is_default": False,
            "priority": 1000,
            "permissions": list(perm_dict.keys()),  # 所有权限
        },
        {
            "name": "tenant_admin",
            "display_name": "租户管理员",
            "description": "租户管理员，管理租户内的所有资源",
            "tenant_id": None,  # 模板角色，为每个租户复制
            "is_system": True,
            "is_default": False,
            "priority": 100,
            "permissions": [
                "users.admin",
                "products.admin",
                "analytics.read",
                "analytics.export",
                "api_keys.write",
                "tenant.admin",
            ],
        },
        {
            "name": "user",
            "display_name": "普通用户",
            "description": "普通用户，可以查看和管理自己的产品",
            "tenant_id": None,  # 模板角色
            "is_system": True,
            "is_default": True,
            "priority": 10,
            "permissions": [
                "products.read",
                "products.write",
                "analytics.read",
                "api_keys.read",
                "api_keys.write",
                "tenant.read",
            ],
        },
        {
            "name": "viewer",
            "display_name": "查看者",
            "description": "只读用户，只能查看信息",
            "tenant_id": None,  # 模板角色
            "is_system": True,
            "is_default": False,
            "priority": 5,
            "permissions": ["products.read", "analytics.read", "tenant.read"],
        },
    ]

    created_roles = []

    for role_data in roles_data:
        # 检查角色是否已存在
        existing = (
            db.query(Role)
            .filter(
                Role.name == role_data["name"], Role.tenant_id == role_data["tenant_id"]
            )
            .first()
        )

        if not existing:
            role = Role(
                name=role_data["name"],
                display_name=role_data["display_name"],
                description=role_data["description"],
                tenant_id=role_data["tenant_id"],
                is_system=role_data["is_system"],
                is_default=role_data["is_default"],
                priority=role_data["priority"],
            )

            # 添加权限
            role_permissions = []
            for perm_name in role_data["permissions"]:
                if perm_name in perm_dict:
                    role_permissions.append(perm_dict[perm_name])

            role.permissions = role_permissions

            db.add(role)
            created_roles.append(role)
            print(f"✓ 创建角色: {role_data['name']} (权限: {len(role_permissions)}个)")
        else:
            created_roles.append(existing)

    db.commit()
    return created_roles


def create_demo_tenant_and_admin(db):
    """创建演示租户和管理员账户"""

    # 检查是否已存在演示租户
    demo_tenant = db.query(Tenant).filter(Tenant.name == "演示租户").first()

    if not demo_tenant:
        # 创建演示租户
        demo_tenant = Tenant(
            name="演示租户",
            subscription_plan=SubscriptionPlan.PROFESSIONAL,
            subscription_status=SubscriptionStatus.ACTIVE,
            max_users=100,
            max_products=2000,
            max_api_calls_per_day=200000,
        )
        db.add(demo_tenant)
        db.flush()  # 获取tenant_id
        print(f"✓ 创建演示租户: {demo_tenant.tenant_id}")

        # 为该租户创建角色副本
        template_roles = (
            db.query(Role)
            .filter(
                Role.tenant_id == None, Role.name != "super_admin"
            )  # 超级管理员角色是全局的
            .all()
        )

        tenant_roles = []
        for template_role in template_roles:
            tenant_role = Role(
                name=template_role.name,
                display_name=template_role.display_name,
                description=template_role.description,
                tenant_id=demo_tenant.tenant_id,
                is_system=False,  # 租户角色不是系统角色
                is_default=template_role.is_default,
                priority=template_role.priority,
                permissions=template_role.permissions,
            )
            db.add(tenant_role)
            tenant_roles.append(tenant_role)

        db.flush()  # 确保角色已保存
        print(f"✓ 为租户创建了 {len(tenant_roles)} 个角色")

    # 检查是否已存在演示管理员
    admin_user = (
        db.query(User)
        .filter(User.email == "admin@demo.com", User.tenant_id == demo_tenant.tenant_id)
        .first()
    )

    if not admin_user:
        # 创建演示管理员
        admin_user = User(
            email="admin@demo.com",
            username="admin",
            full_name="演示管理员",
            tenant_id=demo_tenant.tenant_id,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        )
        admin_user.set_password("admin123456")  # 演示密码

        db.add(admin_user)
        db.flush()

        # 分配租户管理员角色
        tenant_admin_role = (
            db.query(Role)
            .filter(
                Role.name == "tenant_admin", Role.tenant_id == demo_tenant.tenant_id
            )
            .first()
        )

        if tenant_admin_role:
            user_role = UserRole(
                user_id=admin_user.id,
                role_id=tenant_admin_role.id,
                granted_at=datetime.utcnow(),
                is_active=True,
            )
            db.add(user_role)

        print("✓ 创建演示管理员: admin@demo.com (密码: admin123456)")

    db.commit()
    return demo_tenant


def main():
    """主函数"""
    print("开始初始化数据库种子数据...")

    # 初始化数据库
    init_db()

    db = get_db_session()
    try:
        # 1. 创建默认权限
        print("\n1. 创建默认权限...")
        permissions = create_default_permissions(db)
        print(f"权限创建完成，共 {len(permissions)} 个权限")

        # 2. 创建默认角色
        print("\n2. 创建默认角色...")
        roles = create_default_roles(db, permissions)
        print(f"角色创建完成，共 {len(roles)} 个角色")

        # 3. 创建演示租户和用户
        print("\n3. 创建演示租户和用户...")
        demo_tenant = create_demo_tenant_and_admin(db)
        print(f"演示租户创建完成: {demo_tenant.tenant_id}")

        print("\n✓ 数据库种子数据初始化完成!")
        print("\n演示账户:")
        print("- 管理员: admin@demo.com / admin123456")

    except Exception as e:
        print(f"❌ 初始化过程中发生错误: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
