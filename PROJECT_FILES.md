# 📋 项目文件清单

所有创建的文件及其用途说明。

## 📦 核心项目文件

### Django 项目配置
- `manage.py` - Django 管理脚本
- `ruochat/__init__.py` - 项目包初始化
- `ruochat/settings.py` - Django 配置（数据库、中间件、应用等）
- `ruochat/urls.py` - URL 路由配置
- `ruochat/wsgi.py` - WSGI 配置（部署用）
- `ruochat/asgi.py` - ASGI 配置（异步支持）

### 核心应用
- `core/__init__.py` - 应用包初始化
- `core/apps.py` - 应用配置（启动时加载调度器）
- `core/models.py` - 5个数据库模型定义
- `core/views.py` - API 视图函数
- `core/urls.py` - API URL 路由
- `core/admin.py` - Django 管理后台配置
- `core/signals.py` - 信号处理器
- `core/scheduler.py` - APScheduler 任务调度器

### 服务层（核心业务逻辑）
- `core/services/__init__.py` - 服务包初始化
- `core/services/ai_service.py` - AI 决策服务（OpenAI 集成）
- `core/services/context_service.py` - 上下文检索服务（Vertical Container）
- `core/services/wechat_service.py` - 微信消息服务（itchat 集成）
- `core/services/message_handler.py` - 用户消息处理流程
- `core/services/task_executor.py` - 回复任务执行器

### 管理命令
- `core/management/__init__.py` - 管理命令包初始化
- `core/management/commands/__init__.py` - 命令包初始化
- `core/management/commands/init_system.py` - 系统初始化命令
- `core/management/commands/start_wechat.py` - 启动微信监听命令
- `core/management/commands/system_status.py` - 系统状态查看命令

## 🐳 Docker 相关文件

### Docker 配置
- `Dockerfile` - Docker 镜像构建文件
- `docker-compose.yml` - Docker Compose 编排配置
- `.dockerignore` - Docker 构建忽略文件
- `init-db.sql` - PostgreSQL 初始化脚本

### 启动脚本
- `start.bat` - Windows 一键启动脚本（交互式菜单）
- `start.sh` - Linux/macOS 一键启动脚本（支持命令行参数）

## 📚 文档文件

### 主要文档
- `README.md` - 项目主文档（系统介绍、功能说明、API 文档）
- `CLAUDE.md` - 项目设计文档（系统架构、流程说明）

### 部署文档
- `DEPLOYMENT.md` - 完整部署指南（生产环境、Nginx、Supervisor）
- `DOCKER.md` - Docker 详细部署文档（监控、优化、故障排除）
- `QUICKSTART.md` - 本地快速启动指南（5分钟上手）
- `DOCKER_QUICKSTART.md` - Docker 快速启动指南（3步启动）

### 项目说明
- `PROJECT_FILES.md` - 本文件（文件清单）

## ⚙️ 配置文件

### 环境配置
- `.env.example` - 环境变量模板
- `.env` - 实际环境变量（需自行创建，不入 Git）

### 依赖管理
- `requirements.txt` - Python 依赖列表

### Git 配置
- `.gitignore` - Git 忽略文件列表

## 📊 项目统计

### 代码文件统计
- Python 文件：~25 个
- 配置文件：~10 个
- 文档文件：~7 个
- 脚本文件：2 个

### 代码行数估算（不含空行和注释）
- 核心代码：~3000 行
- 配置文件：~500 行
- 文档内容：~2000 行
- 总计：~5500 行

## 🎯 关键文件速查

### 需要首先配置的文件
1. `.env` - 环境变量（从 .env.example 复制）
2. `ruochat/settings.py` - 已配置好，通常无需修改

### 需要理解的核心文件
1. `core/models.py` - 数据库结构
2. `core/services/ai_service.py` - AI 决策逻辑
3. `core/services/message_handler.py` - 消息处理流程
4. `core/scheduler.py` - 定时任务配置

