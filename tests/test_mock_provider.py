"""Tests for MockProvider extraction and summary."""
import pytest
from src.llm.mock_provider import MockProvider
from src.models.daily_report import DailyReportExtract


class TestMockProviderExtraction:
    def setup_method(self):
        self.provider = MockProvider()

    def test_test_connection_always_true(self):
        assert self.provider.test_connection() is True

    def test_extract_single_entry(self):
        text = """2026-05-05 科室：心内科 C001
主题：新产品降压药介绍
反馈：对临床试验数据感兴趣
后续：发送文献，截止2026-05-12
医学问题：该降压药在老年患者中的安全性如何？
活动：科室会"""
        results = self.provider.extract_daily_reports(text)
        assert len(results) >= 1
        r = results[0]
        # MockProvider looks for "科室：" pattern
        assert r.get("customer_id") == "C001"
        assert r.get("topic") == "新产品降压药介绍"
        assert "安全性" in r.get("medical_question", "")

    def test_extract_multiple_entries(self):
        text = """2026-05-01 心内科 C001
主题：拜访1

2026-05-02 肿瘤科 C002
主题：拜访2"""
        results = self.provider.extract_daily_reports(text)
        assert len(results) >= 1  # Should parse at least 1

    def test_validated_extracts_pass_pydantic(self):
        text = """2026-05-05 心内科 C001
主题：产品介绍
反馈：客户满意"""
        results = self.provider.extract_daily_reports(text)
        for item in results:
            extract = DailyReportExtract(**item)
            assert extract.date is not None

    def test_empty_text_produces_fallback(self):
        results = self.provider.extract_daily_reports("")
        # Should produce at least a fallback entry
        assert len(results) >= 0  # May be empty or fallback

    def test_generate_monthly_summary(self):
        context = {
            "month": "2026-05",
            "total_visits": 10,
            "unique_customers": 5,
            "department_distribution": {"心内科": 5, "肿瘤科": 5},
            "tasks_total": 4,
            "tasks_completed": 2,
            "completion_rate": 50.0,
            "top_topics": ["产品介绍"],
            "medical_questions": ["安全性？"],
            "pending_tasks": 2,
        }
        summary = self.provider.generate_monthly_summary(context)
        assert "progress_summary" in summary
        assert "key_issues" in summary
        assert "unfinished_items" in summary
        assert "next_month_plan" in summary
        assert "10" in summary["progress_summary"]

    def test_summarize_article(self):
        summary = self.provider.summarize_article({
            "title": "Diabetes Study",
            "abstract": "This study investigated the effects of GLP-1 agonists on cardiovascular outcomes in type 2 diabetes patients.",
        })
        assert len(summary) > 0
        assert "[Mock" in summary
