"""Tests for monthly report statistics accuracy."""
import pytest
import datetime
from src.services.monthly_service import MonthlyReportService
from src.repositories.daily_report_repo import DailyReportRepository
from src.models.daily_report import DailyReportCreate


class TestMonthlyStats:
    def test_compute_stats_empty_month(self, test_db):
        service = MonthlyReportService(test_db)
        stats = service.compute_stats(2026, 6)
        assert stats["total_visits"] == 0
        assert stats["unique_customers"] == 0
        assert stats["tasks_total"] == 0
        assert stats["completion_rate"] == 0.0

    def test_total_visits_count(self, test_db):
        repo = DailyReportRepository(test_db)
        for i in range(5):
            repo.create(DailyReportCreate(date="2026-05-01", customer_id="C001"))

        service = MonthlyReportService(test_db)
        stats = service.compute_stats(2026, 5)
        assert stats["total_visits"] == 5

    def test_unique_customers(self, test_db):
        repo = DailyReportRepository(test_db)
        for cid in ["C001", "C002", "C003", "C001"]:
            repo.create(DailyReportCreate(date="2026-05-01", customer_id=cid))

        service = MonthlyReportService(test_db)
        stats = service.compute_stats(2026, 5)
        assert stats["unique_customers"] == 3  # C001 appears twice

    def test_department_distribution(self, test_db):
        repo = DailyReportRepository(test_db)
        depts = ["心内科", "心内科", "肿瘤科", "内分泌科", "心内科"]
        for d in depts:
            repo.create(DailyReportCreate(date="2026-05-01", department=d))

        service = MonthlyReportService(test_db)
        stats = service.compute_stats(2026, 5)
        assert stats["department_distribution"]["心内科"] == 3
        assert stats["department_distribution"]["肿瘤科"] == 1
        assert stats["department_distribution"]["内分泌科"] == 1

    def test_task_completion_stats(self, test_db):
        repo = DailyReportRepository(test_db)
        repo.create(DailyReportCreate(
            date="2026-05-01", follow_up_task="T1", follow_up_status="completed",
        ))
        repo.create(DailyReportCreate(
            date="2026-05-02", follow_up_task="T2", follow_up_status="pending",
        ))
        repo.create(DailyReportCreate(
            date="2026-05-03", follow_up_task="T3", follow_up_status="completed",
        ))
        repo.create(DailyReportCreate(
            date="2026-05-04", follow_up_task="", follow_up_status="pending",
        ))

        service = MonthlyReportService(test_db)
        stats = service.compute_stats(2026, 5)
        assert stats["tasks_total"] == 3  # Only 3 have tasks
        assert stats["tasks_completed"] == 2
        assert stats["tasks_pending"] == 1
        assert stats["completion_rate"] == round(2 / 3 * 100, 1)

    def test_only_current_month_reports(self, test_db):
        repo = DailyReportRepository(test_db)
        repo.create(DailyReportCreate(date="2026-05-01", customer_id="C001"))
        repo.create(DailyReportCreate(date="2026-05-15", customer_id="C002"))
        repo.create(DailyReportCreate(date="2026-06-01", customer_id="C003"))

        service = MonthlyReportService(test_db)
        stats_may = service.compute_stats(2026, 5)
        stats_june = service.compute_stats(2026, 6)
        assert stats_may["total_visits"] == 2
        assert stats_june["total_visits"] == 1

    def test_activity_count(self, test_db):
        repo = DailyReportRepository(test_db)
        repo.create(DailyReportCreate(date="2026-05-01", activity_name="科室会"))
        repo.create(DailyReportCreate(date="2026-05-02", activity_name="科室会"))
        repo.create(DailyReportCreate(date="2026-05-03", activity_name=""))

        service = MonthlyReportService(test_db)
        stats = service.compute_stats(2026, 5)
        assert stats["activity_count"] == 2

    def test_medical_questions_collected(self, test_db):
        repo = DailyReportRepository(test_db)
        repo.create(DailyReportCreate(
            date="2026-05-01", medical_question="药物安全性？",
        ))
        repo.create(DailyReportCreate(
            date="2026-05-02", medical_question="疗效对比？",
        ))

        service = MonthlyReportService(test_db)
        stats = service.compute_stats(2026, 5)
        assert len(stats["medical_questions"]) >= 2

    def test_fallback_summary_works(self, test_db):
        repo = DailyReportRepository(test_db)
        repo.create(DailyReportCreate(
            date="2026-05-01", customer_id="C001", department="心内科",
            topic="产品介绍", follow_up_task="T1", follow_up_status="completed",
        ))

        service = MonthlyReportService(test_db)
        stats = service.compute_stats(2026, 5)
        summary = service._fallback_summary(stats)
        assert "progress_summary" in summary
        assert "2026-05" in summary["progress_summary"]
