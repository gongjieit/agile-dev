from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, Task, UserStory, User, Sprint, SprintBacklog, ProjectInfo
from utils import check_system_feature_access
from decorators import check_access_blueprint
from datetime import datetime, timedelta
from sqlalchemy import or_
import re

tasks_bp = Blueprint('tasks', __name__)

def generate_task_id(story_id):
    """
    生成任务编号
    规则：TA_[故事编号]_[3位序号]
    例如：如果故事是US_001_001，则任务编号为TA_US_001_001_001
    """
    # 从故事编号中提取序号部分
    if story_id and story_id.startswith('US_'):
        # 查询当前故事下最大的任务序号
        story = UserStory.query.filter_by(story_id=story_id).first() if story_id else None
        if story:
            tasks = Task.query.filter_by(user_story_id=story.id).all()
            if tasks:
                max_seq = 0
                for task in tasks:
                    if task.task_id and task.task_id.startswith(f"TA_{story_id}_"):
                        try:
                            # 提取序号部分（最后3位）
                            seq_part = task.task_id.split('_')[-1]
                            seq = int(seq_part)
                            if seq > max_seq:
                                max_seq = seq
                        except (IndexError, ValueError):
                            pass
                next_seq = max_seq + 1
            else:
                next_seq = 1
        else:
            next_seq = 1

        # 序号保持3位长度，不够前面补零
        seq_part = str(next_seq).zfill(3)
        task_id = f"TA_{story_id}_{seq_part}"
        return task_id

    # 如果无法从故事编号中提取，则使用默认方式
    # 查询当前故事下最大的任务序号
    story = UserStory.query.filter_by(story_id=story_id).first() if story_id else None
    if story:
        tasks = Task.query.filter_by(user_story_id=story.id).all()
        if tasks:
            max_seq = 0
            for task in tasks:
                if task.task_id and re.match(r'^TA_\d+$', task.task_id):
                    try:
                        seq = int(task.task_id.split('_')[-1])  # 获取最后的序号部分
                        if seq > max_seq:
                            max_seq = seq
                    except ValueError:
                        pass
            next_seq = max_seq + 1
        else:
            next_seq = 1
    else:
        next_seq = 1

    # 生成任务编号
    task_id = f"TA_{next_seq:03d}"
    return task_id


# 应用权限检查装饰器
@tasks_bp.before_request
@check_access_blueprint('tasks')
def check_access():
    # 排除API端点，这些端点有独立的权限检查
    excluded_endpoints = [
        'tasks.get_stories_by_sprint', 
        'tasks.get_tasks_by_story'
    ]
    if request.endpoint in excluded_endpoints:
        return None  # 跳过蓝图级权限检查
    pass  # 其他路由由装饰器处理权限检查逻辑

@tasks_bp.route('/tasks')
def tasks():
    # 检查权限
    if not check_system_feature_access(session, 'tasks.tasks'):
        return redirect(url_for('auth.index'))
    
    # 获取所有迭代
    sprints = Sprint.query.order_by(Sprint.start_date.desc()).all()

    # 获取所有用户用于任务分配
    users = User.query.all()
    
    return render_template('tasks.html', sprints=sprints, users=users)

@tasks_bp.route('/get_stories_by_sprint/<int:sprint_id>')
def get_stories_by_sprint(sprint_id):
    """根据迭代ID获取关联的用户故事"""
    # 检查权限
    if not check_system_feature_access(session, 'tasks.tasks'):
        return jsonify({'success': False, 'message': '权限不足'})
    
    # 获取迭代
    sprint = db.session.get(Sprint, sprint_id)
    if not sprint:
        return jsonify({'success': False, 'message': '迭代不存在'})
    
    # 通过SprintBacklog表关联获取迭代关联的用户故事
    sprint_backlogs = SprintBacklog.query.filter_by(sprint_id=sprint_id).all()
    story_ids = [backlog.user_story_id for backlog in sprint_backlogs]

    # 通过SprintBacklog表获取到用户故事，按优先级排序
    # 优先级排序规则: P0 > P1 > P2 > P3 > P4 > P5
    priority_order = {
        'P0': 0,
        'P1': 1,
        'P2': 2,
        'P3': 3,
        'P4': 4,
        'P5': 5
    }

    user_stories = UserStory.query.filter(UserStory.id.in_(story_ids)).all()

    # 按优先级排序
    user_stories.sort(key=lambda story: priority_order.get(
        next((backlog.priority for backlog in sprint_backlogs if backlog.user_story_id == story.id), story.priority),
        999  # 如果没有找到优先级，放在最后
    ))

    # 获取每个用户故事的任务数和状态分布
    from models import Task
    task_stats = {}
    if story_ids:
        # 使用SQL查询获取每个故事的任务数和状态分布
        task_status_results = db.session.query(
            Task.user_story_id,
            Task.status,
            db.func.count(Task.id).label('count')
        ).filter(Task.user_story_id.in_(story_ids)).group_by(Task.user_story_id, Task.status).all()

        # 整理数据结构
        for result in task_status_results:
            story_id = result.user_story_id
            status = result.status
            count = result.count

            if story_id not in task_stats:
                task_stats[story_id] = {'total': 0, '未开始': 0, '进行中': 0, '已完成': 0}

            task_stats[story_id][status] = count
            task_stats[story_id]['total'] += count

    # 转换用户故事为字典格式
    stories_data = []
    # 创建一个从user_story_id到sprint_backlog的映射，以便获取状态和优先级
    backlog_dict = {backlog.user_story_id: backlog for backlog in sprint_backlogs}

    for story in user_stories:
        # 获取对应的sprint_backlog对象
        backlog = backlog_dict.get(story.id)
        # 获取任务统计信息
        story_task_stats = task_stats.get(story.id, {'total': 0, '未开始': 0, '进行中': 0, '已完成': 0})

        stories_data.append({
            'id': story.id,
            'story_id': story.story_id or '',
            'title': story.title,
            'description': story.description or '',
            'status': backlog.status if backlog else '未知',  # 从SprintBacklog获取状态
            'priority': backlog.priority if backlog else story.priority,  # 优先使用backlog的优先级
            'effort': story.effort or '',
            'task_count': story_task_stats['total'],  # 总任务数
            'task_stats': story_task_stats  # 详细任务状态统计
        })

    return jsonify({
        'success': True,
        'user_stories': stories_data,
        'sprint_id': sprint_id
    })

