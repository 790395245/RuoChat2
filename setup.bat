@echo off
REM RuoChat2 快速初始化脚本 (Windows版)
REM 用于快速设置数据库和初始化系统

echo ============================================
echo   RuoChat2 系统初始化 (Windows)
echo ============================================
echo.

REM 检查是否使用Docker
where docker-compose >nul 2>nul
if %errorlevel% equ 0 (
    if exist docker-compose.yml (
        echo 检测到Docker Compose，推荐使用Docker方式启动
        echo.
        set /p use_docker="是否使用Docker启动? (y/n): "

        if /i "%use_docker%"=="y" (
            echo 正在使用Docker启动所有服务...
            docker-compose down -v 2>nul
            docker-compose up -d

            echo.
            echo 等待服务启动...
            timeout /t 10 /nobreak >nul

            echo.
            echo 检查配置...
            docker-compose exec web python manage.py check_config

            echo.
            echo [SUCCESS] Docker服务启动完成！
            echo.
            echo 下一步：
            echo 1. 查看Web服务: http://localhost:8000/api/status/
            echo 2. 查看微信二维码: http://localhost:8000/api/wechat/qr/
            echo 3. 查看日志: docker-compose logs -f wechat
            pause
            exit /b 0
        )
    )
)

REM 手动安装方式
echo 开始手动初始化...
echo.

REM 1. 检查Python环境
echo 1. 检查Python环境...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python未安装
    echo 请先安装Python 3.8+
    pause
    exit /b 1
)
echo [OK] Python已安装
python --version

REM 2. 检查PostgreSQL
echo.
echo 2. 检查PostgreSQL...
where psql >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] PostgreSQL命令行工具未找到
    echo 请确保PostgreSQL已安装并正在运行
    echo 下载地址: https://www.postgresql.org/download/windows/
    pause
)

REM 3. 检查.env文件
echo.
echo 3. 检查配置文件...
if not exist .env (
    echo [ERROR] .env文件不存在
    echo 请配置.env文件后重新运行此脚本
    pause
    exit /b 1
)
echo [OK] .env文件存在

REM 4. 创建虚拟环境并安装依赖
echo.
echo 4. 安装Python依赖...
if not exist venv (
    echo 创建虚拟环境...
    python -m venv venv
)

call venv\Scripts\activate.bat

if exist requirements.txt (
    echo 安装依赖包...
    pip install -q -r requirements.txt
    echo [OK] 依赖安装完成
) else (
    echo [ERROR] requirements.txt不存在
    pause
    exit /b 1
)

REM 5. 运行数据库迁移
echo.
echo 5. 运行数据库迁移...
python manage.py migrate
if %errorlevel% neq 0 (
    echo [ERROR] 数据库迁移失败
    echo 请检查数据库配置和连接
    pause
    exit /b 1
)
echo [OK] 数据库迁移完成

REM 6. 初始化系统数据
echo.
echo 6. 初始化系统数据...
set /p add_examples="是否添加示例数据? (y/n): "

if /i "%add_examples%"=="y" (
    python manage.py init_system --with-examples
) else (
    python manage.py init_system
)
echo [OK] 系统初始化完成

REM 7. 检查配置
echo.
echo 7. 验证配置...
python manage.py check_config

REM 8. 询问是否创建超级用户
echo.
set /p create_superuser="是否创建管理员账户? (y/n): "
if /i "%create_superuser%"=="y" (
    python manage.py createsuperuser
)

REM 完成
echo.
echo ============================================
echo [SUCCESS] 初始化完成！
echo ============================================
echo.
echo 下一步：
echo 1. 启动Web服务: python manage.py runserver
echo 2. 启动微信服务: python manage.py start_wechat
echo 3. 查看二维码: http://localhost:8000/api/wechat/qr/
echo.
pause
