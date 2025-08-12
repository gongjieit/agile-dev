from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime, UTC
from models import db, User, GameRound, Estimate, UserStory
from utils import check_user_role

estimation_bp = Blueprint('estimation', __name__)

@estimation_bp.before_request
def require_login():
    allowed_routes = {'auth.login', 'auth.register', 'static'}
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        return redirect(url_for('auth.login'))


@estimation_bp.route('/start_estimate/<int:user_story_id>')
def start_estimate(user_story_id):
    # 检查该功能点是否有未结束的 GameRound
    current_round = GameRound.query.filter_by(user_story_id=user_story_id, end_time=None).first()
    if not current_round:
        current_round = GameRound(user_story_id=user_story_id)
        db.session.add(current_round)
        db.session.commit()
    # 跳转到扑克选择页面，需传递 round_id
    return redirect(url_for('estimation.poker', round_id=current_round.id))

@estimation_bp.route('/poker', methods=['GET', 'POST'])
def poker():
    if 'user_id' not in session:
        return redirect(url_for('auth.index'))
    round_id = request.args.get('round_id', type=int)
    if not round_id:
        return redirect(url_for('estimation.estimate'))
    current_round = db.session.get(GameRound, round_id)
    if not current_round or current_round.end_time is not None:
        return redirect(url_for('estimation.estimate'))
    user = db.session.get(User, session['user_id'])
    if not user:
        return redirect(url_for('auth.index'))
    estimate = Estimate.query.filter_by(user_id=user.id, round_id=current_round.id).first()
    cards = [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, '?', '∞', 'coffee']
    if request.method == 'POST':
        card_value = request.form.get('card_value')
        if card_value and not estimate:
            estimate = Estimate(user_id=user.id, round_id=current_round.id, card_value=card_value)
            db.session.add(estimate)
            db.session.commit()
        return redirect(url_for('estimation.wait', round_id=current_round.id))
    return render_template('poker.html', cards=cards, estimate=estimate, user_story=current_round.user_story)

@estimation_bp.route('/wait')
def wait():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    round_id = request.args.get('round_id', type=int)
    if not round_id:
        return redirect(url_for('estimation.estimate'))
    current_round = db.session.get(GameRound, round_id)
    if not current_round or current_round.end_time is not None:
        return redirect(url_for('estimation.estimate'))
    estimates = Estimate.query.filter_by(round_id=current_round.id).all()
    user_ids = {e.user_id for e in estimates}
    users = User.query.filter(User.id.in_(user_ids)).all()
    all_selected = len(estimates) == len(users) and len(users) > 0
    # 直接从数据库获取用户信息，确保获取到正确的管理员状态
    user = db.session.get(User, session['user_id'])
    is_admin = check_user_role(user.id, 'admin') if user else False
    print('is_admin:', is_admin)
    return render_template('wait.html', all_selected=all_selected, user_story=current_round.user_story, round_id=round_id, is_admin=is_admin)

@estimation_bp.route('/reveal')
def reveal():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    round_id = request.args.get('round_id', type=int)
    if not round_id:
        return redirect(url_for('estimation.estimate'))
    current_round = db.session.get(GameRound, round_id)
    if not current_round or current_round.end_time is not None:
        return redirect(url_for('estimation.estimate'))
    estimates = Estimate.query.filter_by(round_id=round_id).all()
    user_ids = {e.user_id for e in estimates}
    users = User.query.filter(User.id.in_(user_ids)).all()
    user_map = {e.user_id: e for e in estimates}
    
    # 计算统计信息
    numeric_estimates = [float(e.card_value) for e in estimates 
                        if e.card_value not in ['?', '∞', 'coffee'] and e.card_value is not None]
    
    average = sum(numeric_estimates) / len(numeric_estimates) if numeric_estimates else 0
    
    # 计算共识 - 所有人选择相同值
    consensus = len(set(e.card_value for e in estimates)) == 1 if estimates else False
    
    # 计算数值分布
    value_counts = {}
    for e in estimates:
        value_counts[e.card_value] = value_counts.get(e.card_value, 0) + 1
    
    
    return render_template('reveal.html', 
                         users=users, 
                         user_map=user_map, 
                         current_round=current_round, 
                         round_id=round_id, 
                         user_story=current_round.user_story,
                         estimates=estimates,
                         average=average,
                         consensus=consensus,
                         value_counts=value_counts,
                         )

@estimation_bp.route('/new_round')
def new_round():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    round_id = request.args.get('round_id', type=int)
    if not round_id:
        return redirect(url_for('estimation.estimate'))
    current_round = db.session.get(GameRound, round_id)
    if current_round and current_round.end_time is None:
        current_round.end_time = datetime.now(UTC)
        db.session.commit()
    return redirect(url_for('estimation.estimate'))


@estimation_bp.route('/estimate')
def estimate():
    # 检查用户是否为管理员
    is_admin = check_user_role(session['user_id'], 'admin')

    # 添加分页支持，每页显示10条数据
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # 使用 paginate 进行分页查询
    user_story_pagination = UserStory.query.order_by(UserStory.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    user_story_list = user_story_pagination.items
    user_count = User.query.count()
    progress_info = {}
    for user_story in user_story_list:
        current_round = GameRound.query.filter_by(user_story_id=user_story.id, end_time=None).first()
        if current_round:
            estimates = Estimate.query.filter_by(round_id=current_round.id).all()
            finished_user_ids = {e.user_id for e in estimates}
            finished_users = User.query.filter(User.id.in_(finished_user_ids)).all()
            progress_info[user_story.id] = {
                'round_id': current_round.id,
                'finished_count': len(finished_user_ids),
                'user_count': user_count,
                'finished_users': finished_users
            }
        else:
            progress_info[user_story.id] = {
                'round_id': None,
                'finished_count': 0,
                'user_count': user_count,
                'finished_users': []
            }
    return render_template('estimate.html',
                           user_story_list=user_story_list,
                           progress_info=progress_info,
                           is_admin=is_admin,
                           pagination=user_story_pagination)
