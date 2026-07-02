"""Database engine, session, and auto-init."""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path

from src.config import Config

Base = declarative_base()

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        db_path = Config().database_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )

        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return _engine


def get_session():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    return _SessionLocal()


def init_db():
    """Create all tables if they don't exist."""
    from src.models.daily_report import DailyReport  # noqa: F401
    from src.models.customer import Customer  # noqa: F401
    from src.models.literature import LiteratureArticle, MedicalQuestion  # noqa: F401
    from src.models.merge_log import MergeLog  # noqa: F401
    Base.metadata.create_all(bind=get_engine())
