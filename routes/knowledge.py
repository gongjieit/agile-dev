from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, AgileKnowledge
from decorators import check_access_blueprint
from utils import check_system_feature_access

knowledge_bp = Blueprint('knowledge', __name__)

# 应用权限检查装饰器
@knowledge_bp.before_request
@check_access_blueprint('knowledge')
def check_access():
    pass  # 装饰器会处理权限检查逻辑

@knowledge_bp.route('/manage')
def knowledge():
    # 检查用户是否有知识库管理权限
    if not check_system_feature_access(session, 'knowledge.manage'):
        return redirect(url_for('auth.index'))

    # 获取所有知识文章，按更新时间倒序排列
    knowledge_articles = AgileKnowledge.query.order_by(AgileKnowledge.updated_at.desc()).all()
    return render_template('knowledge_list.html', knowledge_articles=knowledge_articles)


@knowledge_bp.route('/add_knowledge', methods=['GET', 'POST'])
def add_knowledge():
    # 检查用户是否有知识库管理权限
    if not check_system_feature_access(session, 'knowledge.manage'):
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category = request.form.get('category', '')

        if title and content:
            knowledge_article = AgileKnowledge(
                title=title,
                content=content,
                category=category if category else None,
                author_id=session['user_id']
            )
            db.session.add(knowledge_article)
            db.session.commit()
            flash('知识文章创建成功！')
            return redirect(url_for('knowledge.knowledge'))

        flash('标题和内容不能为空！')

    return render_template('knowledge_form.html', knowledge_article=None)


@knowledge_bp.route('/edit_knowledge/<int:knowledge_id>', methods=['GET', 'POST'])
def edit_knowledge(knowledge_id):
    # 检查用户是否有知识库管理权限
    if not check_system_feature_access(session, 'knowledge.manage'):
        return redirect(url_for('auth.index'))

    knowledge_article = db.session.get(AgileKnowledge, knowledge_id)
    if not knowledge_article:
        flash('知识文章不存在！')
        return redirect(url_for('knowledge.knowledge'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category = request.form.get('category', '')

        if title and content:
            knowledge_article.title = title
            knowledge_article.content = content
            knowledge_article.category = category if category else None
            knowledge_article.author_id = session['user_id']
            db.session.commit()
            flash('知识文章更新成功！')
            return redirect(url_for('knowledge.knowledge'))

        flash('标题和内容不能为空！')

    return render_template('knowledge_form.html', knowledge_article=knowledge_article)


@knowledge_bp.route('/delete_knowledge/<int:knowledge_id>', methods=['POST'])
def delete_knowledge(knowledge_id):
    # 检查用户是否有知识库管理权限
    if not check_system_feature_access(session, 'knowledge.manage'):
        return redirect(url_for('auth.index'))

    knowledge_article = db.session.get(AgileKnowledge, knowledge_id)
    if knowledge_article:
        db.session.delete(knowledge_article)
        db.session.commit()
        flash('知识文章删除成功！')
    else:
        flash('知识文章不存在！')

    return redirect(url_for('knowledge.knowledge'))

@knowledge_bp.route('/knowledge_view')
def knowledge_view():
    # 检查用户是否有知识库查看权限
    if not check_system_feature_access(session, 'knowledge.knowledge_view'):
        return redirect(url_for('auth.index'))

    # 获取所有知识文章，按更新时间倒序排列
    knowledge_articles = AgileKnowledge.query.order_by(AgileKnowledge.updated_at.desc()).all()
    return render_template('knowledge_view.html', knowledge_articles=knowledge_articles)


@knowledge_bp.route('/knowledge_detail/<int:knowledge_id>')
def knowledge_detail(knowledge_id):
    # 检查用户是否有知识库查看权限
    if not check_system_feature_access(session, 'knowledge.knowledge_view'):
        return redirect(url_for('auth.index'))

    # 获取指定的知识文章
    article = db.session.get(AgileKnowledge, knowledge_id)
    if not article:
        flash('知识文章不存在！')
        return redirect(url_for('knowledge.knowledge_view'))

    return render_template('knowledge_detail.html', article=article)