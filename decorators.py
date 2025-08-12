from functools import wraps
from flask import request, session, redirect, url_for
from models import SystemFeature
from utils import check_user_role, check_system_feature_access


def check_access_blueprint(route_prefix):
    """
    为蓝图创建权限检查装饰器
    :param route_prefix: 蓝图的路由前缀，如 'sprints', 'knowledge' 等
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 排除静态文件路由
            if request.endpoint and not request.endpoint.startswith('static'):
                # 检查当前请求的路由是否需要权限控制
                endpoint = request.endpoint
                if endpoint and endpoint.startswith(route_prefix):
                    # 特殊处理sprints蓝图，所有端点都使用sprints.sprints作为路由名称
                    if route_prefix == 'sprints':
                        route_name = 'sprints.sprints'
                    elif route_prefix == 'kanban':
                        route_name = 'kanban.kanban'
                    elif route_prefix == 'tasks':
                        route_name = 'tasks.tasks'
                    elif route_prefix == 'user_stories':
                        route_name = 'user_stories.user_stories'
                    elif route_prefix == 'product_backlog':
                        route_name = 'product_backlog.product_backlog'
                    elif route_prefix == 'test_cases':
                        route_name = 'test_cases.test_cases'
                    elif route_prefix == 'projects' and endpoint == 'projects.get_project_modules':
                        # 允许特定的项目模块获取接口通过权限检查
                        # 这个接口可以被有产品待办列表或用户故事权限的用户访问
                        route_name = 'projects.projects'
                    else:
                        # 对于knowledge蓝图和其他蓝图，直接使用端点名称转换为路由名称
                        # 将 'knowledge.knowledge_view' 转换为 'knowledge.knowledge_view'
                        if '.' in endpoint:
                            # 如果endpoint已经包含蓝图前缀，则直接使用
                            route_name = endpoint
                        else:
                            # 否则按原有逻辑转换
                            route_name = endpoint.replace('_', '.', 1)
                            if not route_name.startswith(f'{route_prefix}.'):
                                # 如果转换后不符合预期格式，则使用基础路由名称
                                route_name = f'{route_prefix}.{route_prefix}'

                    # 使用 utils 中的 check_system_feature_access 函数来检查权限
                    if not check_system_feature_access(session, route_name):
                        return redirect(url_for('auth.index'))
            return func(*args, **kwargs)
        return wrapper
    return decorator
