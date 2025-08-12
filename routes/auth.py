from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User, SystemFeature, RoleSystemFeature, UserRole
from utils import check_user_role, check_system_feature_access

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    user = None
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])

    # 获取系统功能权限设置
    system_features = {}
    all_system_features = SystemFeature.query.all()

    # 检查用户是否为管理员
    is_admin = check_user_role(session.get('user_id'), 'admin') if session.get('user_id') else False

    # 为每个系统功能检查用户是否有访问权限
    session_system_features = {}
    for feature in all_system_features:
        # 如果用户是管理员，或者功能是公开的，或者用户拥有该功能的权限，则添加到session中
        has_access = is_admin or (feature.is_enabled and feature.is_public) or check_system_feature_access(session, feature.route_name)

        if has_access:
            system_features[feature.route_name] = feature
            session_system_features[feature.route_name] = {
                'id': feature.id,
                'name': feature.name,
                'route_name': feature.route_name,
                'is_enabled': feature.is_enabled,
                'is_public': feature.is_public
            }

    # 将system_features传递到session中，供模板使用
    session['features'] = session_system_features

    return render_template('index.html', user=user, system_features=system_features)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')
        user = User.query.filter_by(name=name).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.name  # 添加这行来设置username会话变量
            # 检查用户是否具有管理员角色
            #is_admin = check_user_role(user.id, 'admin')
            #session['is_admin'] = is_admin
            return redirect(url_for('auth.index'))
        flash('用户名或密码错误')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')
        if not name or not password:
            flash('请输入用户名和密码')
            return render_template('register.html')
        if User.query.filter_by(name=name).first():
            flash('用户名已存在')
            return render_template('register.html')
        user = User(name=name, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash('注册成功，请登录')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))