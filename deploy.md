# 🚀 部署到公网 — 让所有人都能用

## 方案对比

| 方案 | 难度 | 速度 | 费用 | 安全性 | 推荐场景 |
|------|------|------|------|--------|----------|
| Cloudflare Tunnel | ⭐ 简单 | 即时 | 免费 | ⭐⭐⭐ 高 | **首选推荐** |
| 路由器端口转发 | ⭐⭐ 中等 | 即时 | 免费 | ⭐ 低 | 有公网IP的家庭宽带 |
| 云服务器部署 | ⭐⭐⭐ 复杂 | 30分钟 | ~50元/月 | ⭐⭐ 中 | 团队长期使用 |

---

## 方案一：Cloudflare Tunnel（推荐 ⭐）

**优点：** 不需要公网 IP、不需要配路由器、自动 HTTPS 证书、免费、安全。

### 步骤

#### 1. 注册 Cloudflare 账号
打开 https://dash.cloudflare.com/sign-up ，用邮箱免费注册。

#### 2. 安装 cloudflared

**Windows (PowerShell 管理员模式):**
```powershell
winget install --id Cloudflare.cloudflared
```

或手动下载：https://github.com/cloudflare/cloudflared/releases

#### 3. 登录并创建隧道

```powershell
# 登录 Cloudflare
cloudflared tunnel login

# 创建隧道
cloudflared tunnel create pharma-app

# 启动隧道（将本地 8501 端口暴露到公网）
cloudflared tunnel run --url http://localhost:8501 pharma-app
```

#### 4. 获取公网地址

启动后会显示类似 `https://pharma-app.xxx.trycloudflare.com` 的公网地址，
把这个地址发给团队成员即可。

#### 5. 后台运行（一直在线）

**Windows 任务计划程序** — 开机自启、后台运行：
```powershell
# 创建 Windows 服务（管理员模式）
New-Service -Name "PharmaApp" `
  -BinaryPathName "C:\Program Files (x86)\cloudflared\cloudflared.exe tunnel run --url http://localhost:8501 pharma-app" `
  -DisplayName "Pharma Report App Tunnel" `
  -StartupType Automatic

Start-Service PharmaApp
```

也可以用更简单的 TryCloudflare 临时隧道（无需注册域名）:
```powershell
cloudflared tunnel --url http://localhost:8501
```
启动后会直接给一个 `https://xxx.trycloudflare.com` 地址，即开即用。

---

## 方案二：路由器端口转发

如果你有公网 IP（电信/联通宽带通常有），在路由器设置端口转发即可。

### 步骤

1. 登录路由器管理页面（通常是 `http://192.168.1.1`）
2. 找到「端口转发」/「虚拟服务器」/「Port Forwarding」
3. 添加规则：
   - 外部端口：`8501`
   - 内部 IP：`192.168.2.7`（本机局域网 IP）
   - 内部端口：`8501`
   - 协议：TCP
4. 保存并重启路由器

之后，你的公网 IP 就是访问地址。在百度搜「我的 IP」获取。

> ⚠️ **风险提示：** 直接暴露端口到公网有安全风险。Streamlit 没有内置用户认证，任何人知道地址都能访问。建议至少配合方案一使用。

---

## 方案三：云服务器部署

适合团队长期使用。推荐配置：2核4G，50GB 磁盘。

### 在云服务器上

```bash
# 1. SSH 登录云服务器
ssh root@<服务器IP>

# 2. 安装 Python
apt update && apt install -y python3 python3-pip python3-venv

# 3. 上传项目（本机执行）
scp -r E:/yaodai root@<服务器IP>:/opt/pharma-app

# 4. 在服务器上安装依赖
cd /opt/pharma-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. 使用 systemd 保持后台运行
cat > /etc/systemd/system/pharma-app.service << 'EOF'
[Unit]
Description=Pharma Report App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/pharma-app
ExecStart=/opt/pharma-app/venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable pharma-app
systemctl start pharma-app

# 6. 配置 Nginx 反向代理（HTTPS + 域名）
apt install -y nginx certbot python3-certbot-nginx

cat > /etc/nginx/sites-available/pharma << 'EOF'
server {
    listen 80;
    server_name your-domain.com;   # 改成你的域名

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }
}
EOF

ln -s /etc/nginx/sites-available/pharma /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx

# 7. 配置 HTTPS
certbot --nginx -d your-domain.com
```

---

## 补充：让 Streamlit 在 Windows 后台持续运行

```powershell
# PowerShell 管理员模式
# 创建 Windows 计划任务，开机自启

$action = New-ScheduledTaskAction -Execute "C:\Python314\python.exe" `
  -Argument "-m streamlit run E:\yaodai\app.py --server.headless true" `
  -WorkingDirectory "E:\yaodai"

$trigger = New-ScheduledTaskTrigger -AtStartup

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "PharmaReportApp" `
  -Action $action -Trigger $trigger -Settings $settings `
  -Description "AI医药业务助手自动启动"
```

---

## 快速上手建议

**最快 1 分钟让别人用上：**

```powershell
# 1. 先确认应用在运行
streamlit run E:/yaodai/app.py

# 2. 另开一个终端，启动 Cloudflare 临时隧道
cloudflared tunnel --url http://localhost:8501
```

把输出的 `https://xxx.trycloudflare.com` 地址发给任何人即可访问。
