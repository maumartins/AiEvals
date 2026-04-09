# Arquitetura — AI Response Quality Lab

## Classificação

- **Tipo**: Analítico / Assistivo
- **Impacto do erro**: Baixo a Médio (erros afetam interpretação de métricas, não sistemas em produção)
- **Autonomia**: Sem autonomia operacional — todas as ações requerem iniciativa humana
- **PII**: Não usa por padrão; redaction básica em logs para email, telefone e chaves API
- **Tool Use**: Somente leitura (consulta a APIs de LLM)
- **Supervisão humana**: Recomendável na interpretação dos resultados

## Stack

```
FastAPI (framework web)
├── Jinja2 + HTMX (UI server-rendered)
├── SQLModel + SQLite (banco de dados local)
├── Pydantic + pydantic-settings (validação e config)
└── OpenTelemetry (observabilidade local)

Providers LLM:
├── Mock (sempre disponível, sem API key)
├── OpenAI (requer OPENAI_API_KEY)
└── Anthropic (requer ANTHROPIC_API_KEY)

Avaliação:
├── Métricas determinísticas (built-in)
├── Métricas com referência (built-in + sentence-transformers opcional)
├── Métricas RAG (Ragas opcional, fallback léxico built-in)
├── LLM-as-judge (mock por padrão, configurável)
└── Safety suite (built-in, baseada em padrões regex)
```

## Estrutura de arquivos

```
app/
├── api/           — Rotas FastAPI (datasets, runs, safety, settings, dashboard)
├── core/          — Configuração, logging com redaction
├── db/            — Engine SQLite, session factory
├── models/        — Entidades SQLModel (Dataset, TestCase, ExperimentRun, etc.)
├── services/
│   ├── datasets.py     — CRUD + importação CSV/JSONL
│   ├── execution.py    — Engine de execução de experimentos
│   ├── evaluation/     — Famílias de métricas
│   │   ├── deterministic.py
│   │   ├── reference.py
│   │   ├── rag_metrics.py
│   │   ├── judge.py
│   │   ├── safety.py
│   │   └── scoring.py
│   ├── llm/           — Abstração de providers
│   │   ├── base.py
│   │   ├── mock_provider.py
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   └── registry.py
│   ├── observability/ — OpenTelemetry
│   └── safety/        — (integrado em evaluation/safety.py)
├── templates/     — Jinja2 HTML
└── static/        — CSS/JS estáticos
scripts/
└── seed.py        — Dados de exemplo
tests/             — pytest
docs/              — Documentação
```

## Fluxo de execução de um run

```
POST /runs/ → ExperimentRun criado (status=pending)
           → background_task(execute_run)
           → Para cada TestCase:
               1. build_final_prompt(case, template)
               2. provider.generate(request) → LLMResponse
               3. RunCaseResult salvo com latência, tokens, custo
               4. Métricas calculadas em paralelo lógico:
                  a. deterministic (sempre)
                  b. reference (se expected_answer)
                  c. rag (se retrieved_context)
                  d. judge (sempre, mock se falhar)
                  e. safety (se safety_adversarial)
               5. composite_score calculado ignorando SKIPs
           → ExperimentRun.status = completed/failed
```

## Decisões de design

- **Background tasks FastAPI**: execução assíncrona sem filas externas — adequado para MVP local
- **Fallback gracioso**: métricas que dependem de libs opcionais retornam SKIPPED em vez de quebrar
- **Judge com mock fallback**: se o judge falhar, usa resposta mock determinística, não propaga erro
- **SQLite**: suficiente para laboratório local; migrar para Postgres em produção com mínima mudança
- **Sem cache de embeddings**: para simplicidade; em produção, cachear embeddings é recomendado
