from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
from sqlalchemy import or_
from models import db, User, Sprint, SprintBacklog, UserStory, SystemFeature, ProjectInfo
from utils import check_system_feature_access, check_user_role
from decorators import check_access_blueprint

sprints_bp = Blueprint('sprints', __name__)

# 应用权限检查装饰器，但排除有独立权限检查的路由
@sprints_bp.before_request
@check_access_blueprint('sprints')
def check_access():
    # 添加和编辑迭代有独立的权限检查，不需要蓝图级权限检查
    excluded_endpoints = ['sprints.add_sprint', 'sprints.edit_sprint', 'sprints.sprint_detail']
    if request.endpoint in excluded_endpoints:
        return None  # 跳过蓝图级权限检查
    pass  # 其他路由由装饰器处理权限检查逻辑

@sprints_bp.route('/sprints')
def sprints():
    # 按状态分组获取迭代
    active_sprints = Sprint.query.filter_by(status='进行中').all()
    upcoming_sprints = Sprint.query.filter_by(status='未开始').all()
    completed_sprints = Sprint.query.filter_by(status='已完成').all()

    # 获取所有用户用于下拉选择
    users = User.query.all()

    # 获取所有项目用于下拉选择
    projects = ProjectInfo.query.filter_by(parent_id=None).all()

    return render_template('sprints.html',
                           active_sprints=active_sprints,
                           upcoming_sprints=upcoming_sprints,
                           completed_sprints=completed_sprints,
                           users=users,
                           projects=projects)


@sprints_bp.route('/sprint/add', methods=['POST'])
def add_sprint():
    # 检查权限
    if not check_system_feature_access(session, 'sprints.sprints'):
        return jsonify({'success': False, 'message': '权限不足'})

    name = request.form.get('name')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    project_id = request.form.get('project_id')
    team = request.form.get('team')
    product_owner_id = request.form.get('product_owner_id')
    scrum_master_id = request.form.get('scrum_master_id')

    if name and start_date and end_date:
        sprint = Sprint(
            name=name,
            start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
            end_date=datetime.strptime(end_date, '%Y-%m-%d').date(),
            team=team if team else None,
            product_owner_id=int(product_owner_id) if product_owner_id else None,
            scrum_master_id=int(scrum_master_id) if scrum_master_id else None,
            project_id=int(project_id) if project_id else None
        )
        db.session.add(sprint)
        db.session.commit()
        flash('迭代添加成功！', 'success')
    else:
        flash('请填写所有必填字段！', 'error')

    return redirect(url_for('sprints.sprints'))


@sprints_bp.route('/sprint/edit', methods=['POST'])
def edit_sprint():
    # 检查权限
    if not check_system_feature_access(session, 'sprints.sprints'):
        return redirect(url_for('auth.index'))

    sprint_id = request.form.get('sprint_id')
    sprint = db.session.get(Sprint, sprint_id)

    if sprint:
        name = request.form.get('name')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        team = request.form.get('team')
        product_owner_id = request.form.get('product_owner_id')
        scrum_master_id = request.form.get('scrum_master_id')
        project_id = request.form.get('project_id')

        if name and start_date and end_date:
            sprint.name = name
            sprint.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            sprint.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            sprint.team = team if team else None
            sprint.product_owner_id = int(product_owner_id) if product_owner_id else None
            sprint.scrum_master_id = int(scrum_master_id) if scrum_master_id else None
            sprint.project_id = int(project_id) if project_id else None

            db.session.commit()
            flash('迭代更新成功！', 'success')
        else:
            flash('请填写所有必填字段！', 'error')

    return redirect(url_for('sprints.sprints'))


@sprints_bp.route('/sprint/<int:sprint_id>')
def sprint_detail(sprint_id):
    # 检查权限
    if not check_system_feature_access(session, 'sprints.sprints'):
        return redirect(url_for('auth.index'))

    sprint = db.session.get(Sprint, sprint_id)
    if not sprint:
        flash('迭代不存在！', 'error')
        return redirect(url_for('sprints.sprints'))

    # 按状态分组待办事项
    todo_backlogs = [b for b in sprint.sprint_backlogs if b.status == '待处理']
    in_progress_backlogs = [b for b in sprint.sprint_backlogs if b.status == '开发中']
    testing_backlogs = [b for b in sprint.sprint_backlogs if b.status == '测试中']
    done_backlogs = [b for b in sprint.sprint_backlogs if b.status == '已完成']

    # 计算统计信息
    completed_count = len(done_backlogs)
    total_story_points = sum(b.story_points or 0 for b in sprint.sprint_backlogs)

    # 获取所有用户用于下拉选择
    users = User.query.all()

    # 获取可以添加到迭代的用户故事（未分配到任何迭代的）
    available_stories = UserStory.query.filter(
        or_(UserStory.sprint_backlogs == None,
            ~UserStory.sprint_backlogs.any())
    ).all()

    # 为每个用户故事添加项目路径信息
    for story in available_stories:
        # 通过产品待办列表获取项目路径信息
        if story.product_backlog and story.product_backlog.project_module and story.product_backlog.project_module.path:
            # 从路径中提取项目、菜单、页面信息
            path_parts = story.product_backlog.project_module.path.split('/')
            if len(path_parts) >= 3:
                # 格式: /项目/菜单/页面 -> 项目-菜单-页面
                story.project_path = ' - '.join(path_parts[1:])
            else:
                story.project_path = story.product_backlog.project_module.path.lstrip('/')
        elif story.product_backlog and story.product_backlog.project:
            # 如果没有功能模块，至少显示项目信息
            story.project_path = story.product_backlog.project.name
        else:
            story.project_path = '未指定'


    return render_template('sprint_detail.html',
                           sprint=sprint,
                           todo_backlogs=todo_backlogs,
                           in_progress_backlogs=in_progress_backlogs,
                           testing_backlogs=testing_backlogs,
                           done_backlogs=done_backlogs,
                           completed_count=completed_count,
                           total_story_points=total_story_points,
                           users=users,
                           available_stories=available_stories)


