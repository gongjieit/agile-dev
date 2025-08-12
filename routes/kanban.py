from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from models import db, Task, UserStory, User, Sprint, SprintBacklog, ProjectInfo
from utils import check_system_feature_access
from decorators import check_access_blueprint
from datetime import datetime, timedelta

kanban_bp = Blueprint('kanban', __name__)

# 应用权限检查装饰器
@kanban_bp.before_request
@check_access_blueprint('kanban')
def check_access():
    pass  # 路由权限由装饰器处理

@kanban_bp.route('/kanban')
def kanban():
    """看板页面"""
    # 检查权限
    if not check_system_feature_access(session, 'kanban.kanban'):
        return redirect(url_for('auth.index'))

    # 获取所有迭代
    sprints = Sprint.query.order_by(Sprint.start_date.desc()).all()

    return render_template('kanban.html', sprints=sprints)

@kanban_bp.route('/get_kanban_data/<int:sprint_id>')
def get_kanban_data(sprint_id):
    """获取看板数据"""
    # 检查权限
    if not check_system_feature_access(session, 'kanban.kanban'):
        return jsonify({'success': False, 'message': '权限不足'})

    try:
        # 获取迭代
        sprint = db.session.get(Sprint, sprint_id)
        if not sprint:
            return jsonify({'success': False, 'message': '迭代不存在'})

        # 获取项目信息（通过迭代关联的用户故事）
        project_info = None
        sprint_backlogs = SprintBacklog.query.filter_by(sprint_id=sprint_id).all()
        story_ids = [backlog.user_story_id for backlog in sprint_backlogs]

        if story_ids:
            # 获取用户故事及关联的项目信息
            user_story = UserStory.query.filter(UserStory.id.in_(story_ids)).first()
            # 通过产品待办列表获取项目信息
            if user_story and user_story.product_backlog:
                project_module = user_story.product_backlog.project_module
                project = user_story.product_backlog.project

                # 优先使用功能模块的路径信息
                if project_module and project_module.path:
                    # 从项目模块的路径中提取项目信息
                    path_parts = project_module.path.split('/')
                    if len(path_parts) >= 2:
                        # 获取根项目节点（第一个路径段对应根项目）
                        root_project = ProjectInfo.query.filter_by(name=path_parts[1], parent_id=None).first()
                        if root_project:
                            project_info = {
                                'name': root_project.name,
                                'short_name': root_project.short_name or ''
                            }
                # 如果没有功能模块，则使用项目信息
                elif project:
                    project_info = {
                        'name': project.name,
                        'short_name': project.short_name or ''
                    }


        # 定义看板列（状态）
        columns = [
            {'status': '未开始', 'name': '待处理'},
            {'status': '进行中', 'name': '进行中'},
            {'status': '已完成', 'name': '已完成'}
        ]

        # 获取这些用户故事下的所有任务
        tasks = Task.query.filter(Task.user_story_id.in_(story_ids)).all()

        # 获取用户故事信息
        user_stories = UserStory.query.filter(UserStory.id.in_(story_ids)).all()
        story_dict = {story.id: story for story in user_stories}

        # 获取用户信息
        user_ids = [task.assignee_id for task in tasks if task.assignee_id]
        users = User.query.filter(User.id.in_(user_ids)).all()
        user_dict = {user.id: user for user in users}

        # 转换任务为字典格式
        tasks_data = []
        for task in tasks:
            story = story_dict.get(task.user_story_id)
            tasks_data.append({
                'id': task.id,
                'task_id': task.task_id or '',
                'name': task.name,
                'description': task.description or '',
                'status': task.status,
                'task_type': task.task_type or '',
                'priority': task.priority,
                'assignee_name': user_dict[task.assignee_id].name if task.assignee_id and task.assignee_id in user_dict else '',
                'assignee_id': task.assignee_id,
                'start_date': task.start_date.strftime('%Y-%m-%d') if task.start_date else '',
                'end_date': task.end_date.strftime('%Y-%m-%d') if task.end_date else '',
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else '',
                'story_title': story.title if story else '',
                'story_id': story.story_id if story else ''
            })

        # 计算燃尽图数据
        burndown_data = calculate_burndown_data(sprint, sprint_backlogs)

        # 迭代信息
        sprint_info = {
            'id': sprint.id,
            'name': sprint.name,
            'start_date': sprint.start_date.strftime('%Y-%m-%d') if sprint.start_date else '',
            'end_date': sprint.end_date.strftime('%Y-%m-%d') if sprint.end_date else '',
            'status': sprint.status,
            'product_owner': sprint.product_owner.name if sprint.product_owner else '',
            'scrum_master': sprint.scrum_master.name if sprint.scrum_master else ''
        }

        # 获取所有用户用于任务分配
        all_users = User.query.all()
        users_data = [{'id': user.id, 'name': user.name} for user in all_users]

        return jsonify({
            'success': True,
            'columns': columns,
            'tasks': tasks_data,
            'burndown_data': burndown_data,
            'sprint_info': sprint_info,
            'project_info': project_info,
            'sprint_id': sprint_id,
            'users': users_data
        })
    except Exception as e:
        # 捕获所有异常并返回错误信息
        import traceback
        traceback.print_exc()  # 打印错误堆栈信息，方便调试
        return jsonify({'success': False, 'message': f'服务器内部错误: {str(e)}'})


