# Notas de Seguranca

## Postura do MVP

- modo local por padrao
- sem autenticacao neste momento
- nao expor na internet sem camada adicional

## Segredos

- API keys ficam apenas em `.env`
- `.env.example` nao contem segredos reais
- logs aplicam redaction de email, telefone, token e padroes de chave
- erros persistidos em `RunCaseResult.raw_error` passam por sanitizacao

## Redaction basica

Padroes cobertos:

- `sk-*`
- `sk-ant-*`
- email
- telefone
- `api_key`, `password`, `secret`, `token` em JSON

## Separacao de falhas

- erro de modelo: salvo em `raw_error`
- erro de avaliacao: salvo como `MetricScore` com status `FAILED`
- metricas indisponiveis: `SKIPPED` com motivo explicito

## Safety suite

Cobertura inicial:

- prompt injection direta
- tentativa de ignorar instrucoes
- extracao de system prompt
- bypass de policy
- refusal quality
- leakage basico de PII/segredo

## Riscos residuais

- regex nao detecta todos os vazamentos nem todos os ataques indiretos
- sem autenticacao qualquer usuario local pode operar o laboratorio
- datasets com PII real continuam sendo responsabilidade do operador

## Recomendacoes para um proximo passo

1. adicionar autenticacao
2. separar ambientes de dev e avaliacao compartilhada
3. ampliar redaction por dominio
4. adicionar rate limiting em rotas de execucao
5. revisar armazenamento de traces e retencao de dados
