from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models import db, User, Task, Sprint, UserRole, Role
from utils import check_system_feature_access, check_user_role
from datetime import datetime, timedelta

todos_bp = Blueprint('todos', __name__)

@todos_bp.before_request
def check_access():
    # 确保用户已登录
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

@todos_bp.route('/my_todos')
def my_todos():
    """我的待办事项页面"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if not user:
        return redirect(url_for('auth.index'))

    return render_template('my_todos.html', user=user)

@todos_bp.route('/api/my_todos')
def api_my_todos():
    """获取我的待办事项API"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if not user:
        return jsonify({'success': False, 'message': '用户未登录'})

    todos = get_user_todos(user_id)

    return jsonify({
        'success': True,
        'todos': todos,
        'count': len(todos)
    })

def get_user_todos(user_id):
    """获取用户待办事项"""
    todos = []
    user = User.query.get(user_id)

    if not user:
        return todos

    # 获取用户角色
    user_roles = UserRole.query.filter_by(user_id=user_id).all()
    role_ids = [ur.role_id for ur in user_roles]
    roles = Role.query.filter(Role.id.in_(role_ids)).all()
    role_names = [role.name for role in roles]

    # 1. 开发团队成员相关待办 - 即将到期或已逾期的任务
    if any(role in role_names for role in ['developer', 'admin']):
        pending_tasks = get_pending_tasks(user_id)
        todos.extend(pending_tasks)

    # 4. 开发团队成员相关待办 - 待处理的缺陷
    if any(role in role_names for role in ['developer', 'admin', 'QA']):
        pending_defects = get_pending_defects(user_id)
        todos.extend(pending_defects)

    # 2. Scrum Master相关待办 - 迭代状态提醒
    if any(role in role_names for role in ['scrum_master', 'admin']):
        sprint_alerts = get_sprint_alerts(user_id)
        todos.extend(sprint_alerts)

    # 3. 系统管理员相关待办 - 未分配角色的用户
    if 'admin' in role_names:
        user_alerts = get_user_alerts()
        todos.extend(user_alerts)

    # 5. 测试人员相关待办 - 待验证的缺陷
    if any(role in role_names for role in ['QA', 'admin']):
        verify_defects = get_verify_defects(user_id)
        todos.extend(verify_defects)

    return todos

def get_pending_tasks(user_id):
    """获取用户即将到期或已逾期的任务"""
    todos = []

    # 获取分配给用户且未完成的任务
    pending_tasks = Task.query.filter(
        Task.assignee_id == user_id,
        Task.status != '已完成'
    ).all()

    today = datetime.now().date()

    for task in pending_tasks:
        # 检查是否已逾期
        if task.end_date and task.end_date < today:
            todos.append({
                'id': f"task_overdue_{task.id}",
                'type': 'task',
                'priority': 'high',
                'title': f'任务已逾期: {task.name}',
                'description': f'任务"{task.name}"应于{task.end_date}完成，现已逾期',
                'due_date': task.end_date.strftime('%Y-%m-%d') if task.end_date else '',
                'related_id': task.id,
                'action_url': f"/tasks/edit/{task.id}"
            })
        # 检查是否即将到期 (1天内)
        elif task.end_date and task.end_date <= today + timedelta(days=1):
            todos.append({
                'id': f"task_due_soon_{task.id}",
                'type': 'task',
                'priority': 'medium' if task.end_date > today else 'high',
                'title': f'任务即将到期: {task.name}',
                'description': f'任务"{task.name}"需要在{task.end_date}前完成',
                'due_date': task.end_date.strftime('%Y-%m-%d') if task.end_date else '',
                'related_id': task.id,
                'action_url': f"/tasks/edit/{task.id}"
            })

    return todos

def get_sprint_alerts(user_id):
    """获取Scrum Master的迭代提醒"""
    todos = []

    # 获取用户负责的迭代（作为Scrum Master）
    sprints = Sprint.query.filter(
        Sprint.scrum_master_id == user_id
    ).all()

    today = datetime.now().date()

    for sprint in sprints:
        # 检查即将开始但状态不是"进行中"的迭代 (1天内开始)
        if sprint.start_date and sprint.start_date <= today + timedelta(days=1) and \
           sprint.start_date >= today and sprint.status != '进行中':
            todos.append({
                'id': f"sprint_starting_{sprint.id}",
                'type': 'sprint',
                'priority': 'medium',
                'title': f'迭代即将开始: {sprint.name}',
                'description': f'迭代"{sprint.name}"将于{sprint.start_date}开始，请更新状态',
                'due_date': sprint.start_date.strftime('%Y-%m-%d'),
                'related_id': sprint.id,
                'action_url': f"/sprints/edit/{sprint.id}"
            })

        # 检查已结束但状态不是"已完成"的迭代
        if sprint.end_date and sprint.end_date < today and sprint.status != '已完成':
            todos.append({
                'id': f"sprint_ended_{sprint.id}",
                'type': 'sprint',
                'priority': 'high',
                'title': f'迭代已结束: {sprint.name}',
                'description': f'迭代"{sprint.name}"已于{sprint.end_date}结束，请更新状态',
                'due_date': sprint.end_date.strftime('%Y-%m-%d'),
                'related_id': sprint.id,
                'action_url': f"/sprints/edit/{sprint.id}"
            })

    return todos

def get_user_alerts():
    """获取未分配角色的用户提醒"""
    todos = []

    # 获取所有用户
    users = User.query.all()

    for user in users:
        # 检查用户是否未分配角色
        user_roles = UserRole.query.filter_by(user_id=user.id).all()
        if not user_roles:
            todos.append({
                'id': f"user_no_role_{user.id}",
                'type': 'user',
                'priority': 'low',
                'title': f'用户未分配角色: {user.name}',
                'description': f'用户"{user.name}"尚未分配任何角色',
                'due_date': '',
                'related_id': user.id,
                'action_url': f"/users/{user.id}/assign_roles"
            })

    return todos


def get_pending_defects(user_id):
    """获取分配给用户的待处理缺陷"""
    todos = []

    from models import Defect

    # 获取分配给用户且状态为"待处理"的缺陷
    pending_defects = Defect.query.filter(
        Defect.resolver_id == user_id,
        Defect.status == '待处理'
    ).all()

    for defect in pending_defects:
        todos.append({
            'id': f"defect_pending_{defect.id}",
            'type': 'defect',
            'priority': 'high',
            'title': f'待处理缺陷: {defect.title}',
            'description': f'缺陷"{defect.title}"需要您处理，请及时查看',
            'due_date': '',
            'related_id': defect.id,
            'action_url': f"/defects/edit/{defect.id}"
        })

    return todos


def get_verify_defects(user_id):
    """获取需要测试人员验证的已修复缺陷"""
    todos = []

    from models import Defect

    # 获取状态为"已修复"且分配给当前测试人员验证的缺陷
    verify_defects = Defect.query.filter(
        Defect.assignee_id == user_id,
        Defect.status == '已修复'
    ).all()

    for defect in verify_defects:
        todos.append({
            'id': f"defect_verify_{defect.id}",
            'type': 'defect',
            'priority': 'medium',
            'title': f'待验证缺陷: {defect.title}',
            'description': f'您修复的缺陷"{defect.title}"已标记为已修复，请等待测试人员验证',
            'due_date': '',
            'related_id': defect.id,
            'action_url': f"/defects/edit/{defect.id}"
        })

    return todos