# Alembic 数据库迁移指南

## 快速命令

```bash
# 查看当前版本
PYTHONPATH=. .venv/bin/alembic current

# 生成新的迁移（修改 models.py 后运行）
PYTHONPATH=. .venv/bin/alembic revision --autogenerate -m "描述你的变更"

# 预览 SQL（不执行）
PYTHONPATH=. .venv/bin/alembic upgrade head --sql

# 执行迁移到最新版本
PYTHONPATH=. .venv/bin/alembic upgrade head

# 回滚一步
PYTHONPATH=. .venv/bin/alembic downgrade -1

# 查看历史
PYTHONPATH=. .venv/bin/alembic history
```

## 工作流程

1. 修改 `src/db/models.py`（添加/修改/删除表或字段）
2. 生成迁移：`alembic revision --autogenerate -m "做什么"`  
3. **审查**生成的迁移脚本（`alembic/versions/xxx.py`），确认没有误操作
4. 执行：`alembic upgrade head`
5. 提交迁移脚本到 Git

## 注意事项

- **不要在迁移脚本中锁死版本号**，Alembic 依赖 `down_revision` 链表  
- 第一次迁移已生成（`e8e232332b1d_初始表结构_26张业务表.py`）  
- 迁移脚本必须提交到 Git，其他开发者直接 `alembic upgrade head` 即可  
- 生产环境执行前先用 `--sql` 预览
