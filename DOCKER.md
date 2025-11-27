# RuoChat2 Docker 部署指南

本指南介绍如何使用 Docker 和 Docker Compose 一键部署 RuoChat2 系统。

## 前置要求

### Windows
- Docker Desktop for Windows 4.0+
- Windows 10/11 或 Windows Server 2019+

### Linux
- Docker Engine 20.10+
- Docker Compose V2

### macOS
- Docker Desktop for Mac 4.0+

## 快速开始

### Windows 用户

1. **安装 Docker Desktop**
   - 下载：https://www.docker.com/products/docker-desktop
   - 安装后确保 Docker Desktop 正在运行

2. **配置环境变量**
   ```batch
   # 双击运行 start.bat，首次运行会自动创建 .env 文件
   start.bat

   # 或者手动复制配置文件
   copy .env.example .env
   notepad .env
   ```

3. **启动系统**
   ```batch
   # 双击运行 start.bat 进入菜单
   start.bat

   # 选择 "1. 启动所有服务"
   ```

### Linux/macOS 用户

1. **安装 Docker**
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER

   # macOS
   brew install --cask docker
   ```

2. **配置环境变量**
   ```bash
   # 复制配置文件
   cp .env.example .env

   # 编辑配置
   nano .env  # 或使用 vim, vi 等编辑器
   ```

3. **添加执行权限并启动**
   ```bash
   # 添加执行权限
   chmod +x start.sh

   # 启动系统
   ./start.sh

   # 或者使用命令行参数
   ./start.sh start
   ```

## 必须配置的环境变量

在 `.env` 文件中必须配置以下内容：

```env
# Django 密钥（使用随机字符串）
DJANGO_SECRET_KEY=your-random-secret-key-here

# OpenAI API 密钥
OPENAI_API_KEY=sk-your-openai-api-key

# 数据库密码
DB_PASSWORD=your-strong-password
```

生成 Django 密钥：
```bash
# Linux/macOS
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Windows (在 Docker 容器中)
docker run --rm ruochat2-web python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 启动脚本功能

### Windows (start.bat)

```batch
start.bat          # 显示交互菜单
```

菜单选项：
1. 启动所有服务
2. 停止所有服务
3. 重启所有服务
4. 查看服务状态
5. 查看日志
6. 查看微信服务日志 (实时)
7. 进入 Django Shell
8. 清理所有数据 (危险操作)
9. 构建镜像
0. 退出

### Linux/macOS (start.sh)

```bash
# 交互式菜单
./start.sh

# 或直接使用命令
./start.sh start              # 启动服务
./start.sh stop               # 停止服务
./start.sh restart            # 重启服务
./start.sh status             # 查看状态
./start.sh logs               # 查看日志
./start.sh logs-wechat        # 查看微信日志
./start.sh shell              # Django Shell
./start.sh system-status      # 系统状态
./start.sh clean              # 清理数据
./start.sh build              # 构建镜像
./start.sh update             # 更新系统
./start.sh backup             # 备份数据库
```

## 服务说明

Docker Compose 会启动三个服务：

### 1. postgres - PostgreSQL 数据库
- 端口：5432
- 数据卷：postgres_data
- 健康检查：每10秒检查一次

### 2. web - Django Web 应用
- 端口：8000
- 功能：API 接口、管理后台
- 依赖：postgres (健康)

### 3. wechat - 微信监听服务
- 功能：微信消息接收和发送
- 依赖：postgres (健康), web
- 交互式：支持二维码显示

## 微信登录

首次启动微信服务需要扫码登录：

### Windows
```batch
# 运行 start.bat，选择 "6. 查看微信服务日志"
start.bat

# 或直接查看日志
docker compose logs -f wechat
```

### Linux/macOS
```bash
# 使用启动脚本
./start.sh logs-wechat

# 或直接查看日志
docker compose logs -f wechat
```

命令行会显示二维码，使用微信扫码即可登录。登录成功后会自动保存会话，下次启动无需重新扫码。

## 访问系统

启动成功后可以访问：

- **管理后台**: http://localhost:8000/admin/
- **API 接口**: http://localhost:8000/api/
- **系统状态**: http://localhost:8000/api/status/

默认管理员账号需要手动创建：
```bash
# Windows
docker compose exec web python manage.py createsuperuser

# Linux/macOS
./start.sh shell
# 在 Shell 中运行
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.create_superuser('admin', 'admin@example.com', 'password')
```

## 数据持久化

数据存储在以下 Docker 卷中：

