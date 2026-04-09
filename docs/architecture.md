# Arquitetura

## Classificacao do sistema

- Tipo: analitico / assistivo
- Impacto do erro: baixo a medio
- Autonomia: sem autonomia operacional
- PII: nao usar por padrao; prever redaction basica
- Tool use: somente leitura
- Supervisao humana: recomendavel na interpretacao dos resultados

## Arquitetura escolhida

O sistema e um monolito FastAPI com renderizacao server-side. A decisao segue o principio de menor complexidade suficiente:

- um processo web
- um banco SQLite local
- um modulo de execucao que roda runs em background via `BackgroundTasks`
- providers LLM simples, sem orquestradores externos
- avaliacao organizada por familias de metricas

Nao ha microservicos, multiagente, event bus ou fila externa.

## Componentes

### Camada web

- FastAPI para rotas HTTP
- Jinja2 + HTMX para paginas SSR
- Tailwind CDN para estilos

### Camada de dados

- SQLite para persistencia local-first
- SQLModel para entidades e relacoes
- migracoes leves on-startup para manter compatibilidade do banco local

### Camada de execucao

- `ExperimentRun` descreve a configuracao do experimento
- `RunCaseResult` guarda resposta, custo, latencia, prompt_version, tokens e erro sanitizado
- cada caso dispara spans de `generation`, `judge_evaluation`, `rag_metrics` e `safety_evaluation`

### Camada de providers

- `mock`
- `openai`
- `anthropic`
- `ollama`

`ollama` usa endpoint OpenAI-compatible e foi adicionado para `gpt-oss:20b`.

### Camada de avaliacao

- `deterministic.py`
- `reference.py`
- `rag_metrics.py`
- `judge.py`
- `safety.py`
- `scoring.py`

Cada familia calcula ou marca `SKIPPED`/`FAILED` sem derrubar a execucao completa.

## Fluxo de um run

1. Usuario cria um run pela UI.
2. O run persiste `provider`, `model`, `prompt_version`, `rubric_preset`, `temperature`, `max_tokens`, `top_p` e familias de metricas habilitadas.
3. A execucao abre sua propria `Session` usando a engine correta.
4. Para cada `TestCase`:
   - resolve prompt final a partir do template
   - chama o provider
   - salva resposta, custo, latencia, tokens, timestamp e hash do contexto
   - calcula familias de metricas habilitadas
   - salva judge prompt, rationale e scores
   - salva safety result quando aplicavel
   - calcula `composite_score` ignorando metricas `SKIPPED`
5. A UI permite inspecao caso a caso, comparacao entre runs e filtros.

## Decisoes de design relevantes

### Menor arquitetura suficiente

Nao foi usado LangChain, LlamaIndex ou framework agentico porque o problema e de execucao + avaliacao, nao de orquestracao complexa.

### Transparencia sobre indisponibilidade

Metricas que dependem de `expected_answer`, `retrieved_context`, Ragas ou embeddings nao quebram o run. Elas salvam `SKIPPED` com motivo.

### Score composto e secundario

O score composto existe para comparacao rapida, mas nao substitui a visao por familia de metrica.

### BackgroundTasks, mas sem vazar Session

A primeira implementacao passava `Session` do request para o background task. Isso e fragil. O fluxo atual passa a `engine` e reabre a sessao dentro do executor.

### HTMX de status

O polling agora retorna HTML e nao JSON cru, evitando quebra visual no badge de status.

## Trade-offs

- SQLite e suficiente para local-first, mas nao e ideal para concorrencia alta.
- Tailwind CDN reduz setup, mas nao traz pipeline de assets.
- Ragas e embeddings ficam opcionais para manter o bootstrap leve. Quando faltam, o sistema explicita fallback.

## Evolucao prevista

- autenticacao e autorizacao
- exportacao Promptfoo
- integracao Phoenix/Langfuse
- suporte a bancos externos
- mais familias de metricas e rubricas customizadas
