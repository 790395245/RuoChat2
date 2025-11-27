@echo off
chcp 65001 >nul
:: RuoChat2 Windows 启动脚本
:: 编码: UTF-8

echo ========================================
echo    RuoChat2 智能消息处理系统
echo    Windows 启动脚本
echo ========================================
echo.

:: 检查 Docker 是否安装
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Docker，请先安装 Docker Desktop
    echo 下载地址: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

:: 检查 Docker Compose 是否可用
docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Docker Compose 不可用，请确保 Docker Desktop 正在运行
    pause
    exit /b 1
)

echo [信息] Docker 环境检查通过
echo.

:: 检查 .env 文件是否存在
if not exist .env (
    echo [警告] 未找到 .env 文件，正在从模板创建...
    copy .env.example .env >nul
    echo [信息] 已创建 .env 文件，请编辑配置后重新运行
    echo.
    echo 必须配置的项目:
    echo   - DJANGO_SECRET_KEY
    echo   - OPENAI_API_KEY
    echo   - DB_PASSWORD
    echo.
    notepad .env
    pause
    exit /b 0
)

echo [信息] 配置文件检查通过
echo.

:: 显示菜单
:menu
echo 请选择操作:
echo   1. 启动所有服务
echo   2. 停止所有服务
echo   3. 重启所有服务
echo   4. 查看服务状态
echo   5. 查看日志
echo   6. 查看微信服务日志 (实时)
echo   7. 进入 Django Shell
echo   8. 清理所有数据 (危险操作)
echo   9. 构建镜像
echo   0. 退出
echo.

set /p choice="请输入选项 (0-9): "

if "%choice%"=="1" goto start
if "%choice%"=="2" goto stop
if "%choice%"=="3" goto restart
if "%choice%"=="4" goto status
if "%choice%"=="5" goto logs
if "%choice%"=="6" goto wechat_logs
if "%choice%"=="7" goto shell
if "%choice%"=="8" goto clean
if "%choice%"=="9" goto build
if "%choice%"=="0" goto end

echo [错误] 无效的选项
echo.
goto menu

:start
echo.
echo [信息] 正在启动服务...
docker compose up -d
if %errorlevel% equ 0 (
    echo.
    echo [成功] 服务启动成功！
    echo.
    echo 访问地址:
    echo   - Web 管理后台: http://localhost:8000/admin/
    echo   - API 接口: http://localhost:8000/api/
    echo.
    echo 微信登录:
    echo   请运行命令查看二维码: start.bat 然后选择 6
    echo   或直接运行: docker compose logs -f wechat
    echo.
) else (
    echo [错误] 服务启动失败，请查看错误信息
)
pause
goto menu

:stop
echo.
echo [信息] 正在停止服务...
docker compose down
if %errorlevel% equ 0 (
    echo [成功] 服务已停止
) else (
    echo [错误] 停止服务失败
)
pause
goto menu

:restart
echo.
echo [信息] 正在重启服务...
docker compose restart
if %errorlevel% equ 0 (
    echo [成功] 服务已重启
) else (
    echo [错误] 重启服务失败
)
pause
goto menu

:status
echo.
echo [信息] 服务状态:
echo.
docker compose ps
echo.
pause
goto menu

:logs
echo.
echo [信息] 查看所有服务日志 (按 Ctrl+C 退出)
echo.
docker compose logs -f --tail=100
goto menu

:wechat_logs
echo.
echo [信息] 查看微信服务日志 (按 Ctrl+C 退出)
echo [提示] 首次运行时会显示二维码，请使用微信扫码登录
echo.
docker compose logs -f wechat
goto menu

:shell
echo.
echo [信息] 进入 Django Shell...
docker compose exec web python manage.py shell
goto menu

:clean
echo.
echo [警告] 此操作将删除所有数据（数据库、日志、缓存等）
set /p confirm="确定要继续吗? (yes/no): "
if /i not "%confirm%"=="yes" (
    echo [信息] 操作已取消
    pause
    goto menu
)
echo.
echo [信息] 正在清理数据...
docker compose down -v
docker volume rm ruochat2_postgres_data ruochat2_logs_volume ruochat2_wechat_cache 2>nul
if exist logs rmdir /s /q logs
if exist itchat.pkl del /f /q itchat.pkl
if exist QR.png del /f /q QR.png
echo [成功] 数据清理完成
pause
goto menu

:build
echo.
echo [信息] 正在构建 Docker 镜像...
docker compose build --no-cache
if %errorlevel% equ 0 (
    echo [成功] 镜像构建完成
) else (
    echo [错误] 镜像构建失败
)
pause
goto menu

:end
echo.
echo 感谢使用 RuoChat2！
exit /b 0
