# =============================================================================
# FraxVerse · 后端 Dockerfile
# FastAPI 服务（Python 3.11）— 手写精简依赖避免 pip install 超时
# =============================================================================

FROM python:3.11-slim-bookworm

WORKDIR /app

# pip 国内镜像（腾讯云内网加速）
RUN pip config set global.index-url http://mirrors.tencentyun.com/pypi/simple && \
    pip config set global.trusted-host mirrors.tencentyun.com

# 系统依赖 + 国内 apt 镜像加速
RUN sed -i 's/deb.debian.org/mirrors.tencentyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# 安装核心运行时依赖（手写列表，避免 requirements 173个包的 vnpy/langchain 等重型包）
# 不锁死版本号，让 pip 自动解析依赖树，避免冲突
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    sqlalchemy \
    asyncpg \
    psycopg2-binary \
    redis \
    httpx \
    pydantic \
    pydantic-settings \
    python-jose \
    passlib \
    bcrypt==4.0.1 \
    akshare \
    psutil \
    python-multipart \
    pytz \
    numpy \
    pandas \
    backtesting \
    alembic

# 复制项目代码（排除本地 requirements.txt 避免冲突）
COPY . .

# 开放端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/v1/health').read().decode())" || exit 1

# 启动
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
