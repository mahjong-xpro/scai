#!/bin/bash
# SSH隧道脚本 - 访问远程服务器的训练仪表板
# 
# 用法:
#   ./ssh_tunnel_dashboard.sh <服务器地址> <用户名> [SSH端口] [本地端口] [远程端口]
#
# 示例:
#   ./ssh_tunnel_dashboard.sh 192.168.1.100 root
#   ./ssh_tunnel_dashboard.sh example.com ubuntu 22 5000 5000
#   ./ssh_tunnel_dashboard.sh 192.168.1.100 root 22 8080 5000

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 参数检查
if [ $# -lt 2 ]; then
    echo -e "${RED}错误: 参数不足${NC}"
    echo ""
    echo "用法: $0 <服务器地址> <用户名> [SSH端口] [本地端口] [远程端口]"
    echo ""
    echo "示例:"
    echo "  $0 192.168.1.100 root"
    echo "  $0 example.com ubuntu 22 5000 5000"
    echo "  $0 192.168.1.100 root 22 8080 5000"
    exit 1
fi

HOST=$1
USER=$2
SSH_PORT=${3:-22}
LOCAL_PORT=${4:-5000}
REMOTE_PORT=${5:-5000}

# 检查SSH是否可用
if ! command -v ssh &> /dev/null; then
    echo -e "${RED}错误: 未找到 ssh 命令，请确保已安装 OpenSSH${NC}"
    exit 1
fi

# 检查本地端口是否被占用
if lsof -Pi :${LOCAL_PORT} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}警告: 本地端口 ${LOCAL_PORT} 已被占用${NC}"
    read -p "是否继续? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 显示信息
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}SSH隧道 - 训练仪表板${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "远程服务器: ${GREEN}${USER}@${HOST}:${SSH_PORT}${NC}"
echo -e "端口转发:   ${GREEN}localhost:${LOCAL_PORT} -> ${HOST}:${REMOTE_PORT}${NC}"
echo -e "访问地址:   ${GREEN}http://localhost:${LOCAL_PORT}${NC}"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止隧道${NC}"
echo ""

# 清理函数
cleanup() {
    echo ""
    echo -e "${YELLOW}正在关闭SSH隧道...${NC}"
    kill $SSH_PID 2>/dev/null || true
    wait $SSH_PID 2>/dev/null || true
    echo -e "${GREEN}✅ SSH隧道已关闭${NC}"
    exit 0
}

# 注册清理函数
trap cleanup SIGINT SIGTERM

# 启动SSH隧道
ssh -N \
    -L ${LOCAL_PORT}:localhost:${REMOTE_PORT} \
    -p ${SSH_PORT} \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3 \
    ${USER}@${HOST} &

SSH_PID=$!

# 等待一下，检查SSH连接是否成功
sleep 2

if ! kill -0 $SSH_PID 2>/dev/null; then
    echo -e "${RED}❌ SSH隧道启动失败${NC}"
    exit 1
fi

echo -e "${GREEN}✅ SSH隧道已建立${NC}"
echo ""

# 检测操作系统，尝试打开浏览器
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open "http://localhost:${LOCAL_PORT}" 2>/dev/null || true
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open "http://localhost:${LOCAL_PORT}" 2>/dev/null || true
fi

# 等待SSH进程
wait $SSH_PID

