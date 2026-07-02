"""Page 4: 文献追踪 — PubMed search and AI literature summarization."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import streamlit as st
import pandas as pd

from src.db import get_session
from src.repositories.literature_repo import LiteratureRepository
from src.services.literature_service import LiteratureService
from src.literature.pubmed import PubMedClient
from src.llm.base import create_provider
from src.config import Config

st.set_page_config(page_title="文献追踪", page_icon="📚", layout="wide")

st.title("📚 文献追踪")
st.warning("⚠️ 免责声明：文献检索和 AI 总结内容仅用于内部信息整理，不构成医学建议。"
           "重要结论必须人工核验原文 PMID/DOI 链接。")


def get_provider():
    cfg = Config()
    return create_provider(
        st.session_state.get("llm_provider", cfg.llm_provider),
        base_url=st.session_state.get("llm_base_url", cfg.llm_base_url),
        api_key=st.session_state.get("llm_api_key", cfg.llm_api_key),
        model=st.session_state.get("llm_model", cfg.llm_model),
    )


session = get_session()
lit_repo = LiteratureRepository(session)
llm = get_provider()
pubmed = PubMedClient()
service = LiteratureService(lit_repo, llm, pubmed)

# ── Init session state keys ────────────────────────────────────
if "lit_search_queries" not in st.session_state:
    st.session_state.lit_search_queries = None
if "lit_current_question" not in st.session_state:
    st.session_state.lit_current_question = ""
if "lit_last_search" not in st.session_state:
    st.session_state.lit_last_search = None
if "lit_searching" not in st.session_state:
    st.session_state.lit_searching = False

# ── Tab Layout ─────────────────────────────────────────────────
tab1, tab2 = st.tabs(["检索文献", "已保存文献"])

with tab1:
    st.markdown("### 🔍 检索 PubMed 文献")

    # Medical questions from daily reports
    from src.repositories.daily_report_repo import DailyReportRepository
    report_repo = DailyReportRepository(session)
    med_reports = report_repo.get_medical_questions()

    question_options = ["手动输入医学问题"] + [
        f"[{r.date}] {r.customer_id}: {(r.medical_question or '')[:60]}"
        for r in med_reports
    ]

    selected = st.selectbox(
        "选择医学问题",
        question_options,
        key="lit_question_select",
    )

    if selected == "手动输入医学问题":
        question_text = st.text_area(
            "输入医学问题",
            placeholder="请输入需要检索的医学问题...",
            height=100,
            key="lit_manual_question",
        )
    else:
        idx = question_options.index(selected)
        question_text = med_reports[idx - 1].medical_question if idx > 0 else ""

    col_q1, col_q2 = st.columns([1, 3])
    max_results = col_q1.number_input("检索数量", min_value=1, max_value=50, value=10)

    # ── Step 1: Generate search queries ─────────────────────
    if col_q2.button(
        "🔍 生成检索词",
        type="primary",
        disabled=not question_text.strip(),
        use_container_width=True,
        key="lit_generate_btn",
    ):
        st.session_state.lit_searching = True
        with st.spinner("正在生成检索词..."):
            queries = service.generate_queries(question_text)
            st.session_state.lit_search_queries = queries
            st.session_state.lit_current_question = question_text
            st.session_state.lit_last_search = None  # clear old results
        st.rerun()

    # ── Show editable queries (outside button block — always visible if queries exist) ──
    if st.session_state.lit_search_queries is not None:
        queries = st.session_state.lit_search_queries

        st.markdown("---")
        st.markdown("**✏️ 编辑检索词（可修改后重新搜索）**")

        zh_default = ", ".join(queries.get("zh_terms", []))
        en_default = ", ".join(queries.get("en_terms", []))

        zh_edited = st.text_area(
            "中文检索词（逗号分隔）",
            value=zh_default,
            key="lit_zh_terms",
        )
        en_edited = st.text_area(
            "英文检索词（逗号分隔）",
            value=en_default,
            key="lit_en_terms",
        )

        # ── Step 2: Confirm and search ───────────────────────
        col_s1, col_s2, col_s3 = st.columns([1, 1, 1])
        search_clicked = col_s1.button(
            "🔬 确认并搜索 PubMed",
            type="primary",
            use_container_width=True,
            key="lit_search_btn",
        )

        if search_clicked:
            zh_terms = [t.strip() for t in zh_edited.split(",") if t.strip()]
            en_terms = [t.strip() for t in en_edited.split(",") if t.strip()]
            custom_queries = {"zh_terms": zh_terms, "en_terms": en_terms}

            with st.spinner(f"正在搜索 PubMed（最多 {max_results} 篇）..."):
                try:
                    result = service.search_and_save(
                        question_text=st.session_state.lit_current_question,
                        max_results=max_results,
                        custom_queries=custom_queries,
                    )
                    st.session_state.lit_last_search = result
                    st.session_state.lit_searching = False

                    if result["errors"]:
                        for err in result["errors"]:
                            st.warning(f"⚠️ {err}")

                    if result["articles"]:
                        st.success(f"✅ 检索到 {len(result['articles'])} 篇文献（已去重保存）")
                    else:
                        st.warning("未检索到相关文献。请尝试修改检索词。")

                    st.rerun()

                except Exception as e:
                    st.error(f"PubMed 检索失败: {e}")
                    st.info("请检查网络连接，或尝试修改检索词。")

        # Reset button
        if col_s3.button("🔄 重新选择问题", use_container_width=True, key="lit_reset_btn"):
            st.session_state.lit_search_queries = None
            st.session_state.lit_current_question = ""
            st.session_state.lit_last_search = None
            st.session_state.lit_searching = False
            st.rerun()

    # ── Show search results ──────────────────────────────────
    last_search = st.session_state.lit_last_search
    if last_search and last_search.get("articles"):
        st.markdown("---")
        st.subheader(f"检索结果 ({len(last_search['articles'])} 篇)")

        for art in last_search["articles"]:
            title_display = art.title or "无标题"
            year_display = f" ({art.year})" if art.year else ""
            with st.expander(f"{title_display}{year_display}"):
                col_m1, col_m2 = st.columns(2)
                col_m1.markdown(f"**PMID:** {art.pmid or 'N/A'}")
                col_m2.markdown(f"**DOI:** {art.doi or 'N/A'}")
                st.markdown(f"**作者:** {art.authors or 'N/A'}")
                st.markdown(f"**期刊:** {art.journal or 'N/A'} ({art.year or 'N/A'})")
                if art.study_type:
                    st.markdown(f"**研究类型:** {art.study_type}")

                if art.source_url:
                    st.markdown(f"🔗 [{art.source_url}]({art.source_url})")

                # Abstract
                if art.abstract:
                    st.markdown("**原始摘要:**")
                    st.text_area(
                        "摘要", value=art.abstract,
                        height=120, key=f"abs_{art.id}", disabled=True,
                    )

                # AI Summary button
                if st.button("🤖 AI 总结", key=f"summarize_{art.id}"):
                    with st.spinner("AI 正在总结..."):
                        summary = service.summarize_article(art.id, {
                            "title": art.title, "authors": art.authors,
                            "journal": art.journal, "year": art.year,
                            "abstract": art.abstract,
                        })
                        st.markdown("**🤖 AI 总结:**")
                        st.info(summary)
                        st.caption("⚠️ AI 总结仅供参考，请以原始摘要和原文为准。")

                        # Save summary
                        art.ai_summary = summary
                        session.commit()

with tab2:
    st.markdown("### 📋 已保存文献")

    questions = service.get_questions()
    if questions:
        for q in questions:
            date_str = q.created_at.strftime('%Y-%m-%d') if q.created_at else ''
            with st.expander(f"问题: {q.question_text[:80]} ({date_str})"):
                articles = service.get_articles_for_question(q.id)
                if articles:
                    for a in articles:
                        st.markdown(f"📄 **{a.title}** ({a.year or 'N/A'})")
                        pmid_doi = f"PMID: {a.pmid}" if a.pmid else ""
                        if a.doi:
                            pmid_doi += f" | DOI: {a.doi}"
                        st.caption(pmid_doi)
                        if a.source_url:
                            st.caption(f"🔗 [{a.source_url}]({a.source_url})")
                        if a.ai_summary:
                            st.info(f"🤖 {a.ai_summary[:200]}")
                        st.markdown("---")
                else:
                    st.caption("暂无检索结果")
    else:
        st.info("暂无保存的文献。请在「检索文献」标签页搜索 PubMed。")

session.close()
