from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, User, Estimate, SystemFeature, UserRole, Role
from decorators import check_access_blueprint
from utils import check_user_role

users_bp = Blueprint('users', __name__, url_prefix='/users')

# 应用权限检查装饰器
@users_bp.before_request
@check_access_blueprint('users')
def check_access():
    pass  # 装饰器会处理权限检查逻辑


@users_bp.route('/')
def users():
    users = User.query.all()
    roles = Role.query.all()

    # 为每个用户获取角色
    for user in users:
        user_roles = UserRole.query.filter_by(user_id=user.id).all()
        user.role_ids = [ur.role_id for ur in user_roles]
        user.role_names = [ur.role.display_name for ur in user_roles]

    return render_template('users.html', users=users, roles=roles)

@users_bp.route('/set_admin/<int:user_id>', methods=['POST'])
def set_admin(user_id):
    # 检查用户是否为管理员
    is_admin = check_user_role(session.get('user_id'), 'admin')
    if not is_admin:
        return redirect(url_for('auth.index'))
    user = db.session.get(User, user_id)
    if user:
        # 检查用户是否已经有admin角色
        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role:
            # 检查用户是否已经有admin角色
            user_role = UserRole.query.filter_by(user_id=user_id, role_id=admin_role.id).first()
            if not user_role:
                # 给用户添加admin角色
                user_role = UserRole(user_id=user_id, role_id=admin_role.id)
                db.session.add(user_role)
                db.session.commit()
    return redirect(url_for('users.users'))

@users_bp.route('/unset_admin/<int:user_id>', methods=['POST'])
def unset_admin(user_id):
    # 检查用户是否为管理员
    is_admin = check_user_role(session.get('user_id'), 'admin')
    if not is_admin:
        return redirect(url_for('auth.index'))
    user = db.session.get(User, user_id)
    if user:
        # 移除用户的admin角色
        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role:
            user_role = UserRole.query.filter_by(user_id=user_id, role_id=admin_role.id).first()
            if user_role:
                db.session.delete(user_role)
                db.session.commit()
    return redirect(url_for('users.users'))


@users_bp.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    # 检查用户是否为管理员
    is_admin = check_user_role(session.get('user_id'), 'admin')
    if not is_admin:
        return redirect(url_for('auth.index'))

    user = db.session.get(User, user_id)
    if user and user.id != session['user_id']:
        # 删除用户前，先删除其相关的估算记录
        Estimate.query.filter_by(user_id=user.id).delete()

        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('users.users'))


@users_bp.route('/assign_roles/<int:user_id>', methods=['POST'])
def assign_roles(user_id):
    # 检查用户是否为管理员
    is_admin = check_user_role(session.get('user_id'), 'admin')
    if not is_admin:
        return jsonify({'success': False, 'message': '权限不足'})

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'})

    role_ids = request.form.getlist('role_ids', type=int)

    try:
        # 删除用户现有的角色关联
        UserRole.query.filter_by(user_id=user_id).delete()

        # 添加新的角色关联
        for role_id in role_ids:
            user_role = UserRole(
                user_id=user_id,
                role_id=role_id
            )
            db.session.add(user_role)

        db.session.commit()
        return jsonify({'success': True, 'message': '角色分配成功'})
    except Exception as e:
        db.session.rollback()
        print(f"分配角色时出错: {str(e)}")  # 记录错误日志
        return jsonify({'success': False, 'message': f'分配失败: {str(e)}'})

@users_bp.route('/get_roles/<int:user_id>')
def get_user_roles(user_id):
    # 检查用户是否为管理员
    is_admin = check_user_role(session.get('user_id'), 'admin')
    if not is_admin:
        return jsonify({'success': False, 'message': '权限不足'})

    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'})

        # 获取用户的角色
        user_roles = UserRole.query.filter_by(user_id=user_id).all()
        role_ids = [ur.role_id for ur in user_roles]

        return jsonify({'success': True, 'role_ids': role_ids})
    except Exception as e:
        print(f"获取用户角色时出错: {str(e)}")  # 记录错误日志
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'}), 500
