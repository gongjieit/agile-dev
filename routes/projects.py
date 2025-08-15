from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from models import db, ProjectInfo
from utils import check_system_feature_access
from decorators import check_access_blueprint

projects_bp = Blueprint('projects', __name__)

# 应用权限检查装饰器
@projects_bp.before_request
@check_access_blueprint('projects')
def check_access():
    pass  # 装饰器会处理权限检查逻辑

@projects_bp.route('/projects')
def projects():
    # 检查权限
    if not check_system_feature_access(session, 'projects.projects'):
        return redirect(url_for('auth.index'))
    
    # 获取所有根节点（项目）
    root_projects = ProjectInfo.query.filter_by(parent_id=None).order_by(ProjectInfo.order).all()
    
    # 递归获取树形结构数据
    def build_tree(nodes):
        tree = []
        for node in nodes:
            children = ProjectInfo.query.filter_by(parent_id=node.id).order_by(ProjectInfo.order).all()
            tree.append({
                'id': node.id,
                'name': node.name,
                'short_name': node.short_name,
                'node_type': node.node_type,
                'path': node.path,
                'created_at': node.created_at,
                'children': build_tree(children) if children else []
            })
        return tree
    
    projects_tree = build_tree(root_projects)
    
    return render_template('projects.html', projects_tree=projects_tree)

@projects_bp.route('/projects/<int:project_id>/modules')
def get_project_modules(project_id):
    """获取指定项目下的功能模块（菜单和页面节点）"""
    # 检查权限
    if not check_system_feature_access(session, 'projects.projects'):
        return jsonify({'success': False, 'message': '权限不足'})

    # 获取项目
    project = db.session.get(ProjectInfo, project_id)
    if not project:
        return jsonify({'success': False, 'message': '项目不存在'})

    # 获取项目下的所有菜单和页面节点（功能模块）
    modules = ProjectInfo.query.filter(
        ProjectInfo.path.like(f"/{project.name}%")
    ).filter(
        ProjectInfo.node_type.in_(['menu', 'page'])
    ).order_by(ProjectInfo.path).all()

    # 转换为字典格式
    modules_data = []
    for module in modules:
        modules_data.append({
            'id': module.id,
            'name': module.name,
            'node_type': module.node_type,
            'path': module.path
        })

    return jsonify({
        'success': True,
        'modules': modules_data
    })


@projects_bp.route('/add_project_node', methods=['POST'])
def add_project_node():
    # 检查权限
    if not check_system_feature_access(session, 'projects.projects'):
        return jsonify({'success': False, 'message': '权限不足'})
    
    name = request.form.get('name')
    short_name = request.form.get('short_name')
    node_type = request.form.get('node_type')
    parent_id = request.form.get('parent_id', type=int)
    
    if not name or not node_type:
        return jsonify({'success': False, 'message': '名称和节点类型不能为空'})
    
    # 计算新节点的order值（在同级节点中排在最后）
    max_order = db.session.query(db.func.max(ProjectInfo.order)).filter_by(parent_id=parent_id).scalar()
    new_order = (max_order or 0) + 10

    # 创建新节点
    new_node = ProjectInfo(
        name=name,
        short_name=short_name if node_type == 'project' else None,
        node_type=node_type,
        parent_id=parent_id if parent_id else None,
        order=new_order  # 设置order值
    )

    # 设置路径
    if parent_id:
        parent = ProjectInfo.query.get(parent_id)
        if parent:
            new_node.path = f"{parent.path}/{name}" if parent.path else f"/{parent.name}/{name}"
    else:
        new_node.path = f"/{name}"

    try:
        db.session.add(new_node)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '添加成功',
            'node': {
                'id': new_node.id,
                'name': new_node.name,
                'short_name': new_node.short_name,
                'node_type': new_node.node_type,
                'path': new_node.path,
                'parent_id': new_node.parent_id
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})


@projects_bp.route('/edit_project_node/<int:node_id>', methods=['POST'])
def edit_project_node(node_id):
    # 检查权限
    if not check_system_feature_access(session, 'projects.projects'):
        return jsonify({'success': False, 'message': '权限不足'})
    
    node = ProjectInfo.query.get(node_id)
    if not node:
        return jsonify({'success': False, 'message': '节点不存在'})
    
    name = request.form.get('name')
    short_name = request.form.get('short_name')
    
    if not name:
        return jsonify({'success': False, 'message': '名称不能为空'})
    
    # 更新节点信息
    node.name = name
    if node.node_type == 'project':
        node.short_name = short_name
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': '更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@projects_bp.route('/delete_project_node/<int:node_id>', methods=['POST'])
def delete_project_node(node_id):
    # 检查权限
    if not check_system_feature_access(session, 'projects.projects'):
        return jsonify({'success': False, 'message': '权限不足'})
    
    node = ProjectInfo.query.get(node_id)
    if not node:
        return jsonify({'success': False, 'message': '节点不存在'})
    
    # 检查是否有子节点
    children_count = ProjectInfo.query.filter_by(parent_id=node_id).count()
    if children_count > 0:
        return jsonify({'success': False, 'message': '该节点下有子节点，请先删除子节点'})
    
    try:
        db.session.delete(node)
        db.session.commit()
        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@projects_bp.route('/move_project_node', methods=['POST'])
