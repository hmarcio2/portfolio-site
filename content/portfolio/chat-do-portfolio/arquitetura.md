---
title: Arquitetura
order: 1
summary: Componentes, fluxo de uma pergunta do navegador ao modelo e de volta, e como o código está organizado.
---

## Visão em camadas

```
 navegador (qualquer página do site)
   └─ widget (assets/chat.js)          Markdown seguro, sessionStorage, feedback
        │  POST /chat (JSON)  ◄── resposta em SSE
        ▼
 Caddy (portfolio-edge)  /api/chat/*  ──►  container "chat" (FastAPI, porta 8000)
                                              ├─ limites: taxa por cliente, teto diário
                                              ├─ SessionStore (histórico no servidor)
                                              ├─ KnowledgeBase (BM25 sobre knowledge/*.md)
                                              ├─ prompt de sistema + trechos recuperados
                                              ├─ LLMProvider (Gemini / Anthropic / OpenAI / Ollama / echo)
                                              ├─ guardrails (notas) e tracer (Langfuse)
                                              └─ /feedback, /health
```

O chat é um app FastAPI pequeno (um arquivo principal de ~280 linhas) sobre a biblioteca compartilhada [`portfolio-core`](@root/portfolio/plataforma-docker-cicd/biblioteca-core.html), que fornece o provedor de LLM, o BM25, as sessões, os limites, o SSE e o tracer.

## O caminho de uma pergunta

1. **Validação.** A mensagem é cortada (`strip`) e conferida: de 1 a 1000 caracteres (`PORTFOLIO_MAX_MESSAGE_CHARS`), senão responde 422.
2. **Limites.** Um limitador de janela deslizante (10 por minuto por cliente, por padrão) e um teto diário global (300 mensagens). Estourar qualquer um devolve 429, com `Retry-After` no caso da taxa.
3. **Sessão.** Se o navegador não mandou `session_id`, o servidor cria um (token aleatório de 16 bytes). A mensagem entra no histórico **do servidor**, que guarda as últimas 12 mensagens por 30 minutos.
4. **Trace.** Abre-se um trace `chat-turn` no Langfuse (um no-op sem chaves), ligado à sessão.
5. **Busca.** Monta-se a consulta (a última pergunta, e a anterior junto se a última for curta demais) e recuperam-se até 5 trechos, no máximo 5000 caracteres. Isso vira a observação `retrieval` do trace.
6. **Prompt.** O prompt de sistema recebe os trechos entre `<contexto>` e `</contexto>`, cada um rotulado com o arquivo e o título da seção.
7. **Geração em streaming.** O provedor devolve pedaços de texto; cada um sai como um evento `delta`. O primeiro token marca o `completion_start_time` do trace.
8. **Fim.** A resposta completa entra no histórico, o evento `done` fecha o stream, e o bloco `finally` grava no trace a resposta, a latência e as 7 notas de guardrails. Isso roda também se o visitante fechar a página no meio da resposta.

## Organização do código

| Arquivo | Responsabilidade |
|---|---|
| `app/main.py` | App FastAPI: rotas, prompt de sistema, ordem das etapas acima, `IssuedTraces` (quais traces pertencem a qual sessão) |
| `app/retrieval.py` | Divisão do Markdown em trechos, índice BM25 com radical, consulta de busca, teto de contexto |
| `app/guardrails.py` | As verificações que viram notas do trace (determinísticas, sem outro LLM) |
| `knowledge/*.md` | A base: `perfil.md` (PT), `profile.en.md` (EN), `portfolio.md` (como o portfólio e o chat foram feitos) e `projetos.md` (catálogo) |
| `evaluation/` | Avaliações e scripts de observabilidade (veja [Avaliação](@root/portfolio/chat-do-portfolio/avaliacao.html)) |
| `tests/` | Testes automáticos (75) |
| `deploy/chat.caddy` | Rota do Caddy instalada pelo deploy |

## Por que assim

- **Histórico no servidor.** Se o navegador mandasse o histórico, um visitante poderia forjar turnos do "assistente" (por exemplo, uma fala inventada dizendo que o assistente concordou em ignorar as regras). Guardando as mensagens no servidor, o cliente só envia a pergunta atual.
- **Estado em memória.** As sessões, os limites e o teto diário vivem na memória do processo. É simples e suficiente para uma réplica; o custo é que reiniciar o container zera as conversas e os contadores. Com mais de uma réplica seria preciso Redis.
- **Interface de busca trocável.** `KnowledgeBase.search(consulta, k)` é a mesma interface que uma busca vetorial teria, então trocar o motor de busca não mexe no resto do app (veja [RAG e busca](@root/portfolio/chat-do-portfolio/rag.html) para a medição que levou ao BM25).
- **Tracing nunca atrapalha.** Toda chamada ao Langfuse é protegida e feita em segundo plano; o chat responde com a mesma latência com o Langfuse fora do ar.
