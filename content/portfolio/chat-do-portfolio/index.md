---
title: Chat do portfólio (RAG com BM25)
date: 2026-11-01
seq: 1
category: agentes-rag
status: local
repo: https://github.com/hmarcio2/portfolio-chat
summary: Assistente que responde, em português ou inglês, sobre meu currículo e meus projetos, com streaming, guardrails e avaliação com o Gemini Flash-Lite real.
tags: [FastAPI, SSE, RAG, BM25, Gemini, Langfuse]
---

## O que é

Um assistente flutuante, presente em todas as páginas deste site, que responde a recrutadores e colegas sobre a minha experiência, as minhas habilidades e os meus projetos, em português ou em inglês. Ele responde **somente** com base numa base de conhecimento em Markdown (perfil, portfólio e catálogo de projetos). O que não está lá (salário, disponibilidade, contato direto), ele diz que não sabe e indica o LinkedIn.

É o projeto 00 do portfólio: a porta de entrada, e também o primeiro chatbot "em produção" (ainda localmente), usado para validar a infraestrutura que os outros projetos reaproveitam: streaming, limites de uso, tracing, imagem Docker e deploy.

## Como funciona, em uma linha

```
pergunta ─► consulta de busca ─► BM25 sobre trechos Markdown ─► até 5 trechos ─► prompt de sistema
        ─► LLM (Gemini Flash-Lite por padrão) ─► resposta por SSE (meta · sources · delta… · done | error)
```

## Estado

- **Implementado e testado:** 75 testes automáticos, avaliação da recuperação (41 perguntas) e avaliação ponta a ponta com o Gemini Flash-Lite real (16 de 16 casos).
- **Código publicado** no GitHub; **sem demo online ainda**: roda localmente e em Docker (a imagem foi construída e executada com as restrições de produção).
- **Observabilidade:** cada pergunta vira um trace no Langfuse, com 7 notas automáticas de guardrails e o feedback do visitante; o envio foi confirmado contra um Langfuse local, ainda sem tráfego real.

## Resultados em números

| O quê | Resultado | Onde está o detalhe |
|---|---|---|
| Recuperação: o trecho certo entre os 5 enviados ao modelo (acerto@5) | **1,00** nas 41 perguntas, depois de ajustar o conteúdo e o radical das palavras | [RAG e busca](@root/portfolio/chat-do-portfolio/rag.html), [Avaliação](@root/portfolio/chat-do-portfolio/avaliacao.html) |
| Respostas com o LLM real (16 casos: fatos, "não sei", estado dos projetos, injeção, fora do tema) | **16/16** corretas, ~1 s por resposta | [Avaliação](@root/portfolio/chat-do-portfolio/avaliacao.html) |
| Alertas de guardrail em 8 conversas reais | 3, todos verdadeiros; 1 falso positivo encontrado e corrigido | [Observabilidade](@root/portfolio/chat-do-portfolio/observabilidade.html) |
| Memória do container em repouso | 108 MiB (teto de 512) | [Operação](@root/portfolio/chat-do-portfolio/operacao.html) |

As ressalvas de cada número (perguntas escritas por mim, uma execução por caso) estão nas páginas de detalhe, e o resumo dos limites em [Limites e próximos passos](@root/portfolio/chat-do-portfolio/limites-e-roadmap.html).

## Tecnologias

Python 3.12, FastAPI, Server-Sent Events, BM25 próprio (em `portfolio-core`), Gemini Flash-Lite (com Anthropic, OpenAI e Ollama como alternativas), Langfuse, Docker e GitHub Actions. O front-end é HTML, CSS e JavaScript puro, sem framework.
