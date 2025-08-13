import os

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash, current_app, Response
from models import db, Defect, ProjectInfo, Sprint, User
from utils import check_system_feature_access
from decorators import check_access_blueprint
from datetime import datetime
import csv
import io
import pandas as pd

defects_bp = Blueprint('defects', __name__)

# 应用权限检查装饰器
@defects_bp.before_request
@check_access_blueprint('defects.defects')
def check_access():
    pass  # 路由权限由装饰器处理

def generate_defect_id():
    """生成缺陷编号，格式为F_001, F_002, ..."""
    # 查询最大的缺陷编号
    last_defect = Defect.query.filter(Defect.defect_id.isnot(None)).order_by(Defect.id.desc()).first()

    if last_defect and last_defect.defect_id and last_defect.defect_id.startswith('F_'):
        try:
            # 提取编号部分并加1
            last_number = int(last_defect.defect_id[2:])
            new_number = last_number + 1
        except ValueError:
            # 如果解析失败，从1开始
            new_number = 1
    else:
        # 如果没有缺陷或编号格式不正确，从1开始
        new_number = 1

    # 格式化为3位数字
    return f"F_{new_number:03d}"


@defects_bp.route('/defects/upload-image', methods=['POST'])
def upload_image():
    """处理CKEditor图片上传"""
    if 'upload' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400

    file = request.files['upload']

    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400

    if file:
        try:
            # 生成唯一文件名
            filename = f"{uuid.uuid4().hex}_{file.filename}"

            # 确保上传目录存在
            upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'defect_images')
            os.makedirs(upload_folder, exist_ok=True)

            # 保存文件
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)

            # 返回成功响应
            url = url_for('defects.serve_image', filename=filename)
            return jsonify({
                'url': url,
                'uploaded': True
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': '文件上传失败'}), 400


@defects_bp.route('/defects/images/<filename>')
def serve_image(filename):
    """提供上传的图片"""
    from flask import send_from_directory
    upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'defect_images')
    return send_from_directory(upload_folder, filename)

@defects_bp.route('/defects')
def defects():
    """缺陷管理主页 - 缺陷列表（分页）"""
    if not check_system_feature_access(session, 'defects.defects'):
        return redirect(url_for('auth.index'))

    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        project_id = request.args.get('project_id', type=int)
        sprint_id = request.args.get('sprint_id', type=int)
        status = request.args.get('status', type=str)
        priority = request.args.get('priority', type=str)
        assignee_id = request.args.get('assignee_id', type=int)
        search = request.args.get('search', type=str)

        # 构建查询
        query = Defect.query

        # 添加过滤条件
        if project_id:
            query = query.filter(Defect.project_id == project_id)
        if sprint_id:
            query = query.filter(Defect.sprint_id == sprint_id)
        if status:
            query = query.filter(Defect.status == status)
        if priority:
            query = query.filter(Defect.priority == priority)
        if assignee_id:
            query = query.filter(Defect.assignee_id == assignee_id)
        if search:
            query = query.filter(Defect.title.contains(search))

        # 分页查询
        pagination = query.order_by(Defect.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False)
        defects = pagination.items

        # 获取筛选选项
        projects = ProjectInfo.query.filter_by(node_type='project').all()
        sprints = Sprint.query.all()
        users = User.query.all()

        return render_template('defects/list.html',
                             defects=defects,
                             pagination=pagination,
                             projects=projects,
                             sprints=sprints,
                             users=users,
                             filters={
                                 'project_id': project_id,
                                 'sprint_id': sprint_id,
                                 'status': status,
                                 'priority': priority,
                                 'assignee_id': assignee_id,
                                 'search': search
                             })
    except Exception as e:
        flash(f'获取缺陷列表失败: {str(e)}', 'error')
        return render_template('defects/list.html', defects=[], pagination=None)

@defects_bp.route('/defects/create', methods=['GET', 'POST'])
def create_defect():
    """创建缺陷"""
    if not check_system_feature_access(session, 'defects.defects'):
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        try:
            title = request.form.get('title')
            project_id = request.form.get('project_id', type=int)
            sprint_id = request.form.get('sprint_id', type=int)
            work_item_type = request.form.get('work_item_type', 'defect')
            description = request.form.get('description')
            priority = request.form.get('priority', 'P3')
            is_online = request.form.get('is_online') == 'on' or request.form.get('is_online') == 'True'
            severity = request.form.get('severity', '一般')
            defect_type = request.form.get('defect_type', '功能问题')
            status = request.form.get('status', '待处理')
            dev_team = request.form.get('dev_team')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            resolver_id = request.form.get('resolver_id', type=int)
            resolution = request.form.get('resolution', '未设置')

            # 必填字段验证
            if not title or not project_id:
                flash('标题和所属项目为必填项', 'error')
                projects = ProjectInfo.query.filter_by(node_type='project').all()
                sprints = Sprint.query.all()
                users = User.query.all()
                return render_template('defects/create.html',
                                     projects=projects,
                                     sprints=sprints,
                                     users=users)

            # 生成缺陷编号
            defect_id = generate_defect_id()

            # 创建缺陷
            defect = Defect(
                defect_id=defect_id,
                title=title,
                project_id=project_id,
                sprint_id=sprint_id,
                work_item_type=work_item_type,
                description=description,
                priority=priority,
                is_online=is_online,
                severity=severity,
                defect_type=defect_type,
                status=status,
                dev_team=dev_team,
                created_by_id=session['user_id'],
                assignee_id=session['user_id'],  # 默认负责人为创建者
                resolver_id=resolver_id,
                resolution=resolution
            )

            # 处理日期字段
            if start_date:
                defect.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                defect.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

            db.session.add(defect)
            db.session.commit()

            flash('缺陷创建成功', 'success')
            return redirect(url_for('defects.defects'))

        except Exception as e:
            db.session.rollback()
            flash(f'创建缺陷失败: {str(e)}', 'error')
            projects = ProjectInfo.query.filter_by(node_type='project').all()
            sprints = Sprint.query.all()
            users = User.query.all()
            return render_template('defects/create.html',
                                 projects=projects,
                                 sprints=sprints,
                                 users=users)

    # GET 请求 - 显示创建表单
    projects = ProjectInfo.query.filter_by(node_type='project').all()
    sprints = Sprint.query.all()
    users = User.query.all()
    return render_template('defects/create.html',
                         projects=projects,
                         sprints=sprints,
                         users=users)


@defects_bp.route('/defects/edit/<int:defect_id>', methods=['GET', 'POST'])
def edit_defect(defect_id):
    """编辑缺陷"""
    if not check_system_feature_access(session, 'defects.defects'):
        return redirect(url_for('auth.index'))

    defect = Defect.query.get_or_404(defect_id)

    if request.method == 'POST':
        try:
            title = request.form.get('title')
            project_id = request.form.get('project_id', type=int)
            sprint_id = request.form.get('sprint_id', type=int)
            work_item_type = request.form.get('work_item_type', defect.work_item_type or 'defect')
            description = request.form.get('description')
            assignee_id = request.form.get('assignee_id', type=int)
            priority = request.form.get('priority')
            is_online = request.form.get('is_online') == 'on' or request.form.get('is_online') == 'True'
            severity = request.form.get('severity')
            defect_type = request.form.get('defect_type')
            status = request.form.get('status')
            resolver_id = request.form.get('resolver_id', type=int)
            resolution = request.form.get('resolution')
            dev_team = request.form.get('dev_team')
            collaborators = request.form.get('collaborators')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')

            # 必填字段验证
            if not title or not project_id:
                flash('标题和所属项目为必填项', 'error')
                projects = ProjectInfo.query.filter_by(node_type='project').all()
                sprints = Sprint.query.all()
                users = User.query.all()
                return render_template('defects/edit.html',
                                     defect=defect,
                                     projects=projects,
                                     sprints=sprints,
                                     users=users)

            # 更新缺陷信息
            defect.title = title
            defect.project_id = project_id
            defect.sprint_id = sprint_id
            defect.work_item_type = work_item_type
            defect.description = description
            defect.assignee_id = assignee_id
            defect.priority = priority
            defect.is_online = is_online
            defect.severity = severity
            defect.defect_type = defect_type
            defect.status = status
            defect.resolver_id = resolver_id
            defect.resolution = resolution
            defect.dev_team = dev_team
            defect.collaborators = collaborators

            # 处理日期字段
            if start_date:
                defect.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            else:
                defect.start_date = None
            if end_date:
                defect.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            else:
                defect.end_date = None

            defect.updated_at = datetime.utcnow()

            db.session.commit()

            flash('缺陷更新成功', 'success')
            return redirect(url_for('defects.defects'))

        except Exception as e:
            db.session.rollback()
            flash(f'更新缺陷失败: {str(e)}', 'error')
            projects = ProjectInfo.query.filter_by(node_type='project').all()
            sprints = Sprint.query.all()
            users = User.query.all()
            return render_template('defects/edit.html',
                                 defect=defect,
                                 projects=projects,
                                 sprints=sprints,
                                 users=users)

    # GET 请求 - 显示编辑表单
    projects = ProjectInfo.query.filter_by(node_type='project').all()
    sprints = Sprint.query.all()
    users = User.query.all()
    return render_template('defects/edit.html',
                         defect=defect,
                         projects=projects,
                         sprints=sprints,
                         users=users)


@defects_bp.route('/defects/delete/<int:defect_id>', methods=['POST'])
def delete_defect(defect_id):
    """删除缺陷"""
    if not check_system_feature_access(session, 'defects.defects'):
        return jsonify({'success': False, 'message': '权限不足'})

    try:
        defect = Defect.query.get_or_404(defect_id)
        db.session.delete(defect)
        db.session.commit()

        return jsonify({'success': True, 'message': '缺陷删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除缺陷失败: {str(e)}'})

@defects_bp.route('/defects/export')
def export_defects():
    """导出缺陷为Excel文件"""
    if not check_system_feature_access(session, 'defects.defects'):
        return redirect(url_for('auth.index'))

    try:
        # 获取查询参数
        project_id = request.args.get('project_id', type=int)
        sprint_id = request.args.get('sprint_id', type=int)
        status = request.args.get('status', type=str)
        priority = request.args.get('priority', type=str)

        # 构建查询
        query = Defect.query

        # 添加过滤条件
        if project_id:
            query = query.filter(Defect.project_id == project_id)
        if sprint_id:
            query = query.filter(Defect.sprint_id == sprint_id)
        if status:
            query = query.filter(Defect.status == status)
        if priority:
            query = query.filter(Defect.priority == priority)

        defects = query.all()

        # 准备数据
        data = []
        for defect in defects:
            data.append({
                '缺陷编号': defect.defect_id or '',
                '标题': defect.title,
                '所属项目': defect.project.name if defect.project else '',
                '所属迭代': defect.sprint.name if defect.sprint else '',
                '工作项类型': defect.work_item_type,
                '缺陷描述': defect.description or '',
                '负责人': defect.assignee.name if defect.assignee else '',
                '优先级': defect.priority,
                '是否线上缺陷': '是' if defect.is_online else '否',
                '严重程度': defect.severity,
                '缺陷类型': defect.defect_type,
                '缺陷状态': defect.status,
                '解决者': defect.resolver.name if defect.resolver else '',
                '处理结果': defect.resolution,
                '开发团队': defect.dev_team or '',
                '协助者': defect.collaborators or '',
                '开始日期': defect.start_date.strftime('%Y-%m-%d') if defect.start_date else '',
                '结束日期': defect.end_date.strftime('%Y-%m-%d') if defect.end_date else '',
                '创建人': defect.created_by.name if defect.created_by else '',
                '创建时间': defect.created_at.strftime('%Y-%m-%d %H:%M:%S') if defect.created_at else '',
                '更新时间': defect.updated_at.strftime('%Y-%m-%d %H:%M:%S') if defect.updated_at else ''
            })

        # 创建DataFrame
        df = pd.DataFrame(data)

        # 将DataFrame写入内存中的Excel文件
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='缺陷列表')
        output.seek(0)

        # 设置响应头
        filename = f"defects_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return Response(
            output.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    except Exception as e:
        flash(f'导出缺陷失败: {str(e)}', 'error')
        return redirect(url_for('defects.defects'))

