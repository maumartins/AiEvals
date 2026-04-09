"""Registro de providers LLM disponíveis."""

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider
from app.services.llm.mock_provider import MockProvider
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.anthropic_provider import AnthropicProvider


def get_provider(name: str | None = None) -> BaseLLMProvider:
    """Retorna instância do provider pelo nome."""
    provider_name = (name or settings.default_provider).lower()
    if provider_name == "openai":
        return OpenAIProvider()
    if provider_name == "anthropic":
        return AnthropicProvider()
    return MockProvider()


def get_judge_provider() -> BaseLLMProvider:
    return get_provider(settings.judge_provider)


AVAILABLE_PROVIDERS = ["mock", "openai", "anthropic"]
