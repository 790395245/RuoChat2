# RuoChat2 - 智能消息处理与自动回复系统

RuoChat2 是一个基于 AI 的智能消息处理和自动回复系统，支持多用户管理，结合自然语言处理、记忆管理和任务调度，通过 Webhook 方式与 Synology Chat 等消息平台集成。

## 系统概述

该系统实现了一个**智能消息处理与自动回复系统**的核心业务逻辑，涵盖**触发方式、数据流转、AI决策、存储交互**四大核心模块。

### 核心特点

1. **多用户支持**：每个聊天用户独立管理，拥有独立的提示词、记忆、任务等数据
2. **双触发模式**：支持「用户交互触发」（实时响应）和「自主定时触发」（主动关怀）
3. **多层AI决策**：AI负责回复内容生成、记忆点判断、任务规划
4. **数据持久化**：所有关键数据均写入 PostgreSQL 数据库
5. **Webhook集成**：通过 Webhook 与 Synology Chat 等平台无缝对接

## 系统架构

### 四大核心模块

#### 1. 触发机制
- **用户消息触发**：通过 Webhook 接收用户消息，实时响应
- **自主触发**：系统主动执行的定时任务（每日 00:00 和 00:05）
- **回复任务触发**：每分钟检查并执行队列中的回复任务

#### 2. 数据存储层（五个数据表）
| 数据表 | 说明 |
|--------|------|
| ChatUser | 聊天用户，支持多用户独立管理 |
| PromptLibrary | 提示词库，存储角色设定和系统提示词 |
| MemoryLibrary | 记忆库，存储用户记忆点（带强度/权重属性） |
| PlannedTask | 计划任务库，存储每日计划任务 |
| ReplyTask | 回复任务库，存储待回复任务 |
| MessageRecord | 消息记录库，存储所有交互消息 |

#### 3. AI决策节点
- 回复内容和时机决策
- 记忆点检测（带强度/遗忘时间/权重）
- 每日任务规划
- 自主消息生成

#### 4. 上下文增强
在每个 AI 决策前，系统从相关数据库检索上下文（历史对话、相关记忆、计划任务等）。

## 技术栈

- **后端框架**：Django 4.2
- **数据库**：PostgreSQL 12+
- **AI服务**：OpenAI API（支持兼容接口如 SiliconFlow）
- **消息平台**：Synology Chat（通过 Webhook）
- **任务调度**：APScheduler
- **Python版本**：3.8+

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
```

主要配置项：

```env
# Django
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True

# 数据库
DB_NAME=ruochat2
DB_USER=ruochat_user
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# OpenAI API（支持兼容接口）
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_API_BASE=https://api.openai.com/v1  # 可选，自定义接口

# Webhook（Synology Chat）
WEBHOOK_URL=https://your-nas/webapi/...
WEBHOOK_TOKEN=  # 可选
```

### 3. 初始化数据库

```bash
# 运行数据库迁移
python manage.py migrate

# 初始化系统数据
python manage.py init_system

# 创建管理员账号
python manage.py createsuperuser
```

### 4. 启动系统

```bash
# 启动 Django 服务
python manage.py runserver 0.0.0.0:8000
```

系统启动后会自动启动定时任务调度器。

## 管理命令

### 系统初始化

```bash
# 基础初始化
python manage.py init_system

# 强制重新初始化
python manage.py init_system --force

# 添加示例数据
python manage.py init_system --with-examples
```

### 配置检查

```bash
python manage.py check_config
```

检查内容包括：
- Django 基础配置
- 数据库连接
- OpenAI API 配置
- Webhook 配置
- 文件系统权限

### 查看系统状态

```bash
python manage.py system_status
```

### 重置数据库

```bash
python manage.py reset_database
```

## 管理后台

访问 `http://localhost:8000/admin/` 登录管理后台。

### 功能特性

- **列表页编辑**：支持直接在列表页修改字段
- **批量操作**：激活/禁用用户、强化记忆、重试任务等
- **可视化展示**：状态徽章、记忆强度进度条
- **多条件筛选**：按用户、类型、状态、时间筛选

### 可管理的数据

| 模块 | 列表页可编辑字段 |
|------|------------------|
| 聊天用户 | 用户名、昵称、是否激活 |
| 提示词库 | 类别、标识、是否激活 |
| 记忆库 | 权重、类型、遗忘时间 |
| 计划任务 | 状态、类型、计划时间 |
| 回复任务 | 状态、触发类型、计划时间 |

## Webhook 接口

### 接收消息

```
POST /webhook/incoming/
Content-Type: application/json

{
    "user_id": 123,
    "username": "用户名",
    "text": "消息内容",
    "post_id": "xxx",
    "timestamp": "xxx"
}
```

### 系统状态

```
GET /api/status/
```

## 工作流程

### 阶段1：用户消息处理
1. Webhook 接收消息 → 识别/创建用户 → 写入消息记录库
2. 检索用户相关上下文
3. AI 决策回复内容和时间 → 写入回复任务库
4. AI 检测记忆点 → 写入/强化记忆库

### 阶段2：自主定时任务
- **00:00** - AI 为每个活跃用户生成全天计划任务
- **00:05** - AI 为每个活跃用户生成自主触发消息

### 阶段3：回复任务执行
1. 每分钟检查待执行任务
2. 发送消息给任务所属用户
3. 记录到消息记录库

## 项目结构

```
RuoChat2/
├── ruochat/                 # Django 项目配置
│   ├── settings.py         # 项目设置
│   ├── urls.py             # URL 路由
│   └── wsgi.py             # WSGI 配置
├── core/                    # 核心应用
│   ├── models.py           # 数据模型
│   ├── views.py            # 视图函数
│   ├── admin.py            # 管理后台配置
│   ├── scheduler.py        # 任务调度器
│   ├── services/           # 业务逻辑层
│   │   ├── ai_service.py         # AI 决策服务
│   │   ├── context_service.py    # 上下文检索服务
│   │   ├── webhook_service.py    # Webhook 服务
│   │   ├── message_handler.py    # 消息处理器
│   │   └── task_executor.py      # 任务执行器
│   └── management/         # 管理命令
│       └── commands/
│           ├── init_system.py
│           ├── check_config.py
│           ├── system_status.py
│           └── reset_database.py
├── logs/                    # 日志文件
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量模板
└── README.md               # 本文件
```

## Docker 部署

```bash
# 启动服务
docker-compose up -d

# 初始化
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py init_system
docker-compose exec web python manage.py createsuperuser

# 查看日志
docker-compose logs -f
```

## 常见问题

### Q: 数据库连接失败？
A: 检查 `.env` 中的数据库配置，确保 PostgreSQL 服务正在运行。

### Q: AI 回复不准确？
A: 在管理后台调整用户的提示词设定，确保上下文信息充足。

### Q: 定时任务没有执行？
A: 检查日志确认 APScheduler 已启动，运行 `python manage.py system_status` 查看状态。

### Q: 如何为新用户配置提示词？
A: 在管理后台的「提示词库」中为该用户添加 category=character 的提示词。

### Q: 自主消息发送给了错误的用户？
A: 确保每个回复任务都关联了正确的用户，系统会自动发送给任务所属用户。

## 许可证

本项目采用 MIT 许可证。
