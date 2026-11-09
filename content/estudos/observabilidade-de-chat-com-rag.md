---
title: "O que medir na observabilidade de um chat com RAG"
date: 2026-11-01
seq: 4
category: analises
summary: Traces, notas automáticas e feedback do visitante no chat do portfólio, e o que 8 conversas reais já revelaram, incluindo um falso positivo corrigido.
tags: [observabilidade, Langfuse, guardrails, RAG]
---

**Contexto:** o [chat do portfólio](@root/portfolio/chat-do-portfolio.html) envia cada turno ao Langfuse. A pergunta que guiou o desenho: *o que eu precisaria ver, no painel, para saber se o assistente está funcionando?*

## O que cada turno registra

Um **trace** por pergunta, com duas observações: `retrieval` (a consulta de busca e os trechos escolhidos) e `generation` (o prompt completo que o modelo viu, a resposta, tokens, tempo até o primeiro token). Dados pessoais são mascarados antes do envio.

## Notas (scores) automáticas

Heurísticas baratas, sem chamar outro LLM, gravadas como notas do trace:

| Pergunta que a nota responde | Nota |
|---|---|
| Alguém tentou injeção de prompt? | `injection_suspect` |
| O visitante colocou dado pessoal? | `pii_in_input`, `pii_in_output` |
| A busca não achou nada? | `no_context` |
| O modelo citou um link que não estava no contexto? | `unsupported_links` |
| O prompt vazou na resposta? | `prompt_leak_suspect` |
| **O que falta na base de conhecimento?** | `knowledge_gap` |
| A resposta ajudou? | `user_feedback` (👍/👎 do visitante) |

São **sinais, não bloqueios**: quem protege é o prompt e a API; as notas medem se isso funciona.

## O que 8 conversas reais mostraram

Capturei 8 conversas pelo pipeline real (Gemini Flash-Lite, base de conhecimento real, SDK do Langfuse ligado a um exportador em memória): 60 notas ao todo, respostas em cerca de 0,8 a 1,5 s, primeiro token em 0,6 a 1,0 s. Houve 3 alertas, todos verdadeiros: `knowledge_gap` em "Ele já trabalhou na Google?", `injection_suspect` num pedido de ignorar instruções e `pii_in_input` num e-mail digitado na pergunta.

## Um falso positivo, corrigido com esse método

O `knowledge_gap` disparava numa resposta correta que, no segundo parágrafo, avisava o que o assistente não sabia ("não há informações sobre salário…"). A detecção passou a olhar só o primeiro parágrafo, e o caso virou teste.

## O que ainda não está provado

Estas 8 conversas foram exportadas do pipeline real antes de eu ter um servidor; o visualizador estático em `docs/observabilidade/` mostra o que o servidor receberia. Depois subi um Langfuse local e confirmei o envio com um teste de fumaça (3 observações e 8 notas chegaram), o que revelou dois problemas: veja [Langfuse: o servidor precisa ser tão novo quanto o SDK](@root/estudos/langfuse-sdk-e-servidor.html). **Ainda faltam** prints da interface e tráfego real; os painéis não foram montados. Mais em [Langfuse self-hosted](@root/portfolio/observabilidade-langfuse.html).
