"""Monthly report service — deterministic stats + AI narrative."""
import logging
from collections import Counter
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.daily_report import DailyReport
from src.models.literature import MedicalQuestion
from src.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class MonthlyReportService:
    def __init__(self, session: Session, llm: LLMProvider = None):
        self.session = session
        self.llm = llm

    def compute_stats(self, year: int, month: int) -> dict:
        """Compute all monthly statistics deterministically from DB."""
        reports = self.session.query(DailyReport).filter(
            func.strftime("%Y", DailyReport.date) == str(year),
            func.strftime("%m", DailyReport.date) == f"{month:02d}",
        ).all()

        total_visits = len(reports)
        unique_customers = len(set(r.customer_id for r in reports if r.customer_id))
        departments = Counter(r.department for r in reports if r.department)

        # Activities
        activities = [r.activity_name for r in reports if r.activity_name]
        activity_count = len(activities)

        # Tasks
        tasks_total = 0
        tasks_completed = 0
        tasks_pending = 0
        for r in reports:
            if r.follow_up_task:
                tasks_total += 1
                if r.follow_up_status == "completed":
                    tasks_completed += 1
                elif r.follow_up_status == "pending":
                    tasks_pending += 1

        completion_rate = round(tasks_completed / tasks_total * 100, 1) if tasks_total > 0 else 0.0

        # Topics
        topics = Counter(r.topic for r in reports if r.topic)
        top_topics = [t[0] for t in topics.most_common(10)]

        # Medical questions
        med_questions = [r.medical_question for r in reports if r.medical_question]
        # Also check MedicalQuestion table for questions from this month
        med_rows = self.session.query(MedicalQuestion).filter(
            func.strftime("%Y-%m", MedicalQuestion.created_at) == f"{year}-{month:02d}"
        ).all()
        for mq in med_rows:
            if mq.question_text not in med_questions:
                med_questions.append(mq.question_text)

        # Pending items detail
        pending_items = [
            {"id": r.id, "task": r.follow_up_task, "customer": r.customer_id,
             "deadline": str(r.task_deadline) if r.task_deadline else None}
            for r in reports
            if r.follow_up_status == "pending" and r.follow_up_task
        ]

        return {
            "month": f"{year}-{month:02d}",
            "total_visits": total_visits,
            "unique_customers": unique_customers,
            "department_distribution": dict(departments.most_common()),
            "activity_count": activity_count,
            "activities": activities,
            "tasks_total": tasks_total,
            "tasks_completed": tasks_completed,
            "tasks_pending": tasks_pending,
            "completion_rate": completion_rate,
            "top_topics": top_topics,
            "medical_questions": med_questions,
            "pending_items": pending_items,
            "reports": reports,
        }

    def generate_ai_summary(self, stats: dict) -> dict:
        """Generate AI narrative summary. Falls back gracefully."""
        if not self.llm:
            return self._fallback_summary(stats)

        context = {
            "month": stats["month"],
            "total_visits": stats["total_visits"],
            "unique_customers": stats["unique_customers"],
            "department_distribution": stats["department_distribution"],
            "activity_count": stats["activity_count"],
            "tasks_total": stats["tasks_total"],
            "tasks_completed": stats["tasks_completed"],
            "completion_rate": stats["completion_rate"],
            "top_topics": stats["top_topics"],
            "medical_questions": stats["medical_questions"],
            "pending_tasks": stats["tasks_pending"],
        }
        try:
            return self.llm.generate_monthly_summary(context)
        except Exception as e:
            logger.warning(f"AI summary failed, using fallback: {e}")
            return self._fallback_summary(stats)

    def _fallback_summary(self, stats: dict) -> dict:
        month = stats["month"]
        depts = stats["department_distribution"]
        dept_str = "、".join(f"{k}({v}次)" for k, v in list(depts.items())[:5])
        return {
            "progress_summary": f"{month}共完成{stats['total_visits']}次拜访，覆盖{stats['unique_customers']}位客户。"
                               f"科室分布：{dept_str}。",
            "key_issues": "本月医学问题：" + ("；".join(stats['medical_questions'][:5]) if stats['medical_questions'] else "无"),
            "unfinished_items": f"跟进任务{stats['tasks_total']}项，完成{stats['tasks_completed']}项，"
                               f"完成率{stats['completion_rate']}%。",
            "next_month_plan": "继续跟进未完成任务，加强重点科室拜访。",
        }

    def get_available_months(self) -> list[str]:
        """List months that have report data."""
        rows = self.session.query(DailyReport.date).filter(
            DailyReport.date.isnot(None)
        ).distinct().all()
        months = sorted(set(d.strftime("%Y-%m") for (d,) in rows if d), reverse=True)
        return months

    def get_all_reports_for_month(self, year: int, month: int) -> list:
        return self.session.query(DailyReport).filter(
            func.strftime("%Y", DailyReport.date) == str(year),
            func.strftime("%m", DailyReport.date) == f"{month:02d}",
        ).order_by(DailyReport.date).all()
