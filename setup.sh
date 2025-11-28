#!/bin/bash

# RuoChat2 快速初始化脚本
# 用于快速设置数据库和初始化系统

set -e  # 遇到错误立即退出

echo "============================================"
echo "  RuoChat2 系统初始化"
echo "============================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查是否使用Docker
if [ -f "docker-compose.yml" ] && command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}检测到Docker Compose，推荐使用Docker方式启动${NC}"
    echo ""
    read -p "是否使用Docker启动? (y/n) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}正在使用Docker启动所有服务...${NC}"
        docker-compose down -v 2>/dev/null || true
        docker-compose up -d

        echo ""
        echo -e "${GREEN}等待服务启动...${NC}"
        sleep 10

        echo ""
        echo -e "${GREEN}检查配置...${NC}"
        docker-compose exec web python manage.py check_config

        echo ""
        echo -e "${GREEN}✓ Docker服务启动完成！${NC}"
        echo ""
        echo "下一步："
        echo "1. 查看Web服务: http://localhost:8000/api/status/"
        echo "2. 查看微信二维码: http://localhost:8000/api/wechat/qr/"
        echo "3. 查看日志: docker-compose logs -f wechat"
        exit 0
    fi
fi

# 手动安装方式
echo -e "${YELLOW}开始手动初始化...${NC}"
echo ""

# 1. 检查Python环境
echo "1. 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python3已安装${NC}"

# 2. 检查PostgreSQL
echo ""
echo "2. 检查PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo -e "${RED}✗ PostgreSQL未安装${NC}"
    echo "请先安装PostgreSQL: sudo apt install postgresql"
    exit 1
fi
echo -e "${GREEN}✓ PostgreSQL已安装${NC}"

# 3. 检查.env文件
echo ""
echo "3. 检查配置文件..."
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env文件不存在${NC}"
    echo "请配置.env文件后重新运行此脚本"
    exit 1
fi
echo -e "${GREEN}✓ .env文件存在${NC}"

# 4. 安装Python依赖
echo ""
echo "4. 安装Python依赖..."
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate

if [ -f "requirements.txt" ]; then
    echo "安装依赖包..."
    pip install -q -r requirements.txt
    echo -e "${GREEN}✓ 依赖安装完成${NC}"
else
    echo -e "${RED}✗ requirements.txt不存在${NC}"
    exit 1
fi

# 5. 运行数据库迁移
echo ""
echo "5. 运行数据库迁移..."
python manage.py migrate
echo -e "${GREEN}✓ 数据库迁移完成${NC}"

# 6. 初始化系统数据
echo ""
echo "6. 初始化系统数据..."
read -p "是否添加示例数据? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    python manage.py init_system --with-examples
else
    python manage.py init_system
fi
echo -e "${GREEN}✓ 系统初始化完成${NC}"

# 7. 检查配置
echo ""
echo "7. 验证配置..."
python manage.py check_config

# 8. 询问是否创建超级用户
echo ""
read -p "是否创建管理员账户? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python manage.py createsuperuser
fi

# 完成
echo ""
echo "============================================"
echo -e "${GREEN}✓ 初始化完成！${NC}"
echo "============================================"
echo ""
echo "下一步："
echo "1. 启动Web服务: python manage.py runserver"
echo "2. 启动微信服务: python manage.py start_wechat"
echo "3. 查看二维码: http://localhost:8000/api/wechat/qr/"
echo ""
