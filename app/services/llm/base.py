"""Abstração base de providers LLM."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMRequest:
    user_prompt: str
    system_prompt: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 1024
    top_p: Optional[float] = None
    model: Optional[str] = None


@dataclass
class LLMResponse:
    text: str
    model: str
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    cost_usd: Optional[float] = None
    latency_ms: Optional[float] = None
    raw_metadata: dict = field(default_factory=dict)


class BaseLLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Gera uma resposta para o prompt dado."""
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        ...
