from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from models import db, User, GameRound, Estimate, SystemFeature, UserStory
from utils import check_system_feature_access, check_user_role

admin_bp = Blueprint('admin', __name__)

def require_admin():
    if not check_user_role(session.get('user_id'), 'admin'):
        return redirect(url_for('auth.index'))

@admin_bp.before_request
def check_admin():
    # 排除静态文件路由
    if request.endpoint and not request.endpoint.startswith('static'):
        # 检查当前请求的路由是否需要权限控制
        endpoint = request.endpoint
        if endpoint and endpoint.startswith('admin'):
            # 获取对应的SystemFeature记录
            route_name = endpoint.replace('_', '.', 1)  # 将admin_users转换为admin.users格式
            if route_name.startswith('admin.'):
                system_feature = SystemFeature.query.filter_by(route_name=route_name).first()
                # 如果该功能存在且需要权限控制
                if system_feature and (not system_feature.is_enabled or
                                       (not check_user_role(session.get('user_id'),
                                                            'admin') and not system_feature.is_public)):
                    return redirect(url_for('auth.index'))


@admin_bp.route('/history')
def history():
    # 检查权限
    if not check_system_feature_access(session, 'admin.history'):
        return redirect(url_for('auth.index'))

    # 获取页码参数
    page = request.args.get('page', 1, type=int)
    per_page = 15  # 每页15条记录

    # 获取已完成的回合（有结束时间的回合）
    # 按结束时间倒序排列
    rounds_query = GameRound.query.filter(GameRound.end_time.isnot(None)).order_by(GameRound.end_time.desc())

    # 分页查询
    rounds_pagination = rounds_query.paginate(page=page, per_page=per_page, error_out=False)
    rounds = rounds_pagination.items

    # 按用户故事分组并计算轮次
    history_records = []
    user_story_rounds = {}  # 记录每个用户故事的所有回合

    # 先收集每个用户故事的所有回合
    for r in rounds:
        user_story_id = r.user_story_id
        if user_story_id not in user_story_rounds:
            user_story_rounds[user_story_id] = []
        user_story_rounds[user_story_id].append(r)

    # 为每个用户故事的回合分配轮次编号（按时间顺序）
    for user_story_id, story_rounds in user_story_rounds.items():
        # 按结束时间排序（需要正序，最早的在前）
        sorted_rounds = sorted(story_rounds, key=lambda x: x.end_time)

        # 为每个回合分配轮次编号
        for index, r in enumerate(sorted_rounds):
            round_number = index + 1  # 第一轮、第二轮...

            estimates = Estimate.query.filter_by(round_id=r.id).all()
            # 构造与模板匹配的数据结构
            history_records.append({
                'id': r.id,
                'user_story': r.user_story,
                'round_number': round_number,  # 添加轮次编号
                'estimates': estimates,
                'start_time': r.start_time,
                'end_time': r.end_time
            })

    # 最后按结束时间倒序排列（保证整体顺序不变）
    history_records.sort(key=lambda x: x['end_time'], reverse=True)

    return render_template('history.html',
                           history=history_records,
                           pagination=rounds_pagination)