@defects_bp.route('/defects/import', methods=['GET', 'POST'])
def import_defects():
    """导入缺陷（仅支持.xlsx格式）"""
    if not check_system_feature_access(session, 'defects.defects'):
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        try:
            if 'file' not in request.files:
                flash('未选择文件', 'error')
                return redirect(request.url)

            file = request.files['file']

            if file.filename == '':
                flash('未选择文件', 'error')
                return redirect(request.url)

            if file and file.filename.endswith('.xlsx'):
                # 读取Excel文件
                df = pd.read_excel(file, engine='openpyxl')

                imported_count = 0
                error_count = 0

                for index, row in df.iterrows():
                    try:
                        # 检查必填字段
                        title = row['标题'] if '标题' in row and pd.notna(row['标题']) else ''
                        project_name = row['所属项目'] if '所属项目' in row and pd.notna(row['所属项目']) else ''

                        # 验证必填字段
                        if not title:
                            flash(f'第{index+2}行: 标题为必填项', 'error')
                            error_count += 1
                            continue

                        if not project_name:
                            flash(f'第{index+2}行: 所属项目为必填项', 'error')
                            error_count += 1
                            continue

                        # 根据项目名称查找项目ID
                        project = ProjectInfo.query.filter_by(name=project_name).first()
                        if not project:
                            flash(f'第{index+2}行: 项目"{project_name}"不存在', 'error')
                            error_count += 1
                            continue

                        # 生成缺陷编号
                        defect_id = generate_defect_id()

                        # 处理可选字段
                        sprint_id = None
                        if '所属迭代' in row and pd.notna(row['所属迭代']):
                            sprint = Sprint.query.filter_by(name=row['所属迭代']).first()
                            if sprint:
                                sprint_id = sprint.id

                        assignee_id = session['user_id']  # 默认负责人为创建者
                        if '负责人' in row and pd.notna(row['负责人']):
                            assignee = User.query.filter_by(name=row['负责人']).first()
                            if assignee:
                                assignee_id = assignee.id

                        resolver_id = None
                        if '解决者' in row and pd.notna(row['解决者']):
                            resolver = User.query.filter_by(name=row['解决者']).first()
                            if resolver:
                                resolver_id = resolver.id

                        # 解析行数据
                        defect = Defect(
                            defect_id=defect_id,
                            title=title,
                            project_id=project.id,
                            sprint_id=sprint_id,
                            work_item_type=row['工作项类型'] if '工作项类型' in row and pd.notna(row['工作项类型']) else 'defect',
                            description=row['缺陷描述'] if '缺陷描述' in row and pd.notna(row['缺陷描述']) else '',
                            assignee_id=assignee_id,
                            priority=row['优先级'] if '优先级' in row and pd.notna(row['优先级']) else 'P3',
                            is_online=(row['是否线上缺陷'] == '是') if '是否线上缺陷' in row and pd.notna(row['是否线上缺陷']) else False,
                            severity=row['严重程度'] if '严重程度' in row and pd.notna(row['严重程度']) else '一般',
                            defect_type=row['缺陷类型'] if '缺陷类型' in row and pd.notna(row['缺陷类型']) else '功能问题',
                            status=row['缺陷状态'] if '缺陷状态' in row and pd.notna(row['缺陷状态']) else '待处理',
                            resolver_id=resolver_id,
                            resolution=row['处理结果'] if '处理结果' in row and pd.notna(row['处理结果']) else '未设置',
                            dev_team=row['开发团队'] if '开发团队' in row and pd.notna(row['开发团队']) else '',
                            collaborators=row['协助者'] if '协助者' in row and pd.notna(row['协助者']) else '',
                            created_by_id=session['user_id']
                        )

                        # 处理日期字段
                        if '开始日期' in row and pd.notna(row['开始日期']):
                            if isinstance(row['开始日期'], str):
                                defect.start_date = datetime.strptime(row['开始日期'], '%Y-%m-%d').date()
                            else:
                                defect.start_date = row['开始日期'].date()

                        if '结束日期' in row and pd.notna(row['结束日期']):
                            if isinstance(row['结束日期'], str):
                                defect.end_date = datetime.strptime(row['结束日期'], '%Y-%m-%d').date()
                            else:
                                defect.end_date = row['结束日期'].date()

                        db.session.add(defect)
                        imported_count += 1
                    except Exception as e:
                        error_count += 1
                        flash(f'第{index+2}行: 导入失败 - {str(e)}', 'error')
                        continue  # 跳过有问题的行

                db.session.commit()
                flash(f'成功导入 {imported_count} 个缺陷，{error_count} 个失败', 'success' if error_count == 0 else 'warning')
                return redirect(url_for('defects.defects'))
            else:
                flash('请上传.xlsx格式的文件', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'导入缺陷失败: {str(e)}', 'error')

    return render_template('defects/import.html')


