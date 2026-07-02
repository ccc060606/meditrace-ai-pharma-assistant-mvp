"""Tests for data models and validation."""
import pytest
import datetime
from src.models.daily_report import DailyReportExtract, DailyReportCreate


class TestDailyReportExtract:
    """Test Pydantic validation for AI extraction results."""

    def test_valid_extract(self):
        ext = DailyReportExtract(
            date="2026-05-05",
            department="心内科",
            customer_id="C001",
            topic="产品介绍",
            feedback="客户满意",
            follow_up_task="发送资料",
            task_deadline="2026-05-12",
            follow_up_status="pending",
            medical_question="药物安全性？",
            activity_name="科室会",
        )
        assert ext.date == "2026-05-05"
        assert ext.department == "心内科"
        assert ext.follow_up_status == "pending"

    def test_empty_fields_default_to_none(self):
        ext = DailyReportExtract()
        assert ext.date is None
        assert ext.department is None
        assert ext.customer_id is None
        assert ext.follow_up_status == "pending"  # default

    def test_date_normalization(self):
        ext = DailyReportExtract(date="2026/05/05")
        assert ext.date == "2026-05-05"

        ext2 = DailyReportExtract(date="2026.05.05")
        assert ext2.date == "2026-05-05"

    def test_invalid_date_returns_none(self):
        ext = DailyReportExtract(date="not-a-date")
        assert ext.date is None

    def test_empty_string_date_returns_none(self):
        ext = DailyReportExtract(date="")
        assert ext.date is None

    def test_chinese_status_mapping(self):
        ext = DailyReportExtract(follow_up_status="待处理")
        assert ext.follow_up_status == "pending"

        ext2 = DailyReportExtract(follow_up_status="已完成")
        assert ext2.follow_up_status == "completed"

        ext3 = DailyReportExtract(follow_up_status="已取消")
        assert ext3.follow_up_status == "cancelled"

    def test_unknown_status_defaults_to_pending(self):
        ext = DailyReportExtract(follow_up_status="unknown")
        assert ext.follow_up_status == "pending"


class TestDailyReportCreate:
    def test_create_with_minimal_fields(self):
        data = DailyReportCreate(
            department="心内科",
            topic="拜访",
        )
        assert data.department == "心内科"
        assert data.follow_up_status == "pending"

    def test_create_with_all_fields(self):
        data = DailyReportCreate(
            date="2026-05-01",
            department="肿瘤科",
            customer_id="C002",
            topic="新药介绍",
            feedback="积极反馈",
            follow_up_task="跟进",
            task_deadline="2026-05-15",
            follow_up_status="pending",
            medical_question="疗效如何？",
            activity_name="科室会",
            raw_text="原始文本",
            ai_result_json='{"key": "value"}',
        )
        assert data.customer_id == "C002"
