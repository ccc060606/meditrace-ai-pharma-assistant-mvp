#!/bin/bash
# AI 医药业务日报与月报助手 — Linux/macOS 启动脚本
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "========================================"
echo "  AI 医药业务日报与月报助手"
echo "========================================"
echo ""
echo "📁 项目目录: $PROJECT_DIR"

# Create .env if missing
if [ ! -f ".env" ]; then
    echo "[1/3] 创建 .env 配置文件..."
    cp .env.example .env
    echo "  ✅ 已使用 Mock 模式（无需 API Key）"
else
    echo "[1/3] .env 配置文件已存在"
fi

# Check Python
echo "[2/3] 检查 Python 环境..."
python3 --version >/dev/null 2>&1 || {
    echo "  ❌ 未找到 Python3，请先安装 Python 3.11+"
    exit 1
}
echo "  ✅ Python 已就绪"

# Check/install deps
echo "[3/3] 检查依赖..."
python3 -c "import streamlit" 2>/dev/null || {
    echo "  ⏳ 安装依赖中..."
    pip3 install -r requirements.txt
}
echo "  ✅ 依赖已就绪"

echo ""
echo "========================================"
echo "  🚀 正在启动..."
echo "  本机访问:  http://localhost:8501"
echo "  局域网访问:  http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '<本机IP>'):8501"
echo "  按 Ctrl+C 停止服务器"
echo "========================================"
echo ""

streamlit run app.py --server.headless true