@sprints_bp.route('/sprint/<int:sprint_id>/add', methods=['POST'])
def add_to_sprint(sprint_id):
    # 检查权限
    if not check_system_feature_access(session, 'sprints.sprints'):
        return redirect(url_for('auth.index'))

    sprint = db.session.get(Sprint, sprint_id)
    if not sprint:
        flash('迭代不存在！', 'error')
        return redirect(url_for('sprints.sprints'))

    user_story_ids = request.form.getlist('user_story_ids', type=int)

    for story_id in user_story_ids:
        user_story = db.session.get(UserStory, story_id)
        if user_story:
            # 检查是否已经添加到该迭代
            existing_backlog = SprintBacklog.query.filter_by(
                sprint_id=sprint_id,
                user_story_id=story_id
            ).first()

            if not existing_backlog:
                backlog = SprintBacklog(
                    sprint_id=sprint_id,
                    user_story_id=story_id,
                    priority=user_story.priority,
                    status='待处理'
                )
                db.session.add(backlog)

    db.session.commit()
    flash(f'成功添加 {len(user_story_ids)} 个用户故事到迭代！', 'success')

    return redirect(url_for('sprints.sprint_detail', sprint_id=sprint_id))


@sprints_bp.route('/sprint/backlog/edit', methods=['POST'])
def edit_sprint_backlog():
    # 检查权限
    if not check_system_feature_access(session, 'sprints.sprints'):
        return redirect(url_for('auth.index'))

    backlog_id = request.form.get('backlog_id')
    backlog = db.session.get(SprintBacklog, backlog_id)

    if backlog:
        story_points = request.form.get('story_points')
        status = request.form.get('status')
        priority = request.form.get('priority')
        assignee_id = request.form.get('assignee_id')

        backlog.story_points = float(story_points) if story_points else None
        backlog.status = status
        backlog.priority = priority
        backlog.assignee_id = int(assignee_id) if assignee_id else None

        db.session.commit()
        flash('待办事项更新成功！', 'success')

    return redirect(url_for('sprints.sprint_detail', sprint_id=backlog.sprint_id))


@sprints_bp.route('/sprint/<int:sprint_id>/start', methods=['POST'])
def start_sprint(sprint_id):
    """开始迭代"""
    # 检查权限
    if not check_system_feature_access(session, 'sprints.sprints'):
        return jsonify({'success': False, 'message': '权限不足'})
    
    sprint = db.session.get(Sprint, sprint_id)
    if not sprint:
        return jsonify({'success': False, 'message': '迭代不存在'})
    
    # 检查迭代状态是否为未开始
    if sprint.status != '未开始':
        return jsonify({'success': False, 'message': '只能开始状态为"未开始"的迭代'})
    
    try:
        sprint.status = '进行中'
        db.session.commit()
        return jsonify({'success': True, 'message': '迭代已开始'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': '操作失败: ' + str(e)})


@sprints_bp.route('/sprint/<int:sprint_id>/complete', methods=['POST'])
def complete_sprint(sprint_id):
    """完成迭代"""
    # 检查权限
    if not check_system_feature_access(session, 'sprints.sprints'):
        return jsonify({'success': False, 'message': '权限不足'})
    
    sprint = db.session.get(Sprint, sprint_id)
    if not sprint:
        return jsonify({'success': False, 'message': '迭代不存在'})
    
    # 检查迭代状态是否为进行中
    if sprint.status != '进行中':
        return jsonify({'success': False, 'message': '只能完成状态为"进行中"的迭代'})
    
    try:
        sprint.status = '已完成'
        db.session.commit()
        return jsonify({'success': True, 'message': '迭代已完成'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': '操作失败: ' + str(e)})


@sprints_bp.route('/sprint/backlog/<int:backlog_id>/remove', methods=['POST'])
def remove_from_sprint(backlog_id):
    """从迭代中移除用户故事"""
    # 检查权限
    if not check_system_feature_access(session, 'sprints.sprints'):
        return jsonify({'success': False, 'message': '权限不足'})

    backlog = db.session.get(SprintBacklog, backlog_id)
    if not backlog:
        return jsonify({'success': False, 'message': '待办事项不存在'})

    try:
        db.session.delete(backlog)
        db.session.commit()
        return jsonify({'success': True, 'message': '已从迭代中移除用户故事'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': '操作失败: ' + str(e)})
