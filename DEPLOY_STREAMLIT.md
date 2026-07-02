# 发布为公开Streamlit应用

## 推荐方案

使用Streamlit Community Cloud。它会从GitHub仓库部署`app.py`，并生成固定的`https://xxx.streamlit.app`链接。

## 发布前检查

以下内容不得上传：

- `.env`
- `.streamlit/secrets.toml`
- `data/pharma.db`
- `exports/`中的本地导出文件
- 真实客户、医生、患者或企业内部资料

当前`.gitignore`已经排除这些文件。

## 第一步：上传GitHub

在`E:\yaodai`目录初始化Git仓库并上传：

```powershell
cd E:\yaodai
git init
git add .
git status
git commit -m "Prepare public AI pharma report demo"
git branch -M main
git remote add origin https://github.com/<你的账号>/<仓库名>.git
git push -u origin main
```

执行`git status`时必须确认没有`.env`、数据库和导出文件。

## 第二步：部署

1. 登录`https://share.streamlit.io/`。
2. 选择`Create app`。
3. 选择刚上传的GitHub仓库。
4. Branch选择`main`。
5. Main file path填写`app.py`。
6. Python选择`3.12`。
7. 在Advanced settings的Secrets中粘贴：

```toml
PUBLIC_DEMO = "true"
LLM_PROVIDER = "mock"
DATABASE_PATH = "/tmp/pharma_demo.db"
EXPORT_DIR = "/tmp/pharma_exports"
PUBMED_EMAIL = "你的联系邮箱"
```

8. 点击Deploy，部署后获得`https://xxx.streamlit.app`链接。

## 第三步：发给HR

推荐消息：

> 您好，这是我基于医药业务日报和月报整理痛点搭建的AI应用MVP。公开版使用虚构数据和Mock模型，可体验日报结构化、匿名客户管理、月报统计导出及PubMed文献追踪。项目链接：<你的链接>。

## 公开版限制

- 免费容器重启后，访客新增的数据可能被清空。
- 多位访客可能共享同一个临时SQLite数据库。
- 公开版不开放API Key配置，不连接真实企业系统。
- 该链接用于作品演示，不适合作为正式生产系统。
