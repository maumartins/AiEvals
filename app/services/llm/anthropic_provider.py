"""Provider Anthropic."""

import time

import anthropic

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider, LLMRequest, LLMResponse

COST_TABLE: dict[str, tuple[float, float]] = {
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-opus": (15.00, 75.00),
}


def estimate_cost(model: str, tokens_input: int, tokens_output: int) -> float:
    for key, (in_cost, out_cost) in COST_TABLE.items():
        if key in model:
            return (tokens_input * in_cost + tokens_output * out_cost) / 1_000_000
    return 0.0


class AnthropicProvider(BaseLLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None):
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key or settings.anthropic_api_key
        )

    @property
    def default_model(self) -> str:
        return settings.anthropic_default_model

    async def generate(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.default_model
        kwargs: dict = {
            "model": model,
            "max_tokens": request.max_tokens,
            "messages": [{"role": "user", "content": request.user_prompt}],
            "temperature": request.temperature,
        }
        if request.system_prompt:
            kwargs["system"] = request.system_prompt
        if request.top_p is not None:
            kwargs["top_p"] = request.top_p

        start = time.time()
        response = await self._client.messages.create(**kwargs)
        latency_ms = (time.time() - start) * 1000

        text = response.content[0].text if response.content else ""
        tokens_input = response.usage.input_tokens
        tokens_output = response.usage.output_tokens
        cost = estimate_cost(model, tokens_input, tokens_output)

        return LLMResponse(
            text=text,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=cost,
            latency_ms=latency_ms,
            raw_metadata={"stop_reason": response.stop_reason},
        )
