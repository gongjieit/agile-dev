from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash, current_app
from models import db, ProjectInfo, PrototypeImage, User
from utils import check_system_feature_access
from decorators import check_access_blueprint
import os
from werkzeug.utils import secure_filename
from datetime import datetime

prototype_bp = Blueprint('prototype', __name__)

# 应用权限检查装饰器
@prototype_bp.before_request
@check_access_blueprint('prototype')
def check_access():
    pass  # 路由权限由装饰器处理

@prototype_bp.route('/prototype')
def prototype_list():
    """原型图管理主页"""
    if not check_system_feature_access(session, 'prototype.prototype'):
        return redirect(url_for('auth.index'))
    
    # 获取所有项目根节点
    root_projects = ProjectInfo.query.filter_by(parent_id=None, node_type='project').all()
    
    return render_template('prototype/list.html', projects=root_projects)

@prototype_bp.route('/prototype/project/<int:project_id>')
def project_prototypes(project_id):
    """查看项目原型图"""
    if not check_system_feature_access(session, 'prototype.prototype'):
        return jsonify({'success': False, 'message': '权限不足'})
    
    try:
        # 获取项目及其所有子节点
        project = ProjectInfo.query.get_or_404(project_id)
        
        # 获取项目的所有节点（包括自身）
        all_nodes = get_all_project_nodes(project_id)
        node_ids = [node.id for node in all_nodes]
        
        # 获取这些节点下的所有原型图
        prototypes = PrototypeImage.query.filter(
            PrototypeImage.project_node_id.in_(node_ids)
        ).order_by(PrototypeImage.created_at.desc()).all()
        
        # 按节点分组原型图
        prototypes_by_node = {}
        for prototype in prototypes:
            node_id = prototype.project_node_id
            if node_id not in prototypes_by_node:
                prototypes_by_node[node_id] = []
            prototypes_by_node[node_id].append(prototype)
        
        return render_template('prototype/project_view.html', 
                             project=project, 
                             all_nodes=all_nodes,
                             prototypes_by_node=prototypes_by_node)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@prototype_bp.route('/prototype/upload', methods=['GET', 'POST'])
