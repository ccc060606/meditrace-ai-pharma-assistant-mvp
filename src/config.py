"""Application configuration with priority: Streamlit session > env vars > .env"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _get_env(key: str, default: str = "") -> str:
    """Read from os.environ (which .env populates)."""
    return os.environ.get(key, default)


class Config:
    """Singleton config that can be overridden by Streamlit session state."""

    _instance = None
    _overrides: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def set_override(key: str, value: str) -> None:
        Config._overrides[key] = value

    @staticmethod
    def clear_overrides() -> None:
        Config._overrides.clear()

    @staticmethod
    def get(key: str, default: str = "") -> str:
        """Priority: overrides > environment > .env"""
        if key in Config._overrides:
            return Config._overrides[key]
        return _get_env(key, default)

    # --- LLM ---
    @property
    def llm_provider(self) -> str:
        return self.get("LLM_PROVIDER", "mock")

    @property
    def llm_base_url(self) -> str:
        return self.get("LLM_BASE_URL", "http://localhost:11434/v1")

    @property
    def llm_api_key(self) -> str:
        return self.get("LLM_API_KEY", "")

    @property
    def llm_model(self) -> str:
        return self.get("LLM_MODEL", "gpt-4o-mini")

    @property
    def public_demo(self) -> bool:
        return self.get("PUBLIC_DEMO", "false").lower() in {"1", "true", "yes", "on"}

    # --- PubMed ---
    @property
    def pubmed_email(self) -> str:
        return self.get("PUBMED_EMAIL", "")

    @property
    def pubmed_api_key(self) -> str:
        return self.get("PUBMED_API_KEY", "")

    # --- Paths ---
    @property
    def database_path(self) -> str:
        return self.get("DATABASE_PATH", str(BASE_DIR / "data" / "pharma.db"))

    @property
    def export_dir(self) -> str:
        return self.get("EXPORT_DIR", str(BASE_DIR / "exports"))

    @property
    def base_dir(self) -> Path:
        return BASE_DIR
