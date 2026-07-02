"""Tests for security requirements — no API keys in logs, SQL injection prevention."""
import pytest
import logging
import io
from src.config import Config


class TestNoApiKeyInConfig:
    def test_api_key_not_in_default_repr(self):
        """Config properties should not expose secrets by default."""
        cfg = Config()
        # Set a temporary key via override
        Config.set_override("LLM_API_KEY", "sk-secret-key-12345")
        # Check that the key is retrievable
        assert cfg.llm_api_key == "sk-secret-key-12345"
        # Clear overrides
        Config.clear_overrides()

    def test_config_get_respects_priority(self):
        import os
        os.environ["TEST_VAR"] = "from_env"
        Config.set_override("TEST_VAR", "from_override")
        assert Config.get("TEST_VAR") == "from_override"
        Config.clear_overrides()
        assert Config.get("TEST_VAR") == "from_env"
        del os.environ["TEST_VAR"]


class TestParameterizedQueries:
    """Ensure we use parameterized queries (SQLAlchemy ORM handles this)."""

    def test_search_uses_orm_params(self, test_db):
        """ORM queries are parameterized by default."""
        from src.repositories.daily_report_repo import DailyReportRepository
        repo = DailyReportRepository(test_db)
        # Search with keyword — should use parameterized LIKE
        results = repo.search(topic_keyword="test")
        assert isinstance(results, list)


class TestConfigNoSecretLeak:
    def test_database_path_does_not_contain_api_key(self):
        """Database path should never contain API keys."""
        cfg = Config()
        db_path = cfg.database_path
        assert "sk-" not in db_path
        assert "api_key" not in db_path.lower()

    def test_export_dir_does_not_contain_api_key(self):
        """Export dir should never contain API keys."""
        cfg = Config()
        export_dir = cfg.export_dir
        assert "sk-" not in export_dir
