---
title: Plataforma comum, Docker e CI/CD
date: 2026-11-01
seq: 5
category: plataforma
status: em-construcao
repo: https://github.com/hmarcio2/portfolio-edge
summary: Sete repositórios públicos com uma biblioteca compartilhada versionada, imagens Docker enxutas e endurecidas, um proxy Caddy único e GitHub Actions, prontos para uma VPS de 16 GB.
tags: [Docker, GitHub Actions, Caddy, Python, GHCR]
---

## O que é

A base que sustenta os projetos do portfólio: **como o código é organizado, empacotado, testado, publicado e hospedado**. Cada projeto é um **repositório próprio**, com testes, imagem Docker e CI/CD, e todos devem rodar juntos numa VPS de 16 GB atrás de **um único proxy**. Esta documentação descreve essa plataforma, incluindo o que **ainda não foi exercitado**.

## Os sete repositórios

| Repositório | Papel | Documentação |
|---|---|---|
| [`portfolio-core`](https://github.com/hmarcio2/portfolio-core) | Biblioteca Python compartilhada, instalada por **tag do Git** | [A biblioteca](@root/portfolio/plataforma-docker-cicd/biblioteca-core.html) |
| [`portfolio-chat`](https://github.com/hmarcio2/portfolio-chat) | O chat do portfólio | [Chat](@root/portfolio/chat-do-portfolio/index.html) |
| [`portfolio-filmes`](https://github.com/hmarcio2/portfolio-filmes) | O recomendador de filmes | [Recomendador](@root/portfolio/recomendador-de-filmes/index.html) |
| [`portfolio-planilhas`](https://github.com/hmarcio2/portfolio-planilhas) | O analista de planilhas | [Analista](@root/portfolio/agente-de-planilhas/index.html) |
| [`portfolio-site`](https://github.com/hmarcio2/portfolio-site) | Este site, gerado de Markdown e servido por nginx | [O site](@root/portfolio/plataforma-docker-cicd/site.html) |
| [`portfolio-edge`](https://github.com/hmarcio2/portfolio-edge) | Caddy com HTTPS e a rede Docker compartilhada | [Edge](@root/portfolio/plataforma-docker-cicd/edge-caddy.html) |
| [`portfolio-langfuse`](https://github.com/hmarcio2/portfolio-langfuse) | Langfuse self-hosted | [Observabilidade](@root/portfolio/observabilidade-langfuse/index.html) |

Todos são **públicos**, com licença MIT, e o código está no GitHub (2026-11-08).

## Como as peças se encaixam

```
GitHub (um repositório por projeto)                     VPS Hostinger
  push → CI (testes + build + /health)
  deploy (manual hoje) → build → ghcr.io/hmarcio2/<repo>:sha-…
                       → SSH: compose.yml + trecho do Caddy → docker compose pull/up --wait
                                                            ┌───────────── rede Docker "edge" ─────────────┐
 internet ─► Caddy (portfolio-edge, 80/443) ──────────────► │ site  chat  filmes  planilhas  (um compose cada) │
              seudominio.com      → site:8080  e /api/chat → chat:8000                                      │
              filmes.seudominio   → filmes:8000                                                            │
              planilhas.seudominio→ planilhas:8000                                                         │
                                                            └──────────────────────────────────────────────┘
```

## Estado

- **Validado localmente:** os testes de todos os repositórios, a construção e a execução das imagens dos quatro componentes (site, chat, filmes, planilhas) **com as restrições de produção**, e o Langfuse levantado de verdade.
- **Nunca executado:** o **build no CI do GitHub** (a conta está com um bloqueio de cobrança, e os jobs nem iniciam), o **pull das imagens do GHCR**, o **deploy por SSH** e **tudo na VPS** (HTTPS, DNS, rede `edge`).
- Por isso, o que está descrito em [CI/CD e deploy](@root/portfolio/plataforma-docker-cicd/ci-cd.html) e [Edge](@root/portfolio/plataforma-docker-cicd/edge-caddy.html) é **projeto não exercitado**, e pode ter defeitos que só aparecem no primeiro deploy.

## Resultados em números

| O quê | Resultado |
|---|---|
| Testes automáticos | core 51, chat 75, filmes 66, planilhas 97, site 29, Langfuse 24: **342**, nenhum chama um LLM real |
| Imagens Docker | site 48,5 MB; chat 271 MB; filmes 354 MB; planilhas 476 MB |
| Memória em repouso, medida em Docker | chat 108 MiB, filmes 217 MiB (321 MiB com 5000 filmes), planilhas 170 MiB |
| Orçamento de memória da VPS | Langfuse 8 GiB + apps ~2,4 GiB de tetos + sistema |
| Restrições dos containers | somente leitura, `cap_drop: ALL`, `no-new-privileges`, limite de memória, usuário sem privilégios |

## Tecnologias

Docker e Docker Compose, GitHub Actions, GitHub Container Registry (GHCR), Caddy 2 (HTTPS automático), nginx (site), Python 3.12, pytest, Jinja2 e Markdown (o gerador do site).
