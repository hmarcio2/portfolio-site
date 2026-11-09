---
title: Instrumentação
order: 1
summary: "A camada de tracing do portfolio-core: como os traces são montados, as regras de projeto e como cada app a usa."
---

## Onde fica

Em `portfolio_core/tracing.py`, na biblioteca compartilhada ([documentação da `portfolio-core`](@root/portfolio/plataforma-docker-cicd/biblioteca-core.html)). Os apps só chamam `get_tracer()` e usam a interface mínima abaixo; não importam o Langfuse.

## A interface

| Objeto | O que faz |
|---|---|
| `get_tracer()` | Devolve um `LangfuseTracer` se houver `LANGFUSE_PUBLIC_KEY` e `LANGFUSE_SECRET_KEY` (e o pacote `langfuse`); senão, um `Tracer` **no-op** |
| `tracer.start(nome, session_id, input, metadata, tags)` | Abre a observação raiz de um turno (`chat-turn`, `movie-turn`, `sheet-turn`) |
| `span.child(nome, as_type, input, model, ...)` | Cria uma observação filha: `retriever`, `generation` ou `tool` |
| `span.update(output, metadata, level, status_message, usage, completion_start_time)` | Atualiza a observação (saída, tokens, erro, tempo até o 1º token) |
| `span.end()` | Encerra |
| `span.score(nome, valor, data_type, comment)` | Nota do trace inteiro (por exemplo, o resultado de um guardrail) |
| `tracer.score_trace(trace_id, ...)` | Nota atribuída **depois** do trace terminar (o feedback do visitante, que chega em outra requisição) |
| `tracer.flush()`, `tracer.shutdown()` | Enviam o que está na fila; o `shutdown` roda ao desligar o app |

O loop de agente do `portfolio-core` aceita um `trace=` e, com ele, cria sozinho uma `generation` por passo do modelo e uma observação `tool` por chamada de ferramenta. Assim, os apps de filmes e de planilhas ganharam a estrutura completa **sem repetir código**.

## Regras de projeto

1. **Nunca derruba nem atrasa a requisição.** Toda chamada ao Langfuse é protegida por `try/except` e o envio é em segundo plano (o SDK usa uma fila). Os testes cobrem cliente quebrado, observação quebrada e servidor fora do ar. Medido no chat: com o Langfuse fora do ar, a latência é a mesma, e o desligamento leva ~5 s para tentar enviar o que sobrou.
2. **Sem contexto global.** As observações são criadas explicitamente a partir do pai (`span.child`), nunca por "o span atual". Isso é seguro com respostas em *streaming*, em que o gerador pode ser fechado por outra tarefa quando o cliente desconecta, e o contexto implícito se perderia.
3. **Raiz limpa.** O trace é aberto num **contexto OpenTelemetry vazio**. Sem isso, o FastAPI recente abre um span `fastapi.endpoint` por requisição que o Langfuse não recebe; ele viraria o pai do trace e deixaria a raiz "órfã" na interface (um defeito real que corrigi).
4. **Sessão, tags e nome em toda observação.** Os atributos de propagação (`session.id`, `langfuse.trace.name`, tags) são aplicados em cada observação filha, para filtrar por qualquer uma.
5. **Privacidade na origem** (veja [Privacidade](@root/portfolio/observabilidade-langfuse/privacidade.html)).

## O que cada app registra

| App | Trace | Observações | Notas |
|---|---|---|---|
| [Chat](@root/portfolio/chat-do-portfolio/observabilidade.html) | `chat-turn` | `retrieval` (retriever) e `generation` | 7 guardrails e `user_feedback` |
| [Recomendador de filmes](@root/portfolio/recomendador-de-filmes/observabilidade.html) | `movie-turn` | `generation` por passo, `search_movies` / `similar_movies` (tool) | `no_search`, `empty_search`, `unretrieved_titles` |
| [Analista de planilhas](@root/portfolio/agente-de-planilhas/observabilidade.html) | `sheet-turn` | `generation` por passo, `run_sql` / `describe_table` / `make_chart` (tool) | `unverified_numbers`, `tool_errors`, `no_query` |

O chat usa a camada diretamente (uma busca e uma geração por turno); os dois agentes usam o loop do core, que cria os passos e as ferramentas.

## Como as notas são enviadas

Todas pelo `create_score` do SDK, com:

- o **mesmo `environment`** do trace (sem isso, o servidor põe a nota em `default`, longe do trace; um defeito que encontrei e corrigi);
- um **id determinístico** `<trace_id>-<nome>`: reenviar atualiza a nota em vez de duplicar (o visitante pode mudar o voto);
- o **comentário** (o que disparou), mascarado e só se a captura de conteúdo estiver ligada.

## Configuração por ambiente

| Variável | Efeito |
|---|---|
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` | Ligam o tracing (as chaves do **projeto** daquele app) |
| `LANGFUSE_BASE_URL` | Endereço do servidor: `http://langfuse-web:3000` na rede interna da VPS, `http://localhost:3300` no Docker local, `https://cloud.langfuse.com` no Cloud |
| `LANGFUSE_TRACING_ENVIRONMENT` | `production`, `development`, `portfolio-smoke`... separa os dados dentro do projeto |
| `LANGFUSE_SAMPLE_RATE` | Fração dos traces enviados (0 a 1) |
| `LANGFUSE_CAPTURE_CONTENT` | `false` grava só métricas, sem textos |
| `LANGFUSE_ENABLED` | `false` desliga mesmo com as chaves |
| `PORTFOLIO_RELEASE` | Versão do código, anotada nos traces |
