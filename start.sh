#!/bin/bash
# RuoChat2 Linux/macOS 启动脚本
# 编码: UTF-8

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[信息]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[成功]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

print_error() {
    echo -e "${RED}[错误]${NC} $1"
}

# 打印标题
print_header() {
    echo "========================================"
    echo "   RuoChat2 智能消息处理系统"
    echo "   Linux/macOS 启动脚本"
    echo "========================================"
    echo
}

# 检查 Docker 是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "未检测到 Docker，请先安装 Docker"
        echo "安装指南: https://docs.docker.com/engine/install/"
        exit 1
    fi

    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose 不可用"
        exit 1
    fi

    print_info "Docker 环境检查通过"
}

# 检查 .env 文件
check_env() {
    if [ ! -f .env ]; then
        print_warning "未找到 .env 文件，正在从模板创建..."
        cp .env.example .env
        print_info "已创建 .env 文件，请编辑配置后重新运行"
        echo
        echo "必须配置的项目:"
        echo "  - DJANGO_SECRET_KEY"
        echo "  - OPENAI_API_KEY"
        echo "  - DB_PASSWORD"
        echo

        # 尝试打开编辑器
        if command -v nano &> /dev/null; then
            nano .env
        elif command -v vim &> /dev/null; then
            vim .env
        elif command -v vi &> /dev/null; then
            vi .env
        else
            print_warning "请手动编辑 .env 文件"
        fi

        exit 0
    fi

    print_info "配置文件检查通过"
}

# 启动服务
start_services() {
    print_info "正在启动服务..."
    docker compose up -d

    if [ $? -eq 0 ]; then
        echo
        print_success "服务启动成功！"
        echo
        echo "访问地址:"
        echo "  - Web 管理后台: http://localhost:8000/admin/"
        echo "  - API 接口: http://localhost:8000/api/"
        echo
        echo "微信登录:"
        echo "  请运行命令查看二维码: ./start.sh logs-wechat"
        echo "  或直接运行: docker compose logs -f wechat"
        echo
    else
        print_error "服务启动失败，请查看错误信息"
        exit 1
    fi
}

# 停止服务
stop_services() {
    print_info "正在停止服务..."
    docker compose down

    if [ $? -eq 0 ]; then
        print_success "服务已停止"
    else
        print_error "停止服务失败"
        exit 1
    fi
}

# 重启服务
restart_services() {
    print_info "正在重启服务..."
    docker compose restart

    if [ $? -eq 0 ]; then
        print_success "服务已重启"
    else
        print_error "重启服务失败"
        exit 1
    fi
}

# 查看状态
show_status() {
    print_info "服务状态:"
    echo
    docker compose ps
}

# 查看所有日志
show_logs() {
    print_info "查看所有服务日志 (按 Ctrl+C 退出)"
    docker compose logs -f --tail=100
}

# 查看微信日志
show_wechat_logs() {
    print_info "查看微信服务日志 (按 Ctrl+C 退出)"
    print_info "首次运行时会显示二维码，请使用微信扫码登录"
    echo
    docker compose logs -f wechat
}

# 进入 Django Shell
enter_shell() {
    print_info "进入 Django Shell..."
    docker compose exec web python manage.py shell
}

# 查看系统状态
system_status() {
    print_info "查看系统状态..."
    docker compose exec web python manage.py system_status
}

# 清理数据
clean_data() {
    echo
    print_warning "此操作将删除所有数据（数据库、日志、缓存等）"
    read -p "确定要继续吗? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        print_info "操作已取消"
        return
    fi

    print_info "正在清理数据..."
    docker compose down -v
    docker volume rm ruochat2_postgres_data ruochat2_logs_volume ruochat2_wechat_cache 2>/dev/null || true
    rm -rf logs itchat.pkl QR.png
    print_success "数据清理完成"
}

# 构建镜像
build_images() {
    print_info "正在构建 Docker 镜像..."
    docker compose build --no-cache

    if [ $? -eq 0 ]; then
        print_success "镜像构建完成"
    else
        print_error "镜像构建失败"
        exit 1
    fi
}

# 更新系统
update_system() {
    print_info "正在更新系统..."
    git pull
    docker compose build
    docker compose up -d
    docker compose exec web python manage.py migrate
    print_success "系统更新完成"
}

# 备份数据库
backup_database() {
    print_info "正在备份数据库..."
    BACKUP_DIR="backups"
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"

    docker compose exec -T postgres pg_dump -U ruochat_user ruochat2 > "$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        print_success "数据库备份成功: $BACKUP_FILE"
    else
        print_error "数据库备份失败"
        exit 1
    fi
}

# 显示菜单
show_menu() {
    echo
    echo "请选择操作:"
    echo "  1. 启动所有服务"
    echo "  2. 停止所有服务"
    echo "  3. 重启所有服务"
    echo "  4. 查看服务状态"
    echo "  5. 查看所有日志"
    echo "  6. 查看微信服务日志 (实时)"
    echo "  7. 进入 Django Shell"
    echo "  8. 查看系统状态"
    echo "  9. 清理所有数据 (危险操作)"
    echo " 10. 构建镜像"
    echo " 11. 更新系统"
    echo " 12. 备份数据库"
    echo "  0. 退出"
    echo
    read -p "请输入选项 (0-12): " choice

    case $choice in
        1) start_services ;;
        2) stop_services ;;
        3) restart_services ;;
        4) show_status ;;
        5) show_logs ;;
        6) show_wechat_logs ;;
        7) enter_shell ;;
        8) system_status ;;
        9) clean_data ;;
        10) build_images ;;
        11) update_system ;;
        12) backup_database ;;
        0)
            echo
            echo "感谢使用 RuoChat2！"
            exit 0
            ;;
        *)
            print_error "无效的选项"
            show_menu
            ;;
    esac

    # 操作完成后返回菜单
    if [ "$choice" != "5" ] && [ "$choice" != "6" ]; then
        read -p "按 Enter 继续..."
        show_menu
    fi
}

# 主函数
main() {
    print_header
    check_docker
    check_env

    # 如果提供了命令行参数，直接执行对应命令
    if [ $# -gt 0 ]; then
        case "$1" in
            start) start_services ;;
            stop) stop_services ;;
            restart) restart_services ;;
            status) show_status ;;
            logs) show_logs ;;
            logs-wechat) show_wechat_logs ;;
            shell) enter_shell ;;
            system-status) system_status ;;
            clean) clean_data ;;
            build) build_images ;;
            update) update_system ;;
            backup) backup_database ;;
            *)
                print_error "未知命令: $1"
                echo
                echo "可用命令:"
                echo "  start         - 启动所有服务"
                echo "  stop          - 停止所有服务"
                echo "  restart       - 重启所有服务"
                echo "  status        - 查看服务状态"
                echo "  logs          - 查看所有日志"
                echo "  logs-wechat   - 查看微信日志"
                echo "  shell         - 进入 Django Shell"
                echo "  system-status - 查看系统状态"
                echo "  clean         - 清理所有数据"
                echo "  build         - 构建镜像"
                echo "  update        - 更新系统"
                echo "  backup        - 备份数据库"
                exit 1
                ;;
        esac
    else
        # 没有参数则显示交互菜单
        show_menu
    fi
}

# 运行主函数
main "$@"
