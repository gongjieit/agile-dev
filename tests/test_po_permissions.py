#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试PO用户的角色和权限
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, User, Role, UserRole, SystemFeature, RoleSystemFeature
from utils import check_system_feature_access, check_user_role

def test_po_permissions():
    """测试PO用户的角色和权限"""
    with app.app_context():
        print("=" * 60)
        print("测试PO用户的角色和权限")
        print("=" * 60)

        # 1. 查找PO用户
        po_user = User.query.filter_by(name='po').first()
        if not po_user:
            print("错误：未找到PO用户")
            return

        print(f"1. PO用户信息:")
        print(f"   ID: {po_user.id}")
        print(f"   用户名: {po_user.name}")
        print()

        # 2. 查找PO角色
        po_role = Role.query.filter_by(name='PO').first()
        if not po_role:
            print("错误：未找到PO角色")
            return

        print(f"2. PO角色信息:")
        print(f"   ID: {po_role.id}")
        print(f"   角色名: {po_role.name}")
        print(f"   显示名: {po_role.display_name}")
        print(f"   描述: {po_role.description}")
        print()

        # 3. 检查PO用户是否关联到PO角色
        user_role = UserRole.query.filter_by(
            user_id=po_user.id,
            role_id=po_role.id
        ).first()

        print(f"3. 用户角色关联:")
        if user_role:
            print(f"   PO用户已正确关联到PO角色")
        else:
            print(f"   错误：PO用户未关联到PO角色")
        print()

        # 4. 获取PO角色的所有权限
        role_features = RoleSystemFeature.query.filter_by(role_id=po_role.id).all()
        print(f"4. PO角色的系统功能权限:")
        if role_features:
            for rf in role_features:
                feature = db.session.get(SystemFeature, rf.system_feature_id)
                if feature:
                    print(f"   - {feature.name} ({feature.route_name})")
        else:
            print(f"   PO角色没有任何系统功能权限")
        print()

        # 5. 检查PO角色是否具有迭代管理权限
        sprint_feature = SystemFeature.query.filter_by(route_name='sprints.sprints').first()
        if sprint_feature:
            print(f"5. 迭代管理功能信息:")
            print(f"   ID: {sprint_feature.id}")
            print(f"   名称: {sprint_feature.name}")
            print(f"   路由名: {sprint_feature.route_name}")
            print(f"   是否启用: {sprint_feature.is_enabled}")
            print(f"   是否公开: {sprint_feature.is_public}")

            # 检查PO角色是否具有此权限
            role_sprint_feature = RoleSystemFeature.query.filter_by(
                role_id=po_role.id,
                system_feature_id=sprint_feature.id
            ).first()

            if role_sprint_feature:
                print(f"   权限状态: PO角色已分配此权限")
            else:
                print(f"   权限状态: 错误：PO角色未分配此权限")
        else:
            print(f"5. 错误：未找到迭代管理功能")
        print()

        # 6. 模拟PO用户会话并检查权限
        print(f"6. 权限检查模拟:")
        test_session = {'user_id': po_user.id}

        # 检查是否具有迭代管理权限
        has_sprint_access = check_system_feature_access(test_session, 'sprints.sprints')
        print(f"   迭代管理访问权限: {'是' if has_sprint_access else '否'}")

        # 检查是否具有PO角色
        has_po_role = check_user_role(po_user.id, 'PO')
        print(f"   PO角色: {'是' if has_po_role else '否'}")

        # 检查是否具有管理员角色
        has_admin_role = check_user_role(po_user.id, 'admin')
        print(f"   管理员角色: {'是' if has_admin_role else '否'}")
        print()

        # 7. 总结
        print(f"7. 测试总结:")
        issues = []
        if not user_role:
            issues.append("PO用户未关联到PO角色")
        if not role_sprint_feature:
            issues.append("PO角色未分配迭代管理权限")
        if not has_sprint_access:
            issues.append("PO用户无法访问迭代管理功能")

        if issues:
            print(f"   发现以下问题:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print(f"   所有权限设置正确，PO用户应该可以正常访问迭代管理功能")

if __name__ == '__main__':
    test_po_permissions()
