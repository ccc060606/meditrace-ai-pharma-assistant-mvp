"""DailyReport SQLAlchemy and Pydantic models."""
import datetime
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, field_validator

from src.db import Base


# ── SQLAlchemy ORM ──────────────────────────────────────────────

class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=True, comment="沟通日期 YYYY-MM-DD")
    department = Column(String(100), nullable=True, comment="科室")
    customer_id = Column(String(20), ForeignKey("customers.customer_id"), nullable=True, comment="客户编号")
    topic = Column(String(500), nullable=True, comment="沟通主题")
    feedback = Column(Text, nullable=True, comment="客户反馈")
    follow_up_task = Column(Text, nullable=True, comment="后续任务")
    task_deadline = Column(Date, nullable=True, comment="任务截止日期")
    follow_up_status = Column(String(50), nullable=True, comment="跟进状态: pending/completed/cancelled")
    medical_question = Column(Text, nullable=True, comment="医学问题")
    activity_name = Column(String(300), nullable=True, comment="活动名称")
    raw_text = Column(Text, nullable=True, comment="原始日报文本")
    ai_result_json = Column(Text, nullable=True, comment="AI 解析原始结果 JSON")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="reports", foreign_keys=[customer_id])

    def __repr__(self):
        return f"<DailyReport id={self.id} date={self.date} customer={self.customer_id}>"


# ── Pydantic Schemas ────────────────────────────────────────────

class DailyReportExtract(BaseModel):
    """AI extraction result for a single daily report entry."""
    date: str | None = Field(default=None, description="沟通日期 YYYY-MM-DD")
    department: str | None = Field(default=None, description="科室")
    customer_id: str | None = Field(default=None, description="客户编号")
    topic: str | None = Field(default=None, description="沟通主题")
    feedback: str | None = Field(default=None, description="客户反馈")
    follow_up_task: str | None = Field(default=None, description="后续任务")
    task_deadline: str | None = Field(default=None, description="任务截止日期")
    follow_up_status: str | None = Field(default="pending", description="跟进状态")
    medical_question: str | None = Field(default=None, description="医学问题")
    activity_name: str | None = Field(default=None, description="活动名称")

    @field_validator("date", "task_deadline")
    @classmethod
    def validate_date_format(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        v = v.strip()
        try:
            parsed = datetime.datetime.strptime(v, "%Y-%m-%d")
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            # Try other common formats
            for fmt in ("%Y/%m/%d", "%Y.%m.%d", "%m-%d", "%m/%d"):
                try:
                    parsed = datetime.datetime.strptime(v, fmt)
                    return parsed.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            return None

    @field_validator("follow_up_status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return "pending"
        v = v.strip()
        allowed = {"pending", "completed", "cancelled", "待处理", "已完成", "已取消"}
        mapping = {"待处理": "pending", "已完成": "completed", "已取消": "cancelled"}
        if v in mapping:
            return mapping[v]
        if v not in allowed:
            return "pending"
        return v


class DailyReportCreate(BaseModel):
    """Manual entry / confirmed entry for saving."""
    date: str | None = None
    department: str | None = None
    customer_id: str | None = None
    topic: str | None = None
    feedback: str | None = None
    follow_up_task: str | None = None
    task_deadline: str | None = None
    follow_up_status: str = "pending"
    medical_question: str | None = None
    activity_name: str | None = None
    raw_text: str | None = None
    ai_result_json: str | None = None
