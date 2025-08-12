from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, Role, SystemFeature, RoleSystemFeature
from utils import check_system_feature_access, check_user_role
from decorators import check_access_blueprint

roles_bp = Blueprint('roles', __name__)

# 应用权限检查装饰器
@roles_bp.before_request
@check_access_blueprint('roles')
def check_access():
    pass  # 装饰器会处理权限检查逻辑

@roles_bp.route('/roles')
def roles():
    # 检查权限
    if not check_system_feature_access(session, 'roles.roles'):
        return redirect(url_for('auth.index'))

    # 获取所有角色
    roles = Role.query.all()

    # 为每个角色获取关联的系统功能
    for role in roles:
        role_features = RoleSystemFeature.query.filter_by(role_id=role.id).all()
        role.system_feature_ids = [rf.system_feature_id for rf in role_features]

    # 获取所有系统功能
    system_features = SystemFeature.query.all()

    return render_template('roles.html', roles=roles, system_features=system_features)

@roles_bp.route('/roles/add', methods=['POST'])
def add_role():
    # 检查权限
    is_admin = check_user_role(session.get('user_id'), 'admin')
    if not is_admin:
        return jsonify({'success': False, 'message': '权限不足'})

    name = request.form.get('name')
    display_name = request.form.get('display_name')
    description = request.form.get('description')
    feature_ids = request.form.getlist('feature_ids', type=int)

    if not name or not display_name:
        return jsonify({'success': False, 'message': '角色名称和显示名称不能为空'})

    # 检查角色名称是否已存在
    existing_role = Role.query.filter_by(name=name).first()
    if existing_role:
        return jsonify({'success': False, 'message': '角色名称已存在'})

    try:
        # 创建新角色
        role = Role(
            name=name,
            display_name=display_name,
            description=description
        )
        db.session.add(role)
        db.session.flush()  # 获取新角色的ID

        # 关联系统功能
        for feature_id in feature_ids:
            role_feature = RoleSystemFeature(
                role_id=role.id,
                system_feature_id=feature_id
            )
            db.session.add(role_feature)

        db.session.commit()
        return jsonify({'success': True, 'message': '角色添加成功'})
    except Exception as e:
        db.session.rollback()
        # 记录错误日志
        print(f"添加角色时出错: {str(e)}")
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})

@roles_bp.route('/roles/edit/<int:role_id>', methods=['POST'])
def edit_role(role_id):
    # 检查权限
    is_admin = check_user_role(session.get('user_id'), 'admin')
    if not is_admin:
        return jsonify({'success': False, 'message': '权限不足'})

    role = db.session.get(Role, role_id)
    if not role:
        return jsonify({'success': False, 'message': '角色不存在'})

    name = request.form.get('name')
    display_name = request.form.get('display_name')
    description = request.form.get('description')
    feature_ids = request.form.getlist('feature_ids', type=int)

    if not name or not display_name:
        return jsonify({'success': False, 'message': '角色名称和显示名称不能为空'})

    # 检查角色名称是否已存在（排除自己）
    existing_role = Role.query.filter(Role.name == name, Role.id != role_id).first()
    if existing_role:
        return jsonify({'success': False, 'message': '角色名称已存在'})

    try:
        # 更新角色信息
        role.name = name
        role.display_name = display_name
        role.description = description

        # 删除原有的角色功能关联
        RoleSystemFeature.query.filter_by(role_id=role_id).delete()

        # 创建新的角色功能关联
        for feature_id in feature_ids:
            role_feature = RoleSystemFeature(
                role_id=role.id,
                system_feature_id=feature_id
            )
            db.session.add(role_feature)

        db.session.commit()
        return jsonify({'success': True, 'message': '角色更新成功'})
    except Exception as e:
        db.session.rollback()
        # 记录错误日志
        print(f"更新角色时出错: {str(e)}")
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@roles_bp.route('/roles/delete/<int:role_id>', methods=['POST'])
def delete_role(role_id):
    # 检查权限
    is_admin = check_user_role(session.get('user_id'), 'admin')
    if not is_admin:
        return jsonify({'success': False, 'message': '权限不足'})

    role = db.session.get(Role, role_id)
    if not role:
        return jsonify({'success': False, 'message': '角色不存在'})

    # 检查是否有用户关联到该角色
    user_roles = role.user_roles
    if user_roles:
        return jsonify({'success': False, 'message': '该角色已分配给用户，无法删除'})

    try:
        # 删除角色功能关联
        RoleSystemFeature.query.filter_by(role_id=role_id).delete()

        # 删除角色
        db.session.delete(role)
        db.session.commit()
        return jsonify({'success': True, 'message': '角色删除成功'})
    except Exception as e:
        db.session.rollback()
        # 记录错误日志
        print(f"删除角色时出错: {str(e)}")
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@roles_bp.route('/roles/get/<int:role_id>')
def get_role(role_id):
    # 检查权限
    if not check_system_feature_access(session, 'roles.roles'):
        return jsonify({'success': False, 'message': '权限不足'})

    try:
        role = db.session.get(Role, role_id)
        if not role:
            return jsonify({'success': False, 'message': '角色不存在'})

        # 获取角色关联的系统功能
        role_features = RoleSystemFeature.query.filter_by(role_id=role_id).all()
        system_feature_ids = [rf.system_feature_id for rf in role_features]

        role_data = {
            'id': role.id,
            'name': role.name,
            'display_name': role.display_name,
            'description': role.description,
            'system_feature_ids': system_feature_ids
        }

        return jsonify({'success': True, 'role': role_data})
    except Exception as e:
        # 记录错误日志
        print(f"获取角色详情时出错: {str(e)}")
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'}), 500