@tasks_bp.route('/get_tasks_by_story/<int:story_id>')
def get_tasks_by_story(story_id):
    """根据用户故事ID获取关联的任务"""
    # 检查权限
    if not check_system_feature_access(session, 'tasks.tasks'):
        return jsonify({'success': False, 'message': '权限不足'})
    
    # 获取用户故事
    user_story = db.session.get(UserStory, story_id)
    if not user_story:
        return jsonify({'success': False, 'message': '用户故事不存在'})
    
    # 获取故事关联的任务
    tasks = Task.query.filter_by(user_story_id=story_id).order_by(Task.created_at.desc()).all()
    
    # 获取所有用户，用于显示负责人信息
    users = User.query.all()
    users_dict = {user.id: user for user in users}
    
    # 转换任务为字典格式
    tasks_data = []
    for task in tasks:
        tasks_data.append({
            'id': task.id,
            'task_id': task.task_id or '',
            'name': task.name,
            'description': task.description or '',
            'status': task.status,
            'task_type': task.task_type or '',
            'priority': task.priority,
            'assignee_name': users_dict[task.assignee_id].name if task.assignee_id and task.assignee_id in users_dict else '',
            'assignee_id': task.assignee_id,
            'start_date': task.start_date.strftime('%Y-%m-%d') if task.start_date else '',
            'end_date': task.end_date.strftime('%Y-%m-%d') if task.end_date else '',
            'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else ''
        })
    
    # 转换用户为字典格式
    users_data = [{'id': user.id, 'name': user.name} for user in users]
    
    return jsonify({
        'success': True,
        'tasks': tasks_data,
        'users': users_data,
        'story_id': story_id
    })

@tasks_bp.route('/add_task/<int:story_id>', methods=['POST'])
def add_task(story_id):
    """为用户故事添加任务"""
    # 检查权限
    if not check_system_feature_access(session, 'tasks.tasks'):
        return jsonify({'success': False, 'message': '权限不足'})
    
    # 获取用户故事
    user_story = db.session.get(UserStory, story_id)
    if not user_story:
        return jsonify({'success': False, 'message': '用户故事不存在'})
    
    # 处理表单提交
    task_id = request.form.get('task_id', '').strip()
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    status = request.form.get('status', '未开始')
    task_type = request.form.get('task_type', '').strip()
    priority = request.form.get('priority', '中')
    assignee_id = request.form.get('assignee_id', '').strip()
    start_date = request.form.get('start_date', '').strip()
    end_date = request.form.get('end_date', '').strip()
    
    # 验证必填字段
    if not name:
        return jsonify({'success': False, 'message': '任务名称不能为空'})

    if not start_date:
        return jsonify({'success': False, 'message': '开始日期不能为空'})

    if not end_date:
        return jsonify({'success': False, 'message': '结束日期不能为空'})

    try:
        # 如果用户没有提供任务编号，则自动生成
        if not task_id:
            task_id = generate_task_id(user_story.story_id)
        
        # 创建任务
        task = Task(
            task_id=task_id,
            user_story_id=story_id,
            name=name,
            description=description if description else None,
            status=status,
            task_type=task_type if task_type else None,
            priority=priority,
            start_date=datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None,
            end_date=datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
        )
        
        # 设置负责人
        if assignee_id:
            try:
                task.assignee_id = int(assignee_id)
            except ValueError:
                pass
        
        db.session.add(task)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '任务添加成功'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'添加任务失败: {str(e)}'})