def move_project_node():
    # 检查权限
    if not check_system_feature_access(session, 'projects.projects'):
        return jsonify({'success': False, 'message': '权限不足'})
    
    node_id = request.form.get('node_id', type=int)
    new_parent_id = request.form.get('new_parent_id', type=int)
    new_order = request.form.get('new_order', type=int)
    
    node = ProjectInfo.query.get(node_id)
    if not node:
        return jsonify({'success': False, 'message': '节点不存在'})
    
    # 更新父节点
    node.parent_id = new_parent_id if new_parent_id else None
    
    # 更新排序
    if new_order is not None:
        node.order = new_order
    
    # 更新路径
    if new_parent_id:
        parent = ProjectInfo.query.get(new_parent_id)
        if parent:
            node.path = f"{parent.path}/{node.name}" if parent.path else f"/{parent.name}/{node.name}"
        else:
            node.path = f"/{node.name}"
    else:
        node.path = f"/{node.name}"
    
    # 递归更新子节点路径
    def update_children_paths(parent_node):
        children = ProjectInfo.query.filter_by(parent_id=parent_node.id).all()
        for child in children:
            child.path = f"{parent_node.path}/{child.name}"
            update_children_paths(child)
    
    update_children_paths(node)
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': '移动成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'移动失败: {str(e)}'})


@projects_bp.route('/move_node_up/<int:node_id>', methods=['POST'])
def move_node_up(node_id):
    """上移节点"""
    # 检查权限
    if not check_system_feature_access(session, 'projects.projects'):
        return jsonify({'success': False, 'message': '权限不足'})

    node = ProjectInfo.query.get(node_id)
    if not node:
        return jsonify({'success': False, 'message': '节点不存在'})

    # 获取同一父节点下的所有子节点，按order排序
    siblings = ProjectInfo.query.filter_by(parent_id=node.parent_id).order_by(ProjectInfo.order).all()

    # 如果只有一个节点或没有节点，则无法移动
    if len(siblings) <= 1:
        return jsonify({'success': False, 'message': '节点无法移动'})

    # 找到当前节点的索引
    current_index = None
    for i, sibling in enumerate(siblings):
        if sibling.id == node_id:
            current_index = i
            break

    # 如果已经是第一个节点，则无法上移
    if current_index is None or current_index == 0:
        return jsonify({'success': False, 'message': '节点已在最顶部'})

    # 重新分配所有同级节点的order值，确保它们是有序的
    for i, sibling in enumerate(siblings):
        sibling.order = i * 10  # 使用间隔为10的数字，方便后续插入

    # 交换当前节点与前一个节点的位置
    siblings[current_index], siblings[current_index - 1] = siblings[current_index - 1], siblings[current_index]

    # 重新分配order值
    for i, sibling in enumerate(siblings):
        sibling.order = i * 10

    try:
        db.session.commit()
        return jsonify({'success': True, 'message': '上移成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'上移失败: {str(e)}'})


@projects_bp.route('/move_node_down/<int:node_id>', methods=['POST'])
def move_node_down(node_id):
    """下移节点"""
    # 检查权限
    if not check_system_feature_access(session, 'projects.projects'):
        return jsonify({'success': False, 'message': '权限不足'})

    node = ProjectInfo.query.get(node_id)
    if not node:
        return jsonify({'success': False, 'message': '节点不存在'})

    # 获取同一父节点下的所有子节点，按order排序
    siblings = ProjectInfo.query.filter_by(parent_id=node.parent_id).order_by(ProjectInfo.order).all()

    # 如果只有一个节点或没有节点，则无法移动
    if len(siblings) <= 1:
        return jsonify({'success': False, 'message': '节点无法移动'})

    # 找到当前节点的索引
    current_index = None
    for i, sibling in enumerate(siblings):
        if sibling.id == node_id:
            current_index = i
            break

    # 如果已经是最后一个节点，则无法下移
    if current_index is None or current_index == len(siblings) - 1:
        return jsonify({'success': False, 'message': '节点已在最底部'})

    # 重新分配所有同级节点的order值，确保它们是有序的
    for i, sibling in enumerate(siblings):
        sibling.order = i * 10  # 使用间隔为10的数字，方便后续插入

    # 交换当前节点与后一个节点的位置
    siblings[current_index], siblings[current_index + 1] = siblings[current_index + 1], siblings[current_index]

    # 重新分配order值
    for i, sibling in enumerate(siblings):
        sibling.order = i * 10

    try:
        db.session.commit()
        return jsonify({'success': True, 'message': '下移成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'下移失败: {str(e)}'})


