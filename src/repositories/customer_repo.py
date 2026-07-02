"""Customer repository — CRUD and queries."""
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.customer import Customer
from src.models.daily_report import DailyReport
from src.models.merge_log import MergeLog


class CustomerRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_next_id(self) -> str:
        """Generate next customer ID C001, C002, ..."""
        last = self.session.query(Customer).order_by(Customer.id.desc()).first()
        if last and last.customer_id:
            try:
                num = int(last.customer_id[1:]) + 1
                return f"C{num:03d}"
            except (ValueError, IndexError):
                pass
        return "C001"

    def create(self, department: str = None, notes: str = None) -> Customer:
        c = Customer(
            customer_id=self.get_next_id(),
            department=department,
            notes=notes,
        )
        self.session.add(c)
        self.session.commit()
        self.session.refresh(c)
        return c

    def get_by_customer_id(self, customer_id: str) -> Customer | None:
        return self.session.query(Customer).filter(
            Customer.customer_id == customer_id, Customer.is_active == 1
        ).first()

    def get_all_active(self) -> list[Customer]:
        return self.session.query(Customer).filter(Customer.is_active == 1).order_by(Customer.customer_id).all()

    def get_all(self) -> list[Customer]:
        return self.session.query(Customer).order_by(Customer.customer_id).all()

    def get_by_department(self, department: str) -> list[Customer]:
        return self.session.query(Customer).filter(
            Customer.department == department, Customer.is_active == 1
        ).all()

    def get_visit_count(self, customer_id: str) -> int:
        return self.session.query(func.count(DailyReport.id)).filter(
            DailyReport.customer_id == customer_id
        ).scalar() or 0

    def get_pending_count(self, customer_id: str) -> int:
        return self.session.query(func.count(DailyReport.id)).filter(
            DailyReport.customer_id == customer_id,
            DailyReport.follow_up_status == "pending",
            DailyReport.follow_up_task.isnot(None),
            DailyReport.follow_up_task != "",
        ).scalar() or 0

    def get_completed_count(self, customer_id: str) -> int:
        return self.session.query(func.count(DailyReport.id)).filter(
            DailyReport.customer_id == customer_id,
            DailyReport.follow_up_status == "completed",
        ).scalar() or 0

    def get_completion_rate(self, customer_id: str) -> float:
        total = self.session.query(func.count(DailyReport.id)).filter(
            DailyReport.customer_id == customer_id,
            DailyReport.follow_up_task.isnot(None),
            DailyReport.follow_up_task != "",
        ).scalar() or 0
        if total == 0:
            return 0.0
        completed = self.get_completed_count(customer_id)
        pending = self.session.query(func.count(DailyReport.id)).filter(
            DailyReport.customer_id == customer_id,
            DailyReport.follow_up_status == "pending",
            DailyReport.follow_up_task.isnot(None),
            DailyReport.follow_up_task != "",
        ).scalar() or 0
        # completion rate = completed / (completed + pending), excluding cancelled
        total_active = completed + pending
        if total_active == 0:
            return 0.0
        return round(completed / total_active * 100, 1)

    def get_top_topics(self, customer_id: str, limit: int = 5) -> list[tuple[str, int]]:
        rows = self.session.query(DailyReport.topic, func.count(DailyReport.id)).filter(
            DailyReport.customer_id == customer_id,
            DailyReport.topic.isnot(None),
            DailyReport.topic != "",
        ).group_by(DailyReport.topic).order_by(func.count(DailyReport.id).desc()).limit(limit).all()
        return [(r[0], r[1]) for r in rows if r[0]]

    def find_duplicates(self) -> list[tuple[Customer, Customer, float]]:
        """Find potential duplicate customers by department + topic overlap.
        Returns list of (cust_a, cust_b, similarity_score)."""
        active = self.get_all_active()
        if len(active) < 2:
            return []
        suspects = []
        for i in range(len(active)):
            for j in range(i + 1, len(active)):
                a, b = active[i], active[j]
                score = 0.0
                # Same department is a strong signal
                if a.department and b.department and a.department == b.department:
                    score += 0.4
                # Topic overlap
                a_topics = set(t[0] for t in self.get_top_topics(a.customer_id, 10))
                b_topics = set(t[0] for t in self.get_top_topics(b.customer_id, 10))
                if a_topics and b_topics:
                    overlap = len(a_topics & b_topics) / max(len(a_topics | b_topics), 1)
                    score += overlap * 0.6
                if score > 0.3:
                    suspects.append((a, b, round(score, 2)))
        suspects.sort(key=lambda x: x[2], reverse=True)
        return suspects

    def merge(self, from_id: str, to_id: str) -> int:
        """Merge from_customer into to_customer. Deactivate source."""
        from_cust = self.get_by_customer_id(from_id)
        to_cust = self.get_by_customer_id(to_id)
        if not from_cust or not to_cust:
            raise ValueError("Customer not found")

        # Count reports being moved
        count = self.session.query(func.count(DailyReport.id)).filter(
            DailyReport.customer_id == from_id
        ).scalar() or 0

        # Move reports
        self.session.query(DailyReport).filter(
            DailyReport.customer_id == from_id
        ).update({DailyReport.customer_id: to_id}, synchronize_session="fetch")

        # Deactivate source customer
        from_cust.is_active = 0

        # Log the merge
        log = MergeLog(
            from_customer_id=from_id,
            to_customer_id=to_id,
            report_count=count,
        )
        self.session.add(log)
        self.session.commit()
        return count

    def update(self, customer_id: str, **kwargs) -> Customer | None:
        c = self.get_by_customer_id(customer_id)
        if not c:
            return None
        for key, value in kwargs.items():
            if hasattr(c, key) and key != "customer_id":
                setattr(c, key, value)
        self.session.commit()
        self.session.refresh(c)
        return c

    def search(self, keyword: str = None, department: str = None) -> list[Customer]:
        q = self.session.query(Customer).filter(Customer.is_active == 1)
        if keyword:
            q = q.filter(Customer.customer_id.contains(keyword))
        if department:
            q = q.filter(Customer.department == department)
        return q.order_by(Customer.customer_id).all()

    def get_departments(self) -> list[str]:
        rows = self.session.query(Customer.department).filter(
            Customer.department.isnot(None),
            Customer.department != "",
            Customer.is_active == 1,
        ).distinct().all()
        return sorted([r[0] for r in rows if r[0]])
