"""MockProvider — for testing and demo. No API key or network needed."""
import datetime
import json
import logging
import re

logger = logging.getLogger(__name__)


class MockProvider:
    provider_name = "mock"

    def __init__(self):
        self._today = datetime.date.today().isoformat()

    def test_connection(self) -> bool:
        return True

    def extract_daily_reports(self, text: str) -> list[dict]:
        """Parse daily report text with simple pattern matching.
        Returns validated dicts that will pass DailyReportExtract."""
        results = []
        # Split by double newline or numbered entries
        entries = re.split(r'\n\s*\n|\n(?=\d+[\.、)])', text.strip())
        if len(entries) <= 1:
            entries = [text.strip()]

        for entry in entries:
            entry = entry.strip()
            if not entry or len(entry) < 10:
                continue

            data = self._parse_single(entry)
            results.append(data)

        if not results:
            # Fallback: treat entire text as one entry
            results.append(self._parse_single(text))

        return results

    def _parse_single(self, text: str) -> dict:
        """Extract fields from a single entry using patterns."""
        data = {
            "date": self._find_date(text),
            "department": self._find_field(text, ["科室", "部门"]),
            "customer_id": self._find_customer(text),
            "topic": self._find_field(text, ["主题", "沟通主题", "拜访目的"]),
            "feedback": self._find_field(text, ["反馈", "客户反馈", "客户意见"]),
            "follow_up_task": self._find_field(text, ["后续", "待办", "后续任务", "跟进事项"]),
            "task_deadline": self._find_date(text, patterns=[r'截止[：:]\s*(\d{4}-\d{2}-\d{2})']),
            "follow_up_status": "pending",
            "medical_question": self._find_field(text, ["医学问题", "医学疑问", "临床问题"]),
            "activity_name": self._find_field(text, ["活动", "会议", "活动名称"]),
        }
        return data

    def _find_date(self, text: str, patterns: list[str] = None) -> str | None:
        if patterns is None:
            patterns = [
                r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
                r'(\d{1,2}月\d{1,2}日)',
            ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                ds = m.group(1)
                # Normalize
                if '月' in ds:
                    ds = ds.replace('月', '-').replace('日', '')
                    parts = ds.split('-')
                    if len(parts) == 2:
                        ds = f"{datetime.date.today().year}-{int(parts[0]):02d}-{int(parts[1]):02d}"
                ds = ds.replace('/', '-')
                return ds
        return self._today

    def _find_field(self, text: str, keywords: list[str]) -> str | None:
        for kw in keywords:
            # Pattern: keyword followed by colon or Chinese colon and content
            m = re.search(rf'{kw}[：:]\s*(.+?)(?:\n|$)', text)
            if m:
                return m.group(1).strip()
        return None

    def _find_customer(self, text: str) -> str | None:
        m = re.search(r'(C\d{3})', text)
        if m:
            return m.group(1)
        m = re.search(r'客户[：:]\s*(\S+)', text)
        if m:
            return m.group(1).strip()
        return None

    def generate_monthly_summary(self, context: dict) -> dict:
        """Generate mock monthly summary."""
        month = context.get("month", "")
        dept_dist = context.get("department_distribution", {})
        dept_str = "、".join(f"{k}({v}次)" for k, v in dept_dist.items()) if dept_dist else "各科室均衡"
        top_topics = context.get("top_topics", [])
        topic_str = "、".join(top_topics[:5]) if top_topics else "产品咨询与用药指导"
        med_questions = context.get("medical_questions", [])
        med_str = "；".join(med_questions[:3]) if med_questions else "暂无重点医学问题"

        return {
            "progress_summary": f"{month}共完成{context.get('total_visits', 0)}次拜访，覆盖{context.get('unique_customers', 0)}位客户，"
                                f"涉及{dept_str}。主要沟通主题包括：{topic_str}。",
            "key_issues": f"本月重点医学问题：{med_str}。",
            "unfinished_items": f"截至月底，仍有{context.get('pending_tasks', 0)}项跟进任务待处理，"
                               f"完成率为{context.get('completion_rate', 0)}%。",
            "next_month_plan": f"下月计划继续跟进未完成事项，加强{list(dept_dist.keys())[0] if dept_dist else '重点科室'}的拜访频次，"
                              f"针对高频医学问题准备学术资料。",
        }

    def generate_literature_queries(self, medical_question: str) -> dict:
        """Generate mock search queries."""
        # Simple keyword extraction
        zh_terms = [medical_question[:30]]
        # Generate English terms by keyword mapping
        en_map = {
            "糖尿病": "diabetes mellitus",
            "高血压": "hypertension",
            "肺癌": "lung cancer",
            "乳腺癌": "breast cancer",
            "靶向": "targeted therapy",
            "免疫": "immunotherapy",
            "化疗": "chemotherapy",
            "放疗": "radiotherapy",
            "药物": "drug",
            "治疗": "treatment",
            "临床": "clinical",
            "试验": "trial",
            "安全性": "safety",
            "疗效": "efficacy",
        }
        en_parts = []
        for cn, en in en_map.items():
            if cn in medical_question:
                en_parts.append(en)
        en_terms = [" ".join(en_parts)] if en_parts else ["clinical trial treatment"]
        return {
            "zh_terms": zh_terms,
            "en_terms": en_terms,
        }

    def summarize_article(self, article: dict) -> str:
        """Generate mock summary."""
        abstract = article.get("abstract", "") or ""
        title = article.get("title", "")
        if abstract:
            # Return first 200 chars as mock summary
            return f"[Mock AI 总结] {abstract[:200]}..."
        return f"[Mock AI 总结] 文献《{title}》涉及相关医学研究，请查看原始摘要获取详细信息。"

    # ── Mock PubMed search results ───────────────────────────────

    _MOCK_ARTICLES = [
        {
            "pmid": "30000001", "doi": "10.1000/mock.001",
            "title": "Efficacy and safety of novel antihypertensive agents in elderly patients: a systematic review",
            "authors": "Zhang W; Li X; Wang Y; Chen H; Liu J",
            "journal": "J Hypertens", "year": 2025, "study_type": "Systematic Review",
            "abstract": "Background: Hypertension in elderly patients presents unique challenges due to age-related physiological changes and polypharmacy. "
                       "Methods: We conducted a systematic review of randomized controlled trials (RCTs) evaluating novel antihypertensive agents "
                       "in patients aged ≥65 years. A total of 45 RCTs involving 28,000 patients were included. "
                       "Results: Novel agents demonstrated superior blood pressure reduction (mean SBP reduction -15.2 mmHg, 95% CI -17.1 to -13.3) "
                       "compared to conventional therapy. The incidence of adverse events was comparable (OR 0.92, 95% CI 0.78-1.08). "
                       "Notably, cognitive function was preserved or improved in the novel agent groups. "
                       "Conclusions: Novel antihypertensive agents show favorable efficacy and safety profiles in elderly hypertensive patients, "
                       "with particular benefits in cognitive preservation. Further long-term studies are needed.",
        },
        {
            "pmid": "30000002", "doi": "10.1000/mock.002",
            "title": "PD-1 inhibitors combined with chemotherapy versus monotherapy in advanced non-small cell lung cancer: a meta-analysis",
            "authors": "Chen X; Wang Z; Liu M; Johnson K; Brown A",
            "journal": "Lancet Oncol", "year": 2025, "study_type": "Meta-Analysis",
            "abstract": "Background: The optimal treatment strategy combining PD-1 inhibitors with chemotherapy remains debated. "
                       "Methods: We performed a meta-analysis of 18 phase III RCTs comparing PD-1 inhibitor plus chemotherapy "
                       "versus PD-1 inhibitor monotherapy in advanced NSCLC. "
                       "Results: Combination therapy significantly improved progression-free survival (HR 0.62, 95% CI 0.54-0.71, p<0.001) "
                       "and overall survival (HR 0.71, 95% CI 0.63-0.80, p<0.001). Grade ≥3 adverse events were higher in the combination "
                       "group (RR 1.35, 95% CI 1.18-1.54). Subgroup analysis showed consistent benefit across PD-L1 expression levels. "
                       "Conclusions: PD-1 inhibitor plus chemotherapy provides superior efficacy over monotherapy, with manageable toxicity.",
        },
        {
            "pmid": "30000003", "doi": "10.1000/mock.003",
            "title": "Long-term cardiovascular safety of GLP-1 receptor agonists: an updated analysis",
            "authors": "Wang H; Zhang L; Liu Y; Smith R; Davis M",
            "journal": "N Engl J Med", "year": 2026, "study_type": "Meta-Analysis",
            "abstract": "Background: GLP-1 receptor agonists have revolutionized diabetes management, but long-term cardiovascular safety data remain limited. "
                       "Methods: We analyzed cardiovascular outcomes from 12 cardiovascular outcome trials (CVOTs) involving 85,000 patients "
                       "followed for median 4.2 years. "
                       "Results: GLP-1 RAs reduced major adverse cardiovascular events (MACE) by 13% (HR 0.87, 95% CI 0.81-0.94). "
                       "No increased risk of heart failure, arrhythmia, or valvular disease was observed. Consistent benefits were seen "
                       "across subgroups. "
                       "Conclusions: Long-term GLP-1 RA use is associated with cardiovascular safety and potential benefit, "
                       "supporting current guideline recommendations.",
        },
        {
            "pmid": "30000004", "doi": "10.1000/mock.004",
            "title": "CAR-T cell therapy in solid tumors: challenges and recent advances",
            "authors": "Li J; Kim S; Park H; Garcia M; Wong T",
            "journal": "Nat Rev Clin Oncol", "year": 2026, "study_type": "Review",
            "abstract": "The application of CAR-T cell therapy to solid tumors has faced significant hurdles including antigen heterogeneity, "
                       "the immunosuppressive tumor microenvironment, and limited T cell infiltration. Recent advances in engineering approaches "
                       "— including armored CAR-T cells, logic-gated circuits, and combination strategies with checkpoint blockade — "
                       "have shown promising early clinical results. This review summarizes the current landscape of CAR-T therapy "
                       "in solid tumors, highlighting key clinical trials and emerging strategies to overcome resistance mechanisms.",
        },
        {
            "pmid": "30000005", "doi": "10.1000/mock.005",
            "title": "Predictive biomarkers for immune-related adverse events in cancer immunotherapy",
            "authors": "Brown K; Chen L; Tanaka H; Miller S; Zhao W",
            "journal": "J Clin Oncol", "year": 2025, "study_type": "Prospective Cohort Study",
            "abstract": "Background: Immune-related adverse events (irAEs) are a major limitation of immune checkpoint inhibitor therapy. "
                       "Methods: We prospectively analyzed 1,200 patients receiving anti-PD-1/PD-L1 therapy. Baseline cytokine profiles, "
                       "autoantibody panels, and T cell repertoire diversity were assessed as potential biomarkers. "
                       "Results: Elevated baseline IL-17 (>15 pg/mL, OR 3.2, p<0.001) and the presence of pre-existing autoantibodies "
                       "(OR 2.8, p=0.002) were significantly associated with grade ≥3 irAEs. Gut microbiome diversity (Shannon index) "
                       "was inversely correlated with irAE risk. A combined biomarker model achieved AUC 0.82 for irAE prediction. "
                       "Conclusions: Baseline biomarkers can identify patients at high risk for severe irAEs, enabling personalized monitoring.",
        },
        {
            "pmid": "30000006", "doi": "10.1000/mock.006",
            "title": "Biomarkers for biologic agent selection in severe asthma: a practical guide",
            "authors": "Smith J; Patel N; Kim D; Zhang R; Lee H",
            "journal": "Am J Respir Crit Care Med", "year": 2026, "study_type": "Review",
            "abstract": "The expanding arsenal of biologic agents for severe asthma necessitates biomarker-guided treatment selection. "
                       "This review synthesizes evidence on blood eosinophil counts, fractional exhaled nitric oxide (FeNO), "
                       "serum total IgE, and periostin as predictors of response to anti-IgE, anti-IL5/IL5R, anti-IL4Rα, and anti-TSLP therapies. "
                       "We propose a pragmatic biomarker-based algorithm for matching patients to the most appropriate biologic agent.",
        },
        {
            "pmid": "30000007", "doi": "10.1000/mock.007",
            "title": "Proarrhythmic risk of novel antiarrhythmic drugs: a comprehensive evaluation",
            "authors": "Wang F; Anderson R; Thompson P; Kumar S; Ito M",
            "journal": "Eur Heart J", "year": 2026, "study_type": "Systematic Review",
            "abstract": "Background: Antiarrhythmic drug development has been hampered by proarrhythmic concerns. "
                       "Methods: We systematically reviewed the proarrhythmic profiles of 8 novel antiarrhythmic agents across "
                       "preclinical and clinical studies. "
                       "Results: Atrial-selective agents (vernakalant, budiodarone) showed minimal ventricular proarrhythmia. "
                       "Novel class III agents showed hERG safety margins >30-fold at therapeutic concentrations. "
                       "Late sodium current inhibitors demonstrated favorable safety profiles. "
                       "Conclusions: Next-generation antiarrhythmic agents show improved cardiac safety profiles compared to traditional drugs.",
        },
        {
            "pmid": "30000008", "doi": "10.1000/mock.008",
            "title": "Novel antifibrotic agents in interstitial lung disease: mechanisms and clinical progress",
            "authors": "Tanaka Y; Garcia R; Wilson B; Johnson P; Adams K",
            "journal": "Chest", "year": 2026, "study_type": "Review",
            "abstract": "Idiopathic pulmonary fibrosis and other interstitial lung diseases have limited treatment options beyond pirfenidone and "
                       "nintedanib. This review examines emerging antifibrotic agents targeting novel pathways: autotaxin-LPA axis inhibitors, "
                       "CTGF inhibitors, galectin-3 inhibitors, and integrin antagonists. Phase II/III clinical data are reviewed for "
                       "each class, highlighting efficacy signals and safety considerations. Combination strategies targeting "
                       "multiple fibrotic pathways show particular promise.",
        },
    ]

    # Chinese keyword → PMID mapping for cross-lingual search
    _CN_KEYWORD_MAP = {
        "高血压": ["30000001", "30000007"],
        "降压药": ["30000001"],
        "安全性": ["30000001", "30000003", "30000007"],
        "老年": ["30000001"],
        "pd-1": ["30000002", "30000005"],
        "免疫": ["30000002", "30000004", "30000005"],
        "化疗": ["30000002"],
        "肺癌": ["30000002"],
        "glp-1": ["30000003"],
        "糖尿病": ["30000003"],
        "心血管": ["30000003", "30000007"],
        "car-t": ["30000004"],
        "实体瘤": ["30000004"],
        "肿瘤": ["30000002", "30000004", "30000005"],
        "生物标志物": ["30000005", "30000006"],
        "不良反应": ["30000005"],
        "哮喘": ["30000006"],
        "心律失常": ["30000007"],
        "抗心律失常": ["30000007"],
        "纤维化": ["30000008"],
        "肺": ["30000002", "30000006", "30000008"],
        "临床试验": ["30000001", "30000002", "30000004", "30000005"],
        "疗效": ["30000001", "30000002", "30000003"],
        "靶向": ["30000002", "30000004"],
        "抑制剂": ["30000001", "30000002", "30000003", "30000005"],
    }

    @staticmethod
    def _match_articles(keywords: list[str], max_results: int = 10) -> list[dict]:
        """Match mock articles against search keywords. Supports both Chinese and English."""
        results: dict[str, float] = {}  # pmid -> score
        art_index = {a["pmid"]: a for a in MockProvider._MOCK_ARTICLES}

        for kw in keywords:
            kw_lower = kw.lower().strip()
            if len(kw_lower) < 2:
                continue

            # 1) Chinese keyword → PMID mapping
            for cn_key, pmids in MockProvider._CN_KEYWORD_MAP.items():
                if cn_key in kw_lower or kw_lower in cn_key:
                    for pmid in pmids:
                        results[pmid] = results.get(pmid, 0) + 2

            # 2) English substring match against article text
            for art in MockProvider._MOCK_ARTICLES:
                search_text = (art["title"] + " " + art["abstract"] + " " + art["journal"]).lower()
                if kw_lower in search_text:
                    results[art["pmid"]] = results.get(art["pmid"], 0) + 1
                # Individual words
                for word in kw_lower.split():
                    if len(word) > 2 and word in search_text:
                        results[art["pmid"]] = results.get(art["pmid"], 0) + 0.5

        # Sort by score descending, then limit
        sorted_pmids = sorted(results.keys(), key=lambda p: results[p], reverse=True)
        return [art_index[pmid] for pmid in sorted_pmids[:max_results] if pmid in art_index]

    def search_pubmed(self, query: str, max_results: int = 10) -> list[dict]:
        """Mock PubMed search — returns keyword-matched demo articles. No network needed."""
        keywords = [w.strip() for w in query.replace(",", " ").split() if len(w.strip()) > 2]
        if not keywords:
            keywords = [query.strip()]
        articles = self._match_articles(keywords, max_results)
        # Generate source URLs
        for art in articles:
            if not art.get("source_url"):
                art["source_url"] = f"https://pubmed.ncbi.nlm.nih.gov/{art['pmid']}/" if art.get("pmid") else ""
        return articles
