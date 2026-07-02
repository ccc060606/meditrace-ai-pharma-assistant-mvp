"""Page 1: 日报录入 — Daily report entry with AI parsing and manual mode."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from io import StringIO

from src.db import get_session
from src.repositories.daily_report_repo import DailyReportRepository
from src.repositories.customer_repo import CustomerRepository
from src.services.report_service import ReportService
from src.llm.base import create_provider
from src.config import Config
from src.utils.sensitive import detect_sensitive_info

st.set_page_config(page_title="日报录入", page_icon="📝", layout="wide")


def get_provider():
    """Get LLM provider from session config."""
    cfg = Config()
    provider_type = st.session_state.get("llm_provider", cfg.llm_provider)
    base_url = st.session_state.get("llm_base_url", cfg.llm_base_url)
    api_key = st.session_state.get("llm_api_key", cfg.llm_api_key)
    model = st.session_state.get("llm_model", cfg.llm_model)
    return create_provider(
        provider_type,
        base_url=base_url,
        api_key=api_key,
        model=model,
    )


st.title("📝 日报录入")

tab1, tab2 = st.tabs(["AI 智能解析", "手工录入"])

# ── Tab 1: AI Parse ─────────────────────────────────────────
with tab1:
    st.markdown("### AI 智能解析日报")
    st.caption("粘贴一条或多条日报文本，或上传 .txt / .csv / .xlsx 文件，AI 将自动提取结构化信息。")

    col_input, col_preview = st.columns([1, 1])

    with col_input:
        input_method = st.radio("输入方式", ["文本输入", "文件上传"], horizontal=True)

        raw_text = ""
        uploaded_filename = ""

        if input_method == "文本输入":
            raw_text = st.text_area(
                "日报原始文本",
                placeholder="请输入日报文本，支持多条（用空行分隔）...\n\n示例：\n2026-05-05 心内科 C001\n主题：新产品降压药介绍\n反馈：对临床试验数据感兴趣\n后续：发送亚洲人群亚组分析文献，截止2026-05-12\n医学问题：该降压药在老年患者中的安全性如何？",
                height=300,
            )
        else:
            uploaded_file = st.file_uploader(
                "上传文件",
                type=["txt", "csv", "xlsx"],
                help="支持 .txt（纯文本）、.csv、.xlsx 文件",
            )
            if uploaded_file:
                uploaded_filename = uploaded_file.name
                try:
                    if uploaded_file.name.endswith(".csv"):
                        df = pd.read_csv(uploaded_file)
                        raw_text = df.to_string(index=False)
                        st.dataframe(df.head(), use_container_width=True)
                    elif uploaded_file.name.endswith(".xlsx"):
                        df = pd.read_excel(uploaded_file, engine="openpyxl")
                        raw_text = df.to_string(index=False)
                        st.dataframe(df.head(), use_container_width=True)
                    else:
                        raw_text = uploaded_file.read().decode("utf-8", errors="replace")
                except Exception as e:
                    st.error(f"文件读取失败: {e}")
                    raw_text = ""

                if uploaded_file.size > 10 * 1024 * 1024:
                    st.error("文件大小超过 10MB 限制，请拆分后上传。")

        # Sensitive info detection
        if raw_text:
            findings = detect_sensitive_info(raw_text)
            if findings:
                st.warning(f"⚠️ 检测到 {len(findings)} 处疑似敏感信息（手机号/身份证/邮箱），"
                          f"建议先去标识化后再解析。")
                for f in findings[:3]:
                    st.caption(f"  - {f['type']}: {f['value'][:3]}****")

        col_btn1, col_btn2 = st.columns(2)
        parse_clicked = col_btn1.button("🔍 AI 解析", type="primary", disabled=not raw_text.strip(),
                                        use_container_width=True)
        clear_clicked = col_btn2.button("清空", use_container_width=True)
        if clear_clicked:
            st.session_state.parsed_results = None
            st.rerun()

    with col_preview:
        if parse_clicked and raw_text.strip():
            with st.spinner("AI 正在解析日报..."):
                try:
                    provider = get_provider()
                    raw_results = provider.extract_daily_reports(raw_text)
                    # Validate through Pydantic
                    from src.models.daily_report import DailyReportExtract
                    validated = []
                    for item in raw_results:
                        try:
                            ext = DailyReportExtract(**item)
                            validated.append(ext.model_dump())
                        except Exception as e:
                            st.warning(f"跳过无效条目: {e}")

                    st.session_state.parsed_results = validated
                    st.session_state.parsed_raw_text = raw_text
                    st.session_state.parsed_ai_json = json.dumps(raw_results, ensure_ascii=False)
                    st.success(f"✅ 解析完成，共提取 {len(validated)} 条记录")
                except Exception as e:
                    st.error(f"❌ 解析失败: {e}")
                    st.session_state.parsed_results = None

        if "parsed_results" in st.session_state and st.session_state.parsed_results:
            results = st.session_state.parsed_results
            st.markdown(f"**解析结果 ({len(results)} 条)**")

            # Editable data table
            df = pd.DataFrame(results)
            columns_order = ["date", "department", "customer_id", "topic", "feedback",
                             "follow_up_task", "task_deadline", "follow_up_status",
                             "medical_question", "activity_name"]
            df = df.reindex(columns=[c for c in columns_order if c in df.columns])

            edited_df = st.data_editor(
                df,
                column_config={
                    "date": st.column_config.TextColumn("日期", help="YYYY-MM-DD"),
                    "department": st.column_config.TextColumn("科室"),
                    "customer_id": st.column_config.TextColumn("客户编号"),
                    "topic": st.column_config.TextColumn("主题"),
                    "feedback": st.column_config.TextColumn("反馈"),
                    "follow_up_task": st.column_config.TextColumn("后续任务"),
                    "task_deadline": st.column_config.TextColumn("截止日期"),
                    "follow_up_status": st.column_config.SelectboxColumn(
                        "状态", options=["pending", "completed", "cancelled"],
                    ),
                    "medical_question": st.column_config.TextColumn("医学问题"),
                    "activity_name": st.column_config.TextColumn("活动名称"),
                },
                num_rows="dynamic",
                use_container_width=True,
                height=400,
                key="edit_table",
            )

            if st.button("💾 确认入库", type="primary", use_container_width=True):
                session = get_session()
                try:
                    repo = DailyReportRepository(session)
                    records = edited_df.to_dict("records")
                    # Save directly using repo for simplicity
                    from src.models.daily_report import DailyReportCreate
                    saved_count = 0
                    for r in records:
                        data = DailyReportCreate(
                            date=r.get("date") or None,
                            department=r.get("department") or None,
                            customer_id=r.get("customer_id") or None,
                            topic=r.get("topic") or None,
                            feedback=r.get("feedback") or None,
                            follow_up_task=r.get("follow_up_task") or None,
                            task_deadline=r.get("task_deadline") or None,
                            follow_up_status=r.get("follow_up_status", "pending"),
                            medical_question=r.get("medical_question") or None,
                            activity_name=r.get("activity_name") or None,
                            raw_text=st.session_state.get("parsed_raw_text", ""),
                            ai_result_json=st.session_state.get("parsed_ai_json", ""),
                        )
                        repo.create(data)
                        saved_count += 1

                    # Ensure customer records exist
                    cust_repo = CustomerRepository(session)
                    for r in records:
                        cid = r.get("customer_id")
                        if cid and not cust_repo.get_by_customer_id(cid):
                            cust_repo.create(department=r.get("department"))

                    st.success(f"✅ 成功保存 {saved_count} 条日报记录！")
                    st.session_state.parsed_results = None
                    st.rerun()
                except Exception as e:
                    st.error(f"保存失败: {e}")
                finally:
                    session.close()

# ── Tab 2: Manual Entry ─────────────────────────────────────
with tab2:
    st.markdown("### 手工录入日报")
    st.caption("无需 AI，直接填写表单录入日报。")

    with st.form("manual_entry_form"):
        col1, col2 = st.columns(2)
        date = col1.date_input("沟通日期", value=None)
        department = col2.text_input("科室", placeholder="心内科")
        customer_id = col1.text_input("客户编号", placeholder="C001")
        topic = col2.text_input("沟通主题", placeholder="产品介绍")
        feedback = st.text_area("客户反馈", height=68)
        col3, col4 = st.columns(2)
        follow_up_task = col3.text_area("后续任务", height=68)
        task_deadline = col4.date_input("任务截止日期", value=None)
        follow_up_status = st.selectbox("跟进状态", ["pending", "completed", "cancelled"])
        medical_question = st.text_area("医学问题", height=68, placeholder="客户提出的医学问题...")
        activity_name = st.text_input("活动名称", placeholder="科室会 / 一对一拜访")

        submitted = st.form_submit_button("💾 保存日报", type="primary", use_container_width=True)
        if submitted:
            session = get_session()
            try:
                repo = DailyReportRepository(session)
                from src.models.daily_report import DailyReportCreate
                data = DailyReportCreate(
                    date=date.isoformat() if date else None,
                    department=department or None,
                    customer_id=customer_id or None,
                    topic=topic or None,
                    feedback=feedback or None,
                    follow_up_task=follow_up_task or None,
                    task_deadline=task_deadline.isoformat() if task_deadline else None,
                    follow_up_status=follow_up_status,
                    medical_question=medical_question or None,
                    activity_name=activity_name or None,
                    raw_text=f"手工录入: {date} {department} {customer_id} {topic}",
                )
                repo.create(data)
                # Ensure customer exists
                if customer_id:
                    cust_repo = CustomerRepository(session)
                    if not cust_repo.get_by_customer_id(customer_id):
                        cust_repo.create(department=department)
                st.success("✅ 日报已保存！")
                st.rerun()
            except Exception as e:
                st.error(f"保存失败: {e}")
            finally:
                session.close()

# ── Recent Reports ───────────────────────────────────────────
st.markdown("---")
st.subheader("📋 最近录入的日报")

session = get_session()
try:
    repo = DailyReportRepository(session)
    recent = repo.get_recent(10)
    if recent:
        data = []
        for r in recent:
            data.append({
                "ID": r.id,
                "日期": str(r.date) if r.date else "",
                "科室": r.department or "",
                "客户": r.customer_id or "",
                "主题": r.topic or "",
                "状态": r.follow_up_status or "",
                "医学问题": (r.medical_question or "")[:50] + ("..." if r.medical_question and len(r.medical_question) > 50 else ""),
            })
        df_recent = pd.DataFrame(data)
        st.dataframe(df_recent, use_container_width=True, hide_index=True)
    else:
        st.info("暂无日报记录。请使用上方工具录入第一条日报。")
finally:
    session.close()
