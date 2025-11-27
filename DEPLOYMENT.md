# RuoChat2 部署指南

## 系统要求

- Python 3.8+
- PostgreSQL 12+
- 2GB+ RAM
- Linux/Windows/macOS

## 安装步骤

### 1. 克隆项目

```bash
git clone <repository-url>
cd RuoChat2
```

### 2. 创建虚拟环境

```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置PostgreSQL数据库

#### 安装PostgreSQL

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql

# Windows
# 从官网下载安装：https://www.postgresql.org/download/windows/
```

#### 创建数据库

```bash
# 登录PostgreSQL
sudo -u postgres psql

# 创建数据库和用户
CREATE DATABASE ruochat2;
CREATE USER ruochat_user WITH PASSWORD 'your_password';
ALTER ROLE ruochat_user SET client_encoding TO 'utf8';
ALTER ROLE ruochat_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE ruochat_user SET timezone TO 'Asia/Shanghai';
GRANT ALL PRIVILEGES ON DATABASE ruochat2 TO ruochat_user;

# 退出
\q
```

### 5. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env  # 或使用其他编辑器
```

必须配置的环境变量：

```env
# Django配置
DJANGO_SECRET_KEY=生成一个随机密钥
DEBUG=False

# PostgreSQL数据库
DB_NAME=ruochat2
DB_USER=ruochat_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# OpenAI API
OPENAI_API_KEY=sk-your-api-key-here

# 微信
WECHAT_ENABLED=True
```

生成Django密钥：

```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

### 6. 初始化数据库

```bash
# 运行数据库迁移
python manage.py migrate

# 初始化系统数据
python manage.py init_system

# 创建管理员账号
python manage.py createsuperuser
```

### 7. 收集静态文件（生产环境）

```bash
python manage.py collectstatic --noinput
```

## 运行系统

### 开发环境

```bash
# 启动Django开发服务器（可选）
python manage.py runserver

# 启动微信监听服务
python manage.py start_wechat
```

### 生产环境

#### 使用Supervisor管理进程

安装Supervisor：

```bash
# Ubuntu/Debian
sudo apt-get install supervisor

# macOS
brew install supervisor
```

创建配置文件 `/etc/supervisor/conf.d/ruochat.conf`：

```ini
[program:ruochat_django]
command=/path/to/venv/bin/gunicorn ruochat.wsgi:application --bind 0.0.0.0:8000 --workers 2
directory=/path/to/RuoChat2
user=your_user
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/path/to/RuoChat2/logs/gunicorn.log

[program:ruochat_wechat]
command=/path/to/venv/bin/python manage.py start_wechat
directory=/path/to/RuoChat2
user=your_user
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/path/to/RuoChat2/logs/wechat.log
```

启动服务：

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start ruochat_django
sudo supervisorctl start ruochat_wechat
```

#### 使用systemd管理进程（Linux）

创建服务文件 `/etc/systemd/system/ruochat-django.service`：

```ini
[Unit]
Description=RuoChat Django Service
After=network.target postgresql.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/RuoChat2
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn ruochat.wsgi:application --bind 0.0.0.0:8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

创建服务文件 `/etc/systemd/system/ruochat-wechat.service`：

```ini
[Unit]
Description=RuoChat WeChat Service
After=network.target postgresql.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/RuoChat2
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python manage.py start_wechat
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable ruochat-django
sudo systemctl enable ruochat-wechat
sudo systemctl start ruochat-django
sudo systemctl start ruochat-wechat

# 查看状态
sudo systemctl status ruochat-django
sudo systemctl status ruochat-wechat
```

## 配置Nginx反向代理（可选）

安装Nginx：

```bash
sudo apt-get install nginx
```

创建配置文件 `/etc/nginx/sites-available/ruochat`：

```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/RuoChat2/staticfiles/;
    }

    location /media/ {
        alias /path/to/RuoChat2/media/;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/ruochat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 管理命令

### 系统状态查看

```bash
python manage.py system_status
```

### 初始化系统

```bash
python manage.py init_system --force  # 强制重新初始化
```

### 启动微信监听

```bash
python manage.py start_wechat
python manage.py start_wechat --no-qr  # 不显示命令行二维码
```

## 访问管理后台

访问 `http://your_domain.com/admin/` 使用创建的超级用户账号登录。

## 日志文件

日志文件位于 `logs/` 目录：

- `ruochat.log` - 应用主日志
- `gunicorn.log` - Gunicorn服务器日志
- `wechat.log` - 微信服务日志

## 故障排除

### 1. 数据库连接失败

检查PostgreSQL服务是否运行：

```bash
sudo systemctl status postgresql
```

检查数据库配置和用户权限。

### 2. 微信登录失败

- 确保网络连接正常
- 检查itchat库版本
- 清除缓存文件：`rm itchat.pkl`

### 3. 定时任务不执行

- 检查Django应用是否正常启动
- 查看日志文件中的错误信息
- 确认APScheduler已正确配置

### 4. OpenAI API调用失败

- 检查API密钥是否正确
- 检查网络连接
- 检查API配额

## 安全建议

1. **生产环境配置**
   - 设置 `DEBUG=False`
   - 使用强密钥 `DJANGO_SECRET_KEY`
   - 配置 `ALLOWED_HOSTS`

2. **数据库安全**
   - 使用强密码
   - 限制数据库访问IP
   - 定期备份数据

3. **API密钥保护**
   - 不要将 `.env` 文件提交到版本控制
   - 使用环境变量或密钥管理服务

4. **防火墙配置**
   - 只开放必要的端口（80, 443）
   - 限制数据库端口访问

## 数据备份

### PostgreSQL备份

```bash
# 备份
pg_dump -U ruochat_user ruochat2 > backup_$(date +%Y%m%d).sql

# 恢复
psql -U ruochat_user ruochat2 < backup_20231201.sql
```

### 定期备份脚本

创建备份脚本 `backup.sh`：

```bash
#!/bin/bash
BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 备份数据库
pg_dump -U ruochat_user ruochat2 > "$BACKUP_DIR/db_$DATE.sql"

# 压缩
gzip "$BACKUP_DIR/db_$DATE.sql"

# 删除7天前的备份
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +7 -delete

echo "Backup completed: db_$DATE.sql.gz"
```

添加到crontab：

```bash
# 每天凌晨2点备份
0 2 * * * /path/to/backup.sh
```

## 性能优化

1. **数据库优化**
   - 定期执行 `VACUUM` 和 `ANALYZE`
   - 创建必要的索引
   - 使用连接池

2. **缓存配置**
   - 使用Redis缓存（可选）
   - 配置Django缓存

3. **静态文件**
   - 使用CDN托管静态文件
   - 启用Gzip压缩

## 更新升级

```bash
# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt --upgrade

# 运行数据库迁移
python manage.py migrate

# 重启服务
sudo systemctl restart ruochat-django
sudo systemctl restart ruochat-wechat
```

## 技术支持

如遇问题，请查看：
- 日志文件
- GitHub Issues
- 项目文档
