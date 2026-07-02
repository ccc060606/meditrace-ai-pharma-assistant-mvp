"""Page 3: 月报生成 — Monthly report with stats, charts, AI summary, export."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.db import get_session
from src.services.monthly_service import MonthlyReportService
from src.llm.base import create_provider
from src.config import Config
from src.exporters.excel_exporter import ExcelExporter
from src.exporters.word_exporter import WordExporter

st.set_page_config(page_title="月报生成", page_icon="📊", layout="wide")

st.title("📊 月报生成")


def get_provider():
    cfg = Config()
    provider_type = st.session_state.get("llm_provider", cfg.llm_provider)
    return create_provider(
        provider_type,
        base_url=st.session_state.get("llm_base_url", cfg.llm_base_url),
        api_key=st.session_state.get("llm_api_key", cfg.llm_api_key),
        model=st.session_state.get("llm_model", cfg.llm_model),
    )


session = get_session()
service = MonthlyReportService(session)

# ── Month Selection ──────────────────────────────────────────
available_months = service.get_available_months()
if not available_months:
    st.warning("暂无日报数据。请先在「日报录入」页面添加日报。")
    session.close()
    st.stop()

col_m1, col_m2 = st.columns([1, 2])
selected_month = col_m1.selectbox("选择月份", available_months)
year, month = map(int, selected_month.split("-"))

if col_m2.button("🔄 刷新数据", use_container_width=True):
    st.rerun()

# ── Compute Stats ────────────────────────────────────────────
stats = service.compute_stats(year, month)
reports = stats.pop("reports")

# ── Metrics Row ──────────────────────────────────────────────
st.markdown("### 📈 数据概览")
cols = st.columns(5)
cols[0].metric("拜访总量", stats["total_visits"])
cols[1].metric("覆盖客户", stats["unique_customers"])
cols[2].metric("活动数量", stats["activity_count"])
cols[3].metric("待处理任务", stats["tasks_pending"])
cols[4].metric("完成率", f"{stats['completion_rate']}%")

# ── Charts ───────────────────────────────────────────────────
st.markdown("---")
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("科室分布")
    if stats["department_distribution"]:
        dept_df = pd.DataFrame(
            list(stats["department_distribution"].items()),
            columns=["科室", "拜访次数"]
        )
        fig = px.pie(dept_df, values="拜访次数", names="科室", hole=0.4)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无数据")

with col_chart2:
    st.subheader("任务统计")
    task_data = {
        "状态": ["已完成", "待处理"],
        "数量": [stats["tasks_completed"], stats["tasks_pending"]],
    }
    task_df = pd.DataFrame(task_data)
    colors = ["#2ecc71", "#e74c3c"]
    fig = px.bar(task_df, x="状态", y="数量", color="状态",
                 color_discrete_sequence=colors, text="数量")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    if stats["tasks_total"] > 0:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=stats["completion_rate"],
            title={"text": "跟进完成率"},
            gauge={"axis": {"range": [0, 100]},
                   "bar": {"color": "#2ecc71"},
                   "steps": [{"range": [0, 50], "color": "#fdebd0"},
                             {"range": [50, 80], "color": "#f9e79f"},
                             {"range": [80, 100], "color": "#d5f5e3"}]},
        ))
        st.plotly_chart(fig_gauge, use_container_width=True)

# ── Top Topics ───────────────────────────────────────────────
st.markdown("---")
col_topics, col_med = st.columns(2)

with col_topics:
    st.subheader("高频沟通主题")
    if stats["top_topics"]:
        for i, t in enumerate(stats["top_topics"][:10], 1):
            st.write(f"{i}. {t}")
    else:
        st.info("暂无主题数据")

with col_med:
    st.subheader("医学问题")
    if stats["medical_questions"]:
        for q in stats["medical_questions"][:10]:
            st.markdown(f"🩺 {q}")
    else:
        st.info("本月无医学问题记录")

# ── AI Summary ───────────────────────────────────────────────
st.markdown("---")
st.subheader("🤖 AI 文字总结")

if "ai_summary" not in st.session_state:
    st.session_state.ai_summary = None

col_ai1, col_ai2 = st.columns([1, 3])
if col_ai1.button("🪄 生成 AI 总结", type="primary", use_container_width=True):
    with st.spinner("AI 正在生成月报总结..."):
        try:
            provider = get_provider()
            svc = MonthlyReportService(session, provider)
            summary = svc.generate_ai_summary(stats)
            st.session_state.ai_summary = summary
        except Exception as e:
            st.warning(f"AI 总结生成失败，使用内置摘要: {e}")
            summary = service._fallback_summary(stats)
            st.session_state.ai_summary = summary

if st.session_state.ai_summary:
    summary = st.session_state.ai_summary

    st.markdown("**本月工作进展**")
    progress = st.text_area("编辑工作进展", value=summary.get("progress_summary", ""),
                            height=80, key="edit_progress")

    st.markdown("**重点医学问题**")
    key_issues = st.text_area("编辑重点问题", value=summary.get("key_issues", ""),
                              height=80, key="edit_issues")

    st.markdown("**未完成事项**")
    unfinished = st.text_area("编辑未完成事项", value=summary.get("unfinished_items", ""),
                              height=80, key="edit_unfinished")

    st.markdown("**下月计划**")
    next_plan = st.text_area("编辑下月计划", value=summary.get("next_month_plan", ""),
                             height=80, key="edit_plan")

    # Update summary with edits
    final_summary = {
        "progress_summary": progress,
        "key_issues": key_issues,
        "unfinished_items": unfinished,
        "next_month_plan": next_plan,
    }
else:
    st.info("点击「生成 AI 总结」按钮，AI 将根据统计数据自动生成月报文字总结。")
    final_summary = {
        "progress_summary": "", "key_issues": "",
        "unfinished_items": "", "next_month_plan": "",
    }

# ── Export ───────────────────────────────────────────────────
st.markdown("---")
st.subheader("📥 导出月报")

col_exp1, col_exp2 = st.columns(2)

if col_exp1.button("📊 导出 Excel", use_container_width=True, type="primary"):
    try:
        exporter = ExcelExporter()
        filepath = exporter.export(stats, final_summary, reports, selected_month)
        with open(filepath, "rb") as f:
            col_exp1.download_button(
                "📥 下载 Excel",
                f.read(),
                file_name=Path(filepath).name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        st.success(f"✅ Excel 已生成！")
    except Exception as e:
        st.error(f"Excel 导出失败: {e}")

if col_exp2.button("📝 导出 Word", use_container_width=True, type="primary"):
    try:
        exporter = WordExporter()
        filepath = exporter.export(stats, final_summary, reports, selected_month)
        with open(filepath, "rb") as f:
            col_exp2.download_button(
                "📥 下载 Word",
                f.read(),
                file_name=Path(filepath).name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        st.success(f"✅ Word 已生成！")
    except Exception as e:
        st.error(f"Word 导出失败: {e}")

# ── Detail Table ─────────────────────────────────────────────
st.markdown("---")
st.subheader(f"📋 {selected_month} 日报明细")

report_data = []
for r in reports:
    report_data.append({
        "ID": r.id,
        "日期": str(r.date) if r.date else "",
        "科室": r.department or "",
        "客户": r.customer_id or "",
        "主题": r.topic or "",
        "状态": r.follow_up_status or "",
        "任务": (r.follow_up_task or "")[:40],
    })
if report_data:
    st.dataframe(pd.DataFrame(report_data), use_container_width=True, hide_index=True)

session.close()
