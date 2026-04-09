"""Provider Ollama via API OpenAI-compatible."""

import time

from openai import AsyncOpenAI

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider, LLMRequest, LLMResponse


class OllamaProvider(BaseLLMProvider):
    name = "ollama"

    def __init__(self, base_url: str | None = None):
        self._client = AsyncOpenAI(
            api_key="ollama-local",
            base_url=base_url or settings.ollama_base_url,
        )

    @property
    def default_model(self) -> str:
        return settings.ollama_default_model

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
        usage = getattr(completion, "usage", None)

        return LLMResponse(
            text=completion.choices[0].message.content or "",
            model=model,
            tokens_input=getattr(usage, "prompt_tokens", None),
            tokens_output=getattr(usage, "completion_tokens", None),
            cost_usd=None,
            latency_ms=latency_ms,
            raw_metadata={
                "provider": "ollama",
                "finish_reason": completion.choices[0].finish_reason,
            },
        )
