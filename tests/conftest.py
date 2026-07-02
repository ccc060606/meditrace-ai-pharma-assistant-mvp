"""Pytest fixtures for pharma report assistant tests."""
import sys
import os
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db import Base, get_engine


@pytest.fixture(scope="function")
def test_db():
    """Create a test in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Import all models to ensure tables are created
    from src.models.daily_report import DailyReport
    from src.models.customer import Customer
    from src.models.literature import LiteratureArticle, MedicalQuestion
    from src.models.merge_log import MergeLog
    Base.metadata.create_all(bind=engine)

    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