- `postgres_data` - PostgreSQL 数据库文件
- `static_volume` - 静态文件
- `media_volume` - 媒体文件
- `logs_volume` - 日志文件
- `wechat_cache` - 微信登录缓存

查看卷：
```bash
docker volume ls | grep ruochat2
```

## 常用操作

### 查看服务状态
```bash
docker compose ps
```

### 查看日志
```bash
# 所有服务
docker compose logs -f

# 特定服务
docker compose logs -f web
docker compose logs -f wechat
docker compose logs -f postgres
```

### 进入容器
```bash
# 进入 Web 容器
docker compose exec web bash

# 进入数据库容器
docker compose exec postgres psql -U ruochat_user -d ruochat2
```

### 运行管理命令
```bash
# 查看系统状态
docker compose exec web python manage.py system_status

# 初始化系统
docker compose exec web python manage.py init_system

# 数据库迁移
docker compose exec web python manage.py migrate
```

### 备份数据库
```bash
# 导出数据库
docker compose exec -T postgres pg_dump -U ruochat_user ruochat2 > backup.sql

# 导入数据库
docker compose exec -T postgres psql -U ruochat_user ruochat2 < backup.sql
```

### 清理数据
```bash
# 停止并删除容器和卷
docker compose down -v

# 删除所有数据
docker volume rm ruochat2_postgres_data ruochat2_logs_volume ruochat2_wechat_cache
```

## 更新系统

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建镜像
docker compose build

# 3. 停止旧容器
docker compose down

# 4. 启动新容器
docker compose up -d

# 5. 运行数据库迁移
docker compose exec web python manage.py migrate
```

或使用启动脚本（Linux/macOS）：
```bash
./start.sh update
```

## 性能优化

### 调整 Worker 数量

编辑 `docker-compose.yml`：

```yaml
web:
  command: >
    sh -c "python manage.py migrate &&
           python manage.py init_system &&
           gunicorn ruochat.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120"
```

推荐 Worker 数量：`CPU核心数 * 2 + 1`

### 增加内存限制

编辑 `docker-compose.yml`，为服务添加资源限制：

```yaml
web:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
```

### 使用外部数据库

如果有独立的 PostgreSQL 服务器：

1. 修改 `.env` 文件：
   ```env
   DB_HOST=your-postgres-server.com
   DB_PORT=5432
   ```

2. 编辑 `docker-compose.yml`，移除 postgres 服务

3. 更新 web 和 wechat 服务的 depends_on

## 监控和日志

### 查看资源使用
```bash
docker stats
```

### 日志轮转

编辑 `docker-compose.yml` 添加日志配置：

```yaml
services:
  web:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 集成监控工具

可以集成 Prometheus、Grafana 等监控工具。

## 故障排除

### 问题 1: 端口被占用
```bash
# 修改 .env 文件中的端口
WEB_PORT=8001
DB_PORT=5433
```

### 问题 2: 数据库连接失败
```bash
# 检查数据库容器状态
docker compose ps postgres

# 查看数据库日志
docker compose logs postgres

# 进入数据库检查
docker compose exec postgres psql -U ruochat_user -d ruochat2
```

### 问题 3: 微信登录失败
```bash
# 清除微信缓存
docker volume rm ruochat2_wechat_cache
rm -f itchat.pkl QR.png

# 重启微信服务
docker compose restart wechat
```

### 问题 4: 构建失败
```bash
# 清理 Docker 缓存
docker system prune -a

# 重新构建
docker compose build --no-cache
```

### 问题 5: 服务无法访问
```bash
# 检查防火墙
# Linux
sudo ufw status
sudo ufw allow 8000/tcp

# 检查端口监听
netstat -tuln | grep 8000
# 或
ss -tuln | grep 8000
```

## 生产环境部署建议

1. **使用 HTTPS**
   - 配置 Nginx 反向代理
   - 使用 Let's Encrypt 获取 SSL 证书

2. **环境变量**
   - 设置 `DEBUG=False`
   - 使用强密钥和密码
   - 配置 `ALLOWED_HOSTS`

3. **数据备份**
   - 设置定时备份任务
   - 定期测试恢复流程

4. **监控告警**
   - 配置日志收集
   - 设置性能监控
   - 配置告警通知

5. **安全加固**
   - 限制数据库访问
   - 定期更新依赖
   - 启用防火墙

## 扩展阅读

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Django 部署清单](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)
- [PostgreSQL Docker 镜像](https://hub.docker.com/_/postgres)

## 获取帮助

如遇到问题：
1. 查看 Docker 日志
2. 查阅本文档的故障排除章节
3. 访问项目 GitHub Issues
4. 查看 README.md 和 DEPLOYMENT.md
