Task 模型包含以下字段：

1. task_id：任务编号，如 Ta001，类型为字符串，唯一且可为空
2. user_story_id：外键，关联到 UserStory 模型的 id 字段
3. name：任务名称，如"周报界面设计"，类型为字符串
4. description：任务描述，文本类型，可为空
5. status：任务状态，默认为"未开始"，可选值包括"未开始"、"进行中"、"已完成"等
6. task_type：任务类型，如"界面设计"、"功能开发"、"功能测试"等
7. priority：优先级，默认为"中"，可选值为"高"、"中"、"低"
8. assignee_id：外键，关联到 User 模型的 id 字段，表示负责人
9. start_date：任务计划开始日期，日期类型
10. end_date：任务计划结束日期，日期类型
11. created_at：创建时间，默认为当前时间
12. updated_at：更新时间，默认为当前时间并会在更新时自动刷新

Task 与 User 和 UserStory 模型的关联关系：

1. 通过 assignee 属性关联到 User 模型
2. 通过 user_story 属性关联到 UserStory 模型
3. 在 User 模型中添加了反向引用 assigned_tasks
4. 在 UserStory 模型中添加了反向引用 tasks
