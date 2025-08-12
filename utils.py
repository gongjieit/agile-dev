from models import SystemFeature, User, UserRole, RoleSystemFeature, Role, db


def check_system_feature_access(session, route_name):
    """检查用户是否有访问特定系统功能的权限"""
    # 检查用户是否具有访问该功能的角色
    user_id = session.get('user_id')
    if user_id:
        # 检查用户是否是管理员
        if check_user_role(user_id, 'admin'):
            return True

        # 获取用户的角色
        user_roles = UserRole.query.filter_by(user_id=user_id).all()
        role_ids = [ur.role_id for ur in user_roles]

        # 检查这些角色是否具有访问该功能的权限
        if role_ids:
            # 获取与这些角色关联的系统功能
            role_features = RoleSystemFeature.query.filter(
                RoleSystemFeature.role_id.in_(role_ids),
                RoleSystemFeature.system_feature_id.in_(
                    db.session.query(SystemFeature.id).filter_by(route_name=route_name)
                )
            ).first()

            if role_features:
                return True

    # 检查系统功能是否公开（无需登录即可访问）
    system_feature = SystemFeature.query.filter_by(route_name=route_name).first()
    if system_feature and system_feature.is_enabled and system_feature.is_public:
        return True

    return False

def get_user_roles(user_id):
    """获取用户的所有角色"""
    user_roles = UserRole.query.filter_by(user_id=user_id).all()
    return [ur.role for ur in user_roles]

def check_user_role(user_id, role_name):
    """检查用户是否具有特定角色"""
    user_roles = UserRole.query.join(Role).filter(
        UserRole.user_id == user_id,
        Role.name == role_name
    ).first()

    return user_roles is not None
