from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, SystemFeature
from utils import check_system_feature_access
from decorators import check_access_blueprint

system_features_bp = Blueprint('system_features', __name__)

# 应用权限检查装饰器
@system_features_bp.before_request
@check_access_blueprint('system_features')
def check_access():
    pass  # 装饰器会处理权限检查逻辑

@system_features_bp.route('/system_features')
def system_features():
    # 检查权限
    if not check_system_feature_access(session, 'system_features.system_features'):
        return redirect(url_for('auth.index'))
    
    # 获取所有系统功能，按order_num排序
    system_features = SystemFeature.query.order_by(SystemFeature.order_num).all()
    return render_template('system_features.html', system_features=system_features)

@system_features_bp.route('/system_features/init')
def init_system_features():
    # 检查权限
    if not check_system_feature_access(session, 'system_features.system_features'):
        return redirect(url_for('auth.index'))
    # 检查是否已初始化
    existing_features = SystemFeature.query.count()
    if existing_features > 0:
        flash('系统功能已初始化，无需重复操作！', 'warning')
        return redirect(url_for('system_features.system_features'))
    
    # 定义系统功能列表
    features_data = [
        {
            'name': '用户管理',
            'description': '管理系统用户',
            'route_name': 'users.users',
            'order_num': 1
        },
        {
            'name': '功能点管理',
            'description': '管理系统功能点',
            'route_name': 'features.features',
            'order_num': 2
        },
        {
            'name': '用户故事管理',
            'description': '管理系统用户故事',
            'route_name': 'user_stories.user_stories',
            'order_num': 3
        },
        {
            'name': '估算历史',
            'description': '查看估算历史记录',
            'route_name': 'admin.history',
            'order_num': 4
        },
        {
            'name': '迭代管理',
            'description': '管理系统迭代',
            'route_name': 'sprints.sprints',
            'order_num': 5
        },
        {
            'name': '敏捷知识',
            'description': '查看敏捷开发知识',
            'route_name': 'knowledge.knowledge_view',
            'order_num': 6
        },
        {
            'name': '知识管理',
            'description': '管理敏捷开发知识',
            'route_name': 'knowledge.manage',
            'order_num': 7
        },
        {
            'name': '项目信息管理',
            'description': '管理系统项目信息',
            'route_name': 'projects.projects',
            'order_num': 8
        },
        {
            'name': '任务管理',
            'description': '管理系统任务',
            'route_name': 'tasks.tasks',
            'order_num': 9
        }
    ]
    
    # 创建系统功能记录
    for feature_data in features_data:
        feature = SystemFeature(
            name=feature_data['name'],
            description=feature_data['description'],
            route_name=feature_data['route_name'],
            order_num=feature_data['order_num'],
            is_enabled=True,
            is_public=False
        )
        db.session.add(feature)
    
    db.session.commit()
    flash('系统功能初始化成功！', 'success')
    return redirect(url_for('system_features.system_features'))

@system_features_bp.route('/system_features/update', methods=['POST'])
def update_system_features():
    # 检查权限
    if not check_system_feature_access(session, 'system_features.system_features'):
        return redirect(url_for('auth.index'))
    
    # 获取所有可能的系统功能ID（通过表单中的字段名）
    updated_features = set()
    for key in request.form.keys():
        if key.startswith('description_'):
            feature_id = int(key.split('_', 1)[1])  # 使用split('_', 1)只分割第一个下划线
            updated_features.add(feature_id)
        elif key.startswith('is_enabled_'):
            feature_id = int(key.split('_', 2)[2])  # 分割前两个下划线，取第三部分
            updated_features.add(feature_id)
        elif key.startswith('is_public_'):
            feature_id = int(key.split('_', 2)[2])  # 分割前两个下划线，取第三部分
            updated_features.add(feature_id)

    # 只更新有变化的系统功能
    for feature_id in updated_features:
        feature = db.session.get(SystemFeature, feature_id)
        if feature:
            # 获取表单数据
            description_key = f'description_{feature_id}'
            is_enabled_key = f'is_enabled_{feature_id}'
            is_public_key = f'is_public_{feature_id}'

            if description_key in request.form:
                feature.description = request.form[description_key]
            if is_enabled_key in request.form:
                feature.is_enabled = request.form[is_enabled_key] == 'on'
            if is_public_key in request.form:
                feature.is_public = request.form[is_public_key] == 'on'

    db.session.commit()
    flash('系统功能更新成功！', 'success')
    return redirect(url_for('system_features.system_features'))


