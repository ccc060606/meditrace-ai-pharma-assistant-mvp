"""DailyReport repository — all DB access for daily reports."""
import datetime
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from src.models.daily_report import DailyReport, DailyReportCreate


class DailyReportRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, data: DailyReportCreate) -> DailyReport:
        report = DailyReport(
            date=_parse_date(data.date),
            department=data.department,
            customer_id=data.customer_id,
            topic=data.topic,
            feedback=data.feedback,
            follow_up_task=data.follow_up_task,
            task_deadline=_parse_date(data.task_deadline),
            follow_up_status=data.follow_up_status or "pending",
            medical_question=data.medical_question,
            activity_name=data.activity_name,
            raw_text=data.raw_text,
            ai_result_json=data.ai_result_json,
        )
        self.session.add(report)
        self.session.commit()
        self.session.refresh(report)
        return report

    def create_batch(self, items: list[DailyReportCreate]) -> list[DailyReport]:
        reports = []
        for data in items:
            r = DailyReport(
                date=_parse_date(data.date),
                department=data.department,
                customer_id=data.customer_id,
                topic=data.topic,
                feedback=data.feedback,
                follow_up_task=data.follow_up_task,
                task_deadline=_parse_date(data.task_deadline),
                follow_up_status=data.follow_up_status or "pending",
                medical_question=data.medical_question,
                activity_name=data.activity_name,
                raw_text=data.raw_text,
                ai_result_json=data.ai_result_json,
            )
            self.session.add(r)
            reports.append(r)
        self.session.commit()
        for r in reports:
            self.session.refresh(r)
        return reports

    def get_all(self) -> list[DailyReport]:
        return self.session.query(DailyReport).order_by(DailyReport.date.desc().nullslast()).all()

    def get_by_id(self, report_id: int) -> DailyReport | None:
        return self.session.query(DailyReport).filter(DailyReport.id == report_id).first()

    def get_recent(self, limit: int = 20) -> list[DailyReport]:
        return self.session.query(DailyReport).order_by(DailyReport.created_at.desc()).limit(limit).all()

    def get_by_month(self, year: int, month: int) -> list[DailyReport]:
        return self.session.query(DailyReport).filter(
            and_(
                func.strftime("%Y", DailyReport.date) == str(year),
                func.strftime("%m", DailyReport.date) == f"{month:02d}",
            )
        ).all()

    def get_by_customer(self, customer_id: str) -> list[DailyReport]:
        return self.session.query(DailyReport).filter(
            DailyReport.customer_id == customer_id
        ).order_by(DailyReport.date.desc()).all()

    def get_by_status(self, status: str) -> list[DailyReport]:
        return self.session.query(DailyReport).filter(
            DailyReport.follow_up_status == status
        ).all()

    def get_pending_tasks(self) -> list[DailyReport]:
        return self.session.query(DailyReport).filter(
            DailyReport.follow_up_status == "pending",
            DailyReport.follow_up_task.isnot(None),
            DailyReport.follow_up_task != "",
        ).all()

    def get_medical_questions(self) -> list[DailyReport]:
        return self.session.query(DailyReport).filter(
            DailyReport.medical_question.isnot(None),
            DailyReport.medical_question != "",
        ).order_by(DailyReport.date.desc()).all()

    def transfer_to_customer(self, from_customer_id: str, to_customer_id: str) -> int:
        """Transfer all reports from one customer to another. Returns count."""
        count = self.session.query(DailyReport).filter(
            DailyReport.customer_id == from_customer_id
        ).update({DailyReport.customer_id: to_customer_id}, synchronize_session="fetch")
        self.session.commit()
        return count

    def update(self, report_id: int, **kwargs) -> DailyReport | None:
        report = self.get_by_id(report_id)
        if not report:
            return None
        for key, value in kwargs.items():
            if hasattr(report, key):
                if key in ("date", "task_deadline") and value is not None:
                    value = _parse_date(value)
                setattr(report, key, value)
        report.updated_at = datetime.datetime.utcnow()
        self.session.commit()
        self.session.refresh(report)
        return report

    def delete(self, report_id: int) -> bool:
        report = self.get_by_id(report_id)
        if not report:
            return False
        self.session.delete(report)
        self.session.commit()
        return True

    def count(self) -> int:
        return self.session.query(func.count(DailyReport.id)).scalar() or 0

    def get_months_with_data(self) -> list[str]:
        """Return distinct YYYY-MM strings that have reports."""
        rows = self.session.query(DailyReport.date).filter(DailyReport.date.isnot(None)).distinct().all()
        months = set()
        for (d,) in rows:
            if d:
                months.add(d.strftime("%Y-%m"))
        return sorted(months, reverse=True)

    def search(self, customer_id: str = None, department: str = None,
               date_from: str = None, date_to: str = None,
               topic_keyword: str = None, status: str = None) -> list[DailyReport]:
        q = self.session.query(DailyReport)
        if customer_id:
            q = q.filter(DailyReport.customer_id == customer_id)
        if department:
            q = q.filter(DailyReport.department == department)
        if date_from:
            q = q.filter(DailyReport.date >= _parse_date(date_from))
        if date_to:
            q = q.filter(DailyReport.date <= _parse_date(date_to))
        if topic_keyword:
            q = q.filter(DailyReport.topic.contains(topic_keyword))
        if status:
            q = q.filter(DailyReport.follow_up_status == status)
        return q.order_by(DailyReport.date.desc()).all()


def _parse_date(value):
    """Parse date string to date object, return None on failure."""
    if value is None:
        return None
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
            try:
                return datetime.datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None
