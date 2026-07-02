"""LiteratureArticle & MedicalQuestion SQLAlchemy models."""
import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.db import Base


class MedicalQuestion(Base):
    __tablename__ = "medical_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_text = Column(Text, nullable=False, comment="医学问题原文")
    report_id = Column(Integer, ForeignKey("daily_reports.id"), nullable=True)
    search_terms_zh = Column(Text, nullable=True, comment="中文检索词 JSON list")
    search_terms_en = Column(Text, nullable=True, comment="英文检索词 JSON list")
    last_searched_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class LiteratureArticle(Base):
    __tablename__ = "literature_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pmid = Column(String(20), unique=True, nullable=True, comment="PubMed ID")
    doi = Column(String(200), nullable=True, comment="DOI")
    title = Column(Text, nullable=True)
    authors = Column(Text, nullable=True)
    journal = Column(String(500), nullable=True)
    year = Column(Integer, nullable=True)
    study_type = Column(String(200), nullable=True, comment="研究类型")
    abstract = Column(Text, nullable=True, comment="原始摘要")
    ai_summary = Column(Text, nullable=True, comment="AI 总结")
    source_url = Column(Text, nullable=True, comment="来源链接")
    medical_question_id = Column(Integer, ForeignKey("medical_questions.id"), nullable=True)
    retrieved_at = Column(DateTime, default=datetime.datetime.utcnow)

    medical_question = relationship("MedicalQuestion", backref="articles")
