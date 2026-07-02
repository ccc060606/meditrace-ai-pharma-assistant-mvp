"""MergeLog model for tracking customer merges."""
import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime

from src.db import Base


class MergeLog(Base):
    __tablename__ = "merge_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_customer_id = Column(String(20), nullable=False, comment="被合并的客户编号 (source)")
    to_customer_id = Column(String(20), nullable=False, comment="合并目标客户编号 (target)")
    report_count = Column(Integer, default=0, comment="迁移的日报数量")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
