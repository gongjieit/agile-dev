from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    nickname = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(128), nullable=False)
    estimates = db.relationship('Estimate', backref='user', lazy=True)


# 角色模型
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)  # 角色名称，如 admin, PO, SM, PM, developer, test
    display_name = db.Column(db.String(128), nullable=False)  # 角色显示名称
    description = db.Column(db.Text, nullable=True)  # 角色描述
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 角色与用户关联关系
    user_roles = db.relationship('UserRole', backref='role', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Role {self.name}>'


# 用户角色关联模型
class UserRole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联关系
    user = db.relationship('User', backref='user_roles')

    def __repr__(self):
        return f'<UserRole user_id={self.user_id} role_id={self.role_id}>'

# 角色系统功能关联模型
class RoleSystemFeature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    system_feature_id = db.Column(db.Integer, db.ForeignKey('system_feature.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联关系
    role = db.relationship('Role', backref='role_system_features')
    system_feature = db.relationship('SystemFeature', backref='role_system_features')

    def __repr__(self):
        return f'<RoleSystemFeature role_id={self.role_id} system_feature_id={self.system_feature_id}>'

# 系统功能模型
class SystemFeature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)  # 功能名称
    description = db.Column(db.Text, nullable=True)   # 功能描述
    route_name = db.Column(db.String(128), unique=True, nullable=False)  # 路由名称
    is_enabled = db.Column(db.Boolean, default=True)  # 是否启用
    is_public = db.Column(db.Boolean, default=False)  # 是否公开（无需登录）
    order_num = db.Column(db.Integer, default=0)  # 排序序号
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SystemFeature {self.name}>'

class AgileKnowledge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    author = db.relationship('User', backref='knowledge_articles')

class GameRound(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_story_id = db.Column(db.Integer, db.ForeignKey('user_story.id'), nullable=True)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    estimates = db.relationship('Estimate', backref='round', lazy=True, cascade='all, delete-orphan')

    # 增加与UserStory的关联关系
    user_story = db.relationship('UserStory', backref='game_rounds')


# 项目信息树形结构模型
class ProjectInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)  # 节点名称
    short_name = db.Column(db.String(32), nullable=True)  # 项目简称（仅根节点使用）
    node_type = db.Column(db.String(20), nullable=False)  # 节点类型: 'project', 'menu', 'page'
    parent_id = db.Column(db.Integer, db.ForeignKey('project_info.id'), nullable=True)  # 父节点ID
    path = db.Column(db.String(512), nullable=True)  # 节点路径，用于快速查询
    order = db.Column(db.Integer, default=0)  # 排序字段
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 自关联关系
    children = db.relationship('ProjectInfo', backref=db.backref('parent', remote_side=[id]), lazy=True)


# 产品待办列表模型，用于管理项目需求
class ProductBacklog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requirement_id = db.Column(db.String(32), unique=True, nullable=True)  # 需求编号
    title = db.Column(db.String(256), nullable=False)  # 需求标题
    description = db.Column(db.Text, nullable=True)  # 需求描述
    requirement_type = db.Column(db.String(32), nullable=True)  # 需求类型（用户故事、Bug修复、技术优化、研究任务等）
    customer_owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # 需求责任人（甲方）
    priority = db.Column(db.String(8), default='P3')  # 需求优先级（PO-P5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 需求提出日期
    status = db.Column(db.String(32), default='待讨论')  # 需求状态（待讨论、已澄清、已纳入冲刺、已完成）
    project_id = db.Column(db.Integer, db.ForeignKey('project_info.id'), nullable=True)  # 需求所属项目
    # 添加功能模块字段，细化需求到功能模块级别
    project_module_id = db.Column(db.Integer, db.ForeignKey('project_info.id'), nullable=True)  # 需求所属功能模块
    analyst_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # 需求分析人员
    progress = db.Column(db.String(32), default='未处理')  # 需求执行进度（未处理、分析中、已确认、开发中、测试中、验收中、已上线）
    related_info = db.Column(db.Text, nullable=True)  # 关联信息（需求文档、UI设计等）
    tags = db.Column(db.String(256), nullable=True)  # 标签
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    customer_owner = db.relationship('User', foreign_keys=[customer_owner_id], backref='owned_requirements')
    analyst = db.relationship('User', foreign_keys=[analyst_id], backref='analyzed_requirements')
    project = db.relationship('ProjectInfo', foreign_keys=[project_id], backref='product_backlogs')
    # 添加功能模块关联关系
    project_module = db.relationship('ProjectInfo', foreign_keys=[project_module_id], backref='module_requirements')


class UserStory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.String(32), unique=True, nullable=True)  # 故事编号，如 US_001_001
    product_backlog_id = db.Column(db.Integer, db.ForeignKey('product_backlog.id'), nullable=True)  # 关联产品待办列表
    title = db.Column(db.String(256), nullable=False)  # 故事名称
    description = db.Column(db.Text, nullable=True)  # 故事描述（原用户故事标题）
    acceptance_criteria = db.Column(db.Text, nullable=True)
    effort = db.Column(db.Float, nullable=True)  # 工作量（人天）
    priority = db.Column(db.String(8), default='P3')  # 优先级 P0-P5
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联关系
    product_backlog = db.relationship('ProductBacklog', backref='user_stories')  # 关联产品待办列表

# 新增Sprint模型，用于管理迭代信息
class Sprint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)  # Sprint名称
    start_date = db.Column(db.Date, nullable=False)  # 开始日期
    end_date = db.Column(db.Date, nullable=False)  # 结束日期
    team = db.Column(db.String(128), nullable=True)  # 团队名称
    product_owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # 产品负责人
    scrum_master_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Scrum Master
    status = db.Column(db.String(32), default='未开始')  # 状态：未开始、进行中、已完成
    project_id = db.Column(db.Integer, db.ForeignKey('project_info.id'), nullable=True)  # 关联项目
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联关系
    product_owner = db.relationship('User', foreign_keys=[product_owner_id], backref='owned_sprints')
    scrum_master = db.relationship('User', foreign_keys=[scrum_master_id], backref='mastered_sprints')
    sprint_backlogs = db.relationship('SprintBacklog', backref='sprint', lazy=True, cascade='all, delete-orphan')
    project = db.relationship('ProjectInfo', backref='sprints')  # 关联项目关系