### 需要运行的脚本
1. `start.bat` (Windows) 或 `start.sh` (Linux/macOS)
2. `manage.py` - Django 管理命令

## 📁 运行时生成的目录/文件

这些文件/目录在运行时自动创建，不需要手动创建：

### 目录
- `logs/` - 日志文件目录
- `staticfiles/` - 收集的静态文件
- `media/` - 上传的媒体文件
- `wechat_cache/` - 微信缓存目录
- `backups/` - 数据库备份目录（使用备份脚本后生成）

### 文件
- `itchat.pkl` - 微信登录缓存
- `QR.png` - 微信登录二维码
- `logs/ruochat.log` - 应用日志
- `db.sqlite3` - SQLite 数据库（如果使用 SQLite）

### Docker 卷
- `ruochat2_postgres_data` - PostgreSQL 数据
- `ruochat2_static_volume` - 静态文件
- `ruochat2_media_volume` - 媒体文件
- `ruochat2_logs_volume` - 日志文件
- `ruochat2_wechat_cache` - 微信缓存

## 🔧 文件修改指南

### 可以安全修改的文件
- `.env` - 环境变量配置
- `core/services/ai_service.py` - 自定义 AI 决策逻辑
- `core/management/commands/*.py` - 添加自定义管理命令

### 需要谨慎修改的文件
- `core/models.py` - 修改后需要运行 `makemigrations` 和 `migrate`
- `docker-compose.yml` - 修改服务配置
- `ruochat/settings.py` - Django 核心配置

### 不建议修改的文件
- `manage.py` - Django 标准管理脚本
- `core/apps.py` - 应用启动配置（除非了解启动流程）
- `Dockerfile` - Docker 镜像构建（除非需要额外依赖）

## 📖 文件阅读顺序建议

对于新用户，建议按以下顺序阅读文件：

### 第一步：了解项目
1. `README.md` - 项目概述
2. `CLAUDE.md` - 系统设计

### 第二步：快速启动
3. `DOCKER_QUICKSTART.md` - Docker 快速启动
   或 `QUICKSTART.md` - 本地快速启动

### 第三步：理解架构
4. `core/models.py` - 数据库结构
5. `core/services/ai_service.py` - AI 决策
6. `core/services/message_handler.py` - 消息流程
7. `core/scheduler.py` - 定时任务

### 第四步：深入部署
8. `DOCKER.md` - Docker 部署详解
9. `DEPLOYMENT.md` - 生产环境部署

## 🎨 项目结构可视化

```
RuoChat2/
├── 📄 管理文件
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   └── .gitignore
│
├── 🐳 Docker 文件
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .dockerignore
│   ├── init-db.sql
│   ├── start.bat
│   └── start.sh
│
├── 📚 文档文件
│   ├── README.md
│   ├── CLAUDE.md
│   ├── DEPLOYMENT.md
│   ├── DOCKER.md
│   ├── QUICKSTART.md
│   ├── DOCKER_QUICKSTART.md
│   └── PROJECT_FILES.md
│
├── ⚙️ Django 项目
│   └── ruochat/
│       ├── __init__.py
│       ├── settings.py
│       ├── urls.py
│       ├── wsgi.py
│       └── asgi.py
│
└── 🎯 核心应用
    └── core/
        ├── 📊 数据层
        │   ├── models.py
        │   └── admin.py
        │
        ├── 🌐 视图层
        │   ├── views.py
        │   └── urls.py
        │
        ├── 🔧 服务层
        │   └── services/
        │       ├── ai_service.py
        │       ├── context_service.py
        │       ├── wechat_service.py
        │       ├── message_handler.py
        │       └── task_executor.py
        │
        ├── ⏰ 任务调度
        │   └── scheduler.py
        │
        └── 🛠️ 管理命令
            └── management/
                └── commands/
                    ├── init_system.py
                    ├── start_wechat.py
                    └── system_status.py
```

---

最后更新：2025-11-25
