"""Provider OpenAI (compatível com qualquer endpoint OpenAI-compatible)."""

import time

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import get_logger
from app.services.llm.base import BaseLLMProvider, LLMRequest, LLMResponse

logger = get_logger(__name__)

# Custo estimado por 1M tokens (input/output) para modelos comuns
COST_TABLE: dict[str, tuple[float, float]] = {
    "gpt-4o": (5.00, 15.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-3.5-turbo": (0.50, 1.50),
}


def estimate_cost(model: str, tokens_input: int, tokens_output: int) -> float:
    for key, (in_cost, out_cost) in COST_TABLE.items():
        if key in model:
            return (tokens_input * in_cost + tokens_output * out_cost) / 1_000_000
    return 0.0


class OpenAIProvider(BaseLLMProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self._client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key,
            base_url=base_url,
        )

    @property
    def default_model(self) -> str:
        return settings.openai_default_model

    async def generate(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.default_model
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.user_prompt})

        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.top_p is not None:
            kwargs["top_p"] = request.top_p

        start = time.time()
        completion = await self._client.chat.completions.create(**kwargs)
        latency_ms = (time.time() - start) * 1000

        text = completion.choices[0].message.content or ""
        tokens_input = completion.usage.prompt_tokens if completion.usage else None
        tokens_output = completion.usage.completion_tokens if completion.usage else None
        cost = estimate_cost(model, tokens_input or 0, tokens_output or 0)

        return LLMResponse(
            text=text,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=cost,
            latency_ms=latency_ms,
            raw_metadata={"finish_reason": completion.choices[0].finish_reason},
        )
