"""Literature repository — articles and medical questions."""
import json
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.literature import LiteratureArticle, MedicalQuestion


class LiteratureRepository:
    def __init__(self, session: Session):
        self.session = session

    # ── Medical Questions ───────────────────────────────────────

    def save_question(self, question_text: str, report_id: int = None,
                      search_terms_zh: list[str] = None, search_terms_en: list[str] = None) -> MedicalQuestion:
        q = MedicalQuestion(
            question_text=question_text,
            report_id=report_id,
            search_terms_zh=json.dumps(search_terms_zh, ensure_ascii=False) if search_terms_zh else None,
            search_terms_en=json.dumps(search_terms_en, ensure_ascii=False) if search_terms_en else None,
        )
        self.session.add(q)
        self.session.commit()
        self.session.refresh(q)
        return q

    def get_all_questions(self) -> list[MedicalQuestion]:
        return self.session.query(MedicalQuestion).order_by(MedicalQuestion.created_at.desc()).all()

    def get_question_by_id(self, qid: int) -> MedicalQuestion | None:
        return self.session.query(MedicalQuestion).filter(MedicalQuestion.id == qid).first()

    def update_search_terms(self, qid: int, terms_zh: list[str], terms_en: list[str]):
        q = self.get_question_by_id(qid)
        if q:
            q.search_terms_zh = json.dumps(terms_zh, ensure_ascii=False)
            q.search_terms_en = json.dumps(terms_en, ensure_ascii=False)
            self.session.commit()

    # ── Articles ────────────────────────────────────────────────

    def upsert_article(self, article_data: dict) -> LiteratureArticle:
        """Insert or update article. Dedup priority: PMID > DOI > title."""
        existing = None
        if article_data.get("pmid"):
            existing = self.session.query(LiteratureArticle).filter(
                LiteratureArticle.pmid == article_data["pmid"]
            ).first()
        if not existing and article_data.get("doi"):
            existing = self.session.query(LiteratureArticle).filter(
                LiteratureArticle.doi == article_data["doi"]
            ).first()
        if not existing and article_data.get("title"):
            normalized = _normalize_title(article_data["title"])
            existing = self.session.query(LiteratureArticle).filter(
                LiteratureArticle.title == normalized
            ).first()

        if existing:
            for key, value in article_data.items():
                if value is not None and hasattr(existing, key):
                    setattr(existing, key, value)
            self.session.commit()
            self.session.refresh(existing)
            return existing

        # Normalize title before saving
        if article_data.get("title"):
            article_data["title"] = _normalize_title(article_data["title"])

        a = LiteratureArticle(**article_data)
        self.session.add(a)
        self.session.commit()
        self.session.refresh(a)
        return a

    def get_articles_for_question(self, question_id: int) -> list[LiteratureArticle]:
        return self.session.query(LiteratureArticle).filter(
            LiteratureArticle.medical_question_id == question_id
        ).order_by(LiteratureArticle.year.desc().nullslast()).all()

    def get_all_articles(self) -> list[LiteratureArticle]:
        return self.session.query(LiteratureArticle).order_by(LiteratureArticle.retrieved_at.desc()).all()

    def article_exists(self, pmid: str = None, doi: str = None, title: str = None) -> bool:
        if pmid:
            return self.session.query(LiteratureArticle).filter(LiteratureArticle.pmid == pmid).count() > 0
        if doi:
            return self.session.query(LiteratureArticle).filter(LiteratureArticle.doi == doi).count() > 0
        if title:
            n = _normalize_title(title)
            return self.session.query(LiteratureArticle).filter(LiteratureArticle.title == n).count() > 0
        return False

    def count(self) -> int:
        return self.session.query(func.count(LiteratureArticle.id)).scalar() or 0


def _normalize_title(title: str) -> str:
    """Normalize title for dedup matching: lowercase, strip punctuation."""
    import re
    t = title.lower().strip()
    t = re.sub(r'[^\w\s]', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t