def upload_prototype():
    """上传原型图"""
    if not check_system_feature_access(session, 'prototype.prototype'):
        return redirect(url_for('auth.index'))
    
    if request.method == 'POST':
        try:
            project_node_id = request.form.get('project_node_id', type=int)
            name = request.form.get('name')
            description = request.form.get('description')
            version = request.form.get('version', '1.0')
            
            if 'image_file' not in request.files:
                flash('未选择文件', 'error')
                return redirect(request.url)
            
            file = request.files['image_file']
            
            if file.filename == '':
                flash('未选择文件', 'error')
                return redirect(request.url)
            
            if not project_node_id or not name:
                flash('项目节点和名称为必填项', 'error')
                return redirect(request.url)
            
            # 检查文件类型
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
            if '.' not in file.filename or \
               file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
                flash('只允许上传图片文件 (png, jpg, jpeg, gif, svg)', 'error')
                return redirect(request.url)
            
            # 创建上传目录（在static目录下）
            upload_folder = os.path.join(current_app.static_folder, 'uploads', 'prototypes')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            # 生成唯一文件名
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(upload_folder, unique_filename)
            
            # 保存文件
            file.save(file_path)
            
            # 创建相对路径用于访问，使用正斜杠
            relative_path = 'uploads/prototypes/' + unique_filename
            
            # 创建原型图记录
            prototype = PrototypeImage(
                project_node_id=project_node_id,
                name=name,
                description=description,
                file_path=relative_path,  # 保存相对路径而不是绝对路径
                file_size=os.path.getsize(file_path),
                mime_type=file.content_type,
                version=version,
                uploaded_by_id=session['user_id']
            )
            
            db.session.add(prototype)
            db.session.commit()
            
            flash('原型图上传成功', 'success')
            return redirect(url_for('prototype.prototype_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'上传失败: {str(e)}', 'error')
            return redirect(request.url)
    
    # GET 请求 - 显示上传表单
    # 获取所有项目节点
    all_projects = ProjectInfo.query.all()
    return render_template('prototype/upload.html', projects=all_projects)

@prototype_bp.route('/prototype/image/<int:image_id>')
def view_prototype(image_id):
    """查看原型图详情"""
    if not check_system_feature_access(session, 'prototype.prototype'):
        return redirect(url_for('auth.index'))
    
    prototype = PrototypeImage.query.get_or_404(image_id)
    return render_template('prototype/view.html', prototype=prototype)

@prototype_bp.route('/prototype/image/edit/<int:image_id>', methods=['GET', 'POST'])
def edit_prototype(image_id):
    """编辑原型图信息"""
    if not check_system_feature_access(session, 'prototype.prototype'):
        return redirect(url_for('auth.index'))
    
    prototype = PrototypeImage.query.get_or_404(image_id)
    
    # 检查权限（只有上传者或管理员可以编辑）
    # if prototype.uploaded_by_id != session['user_id'] and not check_user_role(session['user_id'], 'admin'):
    #     flash('您没有权限编辑此原型图', 'error')
    #     return redirect(url_for('prototype.view_prototype', image_id=image_id))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            version = request.form.get('version')
            
            if not name:
                flash('名称为必填项', 'error')
                return render_template('prototype/edit.html', prototype=prototype)
            
            # 更新原型图信息
            prototype.name = name
            prototype.description = description
            prototype.version = version
            prototype.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('原型图信息更新成功', 'success')
            return redirect(url_for('prototype.view_prototype', image_id=image_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败: {str(e)}', 'error')
            return render_template('prototype/edit.html', prototype=prototype)
    
    return render_template('prototype/edit.html', prototype=prototype)

@prototype_bp.route('/prototype/image/delete/<int:image_id>', methods=['POST'])
def delete_prototype(image_id):
    """删除原型图"""
    if not check_system_feature_access(session, 'prototype.prototype'):
        return jsonify({'success': False, 'message': '权限不足'})
    
    try:
        prototype = PrototypeImage.query.get_or_404(image_id)
        
        # 检查权限（只有上传者或管理员可以删除）
        # if prototype.uploaded_by_id != session['user_id'] and not check_user_role(session['user_id'], 'admin'):
        #     return jsonify({'success': False, 'message': '您没有权限删除此原型图'})
        
        # 删除文件
        file_path = os.path.join(current_app.static_folder, *prototype.file_path.split('/'))
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # 删除数据库记录
        db.session.delete(prototype)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '原型图删除成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})
    
@prototype_bp.route('/prototype/image/preview/<int:image_id>')
def preview_prototype(image_id):
    """预览原型图"""
    if not check_system_feature_access(session, 'prototype.prototype'):
        return jsonify({'success': False, 'message': '权限不足'})
    
    try:
        prototype = PrototypeImage.query.get_or_404(image_id)
        
        # 检查文件是否存在
        full_file_path = os.path.join(current_app.static_folder, *prototype.file_path.split('/'))
        if not os.path.exists(full_file_path):
            return jsonify({'success': False, 'message': '文件不存在'})
        
        # 确保文件路径使用正斜杠
        file_path = prototype.file_path.replace('\\', '/')
        
        # 返回文件信息用于前端预览
        return jsonify({
            'success': True,
            'image': {
                'id': prototype.id,
                'name': prototype.name,
                'description': prototype.description,
                'file_path': url_for('static', filename=file_path),  # 使用url_for生成正确的URL
                'file_size': prototype.file_size,
                'mime_type': prototype.mime_type,
                'version': prototype.version,
                'created_at': prototype.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': prototype.updated_at.strftime('%Y-%m-%d %H:%M:%S') if prototype.updated_at else '',
                'uploaded_by': prototype.uploaded_by.name if prototype.uploaded_by else '未知',
                'project_node': {
                    'id': prototype.project_node.id,
                    'name': prototype.project_node.name,
                    'path': prototype.project_node.path
                }
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@prototype_bp.route('/prototype/project_nodes/<int:project_id>')
def get_project_nodes(project_id):
    """获取项目的所有节点（AJAX）"""
    if not check_system_feature_access(session, 'prototype.prototype'):
        return jsonify({'success': False, 'message': '权限不足'})
    
    try:
        nodes = get_all_project_nodes(project_id)
        nodes_data = [{
            'id': node.id,
            'name': node.name,
            'node_type': node.node_type,
            'path': node.path
        } for node in nodes]
        
        return jsonify({
            'success': True,
            'nodes': nodes_data
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def get_all_project_nodes(project_id):
    """递归获取项目的所有节点"""
    def _get_children(node):
        children = []
        for child in node.children:
            children.append(child)
            children.extend(_get_children(child))
        return children
    
    # 获取根节点
    root_node = ProjectInfo.query.get(project_id)
    if not root_node:
        return []
    
    # 获取所有子节点
    all_nodes = [root_node]
    all_nodes.extend(_get_children(root_node))
    
    return all_nodes