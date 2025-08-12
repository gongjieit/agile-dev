# Agile Dev - 敏捷开发协作工具

Agile Dev 是一个基于 Flask 的敏捷开发协作工具，旨在支持团队进行高效的敏捷项目管理。

## 功能特性

- 用户注册与登录系统
- 功能点管理
- 故事点估算（计划扑克）
- 用户故事管理
- 迭代管理
- 任务管理
- 敏捷看板
- 燃尽图
- 产品待办列表管理
- 测试用例管理
- 知识库管理
- 用户权限管理
- 系统功能配置

## 技术栈

- 后端框架：[Flask](https://flask.palletsprojects.com/)
- 数据库：[MySQL](https://www.mysql.com/) / [PyMySQL](https://pymysql.readthedocs.io/)
- ORM：[Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/)
- 前端框架：[Bootstrap 5](https://getbootstrap.com/)

## 项目结构

```

agile-dev/
├── app.py                 # 应用主文件
├── config.py              # 配置文件
├── models.py              # 数据模型定义
├── decorators.py          # 自定义装饰器
├── utils.py               # 工具函数
├── routes/                # 路由处理模块
│   ├── auth.py            # 认证相关路由
│   ├── admin.py           # 管理员功能路由
│   ├── estimation.py       # 估算功能路由
│   ├── features.py        # 功能点管理路由
│   ├── user_stories.py    # 用户故事管理路由
│   ├── sprints.py         # 迭代管理路由
│   ├── tasks.py           # 任务管理路由
│   ├── kanban.py          # 敏捷看板路由
│   ├── knowledge.py       # 知识库管理路由
│   ├── users.py           # 用户管理路由
│   ├── system_features.py # 系统功能配置路由
│   ├── product_backlog.py # 产品待办列表路由
│   ├── test_cases.py      # 测试用例管理路由
│   ├── projects.py        # 项目管理路由
│   ├── roles.py           # 角色管理路由
│   └── ...
├── templates/             # HTML 模板文件
├── static/                # 静态资源文件
│   ├── bootstrap.min.css  # Bootstrap 样式文件
│   ├── bootstrap.bundle.min.js # Bootstrap JS 文件
│   ├── chart.js           # 图表库
│   ├── marked.min.js      # Markdown 解析库
│   ├── style.css          # 自定义样式
│   └── user_stories.css   # 用户故事页面样式
├── docs/                  # 文档文件
└── requirements.txt       # 项目依赖
```
## 安装与运行

### 环境要求

- Python 3.6+
- MySQL 5.7+

### 安装步骤

1. 克隆项目代码：
   ```bash
   git clone <项目地址>
   cd agile-dev
   ```
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 配置数据库：
   在环境变量中设置数据库连接信息：
   - `DB_HOST`: 数据库主机地址（默认: localhost）
   - `DB_USER`: 数据库用户名（默认: root）
   - `DB_PASSWORD`: 数据库密码（默认: 123456）
   - `MYSQL_DB`: 数据库名称（默认: agile_poker）
   - `DB_PORT`: 数据库端口（默认: 3306）

4. 初始化数据库：
   ```bash
   python app.py
   ```
5. 运行应用：
   ```bash
   python app.py
   ```
6. 访问应用：
   打开浏览器访问 `http://localhost:5000`

## 主要功能模块

### 1. 用户认证
- 用户注册与登录
- 管理员与普通用户权限区分
- Session 管理

### 2. 功能点估算（计划扑克）
- 创建估算回合
- 多人实时估算
- 估算结果展示与讨论
- 历史记录查看

### 3. 用户故事管理
- 用户故事创建与编辑
- 故事点分配
- 状态跟踪（待处理、开发中、测试中、已完成）
- 优先级管理

### 4. 迭代管理
- Sprint 创建与管理
- 迭代周期设置
- 待办事项分配
- 进度跟踪

### 5. 任务管理
- 任务创建、编辑和删除
- 任务分配给团队成员
- 任务状态管理（未开始、进行中、已完成）
- 任务优先级设置

### 6. 敏捷看板
- 可视化任务管理看板
- 拖拽任务以更新状态
- 按负责人筛选任务
- 迭代燃尽图展示进度

### 7. 产品待办列表
- 需求管理
- 需求状态跟踪
- 需求优先级设置

### 8. 测试用例管理
- 测试用例创建和维护
- 测试用例导入导出
- 测试执行记录

### 9. 知识库管理
- 敏捷开发相关知识文档
- 分类管理
- 创建与编辑功能

### 10. 系统管理
- 用户管理
- 角色管理
- 功能点管理
- 系统功能配置
- 项目信息树形结构管理

## 数据模型

主要的数据模型包括：

- [User](file://D:\projects\agile-dev\models.py#L5-L9): 用户信息（含管理员标记）
- [Role](file://D:\projects\agile-dev\models.py#L13-L25): 角色信息
- [UserRole](file://D:\projects\agile-dev\models.py#L29-L39): 用户角色关联
- [GameRound](file://D:\projects\agile-dev\models.py#L96-L104): 估算回合
- [Estimate](file://D:\projects\agile-dev\models.py#L157-L162): 估算记录
- [UserStory](file://D:\projects\agile-dev\models.py#L106-L118): 用户故事
- [Sprint](file://D:\projects\agile-dev\models.py#L122-L138): 迭代信息
- [SprintBacklog](file://D:\projects\agile-dev\models.py#L142-L154): 迭代待办事项
- [Task](file://D:\projects\agile-dev\models.py#L166-L187): 任务信息
- [ProductBacklog](file://D:\projects\agile-dev\models.py#L190-L210): 产品待办列表
- [TestCase](file://D:\projects\agile-dev\models.py#L214-L256): 测试用例
- [ProjectInfo](file://D:\projects\agile-dev\models.py#L71-L83): 项目信息树形结构
- [AgileKnowledge](file://D:\projects\agile-dev\models.py#L85-L94): 敏捷开发知识
- [SystemFeature](file://D:\projects\agile-dev\models.py#L56-L68): 系统功能配置

## 许可证

本项目为内部使用工具，保留所有权利。

## 开发说明

1. 前端使用 Bootstrap 5 实现响应式设计
2. 后端采用 Flask 蓝图(Blueprint)组织路由
3. 数据库使用 SQLAlchemy ORM 进行操作
4. 通过 Session 实现用户认证和权限控制
5. 使用 Jinja2 模板引擎渲染页面
6. 使用 Chart.js 实现数据可视化（燃尽图）

