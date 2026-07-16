# dizical CloudRun Dockerfile
# Phase 0 spike: 把现有 FastAPI 后端打包进 Docker 镜像, 部署到腾讯云托管 (CloudRun)
# Python 3.12 + FastAPI + uvicorn, 跟本地开发一致

FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 系统依赖 (curl 用于健康检查, gcc 用于编译 pymysql 等 C 扩展)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 先 COPY requirements 单独装, 充分利用 Docker 缓存
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 再 COPY 整个项目
COPY . /app

# 设置 Python 路径 (让 uvicorn 能 import src.*)
ENV PYTHONPATH=/app
ENV PORT=80

# 健康检查 (CloudRun 用这个判断容器是否健康)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# 启动 FastAPI
# 注意: app 对象在 src/kid_app/app.py:app
CMD exec uvicorn src.kid_app.app:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --log-level info \
    --no-access-log