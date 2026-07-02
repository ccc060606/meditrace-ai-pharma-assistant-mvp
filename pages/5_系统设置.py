"""Page 5: 系统设置 — 多供应商配置、自动检测、网络共享说明."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import socket

from src.config import Config
from src.llm.base import create_provider, PROVIDER_PRESETS, detect_available_providers

st.set_page_config(page_title="系统设置", page_icon="⚙️", layout="wide")

st.title("⚙️ 系统设置")

cfg = Config()

if cfg.public_demo:
    st.info("公开演示模式已锁定为Mock模型。为避免密钥泄露和外部费用，本页面不开放API配置。")
    st.markdown("- 数据：虚构演示数据\n- 模型：Mock\n- API Key：未配置\n- 企业内部系统：未连接")
    st.stop()

# ── 自动检测可用供应商 ───────────────────────────────────────
detected = detect_available_providers()

# ── 1. LLM 供应商选择 ───────────────────────────────────────
st.subheader("🤖 模型供应商")

# Current provider from session
current_provider = st.session_state.get("llm_provider", cfg.llm_provider)

# Build provider cards
provider_keys = [p["key"] for p in detected]
try:
    current_idx = provider_keys.index(current_provider)
except ValueError:
    current_idx = provider_keys.index("mock") if "mock" in provider_keys else 0

# Radio-style selection with cards
st.markdown("#### 选择供应商")
cols = st.columns(len(detected))

for i, (col, info) in enumerate(zip(cols, detected)):
    with col:
        is_active = (info["key"] == current_provider)
        border_color = "#1a73e8" if is_active else "#e0e0e0"
        bg_color = "#e8f0fe" if is_active else "#ffffff"

        st.markdown(f"""
        <div style="border:2px solid {border_color}; border-radius:10px; padding:12px;
                    background:{bg_color}; cursor:pointer; min-height:120px;
                    text-align:center;">
            <strong>{info['name']}</strong><br>
            <small style="color:#666">{info['description']}</small><br>
            <small>模型: {info.get('default_model', '-')}</small>
        </div>
        """, unsafe_allow_html=True)

        if st.button("选择", key=f"select_{info['key']}", use_container_width=True):
            st.session_state.llm_provider = info["key"]
            # Set defaults
            if info.get("default_url"):
                st.session_state.llm_base_url = info["default_url"]
            if info.get("default_model"):
                st.session_state.llm_model = info["default_model"]
            st.rerun()

st.markdown("---")

# ── 2. 当前供应商配置 ────────────────────────────────────────
provider_info = PROVIDER_PRESETS.get(current_provider, PROVIDER_PRESETS["mock"])
st.subheader(f"🔧 配置: {provider_info['name']}")

if current_provider == "deepseek":
    col1, col2 = st.columns(2)
    api_key = col1.text_input(
        "DeepSeek API Key",
        value=st.session_state.get("llm_api_key", cfg.llm_api_key),
        type="password",
        placeholder="sk-...",
        help="在 https://platform.deepseek.com/api_keys 获取",
    )
    model = col2.selectbox(
        "模型",
        ["deepseek-chat", "deepseek-reasoner"],
        index=0 if st.session_state.get("llm_model", "deepseek-chat") == "deepseek-chat" else 1,
    )
    base_url = "https://api.deepseek.com/v1"
    st.caption(f"API 地址: `{base_url}` （自动配置）")
    st.session_state.llm_api_key = api_key
    st.session_state.llm_model = model
    st.session_state.llm_base_url = base_url

elif current_provider == "openai_compatible":
    col1, col2, col3 = st.columns([1, 1, 1])
    base_url = col1.text_input(
        "API 地址",
        value=st.session_state.get("llm_base_url", cfg.llm_base_url),
        placeholder="https://api.openai.com/v1",
        help="支持硅基流动、通义千问、百川、智谱等任意 OpenAI 兼容接口",
    )
    api_key = col2.text_input(
        "API Key",
        value=st.session_state.get("llm_api_key", cfg.llm_api_key),
        type="password",
        placeholder="sk-...",
    )
    model = col3.text_input(
        "模型名称",
        value=st.session_state.get("llm_model", cfg.llm_model),
        placeholder="gpt-4o-mini / qwen-plus / glm-4",
    )
    st.session_state.llm_base_url = base_url
    st.session_state.llm_api_key = api_key
    st.session_state.llm_model = model

    # Quick presets
    with st.expander("📋 常用供应商预设"):
        presets = {
            "硅基流动 (SiliconFlow)": {"url": "https://api.siliconflow.cn/v1", "model": "Qwen/Qwen2.5-7B-Instruct"},
            "通义千问 (阿里云)": {"url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus"},
            "智谱 GLM": {"url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4"},
            "百川": {"url": "https://api.baichuan-ai.com/v1", "model": "Baichuan4"},
            "Moonshot (月之暗面)": {"url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k"},
            "DeepSeek": {"url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
        }
        for name, preset in presets.items():
            if st.button(f"📌 {name}", key=f"preset_{name}"):
                st.session_state.llm_base_url = preset["url"]
                st.session_state.llm_model = preset["model"]
                st.rerun()

elif current_provider == "ollama":
    col1, col2 = st.columns(2)
    base_url = col1.text_input(
        "Ollama 地址",
        value=st.session_state.get("llm_base_url", "http://localhost:11434"),
        placeholder="http://localhost:11434",
        help="默认端口 11434，可改为局域网地址如 http://192.168.1.100:11434",
    )
    model = col2.text_input(
        "模型名称",
        value=st.session_state.get("llm_model", "llama3"),
        placeholder="qwen2.5 / llama3 / mistral",
    )
    st.session_state.llm_base_url = base_url
    st.session_state.llm_model = model

    # Show available Ollama models
    with st.expander("🔍 检测本地 Ollama 模型"):
        try:
            import httpx
            resp = httpx.get(f"{base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                if models:
                    st.success(f"检测到 {len(models)} 个模型: {', '.join(models)}")
                    for m in models:
                        if st.button(f"使用 {m}", key=f"ollama_{m}"):
                            st.session_state.llm_model = m
                            st.rerun()
                else:
                    st.warning("未检测到已安装的模型，请运行 `ollama pull <model>`")
            else:
                st.warning("无法连接 Ollama，请确认服务已启动")
        except Exception as e:
            st.warning(f"无法连接到 {base_url}: {e}")

else:  # mock
    st.info("✅ Mock 模式：无需任何配置，使用规则匹配和示例数据。所有功能均可用。")

# ── 3. 连接测试 ──────────────────────────────────────────────
st.markdown("---")
col_test, col_status = st.columns([1, 3])
if col_test.button("🔌 测试连接", type="primary", use_container_width=True):
    with st.spinner("正在测试连接..."):
        try:
            provider = create_provider(
                current_provider,
                base_url=st.session_state.get("llm_base_url", ""),
                api_key=st.session_state.get("llm_api_key", ""),
                model=st.session_state.get("llm_model", ""),
            )
            if provider.test_connection():
                col_status.success(f"✅ 连接成功！供应商: {current_provider}")
            else:
                col_status.error("❌ 连接失败，请检查配置。")
        except Exception as e:
            col_status.error(f"❌ 连接异常: {e}")

# ── 4. PubMed 配置 ───────────────────────────────────────────
st.markdown("---")
st.subheader("📚 PubMed 配置")

col_p1, col_p2 = st.columns(2)
pubmed_email = col_p1.text_input(
    "联系邮箱",
    value=st.session_state.get("pubmed_email", cfg.pubmed_email),
    placeholder="your@email.com",
)
pubmed_api_key = col_p2.text_input(
    "PubMed API Key（可选）",
    value=st.session_state.get("pubmed_api_key", cfg.pubmed_api_key),
    type="password",
    placeholder="可选，提高请求频率",
)
st.session_state.pubmed_email = pubmed_email
st.session_state.pubmed_api_key = pubmed_api_key

# ── 5. 局域网共享 ────────────────────────────────────────────
st.markdown("---")
st.subheader("🌐 局域网共享")

hostname = socket.gethostname()
try:
    local_ip = socket.gethostbyname(hostname)
except Exception:
    local_ip = "无法获取"

# Try to get the actual LAN IP
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    lan_ip = s.getsockname()[0]
    s.close()
except Exception:
    lan_ip = local_ip

col_net1, col_net2 = st.columns(2)

with col_net1:
    st.markdown("#### 📡 访问地址")
    st.info(f"""
    **本机访问:**
    `http://localhost:8501`

    **局域网访问:**
    `http://{lan_ip}:8501`
    """)

    st.caption("同一 WiFi/局域网下的其他设备用第二个地址即可访问。")

with col_net2:
    st.markdown("#### ⚠️ 注意事项")
    st.warning("""
    1. 其他设备需和本机在同一局域网
    2. Windows 防火墙需允许端口 8501（已自动配置）
    3. 云服务器需在安全组中放行 8501
    4. 关闭本窗口不会停止服务，需到终端 `Ctrl+C`
    """)

# ── 6. 数据路径 ──────────────────────────────────────────────
st.markdown("---")
st.subheader("📁 数据路径")
st.markdown(f"- 数据库: `{cfg.database_path}`")
st.markdown(f"- 导出目录: `{cfg.export_dir}`")

# ── 7. 会话状态 ──────────────────────────────────────────────
st.markdown("---")
st.subheader("ℹ️ 当前会话")
st.json({
    "provider": current_provider,
    "model": st.session_state.get("llm_model", cfg.llm_model),
    "base_url": st.session_state.get("llm_base_url", "-"),
    "has_api_key": bool(st.session_state.get("llm_api_key", "")),
    "pubmed_email_set": bool(st.session_state.get("pubmed_email", "")),
    "lan_ip": lan_ip,
    "port": 8501,
})

st.caption("💡 配置优先级：当前页面 > 环境变量 > .env 文件。密钥仅保存在当前会话内存中，不会写入数据库或日志。")
