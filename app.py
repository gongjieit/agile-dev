import os

from flask import Flask
from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MYSQL_PORT
from utils import check_user_role, check_system_feature_access
from models import db, User, Sprint, SprintBacklog


# 导入路由模块
from routes.auth import auth_bp
from routes.estimation import estimation_bp
from routes.admin import admin_bp
from routes.sprints import sprints_bp
from routes.knowledge import knowledge_bp
from routes.user_stories import user_stories_bp
from routes.users import users_bp
from routes.roles import roles_bp
from routes.system_features import system_features_bp
from routes.projects import projects_bp
from routes.tasks import tasks_bp
from routes.kanban import kanban_bp
from routes.product_backlog import product_backlog_bp
from routes.test_cases import test_cases_bp
from routes.prototype import prototype_bp
from routes.defects import defects_bp

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key_here'
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 配置上传文件夹
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    
    # 全局上下文处理器，使用户信息在所有模板中可用
    @app.context_processor
    def inject_user():
        user = None
        if 'user_id' in session:
            user = db.session.get(User, session['user_id'])
        return dict(user=user, check_user_role=check_user_role, check_system_feature_access=check_system_feature_access)


    from flask import request, session, redirect, url_for
    # 全局请求前检查
    @app.before_request
    def require_login():
        allowed_routes = {'auth.login', 'auth.register', 'static'}
        if request.endpoint and request.endpoint not in allowed_routes and 'user_id' not in session:
            # 检查是否是蓝图路由
            if request.endpoint and not request.endpoint.startswith('static'):
                return redirect(url_for('auth.login'))


    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(estimation_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(sprints_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(user_stories_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(roles_bp)
    app.register_blueprint(system_features_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(kanban_bp)
    app.register_blueprint(product_backlog_bp)
    app.register_blueprint(test_cases_bp)
    app.register_blueprint(prototype_bp)
    app.register_blueprint(defects_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)