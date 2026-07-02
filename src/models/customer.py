"""Customer SQLAlchemy model."""
import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship

from src.db import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(20), unique=True, nullable=False, index=True, comment="匿名客户编号 C001")
    department = Column(String(100), nullable=True, comment="科室")
    notes = Column(Text, nullable=True, comment="备注")
    is_active = Column(Integer, default=1, comment="1=active, 0=merged/deleted")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    reports = relationship("DailyReport", back_populates="customer", foreign_keys="DailyReport.customer_id")

    def __repr__(self):
        return f"<Customer {self.customer_id} dept={self.department}>"
