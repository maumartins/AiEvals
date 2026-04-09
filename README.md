# AI Response Quality Lab

Laboratorio local-first para avaliar qualidade de respostas de IA sem colapsar tudo em uma unica nota. O MVP cadastra datasets, executa experimentos contra providers LLM, registra rastros operacionais e aplica multiplas familias de metricas com transparencia sobre `COMPUTED`, `SKIPPED` e `FAILED`.

## Classificacao do sistema

- Tipo: analitico / assistivo
- Impacto do erro: baixo a medio
- Autonomia: sem autonomia operacional
- PII: nao usar por padrao; redaction basica em logs
- Tool use: somente leitura
- Supervisao humana: recomendavel na interpretacao dos resultados

## Por que esta arquitetura

- Monolito FastAPI + SQLite: menor complexidade suficiente para um laboratorio local.
- Jinja2 + HTMX + Tailwind CDN: UI SSR simples, sem SPA separada.
- SQLModel: dados tipados com baixo overhead.
- Providers desacoplados e seed mock: a aplicacao funciona mesmo sem chaves reais.
- Observabilidade local com OpenTelemetry: spans basicos para generation, judge, rag e safety.

Nao ha microservicos, filas externas, Redis, Kafka ou arquitetura event-driven.

## O que o MVP entrega

- Cadastro e importacao de datasets em CSV e JSONL.
- Casos de teste com `expected_answer`, `retrieved_context`, `reference_context`, `expected_citations`, `metadata_json`, `severity` e `scenario_type`.
- Execucao de experimentos com `provider`, `model`, `temperature`, `max_tokens`, `top_p`, `prompt template`, `prompt_version`, `rubric_preset` e familias de metricas habilitadas.
- Providers: `mock`, `openai`, `anthropic` e `ollama`.
- Suporte local a Ollama com `gpt-oss:20b`.
- Dashboard com total de runs, sucesso/falha, custo medio, latencia media, medias por modelo e comparativo por versao de prompt.
- Safety suite com prompt injection, bypass, system prompt extraction, refusal quality e leakage basico.

## Metricas disponiveis

### A. Deterministicas / estruturais

- `latency_ms`
- `latency_score`
- `cost_usd`
- `response_length_chars`
- `is_empty_response`
- `json_validity`
- `citation_coverage`
- `structural_completeness`
- `length_adequacy`
- `keyword_rule_adherence`
- `regex_rule_adherence`

Use quando voce precisa validar formato, custo, tempo, resposta vazia, regras configuraveis por metadata e conformidade basica.

### B. Com referencia

- `semantic_similarity`
- `lexical_overlap`
- `factual_correctness`
- `topic_coverage`
- `critical_divergence`

Use quando existe `expected_answer` ou `reference_context` e faz sentido comparar output com uma referencia conhecida.

### C. Grounding / RAG

- `faithfulness`
- `answer_relevancy` (equivalente pratico a response relevancy)
- `context_precision`
- `context_recall`
- `groundedness`

Usa Ragas quando instalado e o formato do caso permite. Se nao houver dependencias ou campos necessarios, a UI mostra `SKIPPED` ou fallback lexical com explicacao.

### D. LLM-as-judge

Notas de 1 a 5 para:

- `correctness`
- `completeness`
- `clarity`
- `helpfulness`
- `safety`
- `instruction_following`

O prompt do judge e salvo junto com o rationale. O judge nao e tratado como verdade absoluta.

### E. Safety / adversarial

- `attack_type`
- `passed` / `failed`
- `severity`
- `explanation`
- `safety_suite_pass` por caso

Use para prompt injection, tentativa de ignorar instrucoes, extracao de prompt, bypass de policy, refusal quality e leakage basico de email, telefone ou API key.

## Score composto

Por padrao a aplicacao mostra metricas individualmente. O `composite_score` e opcional e:

- usa presets `General Assistant`, `RAG Grounded QA`, `Safety First` e `Extraction/Structured Output`
- ignora metricas `SKIPPED`
- nao zera metricas indisponiveis
- depende do contexto e nao substitui analise humana

## Limitacoes do laboratorio

- O provider `mock` e util para infra e regressao, nao para benchmark de qualidade real.
- Ragas e sentence-transformers podem nao estar instalados no ambiente; quando faltam, a aplicacao informa fallback ou skip.
- Judge models trazem vies proprios.
- Safety por regex nao substitui red teaming manual.
- Sem autenticacao neste MVP. Use localmente.

## Como rodar localmente

### Requisitos

- Python 3.12+
- `uv`

### Setup

```bash
uv sync
copy .env.example .env
```

### Subir a aplicacao

```bash
uv run python main.py
```

Abra `http://127.0.0.1:8000`.

Na primeira subida, o app cria `data/aievals.db` e popula seed data com:

- 5 casos `general_qa`
- 5 casos `rag_qa`
- 5 casos `extraction`
- 5 casos `safety_adversarial`
- 3 `PromptTemplate`s iniciais

### Rodar testes

```bash
uv run pytest -v
```

## Providers

### Mock

- sempre disponivel
- custo zero
- ideal para smoke tests e desenvolvimento local

### OpenAI-compatible

- configure `OPENAI_API_KEY`
- opcionalmente configure `OPENAI_BASE_URL`

### Anthropic

- configure `ANTHROPIC_API_KEY`

### Ollama

- configure ou mantenha `OLLAMA_BASE_URL=http://127.0.0.1:11434/v1`
- modelo recomendado no MVP: `gpt-oss:20b`

Exemplo:

```bash
ollama pull gpt-oss:20b
uv run python main.py
```

Na UI, selecione `provider=ollama` e `model=gpt-oss:20b`.

## Como adicionar novos modelos

1. Crie um provider em [app/services/llm/base.py].
2. Implemente `generate()`.
3. Registre no arquivo [app/services/llm/registry.py].
4. Exponha o provider na UI de runs/settings se fizer sentido.

## Como adicionar novas metricas

1. Escolha a familia em `app/services/evaluation/`.
2. Retorne dicionarios no formato `{"name": "...", "value": ..., "status": "computed|skipped|failed"}`.
3. Registre nomes da familia no executor para suportar disable/skip transparente.
4. Se a metrica entrar em score composto, ajuste os pesos em [app/services/evaluation/scoring.py].

## Estrutura principal

- [app/api]
- [app/core]
- [app/db]
- [app/models]
- [app/services]
- [app/templates]
- [docs/architecture.md]
- [docs/evaluation-methodology.md]
- [docs/data-model.md]
- [docs/security-notes.md]
