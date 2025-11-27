# 🚀 RuoChat2 Docker 一键启动指南

## Windows 用户

### 第一步：安装 Docker Desktop
1. 下载并安装：https://www.docker.com/products/docker-desktop
2. 启动 Docker Desktop，等待其完全启动

### 第二步：配置环境变量
1. 双击运行 `start.bat`
2. 首次运行会自动创建 `.env` 文件并打开编辑器
3. 必须修改以下三项：
   ```env
   DJANGO_SECRET_KEY=随机字符串（至少50个字符）
   OPENAI_API_KEY=sk-你的OpenAI密钥
   DB_PASSWORD=设置一个强密码
   ```
4. 保存并关闭编辑器

### 第三步：启动系统
1. 再次双击运行 `start.bat`
2. 选择 `1` - 启动所有服务
3. 等待 3-5 分钟（首次需要下载镜像）

### 第四步：微信登录
1. 在菜单中选择 `6` - 查看微信服务日志
2. 使用微信扫描显示的二维码
3. 登录成功后按 `Ctrl+C` 退出日志查看

### 完成！
- 访问管理后台：http://localhost:8000/admin/
- API 接口：http://localhost:8000/api/status/

---

## Linux/macOS 用户

### 第一步：安装 Docker

**Ubuntu/Debian:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# 重新登录以生效
```

**macOS:**
```bash
brew install --cask docker
# 启动 Docker Desktop
```

### 第二步：配置环境变量
```bash
# 复制配置文件
cp .env.example .env

# 编辑配置
nano .env

# 必须修改以下三项：
# DJANGO_SECRET_KEY=随机字符串（至少50个字符）
# OPENAI_API_KEY=sk-你的OpenAI密钥
# DB_PASSWORD=设置一个强密码
```

### 第三步：启动系统
```bash
# 添加执行权限
chmod +x start.sh

# 启动系统
./start.sh start

# 或者使用交互式菜单
./start.sh
```

### 第四步：微信登录
```bash
# 查看微信二维码
./start.sh logs-wechat

# 使用微信扫描二维码登录
# 登录成功后按 Ctrl+C 退出
```

### 完成！
- 访问管理后台：http://localhost:8000/admin/
- API 接口：http://localhost:8000/api/status/

---

## 📝 生成 Django 密钥

**Windows (在 PowerShell 中):**
```powershell
# 等待 Docker 启动后运行
docker run --rm python:3.11-slim python -c "import secrets; print(secrets.token_urlsafe(50))"
```

**Linux/macOS:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

## 🎯 常用操作

### Windows
- 启动：运行 `start.bat`，选择 `1`
- 停止：运行 `start.bat`，选择 `2`
- 查看状态：运行 `start.bat`，选择 `4`
- 查看微信日志：运行 `start.bat`，选择 `6`

### Linux/macOS
```bash
./start.sh start        # 启动
./start.sh stop         # 停止
./start.sh restart      # 重启
./start.sh status       # 查看状态
./start.sh logs-wechat  # 微信日志
./start.sh backup       # 备份数据库
```

---

## ❓ 常见问题

### 1. 启动失败
- 确保 Docker Desktop 正在运行
- 检查 8000 端口是否被占用
- 查看错误日志：`docker compose logs`

### 2. 无法访问 localhost:8000
- Windows：检查 Docker Desktop 的 WSL 2 设置
- 防火墙：确保 8000 端口未被阻止
- 等待：首次启动需要 3-5 分钟

### 3. 微信登录失败
- 清除缓存：
  - Windows: `start.bat` 选择 `8`
  - Linux: `./start.sh clean`
- 重新启动微信服务

### 4. OpenAI API 调用失败
- 检查 API 密钥是否正确
- 确认账户有足够的配额
- 检查网络连接

---

## 📚 更多文档

- [完整部署指南](DOCKER.md) - Docker 详细说明
- [系统文档](README.md) - 功能介绍和使用说明
- [快速入门](QUICKSTART.md) - 本地开发环境搭建

---

## 🆘 获取帮助

遇到问题？
1. 查看日志：`docker compose logs`
2. 查阅 [DOCKER.md](DOCKER.md) 故障排除章节
3. 提交 GitHub Issue

---

**祝你使用愉快！** 🎉
