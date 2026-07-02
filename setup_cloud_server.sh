#!/bin/bash
# ============================================================
# AI 医药业务助手 — 云服务器一键部署脚本
# 适用: Ubuntu 20.04/22.04
# 用法: bash setup_cloud_server.sh
# ============================================================
set -e

APP_DIR="/opt/pharma-app"
DOMAIN=""
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  AI 医药业务助手 — 云服务器部署${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# ── 1. 基础依赖 ───────────────────────────────────
echo -e "${YELLOW}[1/7] 安装系统依赖...${NC}"
apt update -qq
apt install -y -qq python3 python3-pip python3-venv nginx certbot python3-certbot-nginx curl unzip

# ── 2. 创建项目目录 ───────────────────────────────
echo -e "${YELLOW}[2/7] 部署项目文件...${NC}"
mkdir -p $APP_DIR

# 从当前目录复制（如果是远程，先用 scp 上传后再运行此脚本）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/app.py" ]; then
    cp -r "$SCRIPT_DIR"/* "$APP_DIR/"
    echo "  从本地 $SCRIPT_DIR 复制"
else
    echo -e "${RED}  错误: 未找到项目文件。请先将项目上传到服务器。${NC}"
    echo "  scp -r E:/yaodai/* root@<服务器IP>:/opt/pharma-app/"
    echo "  然后运行: bash /opt/pharma-app/setup_cloud_server.sh"
    exit 1
fi

# ── 3. Python 虚拟环境 ────────────────────────────
echo -e "${YELLOW}[3/7] 创建 Python 虚拟环境...${NC}"
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
deactivate

# ── 4. 初始化数据库 ───────────────────────────────
echo -e "${YELLOW}[4/7] 初始化数据库和演示数据...${NC}"
cd $APP_DIR
source venv/bin/activate
python3 -c "
from src.db import init_db
from src.demo_data import init_demo_data
init_db()
init_demo_data()
print('数据库初始化完成')
"
deactivate

# ── 5. Systemd 服务 ───────────────────────────────
echo -e "${YELLOW}[5/7] 创建 systemd 服务（开机自启）...${NC}"
cat > /etc/systemd/system/pharma-app.service << 'SYSTEMD'
[Unit]
Description=AI Pharma Report Assistant
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/pharma-app
Environment="PYTHONUNBUFFERED=1"
ExecStart=/opt/pharma-app/venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SYSTEMD

systemctl daemon-reload
systemctl enable pharma-app
systemctl restart pharma-app
sleep 3

# 检查服务状态
if systemctl is-active --quiet pharma-app; then
    echo -e "${GREEN}  ✅ 应用服务启动成功${NC}"
else
    echo -e "${RED}  ❌ 应用服务启动失败，查看日志: journalctl -u pharma-app -n 30${NC}"
    journalctl -u pharma-app -n 10
fi

# ── 6. 防火墙 ──────────────────────────────────────
echo -e "${YELLOW}[6/7] 配置防火墙...${NC}"
# 云服务器安全组需要在云控制台配置！这里只配系统防火墙
if command -v ufw &>/dev/null; then
    ufw allow 80/tcp 2>/dev/null || true
    ufw allow 443/tcp 2>/dev/null || true
    ufw allow 8501/tcp 2>/dev/null || true
    echo "  UFW 防火墙已配置"
fi

# ── 7. Nginx + HTTPS ───────────────────────────────
echo -e "${YELLOW}[7/7] 配置 Nginx 反向代理...${NC}"

# 获取服务器公网 IP
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "未知")
echo "  服务器 IP: $SERVER_IP"

cat > /etc/nginx/sites-available/pharma-app << NGINX
server {
    listen 80;
    server_name _;

    # Streamlit 需要 WebSocket 支持
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
        proxy_buffering off;
    }

    # 上传大小限制
    client_max_body_size 50M;
}
NGINX

# 启用站点
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/pharma-app /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  🎉 部署完成！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "应用地址:  ${YELLOW}http://${SERVER_IP}${NC}"
echo -e "          ${YELLOW}http://${SERVER_IP}:8501${NC}"
echo ""
echo -e "${RED}⚠️  接下来必须做的 3 件事:${NC}"
echo ""
echo "1️⃣  去云控制台「安全组」放行以下端口:"
echo "   - 80 (HTTP)"
echo "   - 443 (HTTPS)"
echo "   - 8501 (Streamlit 直连，可选)"
echo ""
echo "2️⃣  如有域名，配置 DNS A 记录指向 ${SERVER_IP}"
echo "   然后执行: certbot --nginx -d your-domain.com"
echo ""
echo "3️⃣  在系统设置页配置 DeepSeek / OpenAI 模型 Key"
echo ""
echo "管理命令:"
echo "  查看状态:  systemctl status pharma-app"
echo "  查看日志:  journalctl -u pharma-app -f"
echo "  重启应用:  systemctl restart pharma-app"
echo "  停止应用:  systemctl stop pharma-app"
echo ""
echo "数据库位置: /opt/pharma-app/data/pharma.db"
echo "导出文件:   /opt/pharma-app/exports/"
NGINX