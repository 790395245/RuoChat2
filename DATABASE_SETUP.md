# RuoChat2 数据库初始化指南

本文档详细说明如何初始化数据库并预填入必要的数据，确保系统可以正常启动。

## 🚀 快速开始（Docker方式 - 推荐）

这是最简单的方式，Docker会自动处理数据库和所有依赖。

### 1. 一键启动所有服务

```bash
# 启动所有服务（数据库、Web、微信）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

Docker Compose会自动完成以下操作：
- ✓ 创建PostgreSQL数据库容器
- ✓ 初始化数据库（执行init-db.sql）
- ✓ 运行数据库迁移（migrate）
- ✓ 初始化系统数据（init_system）
- ✓ 启动Web服务
- ✓ 启动微信服务

### 2. 验证系统配置

```bash
# 进入Web容器
docker-compose exec web python manage.py check_config

# 查看系统状态
curl http://localhost:8000/api/status/
```

### 3. 查看微信登录二维码

在浏览器访问：`http://localhost:8000/api/wechat/qr/`

---

## 💻 手动安装方式

如果你不使用Docker，可以手动设置数据库和系统。

### 第一步：安装PostgreSQL

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### macOS
```bash
brew install postgresql
brew services start postgresql
```

#### Windows
下载并安装：https://www.postgresql.org/download/windows/

### 第二步：创建数据库和用户

```bash
# 切换到postgres用户
sudo -u postgres psql

# 在PostgreSQL命令行中执行：
CREATE DATABASE ruochat2;
CREATE USER ruochat_user WITH PASSWORD 'Eq021793';
ALTER DATABASE ruochat2 OWNER TO ruochat_user;
GRANT ALL PRIVILEGES ON DATABASE ruochat2 TO ruochat_user;

# 退出PostgreSQL
\q
```

### 第三步：配置.env文件

确保`.env`文件包含正确的数据库配置：

```env
# 数据库配置
DB_NAME=ruochat2
DB_USER=ruochat_user
DB_PASSWORD=Eq021793
DB_HOST=localhost  # 注意：本地部署使用localhost
DB_PORT=5432

# OpenAI配置（必须）
OPENAI_API_KEY=你的API密钥
OPENAI_MODEL=Qwen/Qwen3-8B
OPENAI_API_BASE=https://api.siliconflow.cn/v1

# 微信配置
WECHAT_ENABLED=True
```

### 第四步：安装Python依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 第五步：初始化数据库

```bash
# 1. 运行数据库迁移（创建表结构）
python manage.py migrate

# 2. 初始化系统数据（创建默认配置和提示词）
python manage.py init_system

# 3. 可选：添加示例数据（用于测试）
python manage.py init_system --with-examples

# 4. 检查配置是否正确
python manage.py check_config
```

### 第六步：创建管理员账户（可选）

```bash
python manage.py createsuperuser
```

### 第七步：启动服务

```bash
# 启动Web服务
python manage.py runserver

# 在另一个终端启动微信服务
python manage.py start_wechat
```

---

## 📊 数据库表结构说明

系统包含5个核心数据库表：

### 1. prompt_library（提示词库）
存储人物设定和系统提示词
- 默认包含：1个人物设定 + 4个系统提示词

### 2. memory_library（记忆库）
存储热点话题和用户记忆点
- 初始为空，运行时动态添加

### 3. planned_task（计划任务库）
存储全天计划任务
- 初始为空，每天00:00自动生成

### 4. reply_task（回复任务库）
存储待回复任务
- 初始为空，接收消息时动态创建

### 5. message_record（消息记录库）
存储所有消息交互
- 初始为空，运行时记录

---

## 🔍 验证和排查

### 检查数据库连接

```bash
# 使用psql连接数据库
psql -h localhost -U ruochat_user -d ruochat2

# 查看所有表
\dt

# 查看提示词库数据
SELECT category, key FROM prompt_library;

# 退出
\q
```

### 检查系统配置

```bash
# 运行配置检查命令
python manage.py check_config
```

输出应该显示：
```
✓ SECRET_KEY: 已配置
✓ 数据库连接: 成功
✓ OPENAI_API_KEY: sk-xxxx...xxxx
✓ 人物设定: 1 个
✓ 系统提示词: 4 个
```

### 查看初始数据

```bash
# 查看提示词库
python manage.py shell
>>> from core.models import PromptLibrary
>>> PromptLibrary.objects.all()
>>> exit()
```

### 常见问题

#### 1. 数据库连接失败
```
错误: could not connect to server
解决:
- 检查PostgreSQL是否运行: sudo systemctl status postgresql
- 检查.env中的DB_HOST（本地用localhost，Docker用postgres）
- 检查数据库密码是否正确
```

#### 2. 表不存在
```
错误: relation "prompt_library" does not exist
解决: python manage.py migrate
```

#### 3. 没有初始数据
```
错误: 人物设定未配置
解决: python manage.py init_system
```

#### 4. OpenAI配置错误
```
错误: OPENAI_API_KEY未配置
解决:
- 编辑.env文件
- 添加有效的API密钥
```

---

## 🎯 验证系统正常运行

### 1. Web服务正常
```bash
curl http://localhost:8000/api/status/
```

应该返回：
```json
{
  "status": "running",
  "prompts_count": 5,
  "memories_count": 0,
  "planned_tasks_count": 0,
  "reply_tasks_count": 0,
  "messages_count": 0
}
```

### 2. 微信二维码显示
浏览器访问：`http://localhost:8000/api/wechat/qr/`

应该看到一个漂亮的页面显示二维码。

### 3. 数据库数据正常
```bash
python manage.py check_config
```

所有检查项都应该显示 ✓（绿色勾号）。

---

## 🔄 重置数据库（可选）

如果需要完全重置数据库：

### Docker方式
```bash
# 停止并删除所有容器和卷
docker-compose down -v

# 重新启动
docker-compose up -d
```

### 手动方式
```bash
# 删除数据库
sudo -u postgres psql
DROP DATABASE ruochat2;
CREATE DATABASE ruochat2;
ALTER DATABASE ruochat2 OWNER TO ruochat_user;
\q

# 重新迁移和初始化
python manage.py migrate
python manage.py init_system --with-examples
```

---

## 📝 管理命令总览

| 命令 | 说明 |
|------|------|
| `python manage.py migrate` | 创建/更新数据库表结构 |
| `python manage.py init_system` | 初始化系统数据 |
| `python manage.py init_system --force` | 强制重新初始化（覆盖已有数据） |
| `python manage.py init_system --with-examples` | 初始化并添加示例数据 |
| `python manage.py check_config` | 检查系统配置 |
| `python manage.py createsuperuser` | 创建管理员账户 |
| `python manage.py runserver` | 启动Web服务 |
| `python manage.py start_wechat` | 启动微信服务 |

---

## 🎉 完成！

现在你的RuoChat2系统应该已经完全初始化并可以正常运行了。

下一步：
1. 访问 `http://localhost:8000/api/wechat/qr/` 扫码登录微信
2. 发送消息测试系统响应
3. 查看日志了解系统运行情况：`docker-compose logs -f wechat`
