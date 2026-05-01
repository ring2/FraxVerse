# 碎片宇宙（FraxVerse）智能量化交易系统
> 万千心念皆碎片，一怀内观即宇宙
基于经验驱动型量化方法论的 A 股全自动智能量化交易系统。
## 技术栈
- 前端: React 18 + TypeScript + Vite + Ant Design 5.x
- 后端: FastAPI + Python 3.11
- 数据库: PostgreSQL 16 + Redis 7
- 部署: Docker + Docker Compose
## 开发
pip install -r requirements-dev.txt
pytest tests/ -v
ruff check .
mypy src/
## 架构
4进程合并方案: API Server :8000 | Scheduler | Stop-Loss Monitor | Frontend :3000
