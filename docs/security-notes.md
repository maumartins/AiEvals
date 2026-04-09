# Notas de Segurança

## Modo de operação

O AI Response Quality Lab opera em modo **local por padrão**, sem autenticação. Não deve ser exposto à internet sem camada de autenticação adicional.

## Dados sensíveis

- API keys são lidas apenas de variáveis de ambiente via `.env` — nunca commitadas
- Logs passam por redaction automática: email, telefone, chaves API (padrões `sk-*`, `sk-ant-*`)
- Stacktraces brutos não são exibidos na UI — apenas tipo e mensagem sanitizada
- Erros de modelo são separados de erros de avaliação

## Redaction de logs

Os seguintes padrões são removidos automaticamente dos logs:

```
sk-[A-Za-z0-9]{20,}        → [REDACTED_API_KEY]
sk-ant-[A-Za-z0-9]{20,}    → [REDACTED_API_KEY]
email@dominio.com           → [REDACTED_EMAIL]
"api_key": "..."            → "api_key": "[REDACTED]"
"password": "..."           → "password": "[REDACTED]"
"secret": "..."             → "secret": "[REDACTED]"
"token": "..."              → "token": "[REDACTED]"
```

## Variáveis de ambiente

Nunca inclua chaves reais no `.env.example`. Apenas `.env` deve conter segredos e deve estar no `.gitignore`.

## SQL Injection

Todas as queries usam SQLModel/SQLAlchemy com parâmetros vinculados — sem SQL dinâmico.

## Preparação para produção

Para usar em ambiente compartilhado:
1. Adicionar autenticação (módulo preparado para inclusão futura)
2. Configurar HTTPS
3. Usar banco Postgres (troca de `DATABASE_URL` apenas)
4. Revisar os padrões de redaction para o contexto do domínio
5. Adicionar rate limiting nas rotas de execução

## Considerações PII

Por padrão, o laboratório não captura PII. Se os datasets de teste contiverem dados pessoais:
- Use dados sintéticos sempre que possível
- Habilite redaction adicional nas configurações
- Não use em produção sem revisão de conformidade (LGPD/GDPR)
