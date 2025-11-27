# RuoChat2 - 智能消息处理与自动回复系统

RuoChat2 是一个基于 AI 的智能消息处理和自动回复系统，结合了自然语言处理、记忆管理和任务调度等功能，能够实现智能化的微信消息交互。

## 系统概述

该系统完整呈现了一个**智能消息处理与自动回复系统**的核心业务逻辑，涵盖**触发方式、数据流转、AI决策、存储交互**四大核心模块，整体分为「系统配置初始化」「消息触发与处理」「定时任务执行」「回复任务触发与发送」四个关键阶段。

### 核心特点

1. **双触发模式**：支持「用户交互触发」（实时响应）和「自主定时触发」（批量处理）
2. **多层AI决策**：AI负责回复内容生成、记忆点判断、热点筛选、任务类型识别
3. **数据持久化**：所有关键数据（消息、记忆、任务、提示词）均写入数据库
4. **模块化设计**：通过容器节点整合多库资源，降低组件耦合度

## 系统架构

### 四大核心模块

#### 1. 触发机制
- **用户消息触发**：实时响应接收到的用户消息
- **自主触发**：系统主动执行的定时任务（每日 00:00 和 00:05）
- **回复任务触发**：执行队列中的回复任务

#### 2. 数据存储层（五个数据库）
- **提示词库**：存储角色设定和系统提示词
- **记忆库**：存储热点话题和用户记忆点（带强度/权重属性）
- **计划任务库**：存储每日计划任务
- **回复任务库**：存储待回复任务（用户触发和自主触发）
- **消息记录库**：存储所有交互消息（接收/发送）

#### 3. AI决策节点
系统使用多个 AI 决策点：
- 热点话题判断
- 回复内容和时机决策
- 记忆点检测（带强度/遗忘时间/权重）
- 每日任务规划
- 自主消息触发

#### 4. 上下文增强
在每个 AI 决策前，系统通过 Vertical Container 聚合器从相关数据库检索上下文，实现高效的多数据源整合。

## 技术栈

- **后端框架**：Django 4.2
- **数据库**：PostgreSQL 12+
- **AI服务**：OpenAI GPT-4
- **消息平台**：微信（基于 itchat）
- **任务调度**：APScheduler
- **Python版本**：3.8+

## 快速开始

### 方式一：Docker 部署（推荐）⭐

Docker 部署是最简单快速的方式，无需手动配置 Python 环境和数据库。

**Windows 用户：**
```batch
# 1. 安装 Docker Desktop
# 2. 双击运行 start.bat
start.bat

# 3. 选择 "1. 启动所有服务"
```

**Linux/macOS 用户：**
```bash
# 1. 安装 Docker
# 2. 配置环境变量
cp .env.example .env
nano .env  # 编辑配置

# 3. 启动系统
chmod +x start.sh
./start.sh start
```

详细说明请参阅：[Docker 快速启动指南](DOCKER_QUICKSTART.md) | [Docker 完整文档](DOCKER.md)

### 方式二：本地部署

适合需要自定义开发环境的用户。

#### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置必要的环境变量
# - DJANGO_SECRET_KEY
# - DB_* (数据库配置)
# - OPENAI_API_KEY
```

#### 3. 初始化数据库

```bash
# 运行数据库迁移
python manage.py migrate

# 初始化系统数据
python manage.py init_system

# 创建管理员账号
python manage.py createsuperuser
```

#### 4. 启动系统

```bash
# 启动微信监听服务
python manage.py start_wechat

# 或者在后台运行Django服务（可选）
python manage.py runserver
```

详细说明请参阅：[本地快速启动指南](QUICKSTART.md) | [完整部署文档](DEPLOYMENT.md)

## 主要功能

### 1. 智能消息处理

当接收到用户消息时，系统会：
- 自动记录消息到数据库
- 从多个数据源检索相关上下文
- 使用 AI 决定回复内容和回复时机
- 检测并存储对话中的记忆点
- 避免与其他自动回复任务冲突

### 2. 自主任务调度

系统会在特定时间自动执行：
- **每日 00:00**：根据记忆和历史生成全天计划任务
- **每日 00:05**：生成需要主动发送的消息
- **每分钟检查**：执行到期的回复任务

### 3. 记忆管理

系统维护一个智能记忆库：
- 自动识别值得记忆的信息
- 记忆带有强度、权重和遗忘时间属性
- 支持记忆强化机制
- 过期记忆自动淡出

### 4. 上下文感知

通过 Vertical Container 机制整合多源数据：
- 历史对话记录
- 相关记忆点
- 今日计划任务
- 待回复任务列表

## 管理命令

### 系统初始化

```bash
python manage.py init_system [--force]
```

初始化系统数据，包括默认提示词和必要目录。

### 启动微信监听

```bash
python manage.py start_wechat [--no-qr]
```

启动微信消息监听服务。首次运行需要扫码登录。

### 查看系统状态

```bash
python manage.py system_status
```

显示系统各模块的统计信息。

## 管理后台

访问 `http://localhost:8000/admin/` 登录管理后台，可以：
- 查看和管理所有数据库记录
- 配置人物设定和提示词
- 查看任务执行状态
- 管理记忆库

