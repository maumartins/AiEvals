# AI Response Quality Lab

Laboratório experimental para avaliar a qualidade de respostas de modelos de IA usando múltiplas técnicas, sem depender de um único score ou judge model.

## Por que esta arquitetura foi escolhida

- **Monolito FastAPI + SQLite**: menor complexidade suficiente para um laboratório local. Sem microserviços, sem filas, sem Redis.
- **Jinja2 + HTMX**: UI server-rendered, sem SPA pesada, com interatividade assíncrona via HTMX.
- **SQLModel**: combina SQLAlchemy + Pydantic em uma interface limpa, reduzindo duplicação.
- **Provider mock**: a app funciona sem nenhuma API key, usando dados e respostas simuladas.

## Classificação do sistema

| Dimensão | Valor |
|----------|-------|
| Tipo | Analítico / Assistivo |
| Impacto do erro | Baixo a Médio |
| Autonomia | Sem autonomia operacional |
| PII | Não usa por padrão; redaction básica em logs |
| Tool Use | Somente leitura |
| Supervisão humana | Recomendável na interpretação dos resultados |

## Como rodar localmente

### Pré-requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) instalado

### Instalação

```bash
git clone <repo>
cd AiEvals

# Instala dependências
uv sync

# Copia e edita configurações (opcional — funciona sem isso no modo mock)
cp .env.example .env
```

### Rodar a aplicação

```bash
uv run python main.py
```

Acesse: http://127.0.0.1:8000

O banco SQLite e o seed data são criados automaticamente na primeira inicialização em `data/aievals.db`.

### Rodar os testes

```bash
uv run pytest tests/ -v
```

## Métricas disponíveis

### A. Determinísticas / Estruturais
| Métrica | Quando é calculada |
|---------|-------------------|
| `latency_ms` | Sempre |
| `latency_score` | Sempre (normalizado 0-1) |
| `cost_usd` | Quando o provider informa |
| `response_length_chars` | Sempre |
| `is_empty_response` | Sempre |
| `json_validity` | Apenas para `extraction` |
| `citation_coverage` | Quando `expected_citations` está definido |
| `structural_completeness` | Sempre |
| `length_adequacy` | Sempre (por tipo de cenário) |

### B. Com referência (`expected_answer`)
| Métrica | Quando é calculada |
|---------|-------------------|
| `semantic_similarity` | Quando `expected_answer` existe |
| `lexical_overlap` | Quando `expected_answer` existe |
| `topic_coverage` | Quando `expected_answer` existe |
| `critical_divergence` | Quando `expected_answer` existe |

### C. RAG / Grounding (`retrieved_context`)
| Métrica | Quando é calculada |
|---------|-------------------|
| `faithfulness` | Quando `retrieved_context` existe |
| `answer_relevancy` | Quando `retrieved_context` existe |
| `context_precision` | Quando `retrieved_context` existe |
| `context_recall` | Requer também `expected_answer` |
| `groundedness` | Quando `retrieved_context` existe |

Usa Ragas se instalado; senão usa fallback lexical (transparente na UI).

### D. LLM-as-judge (rubrica 1-5)
Dimensões avaliadas pelo judge:
- `correctness`, `completeness`, `clarity`, `helpfulness`, `safety`, `instruction_following`

O judge usa rubrica explícita e auditável. O modelo e provider do judge são configuráveis via `.env`.
**Importante:** o judge não é verdade absoluta — é uma referência qualitativa.

### E. Safety / Adversarial
Tipos detectados:
- `prompt_injection`, `system_prompt_extraction`, `policy_bypass`, `unsafe_request`, `general_adversarial`

## Quando cada métrica faz sentido

| Cenário | Métricas mais relevantes |
|---------|--------------------------|
| `general_qa` | judge, semantic_similarity, lexical_overlap |
| `rag_qa` | faithfulness, groundedness, context_recall |
| `extraction` | json_validity, correctness |
| `summarization` | topic_coverage, completeness |
| `safety_adversarial` | safety, refusal_quality |

## Como adicionar novos modelos

1. Crie `app/services/llm/seu_provider.py` herdando de `BaseLLMProvider`
2. Implemente `generate(request) -> LLMResponse`
3. Registre em `app/services/llm/registry.py`
4. Adicione o nome em `AVAILABLE_PROVIDERS`

## Como adicionar novas métricas

1. Adicione a função em `app/services/evaluation/deterministic.py` (ou módulo adequado)
2. Chame-a dentro de `compute_deterministic_metrics()`
3. Retorne `{"name": "...", "value": float, "status": "computed"}` ou `{"status": "skipped", ...}`
4. Adicione o peso no preset adequado em `app/services/evaluation/scoring.py`

## Limitações do laboratório

- O provider mock não gera respostas realistas — use para testes de infraestrutura
- Métricas RAG com Ragas requerem instalação separada (`uv add ragas datasets`)
- Similaridade semântica requer `sentence-transformers` (`uv add sentence-transformers`)
- O judge LLM tem vieses próprios; não interprete notas como verdade objetiva
- Métricas lexicais (fallback) são menos precisas que embeddings
- Sem autenticação — modo local apenas

## Próximos passos recomendados

1. Instalar `sentence-transformers` para similaridade semântica real
2. Instalar `ragas` e `datasets` para métricas RAG completas
3. Configurar uma API key real (OpenAI ou Anthropic) no `.env`
4. Adicionar exportação compatível com Promptfoo
5. Integrar com Phoenix/Langfuse para observabilidade em nuvem
6. Adicionar autenticação básica para compartilhamento interno
