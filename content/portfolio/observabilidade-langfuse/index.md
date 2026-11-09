---
title: Observabilidade com Langfuse (self-hosted)
date: 2026-11-01
seq: 4
category: observabilidade
status: em-construcao
repo: https://github.com/hmarcio2/portfolio-langfuse
summary: Tracing, notas de guardrails e feedback do visitante nos três apps, mais um Langfuse em Docker com orçamento de 8 GB de memória, já testado localmente.
tags: [Langfuse, OpenTelemetry, guardrails, Docker, ClickHouse]
---

## O que é

Duas coisas que andam juntas e que documento separadas:

1. **A instrumentação** dos apps do portfólio (chat, recomendador de filmes e analista de planilhas): cada pergunta vira um *trace* no Langfuse, com os passos do agente, os tokens, a latência, **notas automáticas** de qualidade e segurança e o feedback do visitante. Fica numa camada comum do `portfolio-core`, que vira um **no-op sem chaves**: os apps rodam sem Langfuse.
2. **O servidor**: um Langfuse *self-hosted* em Docker (`portfolio-langfuse`), com seis serviços, memória limitada a 8 GB e pronto para a VPS de 16 GB.

O objetivo é mostrar que sei **instrumentar um agente para observabilidade**, mais do que operar um produto de observabilidade. Por isso há dois modos de uso: **só local** (o padrão agora) e **na VPS** com o orçamento de 8 GB.

## Estado

- **Instrumentação:** feita nos três apps, testada com um tracer falso e com o SDK real do Langfuse em memória.
- **Servidor:** o compose subiu os seis serviços, todos `healthy`, **localmente** (Langfuse 4.72.0), e os testes de fumaça dos três apps passaram: observações (com a hierarquia correta) e notas chegaram ao servidor. Isso usou provedores roteirizados, sem LLM e sem tráfego real.
- **Dois defeitos só apareceram ao subir de verdade** e foram corrigidos: uma imagem `:4` antiga em cache que rejeitava as notas em lote, e um healthcheck que ficava `unhealthy`. Veja [Validação e problemas encontrados](@root/portfolio/observabilidade-langfuse/validacao.html).
- **Não testado:** o modo VPS (Caddy, HTTPS, rede `edge`), o consumo de memória sob carga e o backup.

## O que o Langfuse mostra para cada pergunta

```
Sessão (a conversa) ─► Trace "chat-turn" | "movie-turn" | "sheet-turn"
                          ├─ retrieval (retriever)           só no chat: a busca e os trechos
                          ├─ generation (um por passo)        prompt, resposta, tokens, 1º token
                          ├─ search_movies / run_sql ... (tool)  argumentos, resultado, erro
                          └─ notas (scores)                   guardrails e feedback do visitante
```

## Um Langfuse para todos os projetos

**Sim, uma instância atende todos.** O modelo do Langfuse é organização → projeto, e **projeto é o nível mais baixo de isolamento** (não há subprojetos). A recomendação aqui é **um projeto por app**, porque as chaves do Langfuse também *leem* os dados: se a chave do chat (público) vazar, só expõe o projeto do chat, não as planilhas. Dentro de cada projeto, separa-se por `environment`, tags, nome do trace, sessão e release. Detalhes em [O servidor](@root/portfolio/observabilidade-langfuse/servidor.html).

## Resultados em números

| O quê | Resultado | Onde |
|---|---|---|
| Orçamento de memória do servidor | **8 GiB** exatos (ClickHouse 3,5 + web 1,5 + worker 1 + Postgres 1 + Redis 0,5 + MinIO 0,5), conferido por script no CI e no deploy | [Servidor](@root/portfolio/observabilidade-langfuse/servidor.html) |
| 8 conversas reais com o Gemini Flash-Lite | 60 notas e **3 alertas, todos verdadeiros** | [Notas](@root/portfolio/observabilidade-langfuse/notas.html) |
| Teste de fumaça nos 3 apps contra o servidor real | Passou: observações e notas chegaram | [Validação](@root/portfolio/observabilidade-langfuse/validacao.html) |
| Testes do repositório do servidor | 24, mais 1 ignorado | [Operação](@root/portfolio/observabilidade-langfuse/operacao.html) |

## Tecnologias

Langfuse 4 (web e worker), OpenTelemetry (base do SDK), ClickHouse, PostgreSQL, Redis, MinIO, Docker Compose, Caddy e um gerador de `.env` em Python.
