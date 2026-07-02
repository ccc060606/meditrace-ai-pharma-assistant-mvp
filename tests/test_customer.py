"""Tests for customer management."""
import pytest
from src.repositories.customer_repo import CustomerRepository
from src.repositories.daily_report_repo import DailyReportRepository
from src.services.customer_service import CustomerService
from src.models.daily_report import DailyReportCreate


class TestCustomerIdGeneration:
    def test_first_customer_gets_c001(self, test_db):
        repo = CustomerRepository(test_db)
        cid = repo.get_next_id()
        assert cid == "C001"

    def test_sequential_ids(self, test_db):
        repo = CustomerRepository(test_db)
        repo.create(department="心内科")
        repo.create(department="肿瘤科")
        assert repo.get_next_id() == "C003"

    def test_id_increments_after_create(self, test_db):
        repo = CustomerRepository(test_db)
        c1 = repo.create(department="心内科")
        c2 = repo.create(department="肿瘤科")
        assert c1.customer_id == "C001"
        assert c2.customer_id == "C002"


class TestCustomerMerge:
    def test_merge_transfers_reports(self, test_db):
        cust_repo = CustomerRepository(test_db)
        report_repo = DailyReportRepository(test_db)

        # Create two customers
        c1 = cust_repo.create(department="心内科")
        c2 = cust_repo.create(department="心内科")

        # Add reports to c1
        for i in range(3):
            report_repo.create(DailyReportCreate(
                date="2026-05-01",
                customer_id=c1.customer_id,
                topic=f"Topic {i}",
            ))

        # Merge c1 -> c2
        service = CustomerService(cust_repo, report_repo)
        count = service.merge_customers(c1.customer_id, c2.customer_id)
        assert count == 3

        # Verify reports moved
        c1_reports = report_repo.get_by_customer(c1.customer_id)
        c2_reports = report_repo.get_by_customer(c2.customer_id)
        assert len(c1_reports) == 0
        assert len(c2_reports) == 3

        # Verify c1 is inactive
        c1_check = cust_repo.get_by_customer_id(c1.customer_id)
        assert c1_check is None  # is_active=0 filtered out

    def test_cannot_merge_to_self(self, test_db):
        cust_repo = CustomerRepository(test_db)
        report_repo = DailyReportRepository(test_db)
        c1 = cust_repo.create(department="心内科")
        service = CustomerService(cust_repo, report_repo)
        with pytest.raises(ValueError, match="不能将客户合并到自身"):
            service.merge_customers(c1.customer_id, c1.customer_id)


class TestCompletionRate:
    def test_no_tasks_returns_zero(self, test_db):
        repo = CustomerRepository(test_db)
        repo.create(department="心内科")
        rate = repo.get_completion_rate("C001")
        assert rate == 0.0

    def test_all_completed_returns_100(self, test_db):
        cust_repo = CustomerRepository(test_db)
        report_repo = DailyReportRepository(test_db)
        cust_repo.create(department="心内科")

        for i in range(5):
            report_repo.create(DailyReportCreate(
                date="2026-05-01",
                customer_id="C001",
                follow_up_task=f"Task {i}",
                follow_up_status="completed",
            ))

        rate = cust_repo.get_completion_rate("C001")
        assert rate == 100.0

    def test_half_completed(self, test_db):
        cust_repo = CustomerRepository(test_db)
        report_repo = DailyReportRepository(test_db)
        cust_repo.create(department="心内科")

        report_repo.create(DailyReportCreate(
            date="2026-05-01", customer_id="C001",
            follow_up_task="Task 1", follow_up_status="completed",
        ))
        report_repo.create(DailyReportCreate(
            date="2026-05-02", customer_id="C001",
            follow_up_task="Task 2", follow_up_status="pending",
        ))

        rate = cust_repo.get_completion_rate("C001")
        assert rate == 50.0

    def test_cancelled_excluded_from_rate(self, test_db):
        cust_repo = CustomerRepository(test_db)
        report_repo = DailyReportRepository(test_db)
        cust_repo.create(department="心内科")

        report_repo.create(DailyReportCreate(
            date="2026-05-01", customer_id="C001",
            follow_up_task="Task 1", follow_up_status="completed",
        ))
        report_repo.create(DailyReportCreate(
            date="2026-05-02", customer_id="C001",
            follow_up_task="Task 2", follow_up_status="cancelled",
        ))

        rate = cust_repo.get_completion_rate("C001")
        # Only 1 active task (completed), no pending => 100%
        assert rate == 100.0
