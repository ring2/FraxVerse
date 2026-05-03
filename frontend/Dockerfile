# =============================================================================
# FraxVerse · 前端 Dockerfile
# Vite + React 构建，Nginx 托管
# =============================================================================

FROM node:20-alpine AS builder

WORKDIR /app

# 安装依赖（利用 Docker 缓存层，宽松处理 peer dep 兼容性）
COPY package.json package-lock.json* ./
RUN npm ci --legacy-peer-deps

# 复制源码
COPY . .

# 构建生产版本
RUN npm run build

# =============================================================================
# 生产阶段 — Nginx 托管静态文件
# =============================================================================

FROM nginx:alpine AS runtime

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx 配置（前端 SPA + /api 反向代理）
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
