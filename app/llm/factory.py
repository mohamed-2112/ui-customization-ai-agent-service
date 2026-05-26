from app.core.config import settings
from app.llm.base import LLMClient
from app.llm.huggingface_client import HuggingFaceLLMClient


def get_llm_client() -> LLMClient:
    if settings.llm_provider == "huggingface":
        return HuggingFaceLLMClient()

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")