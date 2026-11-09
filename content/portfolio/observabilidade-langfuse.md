---
title: Observabilidade com Langfuse (self-hosted)
date: 2026-11-01
seq: 4
category: observabilidade
status: em-construcao
repo: https://github.com/hmarcio2/portfolio-langfuse
summary: Tracing, notas de guardrails e feedback do visitante no chat, mais um Langfuse em Docker com orçamento de 8 GB de memória, já testado localmente com os três apps.
tags: [Langfuse, OpenTelemetry, guardrails, Docker, ClickHouse]
---

## Objetivo

Mostrar que sei instrumentar um agente para observabilidade, mais do que operar um produto de observabilidade. Por isso há dois modos de uso:

- **Só local (o padrão agora):** os apps rodam sem Langfuse; o tracer é desligado sem chaves. As evidências estão num visualizador estático com traces reais exportados.
- **Na VPS de 16 GB, com 8 GB para o Langfuse:** o Docker está pré-configurado e os 8 GB restantes ficam para os apps.

## O que é instrumentado

Em `portfolio-core` há uma camada de tracing (`Span`/`Tracer`) que vira um no-op sem chaves e usa o SDK do Langfuse (baseado em OpenTelemetry) com elas. O loop de agente da biblioteca também a usa: com um `trace`, cada passo do modelo vira uma `generation` e cada chamada de ferramenta vira uma observação `tool`. Os três apps usam essa camada. O [chat](@root/portfolio/chat-do-portfolio.html) a usa para:

- um **trace por turno** com `retrieval` e `generation` (prompt completo, resposta, tokens, tempo até o primeiro token);
- **7 notas automáticas** (injeção de prompt, dado pessoal na entrada e na saída, ausência de contexto, links inventados, vazamento do prompt, lacuna de conhecimento) e a nota `user_feedback` do visitante;
- **privacidade:** dados pessoais mascarados antes do envio, `LANGFUSE_CAPTURE_CONTENT=false` para gravar só métricas, e o visitante nunca é identificado;
- **robustez:** toda chamada ao Langfuse é protegida e feita em segundo plano; testes cobrem cliente quebrado e servidor fora do ar.

Os **agentes** ([filmes](@root/portfolio/recomendador-de-filmes.html) e [planilhas](@root/portfolio/agente-de-planilhas.html)) têm traces com a estrutura completa (passos do modelo e ferramentas) e notas próprias: `no_search`, `empty_search` e `unretrieved_titles` (filme do catálogo citado que a busca não devolveu) no recomendador; `unverified_numbers`, `tool_errors` e `no_query` no analista de planilhas. Como os traces do analista podem conter trechos da planilha do visitante, o exemplo de configuração dele deixa a captura de conteúdo desligada.

## Evidências sem servidor

`docs/observabilidade/trace-viewer.html` é um visualizador estático (abre direto no navegador) com **8 conversas reais** pelo pipeline completo: lista de traces, linha do tempo, tokens, entrada e saída, e as notas. Foram 60 notas e 3 alertas, todos verdadeiros. **Não é uma captura da interface do Langfuse**; prints reais entram quando o servidor subir. Análise no estudo [O que medir na observabilidade de um chat com RAG](@root/estudos/observabilidade-de-chat-com-rag.html).

## O Docker do Langfuse

Seis serviços (web, worker, Postgres, ClickHouse, Redis e MinIO):

| Decisão | Por quê |
|---|---|
| Só o `langfuse-web` entra na rede do proxy; **nenhuma porta publicada** | o compose de exemplo do Langfuse publica várias portas; aqui só o Caddy fala com o mundo |
| Sem segredos padrão: toda senha é obrigatória e gerada aleatoriamente (`.env` com permissão 600) | exemplos com `mysalt` e `miniosecret` não servem para uma instância pública |
| Cadastro aberto desligado | numa instância pública, qualquer um criaria conta |
| Tetos de memória por serviço que **somam exatamente 8 GiB** | ClickHouse 3,5 GB, web 1,5 GB, worker 1 GB, Postgres 1 GB, Redis e MinIO 0,5 GB cada |
| Um script confere a soma e roda no CI e no deploy | subir um teto além do orçamento faz o deploy falhar |

**Um Langfuse para todos os projetos:** uma organização, um *projeto* Langfuse por app (isolamento de chaves e de dados), e dentro de cada projeto `environment`, tags, sessão e release. O Langfuse não tem subprojetos.

## Estado e limites (sem disfarçar)

- **Testado de verdade em 2026-11-01:** o compose subiu os seis serviços (todos `healthy`), o Langfuse 4.72.0 respondeu e os testes de fumaça do chat, do recomendador e do analista de planilhas passaram: as observações (com a hierarquia trace → generation/tool) e as notas chegaram ao servidor. Isso usou provedores roteirizados, sem LLM e sem tráfego real.
- **Dois defeitos só apareceram ao subir de verdade** e foram corrigidos: uma imagem `:4` antiga em cache (4.30.0) que rejeitava as notas enviadas em lote pelo SDK 5.1 (os traces chegavam, as notas não), e um healthcheck que ficava `unhealthy` porque o Next.js não escutava em `127.0.0.1`. Veja o estudo [Langfuse: o servidor precisa ser tão novo quanto o SDK](@root/estudos/langfuse-sdk-e-servidor.html).
- **Não testado:** o modo VPS (Caddy, HTTPS, rede `edge`), o consumo de memória sob carga (os tetos continuam sendo configuração) e o backup.
- Os tetos de memória são configuração, não consumo medido; medir com `docker stats` sob carga.
- Os três apps enviam traces de teste com a estrutura esperada, mas nenhum recebeu tráfego real ainda.

## Próximos passos

- Tirar prints reais da interface (logado no Langfuse local) e guardar no repositório.
- Montar os painéis: taxa semanal de `knowledge_gap`, de `injection_suspect`, de feedback positivo, latência p50/p95 e tokens por dia.
- Medir, com os painéis, a taxa das notas dos agentes (por exemplo `unretrieved_titles` e `unverified_numbers`) e ajustar as heurísticas pelos falsos positivos que aparecerem.
