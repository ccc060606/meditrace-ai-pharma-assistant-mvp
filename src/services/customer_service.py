"""Customer service — customer CRUD, merge, duplicate detection."""
import logging

from src.repositories.customer_repo import CustomerRepository
from src.repositories.daily_report_repo import DailyReportRepository

logger = logging.getLogger(__name__)


class CustomerService:
    def __init__(self, customer_repo: CustomerRepository, report_repo: DailyReportRepository):
        self.customer_repo = customer_repo
        self.report_repo = report_repo

    def create(self, department: str = None, notes: str = None):
        return self.customer_repo.create(department, notes)

    def get_all_active(self):
        return self.customer_repo.get_all_active()

    def get_by_id(self, customer_id: str):
        return self.customer_repo.get_by_customer_id(customer_id)

    def get_customer_detail(self, customer_id: str) -> dict:
        """Get full customer detail with stats."""
        cust = self.customer_repo.get_by_customer_id(customer_id)
        if not cust:
            return {}
        reports = self.report_repo.get_by_customer(customer_id)
        visits = len(reports)
        topics = self.customer_repo.get_top_topics(customer_id)
        pending = self.customer_repo.get_pending_count(customer_id)
        completion = self.customer_repo.get_completion_rate(customer_id)
        return {
            "customer": cust,
            "visit_count": visits,
            "top_topics": topics,
            "pending_tasks": pending,
            "completion_rate": completion,
            "reports": reports,
        }

    def find_duplicates(self):
        return self.customer_repo.find_duplicates()

    def merge_customers(self, from_id: str, to_id: str) -> int:
        """Merge from_id into to_id. Returns number of reports moved."""
        if from_id == to_id:
            raise ValueError("不能将客户合并到自身")
        count = self.customer_repo.merge(from_id, to_id)
        logger.info(f"Merged {from_id} -> {to_id}, moved {count} reports")
        return count

    def update(self, customer_id: str, **kwargs):
        return self.customer_repo.update(customer_id, **kwargs)

    def search(self, **kwargs):
        return self.customer_repo.search(**kwargs)

    def get_departments(self) -> list[str]:
        return self.customer_repo.get_departments()

    def get_merge_logs(self):
        """Get recent merge logs."""
        from src.db import get_session
        from src.models.merge_log import MergeLog
        session = get_session()
        try:
            return session.query(MergeLog).order_by(MergeLog.created_at.desc()).limit(50).all()
        finally:
            session.close()
