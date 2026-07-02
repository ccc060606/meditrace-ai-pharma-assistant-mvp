"""Page 2: 客户管理 — Customer list, detail, merge duplicates."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import datetime

from src.db import get_session
from src.repositories.customer_repo import CustomerRepository
from src.repositories.daily_report_repo import DailyReportRepository
from src.services.customer_service import CustomerService

st.set_page_config(page_title="客户管理", page_icon="👥", layout="wide")

st.title("👥 客户管理")
st.caption("匿名化客户记录管理。客户信息以编号（C001、C002）存储，不保存真实身份信息。")

session = get_session()
cust_repo = CustomerRepository(session)
report_repo = DailyReportRepository(session)
service = CustomerService(cust_repo, report_repo)

# ── Filters ──────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
keyword = col1.text_input("🔍 搜索客户编号", placeholder="C001")
departments = service.get_departments()
dept_filter = col2.selectbox("科室筛选", ["全部"] + departments)

# Build query
customers = service.search(keyword=keyword or None,
                           department=dept_filter if dept_filter != "全部" else None)

# ── Customer List ────────────────────────────────────────────
st.markdown(f"### 客户列表 ({len(customers)} 位)")

if customers:
    cols = st.columns([1, 2, 2, 1, 1])
    cols[0].markdown("**编号**")
    cols[1].markdown("**科室**")
    cols[2].markdown("**备注**")
    cols[3].markdown("**拜访次数**")
    cols[4].markdown("**操作**")

    for c in customers:
        visits = cust_repo.get_visit_count(c.customer_id)
        pending = cust_repo.get_pending_count(c.customer_id)
        cols = st.columns([1, 2, 2, 1, 1])
        cols[0].write(c.customer_id)
        cols[1].write(c.department or "-")
        cols[2].write((c.notes or "")[:50])
        cols[3].write(f"{visits} 次")
        if cols[4].button("详情", key=f"detail_{c.customer_id}"):
            st.session_state.selected_customer = c.customer_id
            st.rerun()
else:
    st.info("暂无客户记录。")

# ── Customer Detail ──────────────────────────────────────────
if "selected_customer" in st.session_state:
    cid = st.session_state.selected_customer
    detail = service.get_customer_detail(cid)

    if detail:
        st.markdown("---")
        st.subheader(f"📋 客户详情: {cid}")

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("拜访次数", detail["visit_count"])
        col_b.metric("待跟进任务", detail["pending_tasks"])
        col_c.metric("跟进完成率", f"{detail['completion_rate']}%")
        col_d.metric("科室", detail["customer"].department or "未设置")

        # Notes
        notes = st.text_area("备注", value=detail["customer"].notes or "", key=f"notes_{cid}")
        if st.button("💾 更新备注", key=f"save_notes_{cid}"):
            service.update(cid, notes=notes)
            st.success("备注已更新")
            st.rerun()

        # Top topics
        if detail["top_topics"]:
            st.markdown("**关注主题:**")
            topics_str = " | ".join(f"{t[0]} ({t[1]})" for t in detail["top_topics"][:5])
            st.markdown(f"*{topics_str}*")

        # Reports timeline
        if detail["reports"]:
            st.markdown("**历史沟通记录:**")
            for r in sorted(detail["reports"], key=lambda x: x.date or datetime.date.min, reverse=True):
                with st.expander(f"{r.date or '未知日期'} — {r.topic or '无主题'}"):
                    st.markdown(f"**主题:** {r.topic or '-'}")
                    st.markdown(f"**反馈:** {r.feedback or '-'}")
                    if r.follow_up_task:
                        status_emoji = {"completed": "✅", "pending": "⏳", "cancelled": "❌"}.get(
                            r.follow_up_status, "❓")
                        st.markdown(f"**任务:** {status_emoji} {r.follow_up_task}")
                    if r.medical_question:
                        st.markdown(f"**医学问题:** 🩺 {r.medical_question}")
                    if r.activity_name:
                        st.markdown(f"**活动:** {r.activity_name}")
                    st.caption(f"状态: {r.follow_up_status or '-'}")

# ── Duplicate Detection ──────────────────────────────────────
st.markdown("---")
st.subheader("🔍 疑似重复客户")

duplicates = service.find_duplicates()
if duplicates:
    for a, b, score in duplicates:
        with st.container(border=True):
            cols = st.columns([2, 1, 2, 1])
            cols[0].write(f"**{a.customer_id}** ({a.department or '-'})")
            cols[1].write(f"相似度: {score:.0%}")
            cols[2].write(f"**{b.customer_id}** ({b.department or '-'})")

            a_visits = cust_repo.get_visit_count(a.customer_id)
            b_visits = cust_repo.get_visit_count(b.customer_id)
            cols[3].caption(f"拜访: {a_visits} vs {b_visits}")

            if cols[3].button(f"合并 {a.customer_id} → {b.customer_id}",
                              key=f"merge_{a.customer_id}_{b.customer_id}"):
                st.session_state.merge_from = a.customer_id
                st.session_state.merge_to = b.customer_id
                st.rerun()

# Merge confirmation
if "merge_from" in st.session_state and "merge_to" in st.session_state:
    from_id = st.session_state.merge_from
    to_id = st.session_state.merge_to
    st.warning(f"⚠️ 确认合并: 将 **{from_id}** 的所有日报记录转移至 **{to_id}**，"
               f"{from_id} 将被标记为已合并。此操作不可撤销。")

    col_yes, col_no = st.columns(2)
    if col_yes.button("✅ 确认合并", type="primary"):
        try:
            count = service.merge_customers(from_id, to_id)
            st.success(f"合并完成！迁移了 {count} 条日报。{from_id} → {to_id}")
            del st.session_state.merge_from
            del st.session_state.merge_to
            st.rerun()
        except Exception as e:
            st.error(f"合并失败: {e}")
    if col_no.button("❌ 取消"):
        del st.session_state.merge_from
        del st.session_state.merge_to
        st.rerun()

# ── Add Customer ─────────────────────────────────────────────
st.markdown("---")
st.subheader("➕ 新建客户")
with st.form("new_customer_form"):
    col_n1, col_n2 = st.columns(2)
    new_dept = col_n1.text_input("科室")
    new_notes = col_n2.text_input("备注")
    if st.form_submit_button("创建客户"):
        c = service.create(department=new_dept or None, notes=new_notes or None)
        st.success(f"✅ 客户 {c.customer_id} 已创建！")
        st.rerun()

session.close()
