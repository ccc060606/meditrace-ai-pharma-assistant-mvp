"""AI 医药业务日报与月报助手 — Main Entry Point."""
import sys
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

from src.config import Config
from src.db import init_db
from src.demo_data import init_demo_data

# ── Page Config ─────────────────────────────────────────────────
st.set_page_config(
    page_title="AI 医药业务助手",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar: Network & Status ───────────────────────────────────
import socket
with st.sidebar:
    st.markdown("## 💊 医药业务助手")
    st.markdown("---")

    cfg = Config()
    if cfg.public_demo:
        st.success("公开演示模式")
        st.caption("仅使用虚构数据与Mock模型，不连接企业内部系统。")

    # Network info
    if not cfg.public_demo:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            lan_ip = s.getsockname()[0]
            s.close()
        except Exception:
            lan_ip = "localhost"

        st.markdown("### 🌐 局域网访问")
        st.code(f"http://{lan_ip}:8501")
        st.caption("同一网络下的设备用此地址访问")

    st.markdown("---")
    st.markdown("### ⚙️ 当前模型")
    provider = st.session_state.get("llm_provider", "mock")
    provider_names = {
        "mock": "Mock 演示模式",
        "deepseek": "DeepSeek",
        "openai_compatible": "OpenAI 兼容",
        "ollama": "Ollama 本地",
    }
    st.caption(f"供应商: {provider_names.get(provider, provider)}")

    st.markdown("---")
    st.markdown("[📖 项目说明](/)")

# ── Init ────────────────────────────────────────────────────────
init_db()

# Auto-init demo data on first run
if "demo_initialized" not in st.session_state:
    try:
        init_demo_data()
    except Exception:
        pass  # Silent if already exists
    st.session_state.demo_initialized = True

# ── Home Page ───────────────────────────────────────────────────
st.title("💊 AI 医药业务日报与月报助手")
if Config().public_demo:
    st.info("这是个人求职概念项目的公开演示版。全部客户与日报均为虚构数据，默认使用Mock模型。")
st.markdown("---")

st.markdown("""
### 欢迎使用医药业务智能管理平台

本系统帮助医药业务人员：
- 📝 **日报录入** — 将原始日报文本自动解析为结构化数据，支持文件上传和手工录入
- 👥 **客户管理** — 匿名化客户记录管理，支持合并重复客户和查看沟通历史
- 📊 **月报生成** — 一键生成本月统计报告，支持 Excel/Word 导出
- 📚 **文献追踪** — 从医学问题自动检索 PubMed 文献，AI 辅助总结

---

### 快速开始

1. 前往 **日报录入** 页面粘贴或上传日报文本
2. 在 **客户管理** 中查看客户详情和沟通历史
3. 选择月份，在 **月报生成** 中一键导出报告
4. 在 **文献追踪** 中检索医学问题相关文献

---

### 模型配置

默认使用 **Mock 模式**（无需 API Key），可完整演示所有流程。
如需接入真实模型，请在 **系统设置** 中配置 OpenAI 兼容接口或本地 Ollama。

> ⚠️ **隐私提示**：本系统默认只记录匿名客户编号（C001、C002等），请勿输入真实姓名、手机号等个人信息。
> 使用云端模型时，所选文本将被发送到配置的第三方服务。

---

### 系统状态
""")

# Quick stats
from src.db import get_session
from src.models.daily_report import DailyReport
from src.models.customer import Customer
from src.models.literature import LiteratureArticle

session = get_session()
try:
    col1, col2, col3, col4 = st.columns(4)
    report_count = session.query(DailyReport).count()
    customer_count = session.query(Customer).filter(Customer.is_active == 1).count()
    pending_count = session.query(DailyReport).filter(
        DailyReport.follow_up_status == "pending",
        DailyReport.follow_up_task.isnot(None),
        DailyReport.follow_up_task != "",
    ).count()
    lit_count = session.query(LiteratureArticle).count()

    col1.metric("📝 日报总数", report_count)
    col2.metric("👥 活跃客户", customer_count)
    col3.metric("⏳ 待跟进任务", pending_count)
    col4.metric("📚 文献数量", lit_count)
finally:
    session.close()
