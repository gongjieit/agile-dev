#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
初始化系统功能菜单
"""

import sys
import os

from flask import redirect, session, url_for, flash

from utils import check_system_feature_access

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, SystemFeature

def init_system_features():
    # 检查权限
    if not check_system_feature_access(session, 'system_features.system_features'):
        return redirect(url_for('auth.index'))

    # 检查是否已初始化
    existing_features = SystemFeature.query.count()
    if existing_features > 0:
        flash('系统功能已初始化，无需重复操作！', 'warning')
        return redirect(url_for('system_features.system_features'))

    """初始化系统功能"""
    with app.app_context():
        # 定义系统功能列表
        features = [
            # 项目管理相关功能
            {
                'name': '项目管理',
                'description': '项目、菜单、页面结构管理',
                'route_name': 'projects.projects',
                'is_enabled': True,
                'is_public': False
            },
            
            # 用户故事管理相关功能
            {
                'name': '用户故事管理',
                'description': '用户故事的增删改查',
                'route_name': 'user_stories.user_stories',
                'is_enabled': True,
                'is_public': False
            },

            # 产品待办事项管理相关功能
            {
                'name': '产品待办事项',
                'description': '产品待办事项的增删改查',
                'route_name': 'product_backlog.product_backlog',
                'is_enabled': True,
                'is_public': False
            },
            
            # 迭代管理相关功能
            {
                'name': '迭代管理',
                'description': '迭代的增删改查',
                'route_name': 'sprints.sprints',
                'is_enabled': True,
                'is_public': False
            },
            
            # 任务管理相关功能
            {
                'name': '任务管理',
                'description': '任务的增删改查',
                'route_name': 'tasks.tasks',
                'is_enabled': True,
                'is_public': False
            },
            
            # 看板功能
            {
                'name': '敏捷看板',
                'description': '敏捷看板视图',
                'route_name': 'kanban.kanban',
                'is_enabled': True,
                'is_public': False
            },

            # 管理知识库
            {
                'name': '知识管理',
                'description': '管理知识库内容',
                'route_name': 'knowledge.manage',
                'is_enabled': True,
                'is_public': False
            },
            
            # 查看知识库
            {
                'name': '知识查看',
                'description': '查看知识库内容',
                'route_name': 'knowledge.knowledge_view',
                'is_enabled': True,
                'is_public': False
            },
            
            # 系统管理相关功能（仅管理员）
            {
                'name': '系统管理',
                'description': '用户和系统功能管理',
                'route_name': 'system_features.system_features',
                'is_enabled': True,
                'is_public': False
            },
            
            # 首页功能（公开）
            {
                'name': '首页',
                'description': '系统首页',
                'route_name': 'auth.index',
                'is_enabled': True,
                'is_public': True
            },
            
            # 登录功能（公开）
            {
                'name': '登录',
                'description': '用户登录',
                'route_name': 'auth.login',
                'is_enabled': True,
                'is_public': True
            },
            
            # 注册功能（公开）
            {
                'name': '注册',
                'description': '用户注册',
                'route_name': 'auth.register',
                'is_enabled': True,
                'is_public': True
            },

            # 角色管理功能
            {
                'name': '角色管理',
                'description': '角色的增删改查',
                'route_name': 'roles.roles',
                'is_enabled': True,
                'is_public': False
            },

            # 测试用例管理功能
            {
                'name': '测试用例管理',
                'description': '测试用例的增删改查、导入导出',
                'route_name': 'test_cases.test_cases',
                'is_enabled': True,
                'is_public': False
            },

            # 原型图管理功能
            {
                'name': '原型图管理',
                'description': '原型图上传、查看和管理',
                'route_name': 'prototype.prototype_list',
                'is_enabled': True,
                'is_public': False
            },

            # 缺陷管理功能
            {
                'name': '缺陷管理',
                'description': '缺陷的增删改查、导入导出',
                'route_name': 'defects.defects',
                'is_enabled': True,
                'is_public': False
            }
        ]
        
        # 添加或更新功能
        for feature_data in features:
            # 检查功能是否已存在
            feature = SystemFeature.query.filter_by(route_name=feature_data['route_name']).first()
            if feature:
                # 更新现有功能
                feature.name = feature_data['name']
                feature.description = feature_data['description']
                feature.is_enabled = feature_data['is_enabled']
                feature.is_public = feature_data['is_public']
                print(f"更新功能: {feature.name} ({feature.route_name})")
            else:
                # 创建新功能
                feature = SystemFeature(
                    name=feature_data['name'],
                    description=feature_data['description'],
                    route_name=feature_data['route_name'],
                    is_enabled=feature_data['is_enabled'],
                    is_public=feature_data['is_public']
                )
                db.session.add(feature)
                print(f"添加功能: {feature.name} ({feature.route_name})")
        
        # 提交更改
        db.session.commit()
        print("系统功能初始化完成!")

if __name__ == '__main__':
    init_system_features()
