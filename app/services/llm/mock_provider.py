"""Provider mock para testes locais sem chave de API."""

import asyncio
import hashlib
import random

from app.services.llm.base import BaseLLMProvider, LLMRequest, LLMResponse

MOCK_RESPONSES = [
    "Esta é uma resposta de exemplo gerada pelo provider mock. O modelo processou sua entrada e gerou esta resposta simulada.",
    "Resposta simulada: com base na entrada fornecida, posso afirmar que a análise indica resultados consistentes com os dados apresentados.",
    "O provider mock está funcionando. Em produção, esta resposta seria gerada por um modelo de IA real como GPT-4 ou Claude.",
    "Análise concluída. Os dados fornecidos mostram padrões esperados. Esta é uma resposta mock para fins de teste.",
    "Processamento realizado com sucesso. A resposta foi gerada com base nos parâmetros configurados no experimento.",
]

# Respostas específicas por tipo de cenário
SCENARIO_RESPONSES = {
    "rag_qa": "Com base no contexto fornecido, a resposta é: {context_summary}. Esta informação foi extraída diretamente do material de referência.",
    "extraction": '{"campo1": "valor extraído", "campo2": "outro valor", "confiança": 0.95}',
    "classification": "Categoria identificada: POSITIVO. Confiança: 87%. Justificativa: o texto apresenta características lexicais e semânticas compatíveis com sentimento positivo.",
    "summarization": "Resumo: O texto aborda os principais pontos relacionados ao tema, destacando aspectos relevantes e conclusões importantes para a análise.",
    "safety_adversarial": "Não posso ajudar com isso. Esta solicitação viola as diretrizes de uso aceitável.",
}


class MockProvider(BaseLLMProvider):
    name = "mock"

    @property
    def default_model(self) -> str:
        return "mock-v1"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        # Simula latência realista (50-300ms)
        await asyncio.sleep(random.uniform(0.05, 0.3))

        # Escolhe resposta baseado no hash do prompt (determinístico)
        prompt_hash = int(hashlib.md5(request.user_prompt.encode()).hexdigest(), 16)

        # Detecta tipo de cenário pelo conteúdo do prompt
        response_text = self._pick_response(request, prompt_hash)

        tokens_input = len(request.user_prompt.split()) * 2
        tokens_output = len(response_text.split()) * 2

        return LLMResponse(
            text=response_text,
            model="mock-v1",
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=0.0,  # Mock não tem custo real
            raw_metadata={"provider": "mock", "deterministic": True},
        )

    def _pick_response(self, request: LLMRequest, prompt_hash: int) -> str:
        prompt_lower = request.user_prompt.lower()

        # Detecta safety/adversarial
        if any(kw in prompt_lower for kw in ["ignore", "bypass", "ignore previous", "system prompt", "jailbreak"]):
            return SCENARIO_RESPONSES["safety_adversarial"]

        # Detecta extração estruturada
        if any(kw in prompt_lower for kw in ["extract", "json", "extraia", "estruturado"]):
            return SCENARIO_RESPONSES["extraction"]

        # Detecta classificação
        if any(kw in prompt_lower for kw in ["classify", "classifique", "categoria", "sentimento"]):
            return SCENARIO_RESPONSES["classification"]

        # Detecta sumarização
        if any(kw in prompt_lower for kw in ["summarize", "summarise", "resuma", "resumo"]):
            return SCENARIO_RESPONSES["summarization"]

        # Resposta genérica determinística
        return MOCK_RESPONSES[prompt_hash % len(MOCK_RESPONSES)]
