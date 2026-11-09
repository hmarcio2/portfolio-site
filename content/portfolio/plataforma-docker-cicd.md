---
title: Plataforma comum, Docker e CI/CD
date: 2026-11-01
seq: 5
category: plataforma
status: em-construcao
repo: https://github.com/hmarcio2/portfolio-edge
summary: Biblioteca compartilhada versionada, imagens Docker enxutas, proxy Caddy único e GitHub Actions por repositório, prontos para uma VPS de 16 GB.
tags: [Docker, GitHub Actions, Caddy, Python, GHCR]
---

## Objetivo

Cada projeto do portfólio é um **repositório próprio**, com testes, imagem Docker e CI/CD, e todos rodam juntos numa VPS de 16 GB atrás de um único proxy. Esta página documenta essa plataforma.

## Peças

| Repositório | Papel |
|---|---|
| [`portfolio-core`](https://github.com/hmarcio2/portfolio-core) | Biblioteca Python compartilhada: configuração, abstração de LLM, loop de ferramentas, BM25, sessões, SSE e tracing. É instalada por **tag do Git** (`requirements-core.txt`), não copiada |
| [`portfolio-chat`](https://github.com/hmarcio2/portfolio-chat), [`portfolio-filmes`](https://github.com/hmarcio2/portfolio-filmes), [`portfolio-planilhas`](https://github.com/hmarcio2/portfolio-planilhas) | Os apps FastAPI |
| [`portfolio-site`](https://github.com/hmarcio2/portfolio-site) | Este site: gerado a partir de Markdown e servido por nginx |
| [`portfolio-edge`](https://github.com/hmarcio2/portfolio-edge) | Caddy com HTTPS automático; cada app instala um trecho em `routes/` ou `sites/` |
| [`portfolio-langfuse`](https://github.com/hmarcio2/portfolio-langfuse) | Langfuse self-hosted (veja a [página de observabilidade](@root/portfolio/observabilidade-langfuse.html)) |

## Decisões

- **Abstração de LLM:** `LLM_PROVIDER`/`LLM_MODEL` e as chaves definem o provedor (Anthropic nativo; Gemini, OpenAI e Ollama via LangChain). O padrão é o modelo mínimo do Google para economizar custo, com um fallback API → local. Sem chaves, o provedor `echo` mantém tudo testável offline.
- **Imagens em 2 estágios**, com usuário sem privilégios e `HEALTHCHECK`. O `portfolio-core` entra por um *named build context* (`--build-context core=...`) no desenvolvimento local e pela tag em produção.
- **Containers endurecidos:** sistema de arquivos somente leitura, sem capabilities, limite de memória, `tmpfs` para temporários.
- **CI em todo push:** testes (Python 3.12), build da imagem e `/health` no container.
- **Deploy manual por enquanto** (`workflow_dispatch`): build → GHCR → SSH → `docker compose up --wait` → recarrega o Caddy. Para automatizar, basta trocar o gatilho por push na `main`.
- **Orçamento de memória:** Langfuse limitado a 8 GB; os outros 8 GB para os apps (cerca de 2,5 GB de tetos configurados) e o sistema.

## Testes

A biblioteca comum tem 51 testes; os apps têm 75 (chat), 66 (filmes) e 97 (planilhas), e o Langfuse 24. Os testes não chamam LLMs reais; a qualidade é medida em avaliações separadas, descritas em cada projeto.

## Estado e limites

- Os repositórios estão publicados no GitHub (core, chat, filmes, planilhas, site, edge e langfuse), mas **nada foi publicado numa VPS ainda**, e as imagens Docker dos apps e do site ainda não foram construídas e executadas. Só o Langfuse foi levantado de verdade, localmente (com dois defeitos encontrados e corrigidos).
- Ordem de publicação seguida: `portfolio-core` (tag `v0.3.0`) primeiro, depois os apps. O botão "Código no GitHub" desta página aponta para o `portfolio-edge`; os outros repositórios estão na tabela acima.
- Backups, retenção de dados e monitoramento da VPS ainda precisam ser configurados.
