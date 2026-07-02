"""Report service — orchestrate daily report parsing and persistence."""
import json
import logging

from src.models.daily_report import DailyReportExtract, DailyReportCreate
from src.repositories.daily_report_repo import DailyReportRepository
from src.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self, repo: DailyReportRepository, llm: LLMProvider = None):
        self.repo = repo
        self.llm = llm

    def parse_text(self, raw_text: str) -> list[dict]:
        """Use LLM to parse raw text into structured dicts."""
        if not self.llm:
            raise ValueError("No LLM provider configured")
        return self.llm.extract_daily_reports(raw_text)

    def validate_and_normalize(self, items: list[dict]) -> list[DailyReportExtract]:
        """Validate parsed items through Pydantic."""
        validated = []
        for item in items:
            try:
                extract = DailyReportExtract(**item)
                validated.append(extract)
            except Exception as e:
                logger.warning(f"Validation failed: {e}")
        return validated

    def save_reports(self, extracts: list[DailyReportExtract], raw_text: str = "",
                     ai_json: str = "") -> list:
        """Save validated extracts to database."""
        reports = []
        for ext in extracts:
            data = DailyReportCreate(
                date=ext.date,
                department=ext.department,
                customer_id=ext.customer_id,
                topic=ext.topic,
                feedback=ext.feedback,
                follow_up_task=ext.follow_up_task,
                task_deadline=ext.task_deadline,
                follow_up_status=ext.follow_up_status or "pending",
                medical_question=ext.medical_question,
                activity_name=ext.activity_name,
                raw_text=raw_text,
                ai_result_json=ai_json,
            )
            report = self.repo.create(data)
            reports.append(report)
        return reports

    def save_manual(self, data: dict) -> object:
        """Save a manually entered report."""
        create_data = DailyReportCreate(**data)
        return self.repo.create(create_data)

    def get_recent(self, limit: int = 20):
        return self.repo.get_recent(limit)

    def get_all(self):
        return self.repo.get_all()

    def update(self, report_id: int, **kwargs):
        return self.repo.update(report_id, **kwargs)

    def delete(self, report_id: int) -> bool:
        return self.repo.delete(report_id)

    def search(self, **kwargs):
        return self.repo.search(**kwargs)

    def get_pending_tasks(self):
        return self.repo.get_pending_tasks()

    def get_medical_questions(self):
        return self.repo.get_medical_questions()

    def get_monthly_reports(self, year: int, month: int):
        return self.repo.get_by_month(year, month)