## API接口

系统提供 RESTful API 接口：

- `GET /api/status/` - 获取系统状态
- `POST /api/config/character/` - 设置人物设定
- `POST /api/config/hotspot/` - 添加热点话题
- `GET /api/tasks/planned/` - 获取计划任务列表
- `GET /api/tasks/reply/` - 获取回复任务列表
- `GET /api/memories/` - 获取记忆列表
- `GET /api/messages/` - 获取消息记录

## 项目结构

```
RuoChat2/
├── ruochat/                 # Django项目配置
│   ├── settings.py         # 项目设置
│   ├── urls.py             # URL路由
│   └── wsgi.py             # WSGI配置
├── core/                    # 核心应用
│   ├── models.py           # 数据模型
│   ├── views.py            # 视图函数
│   ├── admin.py            # 管理后台配置
│   ├── scheduler.py        # 任务调度器
│   ├── services/           # 业务逻辑层
│   │   ├── ai_service.py         # AI决策服务
│   │   ├── context_service.py    # 上下文检索服务
│   │   ├── wechat_service.py     # 微信服务
│   │   ├── message_handler.py    # 消息处理器
│   │   └── task_executor.py      # 任务执行器
│   └── management/         # 管理命令
│       └── commands/
├── logs/                    # 日志文件
├── requirements.txt        # Python依赖
├── .env.example            # 环境变量模板
├── DEPLOYMENT.md           # 部署文档
└── README.md               # 本文件
```

## 工作流程

### 阶段1：系统配置初始化
1. 配置人物设定 → 写入提示词库
2. AI判断热点话题 → 写入记忆库
3. 初始化触发模式

### 阶段2：用户消息处理
1. 接收消息 → 写入消息记录库
2. 检索上下文（Vertical Container）
3. AI决策回复内容和时间 → 写入回复任务库
4. AI检测记忆点 → 写入/强化记忆库
5. 同步调整其他自动回复任务

### 阶段3：自主定时任务
1. **00:00** - AI生成全天计划任务 → 写入计划任务库
2. **00:05** - AI生成自主触发消息 → 写入回复任务库

### 阶段4：回复任务执行
1. 定时检查待执行任务
2. 发送消息
3. 记录到消息记录库

## 配置说明

### 人物设定

在管理后台或通过 API 配置系统的人物设定，AI 会基于这个设定来生成回复：

```json
{
  "性格": "友好、热情、有耐心",
  "职业": "AI助手",
  "爱好": "帮助他人、学习新知识",
  "沟通风格": "简洁明了、富有同理心"
}
```

### OpenAI 模型选择

在 `.env` 文件中配置：

```env
OPENAI_MODEL=gpt-4-turbo-preview
# 或使用其他模型：gpt-4, gpt-3.5-turbo
```

## 部署

详细的部署指南请参阅 [DEPLOYMENT.md](DEPLOYMENT.md)，包括：
- 生产环境配置
- Supervisor/systemd 配置
- Nginx 反向代理
- 安全建议
- 数据备份策略

## 常见问题

### Q: 微信登录失败怎么办？
A: 检查网络连接，清除 `itchat.pkl` 缓存文件，重新运行 `start_wechat` 命令。

### Q: AI 回复不准确？
A: 调整人物设定和系统提示词，确保上下文信息充足。

### Q: 定时任务没有执行？
A: 检查日志文件，确认 Django 应用正常运行且 APScheduler 已启动。

### Q: 如何自定义 AI 决策逻辑？
A: 修改 `core/services/ai_service.py` 中的决策方法。

## 开发计划

- [ ] 支持更多消息平台（QQ、Telegram）
- [ ] 添加 Web UI 界面
- [ ] 实现向量数据库进行语义检索
- [ ] 支持多模态消息处理（图片、语音）
- [ ] 增强记忆管理（自动归类、关联分析）

## 许可证

本项目采用 MIT 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题或建议，请通过 GitHub Issues 联系。
