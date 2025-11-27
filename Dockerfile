# 使用 Python 3.11 基础镜像（国内镜像源）
FROM docker.1ms.run/python:3.11-slim

# 设置环境变量（整合时区，提前设置 DEBIAN_FRONTEND 避免交互）
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    # pip 清华镜像源
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

# 设置工作目录
WORKDIR /app

# 替换 Ubuntu 清华镜像源（适配 slim 镜像的 sources.list 结构）
RUN sed -i.bak \
    -e 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' \
    -e 's|security.debian.org|mirrors.tuna.tsinghua.edu.cn/debian-security|g' \
    /etc/apt/sources.list.d/debian.sources || \
    # 兼容旧版 slim 镜像的 sources.list 格式
    sed -i.bak \
    -e 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' \
    -e 's|security.debian.org/debian-security|mirrors.tuna.tsinghua.edu.cn/debian-security|g' \
    /etc/apt/sources.list

# 安装系统依赖（适配 slim 镜像，补充 libjpeg62-turbo-dev 兼容）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    libpq-dev \
    libfreetype6-dev \
    libjpeg62-turbo-dev \
    libpng-dev \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

# 复制依赖文件（先复制 requirements.txt 利用镜像分层缓存）
COPY requirements.txt .

# 安装 Python 依赖（升级 pip + 清华源）
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# 复制项目文件
COPY . .

# 创建必要的目录（统一权限，避免运行时权限问题）
RUN mkdir -p logs media staticfiles wechat_cache \
    && chmod 755 logs media staticfiles wechat_cache

# 收集静态文件（捕获错误但提示，避免静默失败）
RUN python manage.py collectstatic --noinput || \
    (echo "警告：静态文件收集失败，可能影响运行" && true)

# 暴露端口
EXPOSE 8000

# 健康检查（适配 gunicorn 启动特性，延长启动周期）
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/status/ || exit 1

# 默认命令（优化 gunicorn 配置，增加超时参数）
CMD ["gunicorn", "ruochat.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "60", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]