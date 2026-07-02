"""DeepSeek provider — pre-configured for DeepSeek API."""
import logging
from src.llm.openai_provider import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek API provider — OpenAI-compatible with DeepSeek defaults.

    DeepSeek API: https://platform.deepseek.com/api_keys
    Default endpoint: https://api.deepseek.com/v1
    Models: deepseek-chat, deepseek-reasoner
    """
    provider_name = "deepseek"

    def __init__(self, api_key: str = "", model: str = "deepseek-chat",
                 base_url: str = "https://api.deepseek.com/v1",
                 timeout: float = 120.0):
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout=timeout,
        )
