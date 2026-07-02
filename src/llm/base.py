"""LLM Provider abstract base and factory."""
from typing import Protocol, runtime_checkable
import json
import logging

from src.models.daily_report import DailyReportExtract

logger = logging.getLogger(__name__)


@runtime_checkable
class LLMProvider(Protocol):
    """Unified LLM provider interface."""

    provider_name: str

    def test_connection(self) -> bool:
        """Test if the provider is reachable."""
        ...

    def extract_daily_reports(self, text: str) -> list[dict]:
        """Parse raw text into structured daily report dicts.
        Returns list of dicts matching DailyReportExtract fields."""
        ...

    def generate_monthly_summary(self, context: dict) -> dict:
        """Generate monthly report narrative from statistics context.
        Returns dict with keys: progress_summary, key_issues, unfinished_items, next_month_plan"""
        ...

    def generate_literature_queries(self, medical_question: str) -> dict:
        """Generate Chinese and English search queries for a medical question.
        Returns dict with keys: zh_terms (list[str]), en_terms (list[str])"""
        ...

    def summarize_article(self, article: dict) -> str:
        """Summarize a literature article abstract.
        article is dict with: title, authors, journal, year, abstract.
        Returns summary string."""
        ...


def _validate_extract(items: list[dict]) -> list[DailyReportExtract]:
    """Validate AI output through Pydantic. Returns validated extracts."""
    validated = []
    for item in items:
        try:
            extract = DailyReportExtract(**item)
            validated.append(extract)
        except Exception as e:
            logger.warning(f"Skipping invalid extract: {e} | data: {item}")
    return validated


def create_provider(provider_type: str, **kwargs) -> LLMProvider:
    """Factory to create the configured provider."""
    provider_type = provider_type.lower().strip()
    if provider_type in ("openai", "openai_compatible"):
        from src.llm.openai_provider import OpenAICompatibleProvider
        return OpenAICompatibleProvider(**kwargs)
    elif provider_type == "ollama":
        from src.llm.ollama_provider import OllamaProvider
        return OllamaProvider(**kwargs)
    elif provider_type == "deepseek":
        from src.llm.deepseek_provider import DeepSeekProvider
        return DeepSeekProvider(**kwargs)
    elif provider_type == "mock":
        from src.llm.mock_provider import MockProvider
        return MockProvider()
    else:
        logger.warning(f"Unknown provider '{provider_type}', falling back to MockProvider")
        from src.llm.mock_provider import MockProvider
        return MockProvider()


PROVIDER_PRESETS = {
    "mock": {
        "name": "Mock（演示模式）",
        "description": "无需网络和密钥，规则匹配解析",
        "requires_key": False,
        "requires_url": False,
        "default_model": "-",
    },
    "deepseek": {
        "name": "DeepSeek",
        "description": "DeepSeek 官方 API，性价比高",
        "requires_key": True,
        "requires_url": False,
        "default_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "openai_compatible": {
        "name": "OpenAI 兼容 / 自定义",
        "description": "任意 OpenAI 兼容接口（硅基流动、通义千问、vLLM 等）",
        "requires_key": True,
        "requires_url": True,
        "default_model": "gpt-4o-mini",
    },
    "ollama": {
        "name": "Ollama（本地）",
        "description": "本地 Ollama 服务，数据不出本机",
        "requires_key": False,
        "requires_url": True,
        "default_url": "http://localhost:11434",
        "default_model": "llama3",
    },
}


def detect_available_providers() -> list[dict]:
    """Auto-detect which providers are available based on environment."""
    import os
    available = []

    # Mock is always available
    available.append({"key": "mock", **PROVIDER_PRESETS["mock"]})

    # Check for DeepSeek
    if os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY"):
        available.append({"key": "deepseek", **PROVIDER_PRESETS["deepseek"]})

    # Check for Ollama
    try:
        import httpx
        resp = httpx.get("http://localhost:11434/api/tags", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            preset = dict(PROVIDER_PRESETS["ollama"])
            preset["available_models"] = models
            available.append({"key": "ollama", **preset})
    except Exception:
        pass

    # DeepSeek and OpenAI-compatible always available as options (can be configured)
    if not any(p["key"] == "deepseek" for p in available):
        available.append({"key": "deepseek", **PROVIDER_PRESETS["deepseek"]})

    available.append({"key": "openai_compatible", **PROVIDER_PRESETS["openai_compatible"]})

    # Only show Ollama if not already detected
    if not any(p["key"] == "ollama" for p in available):
        available.append({"key": "ollama", **PROVIDER_PRESETS["ollama"]})

    return available