def calculate_burndown_data(sprint, sprint_backlogs):
    """计算燃尽图数据"""
    if not sprint.start_date or not sprint.end_date:
        return []

    # 计算总故事点数
    total_points = sum(backlog.story_points or 0 for backlog in sprint_backlogs)

    # 生成日期范围
    start_date = sprint.start_date
    end_date = sprint.end_date
    date_range = []

    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date)
        current_date += timedelta(days=1)

    # 计算理想燃尽线数据
    ideal_points = []
    days_total = (end_date - start_date).days + 1
    for i, date in enumerate(date_range):
        ideal_points.append(total_points * (days_total - i) / days_total)

    # 计算实际剩余故事点数（基于任务完成历史）
    remaining_points = []

    # 获取所有相关的用户故事ID
    story_ids = [backlog.user_story_id for backlog in sprint_backlogs]

    # 获取这些用户故事下的所有任务
    from models import Task
    tasks = Task.query.filter(Task.user_story_id.in_(story_ids)).all()

    # 为每个用户故事计算总任务数
    story_task_count = {}
    for task in tasks:
        story_id = task.user_story_id
        if story_id not in story_task_count:
            story_task_count[story_id] = 0
        story_task_count[story_id] += 1

    # 计算每天的剩余故事点数
    for i, date in enumerate(date_range):
        remaining_points_today = total_points

        # 按用户故事分组任务
        tasks_by_story = {}
        for task in tasks:
            story_id = task.user_story_id
            if story_id not in tasks_by_story:
                tasks_by_story[story_id] = []
            tasks_by_story[story_id].append(task)

        # 遍历每个用户故事
        for backlog in sprint_backlogs:
            story_id = backlog.user_story_id
            story_points = backlog.story_points or 0

            # 如果该用户故事没有任务，跳过
            if story_id not in tasks_by_story:
                continue

            story_tasks = tasks_by_story[story_id]
            total_story_tasks = len(story_tasks)

            # 计算在当前日期前完成的任务数
            completed_tasks_count = 0
            for task in story_tasks:
                if (task.status == '已完成' and
                    task.completed_at and
                    task.completed_at.date() <= date):
                    completed_tasks_count += 1

            # 如果该用户故事的所有任务都已完成，则减去全部故事点
            if total_story_tasks > 0 and completed_tasks_count == total_story_tasks:
                remaining_points_today -= story_points
            # 否则按完成的任务比例减去部分故事点
            elif total_story_tasks > 0:
                completed_ratio = completed_tasks_count / total_story_tasks
                remaining_points_today -= story_points * completed_ratio

        # 确保不会出现负数
        remaining_points_today = max(0, remaining_points_today)
        remaining_points.append(remaining_points_today)

    # 构造燃尽图数据
    burndown_data = []
    for i, date in enumerate(date_range):
        burndown_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'remaining_points': round(remaining_points[i], 2) if i < len(remaining_points) else 0,
            'ideal_points': round(ideal_points[i], 2) if i < len(ideal_points) else 0
        })

    return burndown_data


@kanban_bp.route('/get_task_detail/<int:task_id>')
def get_task_detail(task_id):
    """获取任务详情"""
    # 检查权限
    if not check_system_feature_access(session, 'kanban.kanban'):
        return jsonify({'success': False, 'message': '权限不足'})

    # 获取任务
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({'success': False, 'message': '任务不存在'})

    # 获取用户故事信息
    user_story = task.user_story

    # 获取负责人信息
    assignee = task.assignee if task.assignee_id else None

    # 转换任务为字典格式
    task_data = {
        'id': task.id,
        'task_id': task.task_id or '',
        'name': task.name,
        'description': task.description or '',
        'status': task.status,
        'task_type': task.task_type or '',
        'priority': task.priority,
        'assignee_name': assignee.name if assignee else '',
        'assignee_id': task.assignee_id,
        'start_date': task.start_date.strftime('%Y-%m-%d') if task.start_date else '',
        'end_date': task.end_date.strftime('%Y-%m-%d') if task.end_date else '',
        'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else '',
        'story_title': user_story.title if user_story else '',
        'story_id': user_story.story_id if user_story else ''
    }

    return jsonify({
        'success': True,
        'task': task_data
    })