# 新增SprintBacklog模型，用于管理迭代待办事项
class SprintBacklog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sprint_id = db.Column(db.Integer, db.ForeignKey('sprint.id'), nullable=False)
    user_story_id = db.Column(db.Integer, db.ForeignKey('user_story.id'), nullable=False)
    story_points = db.Column(db.Float, nullable=True)  # 故事点
    status = db.Column(db.String(32), default='待处理')  # 状态：待处理、开发中、测试中、已完成
    priority = db.Column(db.String(8), default='P3')  # 优先级 P0-P5
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # 负责人
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联关系
    user_story = db.relationship('UserStory', backref='sprint_backlogs')
    assignee = db.relationship('User', foreign_keys=[assignee_id], backref='assigned_sprint_tasks')


class Estimate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    round_id = db.Column(db.Integer, db.ForeignKey('game_round.id'), nullable=False)
    card_value = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# 任务模型，用于将用户故事拆分成任务
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(32), unique=True, nullable=True)  # 任务编号，如 Ta001
    user_story_id = db.Column(db.Integer, db.ForeignKey('user_story.id'), nullable=False)  # 关联用户故事
    name = db.Column(db.String(256), nullable=False)  # 任务名称
    description = db.Column(db.Text, nullable=True)  # 任务描述
    status = db.Column(db.String(32), default='未开始')  # 状态：未开始、进行中、已完成等
    task_type = db.Column(db.String(64), nullable=True)  # 任务类型：界面设计、功能开发、功能测试等
    priority = db.Column(db.String(8), default='中')  # 优先级：高、中、低
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # 负责人
    start_date = db.Column(db.Date, nullable=True)  # 计划开始日期
    end_date = db.Column(db.Date, nullable=True)  # 计划结束日期
    actual_start_date = db.Column(db.Date, nullable=True)  # 实际开始日期
    actual_end_date = db.Column(db.Date, nullable=True)  # 实际结束日期
    estimated_hours = db.Column(db.Float, nullable=True) # 预估工时
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)  # 任务完成时间

    # 关联关系
    assignee = db.relationship('User', foreign_keys=[assignee_id], backref='assigned_tasks')
    user_story = db.relationship('UserStory', backref='tasks')

