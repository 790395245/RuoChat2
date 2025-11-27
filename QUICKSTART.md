# RuoChat2 快速启动指南

本指南将帮助你在 5 分钟内启动并运行 RuoChat2 系统。

## 前置要求

- Python 3.8 或更高版本
- PostgreSQL 12 或更高版本
- OpenAI API 密钥

## 步骤 1：安装 PostgreSQL（如果未安装）

### Windows
从官网下载并安装：https://www.postgresql.org/download/windows/

### macOS
```bash
brew install postgresql
brew services start postgresql
```

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

## 步骤 2：创建数据库

```bash
# 登录 PostgreSQL
sudo -u postgres psql  # Linux/macOS
# 或直接使用 psql 命令（Windows）

# 在 psql 命令行中执行：
CREATE DATABASE ruochat2;
CREATE USER ruochat_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE ruochat2 TO ruochat_user;
\q
```

## 步骤 3：安装 Python 依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 步骤 4：配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
# Windows: notepad .env
# Linux/macOS: nano .env
```

在 `.env` 文件中配置以下内容：

```env
# Django 配置
DJANGO_SECRET_KEY=your-random-secret-key-here  # 生成一个随机字符串
DEBUG=True

# PostgreSQL 数据库
DB_NAME=ruochat2
DB_USER=ruochat_user
DB_PASSWORD=your_password  # 替换为步骤2中设置的密码
DB_HOST=localhost
DB_PORT=5432

# OpenAI API
OPENAI_API_KEY=sk-your-api-key-here  # 替换为你的 OpenAI API 密钥
OPENAI_MODEL=gpt-4-turbo-preview

# 微信
WECHAT_ENABLED=True
```

> 提示：生成 Django 密钥的方法：
> ```python
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

## 步骤 5：初始化数据库

```bash
# 运行数据库迁移
python manage.py migrate

# 初始化系统数据
python manage.py init_system

# 创建管理员账号（可选）
python manage.py createsuperuser
```

## 步骤 6：启动系统

```bash
# 启动微信监听服务
python manage.py start_wechat
```

首次运行会显示二维码，使用微信扫码登录即可。

## 步骤 7：测试系统

登录成功后，系统会自动监听微信消息。你可以：

1. 发送消息给自己的微信（文件传输助手）
2. 系统会自动处理并在合适的时间回复
3. 查看日志文件 `logs/ruochat.log` 了解运行状态

## 常用命令

```bash
# 查看系统状态
python manage.py system_status

# 访问管理后台（需先启动 Django 开发服务器）
python manage.py runserver
# 然后访问 http://localhost:8000/admin/

# 重新初始化系统（会清除已有数据）
python manage.py init_system --force
```

## 配置人物设定

### 方法 1：通过管理后台
1. 启动服务：`python manage.py runserver`
2. 访问 http://localhost:8000/admin/
3. 登录后进入「提示词库」
4. 编辑「main_character」条目

### 方法 2：通过 API
```bash
curl -X POST http://localhost:8000/api/config/character/ \
  -H "Content-Type: application/json" \
  -d '{"content": "我是一个友好的AI助手，性格开朗..."}'
```

## 故障排除

### 问题 1：数据库连接失败
```bash
# 检查 PostgreSQL 是否运行
sudo systemctl status postgresql  # Linux
brew services list  # macOS

# 检查数据库配置
psql -U ruochat_user -d ruochat2 -h localhost
```

### 问题 2：微信登录失败
```bash
# 清除缓存文件
rm itchat.pkl

# 重新启动
python manage.py start_wechat
```

### 问题 3：OpenAI API 调用失败
- 检查 API 密钥是否正确
- 检查网络连接
- 确认 API 配额充足

### 问题 4：导入错误
```bash
# 确保在虚拟环境中
which python  # 应该指向 venv 中的 python

# 重新安装依赖
pip install -r requirements.txt --upgrade
```

## 下一步

- 阅读完整的 [README.md](README.md) 了解系统架构
- 查看 [DEPLOYMENT.md](DEPLOYMENT.md) 了解生产环境部署
- 通过管理后台配置更多提示词和记忆
- 自定义 AI 决策逻辑（编辑 `core/services/ai_service.py`）

## 获取帮助

如遇到问题：
1. 查看日志文件：`logs/ruochat.log`
2. 查阅 README.md 中的常见问题
3. 提交 GitHub Issue

祝你使用愉快！