@tasks_bp.route('/edit_task/<int:task_id>', methods=['POST'])
def edit_task(task_id):
    """编辑任务"""
    # 检查权限
    if not check_system_feature_access(session, 'tasks.tasks'):
        return jsonify({'success': False, 'message': '权限不足'})
    
    # 获取任务
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({'success': False, 'message': '任务不存在'})
    
    # 处理表单提交
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    status = request.form.get('status', task.status)
    task_type = request.form.get('task_type', '').strip()
    priority = request.form.get('priority', task.priority)
    assignee_id = request.form.get('assignee_id', '').strip()
    start_date = request.form.get('start_date', '').strip()
    end_date = request.form.get('end_date', '').strip()
    actual_start_date = request.form.get('actual_start_date', '').strip()
    actual_end_date = request.form.get('actual_end_date', '').strip()

    # 只有在提供了名称且名称不为空时才验证任务名称（允许部分更新）
    is_partial_update = not name  # 如果没有提供名称，则认为是部分更新

    # 验证必填字段（仅在非部分更新时检查）
    if not is_partial_update and not name:
        return jsonify({'success': False, 'message': '任务名称不能为空'})
    
    try:
        old_status = task.status

        # 更新任务（仅在提供了相应字段时更新）
        if name:
            task.name = name
        if description:
            task.description = description if description else None
        if 'status' in request.form:
            task.status = status
        if 'task_type' in request.form:
            task.task_type = task_type if task_type else None
        if priority:
            task.priority = priority
        if 'start_date' in request.form:  # 处理开始日期
            if start_date:  # 如果提供了日期
                task.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            else:  # 如果提供了空字符串，设为None
                task.start_date = None
        if 'end_date' in request.form:  # 处理结束日期
            if end_date:  # 如果提供了日期
                task.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            else:  # 如果提供了空字符串，设为None
                task.end_date = None
        if 'actual_start_date' in request.form:  # 处理实际开始日期
            if actual_start_date:  # 如果提供了日期
                task.actual_start_date = datetime.strptime(actual_start_date, '%Y-%m-%d').date()
            else:  # 如果提供了空字符串，设为None
                task.actual_start_date = None
        if 'actual_end_date' in request.form:  # 处理实际结束日期
            if actual_end_date:  # 如果提供了日期
                task.actual_end_date = datetime.strptime(actual_end_date, '%Y-%m-%d').date()
            else:  # 如果提供了空字符串，设为None
                task.actual_end_date = None

        # 自动更新实际开始时间和实际结束时间
        # 如果状态从未开始变为进行中，且没有设置实际开始时间，则设置为今天
        if 'status' in request.form and old_status == '未开始' and status == '进行中' and task.actual_start_date is None:
            task.actual_start_date = datetime.utcnow().date()
        # 如果状态从进行中变为已完成，且没有设置实际结束时间，则设置为今天
        elif 'status' in request.form and old_status == '进行中' and status == '已完成' and task.actual_end_date is None:
            task.actual_end_date = datetime.utcnow().date()
        # 如果状态从进行中或已完成改回未开始，则清除实际开始时间
        elif 'status' in request.form and (
                old_status == '进行中' or old_status == '已完成') and status == '未开始':
            task.actual_start_date = None
            # 如果是从已完成改回未开始，也清除实际结束时间
            if old_status == '已完成':
                task.actual_end_date = None
        # 如果状态从已完成改回进行中，则清除实际结束时间
        elif 'status' in request.form and old_status == '已完成' and status == '进行中':
            task.actual_end_date = None

        # 如果任务状态变为"已完成"且completed_at为空，则设置completed_at为当前时间
        if 'status' in request.form and status == '已完成' and task.completed_at is None:
            task.completed_at = datetime.utcnow()
        # 如果任务状态从"已完成"改回其他状态，则将completed_at设为None
        elif 'status' in request.form and task.status == '已完成' and status != '已完成':
            task.completed_at = None

        # 设置负责人
        # 只在提供了assignee_id参数时更新负责人
        if 'assignee_id' in request.form:
            if assignee_id:
                try:
                    task.assignee_id = int(assignee_id)
                except ValueError:
                    task.assignee_id = None
            else:
                task.assignee_id = None
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': '任务更新成功'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新任务失败: {str(e)}'})

@tasks_bp.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    """删除任务"""
    # 检查权限
    if not check_system_feature_access(session, 'tasks.tasks'):
        return jsonify({'success': False, 'message': '权限不足'})
    
    # 获取任务
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({'success': False, 'message': '任务不存在'})
    
    try:
        db.session.delete(task)
        db.session.commit()
        return jsonify({'success': True, 'message': '任务删除成功'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除任务失败: {str(e)}'})