# 测试用例模型
class TestCase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.String(64), unique=True, nullable=True)  # 用例编号：项目简称-用户故事ID-001
    project_id = db.Column(db.Integer, db.ForeignKey('project_info.id'), nullable=False)  # 所属项目
    project_module = db.Column(db.String(256), nullable=True)  # 项目模块：菜单-页面
    sprint_id = db.Column(db.Integer, db.ForeignKey('sprint.id'), nullable=True)  # 所属迭代
    user_story_id = db.Column(db.Integer, db.ForeignKey('user_story.id'), nullable=True)  # 用户故事

    # 状态字段
    edit_status = db.Column(db.String(32), default='新增')  # 用例编辑状态：新增、修改、作废
    execution_status = db.Column(db.String(32), default='未开始')  # 用例执行状态：未开始、进行中、已完成
    test_result = db.Column(db.String(32), nullable=True)  # 测试结果：通过、失败、阻塞、取消

    # 用例基本信息
    case_type = db.Column(db.String(32), nullable=True)  # 测试用例类型：页面验证、功能验证、数据验证
    function_point = db.Column(db.String(64), nullable=True)  # 具体功能点
    title = db.Column(db.String(256), nullable=False)  # 用例标题
    precondition = db.Column(db.Text, nullable=True)  # 预置条件
    steps = db.Column(db.Text, nullable=True)  # 测试步骤
    expected_result = db.Column(db.Text, nullable=True)  # 预期结果
    actual_result = db.Column(db.Text, nullable=True)  # 实际结果
    test_environment = db.Column(db.String(256), nullable=True)  # 测试环境：浏览器版本、操作系统等

    # 优先级和自动化
    priority = db.Column(db.String(8), default='P3')  # 优先级：P0-P5
    is_automated = db.Column(db.Boolean, default=False)  # 是否自动化: 是、否

    # 人员和时间信息
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # 编写人
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 编写时间
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间
    tested_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # 测试人
    tested_at = db.Column(db.DateTime, nullable=True)  # 测试时间

    # 其他信息
    remarks = db.Column(db.Text, nullable=True)  # 备注

    # 关联关系
    project = db.relationship('ProjectInfo', foreign_keys=[project_id], backref='test_cases')
    sprint = db.relationship('Sprint', foreign_keys=[sprint_id], backref='test_cases')
    user_story = db.relationship('UserStory', foreign_keys=[user_story_id], backref='test_cases')
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_test_cases')
    tested_by = db.relationship('User', foreign_keys=[tested_by_id], backref='tested_test_cases')

# 原型图管理模型
class PrototypeImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_node_id = db.Column(db.Integer, db.ForeignKey('project_info.id'), nullable=False)  # 关联项目节点
    name = db.Column(db.String(128), nullable=False)  # 图片名称
    description = db.Column(db.Text, nullable=True)  # 图片描述
    file_path = db.Column(db.String(512), nullable=False)  # 文件存储路径
    file_size = db.Column(db.Integer, nullable=True)  # 文件大小（字节）
    mime_type = db.Column(db.String(64), nullable=True)  # 文件MIME类型
    version = db.Column(db.String(32), default='1.0')  # 版本号
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 上传者
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    project_node = db.relationship('ProjectInfo', backref='prototype_images')
    uploaded_by = db.relationship('User', backref='uploaded_prototypes')
    
    def __repr__(self):
        return f'<PrototypeImage {self.name}>'


# 缺陷模型
class Defect(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    defect_id = db.Column(db.String(64), unique=True, nullable=True)  # 缺陷编号
    title = db.Column(db.String(256), nullable=False)  # 标题（必填）
    project_id = db.Column(db.Integer, db.ForeignKey('project_info.id'), nullable=False)  # 所属项目（必填）
    sprint_id = db.Column(db.Integer, db.ForeignKey('sprint.id'), nullable=True)  # 所属迭代
    work_item_type = db.Column(db.String(32), default='defect', nullable=False)  # 工作项类型（必填）
    description = db.Column(db.Text, nullable=True)  # 缺陷描述：支持富文本编辑
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # 负责人：默认为创建者
    priority = db.Column(db.String(8), default='P3')  # 优先级：P0-P5
    is_online = db.Column(db.Boolean, default=False)  # 是否线上缺陷：默认否
    severity = db.Column(db.String(32), default='一般')  # 严重程度：致命，严重，一般，提示，建议，保留
    defect_type = db.Column(db.String(64), default='功能问题')  # 缺陷类型
    status = db.Column(db.String(32), default='待处理')  # 缺陷状态：默认为待处理
    resolver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # 解决者：默认为未设置
    resolution = db.Column(db.String(64), default='未设置')  # 处理结果：为空为未设置
    dev_team = db.Column(db.String(128), nullable=True)  # 开发团队
    collaborators = db.Column(db.String(256), nullable=True)  # 协助者：默认为未设置
    start_date = db.Column(db.Date, nullable=True)  # 开始日期：默认为未设置
    end_date = db.Column(db.Date, nullable=True)  # 结束日期：默认为未设置
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 创建人
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间

    # 关联关系
    project = db.relationship('ProjectInfo', foreign_keys=[project_id], backref='defects')
    sprint = db.relationship('Sprint', foreign_keys=[sprint_id], backref='defects')
    assignee = db.relationship('User', foreign_keys=[assignee_id], backref='assigned_defects')
    resolver = db.relationship('User', foreign_keys=[resolver_id], backref='resolved_defects')
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_defects')

    def __repr__(self):
        return f'<Defect {self.defect_id or self.title}>'