# 💊 AI 医药业务日报与月报助手

面向医药业务人员的 AI 智能助手，将分散的原始日报转换为结构化数据，维护匿名客户沟通记录，自动生成月报，并针对日报中的医学问题检索公开文献。

## 功能概览

- 📝 **日报录入** — AI 自动解析日报文本为结构化字段，支持文本/CSV/Excel 输入和手工录入
- 👥 **客户管理** — 匿名化客户记录，历史沟通时间线，疑似重复检测与合并
- 📊 **月报生成** — 确定性统计 + AI 文字总结，Plotly 图表，Excel/Word 导出
- 📚 **文献追踪** — 从医学问题自动生成 PubMed 检索词，文献去重保存与 AI 摘要
- ⚙️ **系统设置** — 支持 Mock/OpenAI 兼容/Ollama 三种模型供应商，可随时切换

## 技术栈

- Python 3.11+
- Streamlit（前端）
- SQLAlchemy + SQLite（数据层）
- Pydantic（数据校验）
- Plotly（图表）
- openpyxl + python-docx（导出）
- HTTPX（PubMed API）

## 快速开始

### 1. 环境准备

**Windows (PowerShell):**

```powershell
# 克隆或下载项目后进入目录
cd ai-pharma-report-assistant

# 创建虚拟环境
python -m venv venv
.\venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
cd ai-pharma-report-assistant

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置（可选）

系统默认使用 **Mock 模式**，无需任何 API Key 即可完整体验所有功能。

如需接入真实 AI 模型：

```bash
cp .env.example .env
# 编辑 .env 文件填入配置
```

或在应用启动后在 **系统设置** 页面动态配置。

### 3. 启动应用

```bash
streamlit run app.py
```

浏览器打开 `http://localhost:8501` 即可使用。

首次启动会自动初始化演示数据（8 个客户、30 条日报、5 个医学问题）。

## 模型供应商

| 供应商 | 说明 | 需要配置 |
|--------|------|----------|
| **Mock** | 规则匹配，无需网络/密钥 | 无 |
| **OpenAI 兼容** | 支持任何 OpenAI 兼容接口 | API 地址、Key、模型名 |
| **Ollama** | 本地部署，无需联网 | Ollama 地址、模型名 |

在 **系统设置** 页面可以随时切换和测试连接。

## 项目结构

```text
ai-pharma-report-assistant/
├── app.py                    # 入口与首页
├── pages/
│   ├── 1_日报录入.py         # 日报 AI 解析与手工录入
│   ├── 2_客户管理.py         # 客户列表、详情、合并
│   ├── 3_月报生成.py         # 月报统计、图表、导出
│   ├── 4_文献追踪.py         # PubMed 检索与 AI 总结
│   └── 5_系统设置.py         # 模型供应商配置
├── src/
│   ├── config.py             # 配置管理
│   ├── db.py                 # 数据库引擎与会话
│   ├── demo_data.py          # 演示数据
│   ├── models/               # SQLAlchemy + Pydantic 模型
│   ├── repositories/         # 数据访问层
│   ├── services/             # 业务逻辑层
│   ├── llm/                  # LLM Provider 抽象与实现
│   ├── literature/           # PubMed 客户端
│   ├── exporters/            # Excel/Word 导出
│   └── utils/                # 敏感信息检测等工具
├── tests/                    # pytest 测试
├── data/                     # 数据库文件（gitignore）
├── exports/                  # 导出文件（gitignore）
├── .env.example
├── requirements.txt
└── README.md
```

## 运行测试

```bash
# 安装测试依赖
pip install pytest

# 运行全部测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_models.py -v
pytest tests/test_customer.py -v
pytest tests/test_monthly_stats.py -v
```

## 安全与隐私

- 所有客户以匿名编号（C001, C002...）存储，不保存手机号、姓名等身份信息
- 输入文本自动检测疑似手机号/身份证/邮箱，提示先去标识化
- 密钥不写入数据库、日志或导出文件
- 所有数据库查询使用 ORM 参数化，防止注入
- 文献总结明确标注「AI 总结」与「原始摘要」，保留 PMID/DOI 供核验

## 演示数据

首次启动自动加载：

- 8 个客户（4 个科室：心内科、肿瘤科、内分泌科、神经内科/呼吸科）
- 30 条日报（2026年5月 15 条 + 6月 15 条）
- 5 个医学问题
- 1 组疑似重复客户（C003 与 C008，同属内分泌科）

所有演示数据均为虚构，不包含真实个人信息。

## 常见问题

**Q: 没有 API Key 能使用吗？**
A: 可以。系统默认 Mock 模式，所有功能均可完整体验。

**Q: 如何接入自己的模型？**
A: 系统设置 → 选择 OpenAI 兼容 → 填入 API 地址和 Key → 测试连接。

**Q: 数据库在哪里？**
A: 默认 `data/pharma.db`（SQLite 文件）。

**Q: 文献检索需要网络吗？**
A: PubMed 检索需要网络连接。Mock 模式下可完成所有其他操作。

## 免责声明

本系统产生的 AI 总结和文献检索内容仅用于内部信息整理，不构成医学建议。
重要临床决策必须基于原始文献和专业医学判断。
