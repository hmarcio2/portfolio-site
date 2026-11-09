---
title: Operação
order: 8
summary: Como rodar, as variáveis de ambiente, o Docker medido, o custo e o risco do índice do catálogo grande na VPS.
---

## Rodar localmente

```bash
.venv/Scripts/python -m pip install -e "_core[langchain]" -r 01-recomendador-filmes/requirements.txt pytest pytest-asyncio httpx
cd 01-recomendador-filmes
../.venv/Scripts/python -m uvicorn app.main:create_app --factory --port 8003
```

Abra `http://localhost:8003`. Sem chaves, o LLM é o `echo` (a página abre, mas não conversa) e o embedder é o de hash. Com `GOOGLE_API_KEY`, usa o Gemini Flash-Lite e os embeddings do Google; com `LOCAL_EMBEDDING_ENABLED=true`, embeddings no Ollama. O índice fica em `data/index/` (ignorado pelo git); **se mudar de embedder ou de catálogo, é recriado sozinho**.

Para usar o catálogo grande: [Catálogos](@root/portfolio/recomendador-de-filmes/catalogos.html).

## Variáveis de ambiente

As do `portfolio-core` (LLM, limites, CORS, Langfuse) são as mesmas do [chat](@root/portfolio/chat-do-portfolio/operacao.html). As específicas deste app:

| Variável | Padrão | Efeito |
|---|---|---|
| `PORTFOLIO_FILMES_CATALOG` | auto | `sample`, `cmu` ou `tmdb` força um catálogo; sem isso, o primeiro que existir (TMDB, CMU, amostra) |
| `PORTFOLIO_FILMES_CATALOG_DIR` | `data/` | Pasta dos CSVs `cmu_movies.csv` e `tmdb_movies.csv` (no Docker, `/srv/catalog`) |
| `PORTFOLIO_FILMES_CATALOG_LANG` | por fonte | `pt` ou `en`: idioma da consulta que o agente escreve |
| `PORTFOLIO_FILMES_INDEX_DIR` | `data/index` | Pasta do índice Qdrant; `memory` mantém o índice só na memória |
| `PORTFOLIO_FILMES_TEXT_WEIGHT` | por embedder | Peso do BM25 na busca híbrida (0 = só vetor) |
| `EMBEDDING_PROVIDER` | automático | `ollama`, `google_genai` ou `hash` |
| `LOCAL_EMBEDDING_ENABLED`, `LOCAL_EMBEDDING_MODEL`, `LOCAL_LLM_BASE_URL` | `false`, `nomic-embed-text` | Embeddings no Ollama |
| `EMBEDDING_MODEL` | `gemini-embedding-001` | Modelo de embeddings do Google |
| `TMDB_API_KEY` | | Só para o script `fetch_tmdb.py` |

## Docker

Imagem em dois estágios, usuário sem privilégios, `HEALTHCHECK` em `/health` (com 90 s de carência, porque o app monta o índice no start). O `portfolio-core` vem da tag de `requirements-core.txt`.

```bash
cp .env.example .env                      # preencha GOOGLE_API_KEY
docker compose -f compose.yml -f compose.local.yml up --build     # http://localhost:8003
```

**O que o `.dockerignore` deixa de fora:** `data/index`, os CSVs grandes (`cmu_movies.csv`, `tmdb_movies.csv`), os resultados de avaliação e o `.env`. O catálogo grande **não vai na imagem**: o compose o monta de `./catalog` no host para `/srv/catalog` (somente leitura), e o índice fica no volume `filmes_index`, então os embeddings não são recalculados a cada deploy.

**Medido em Docker (2026-11-08)**, com as restrições de produção (sistema de arquivos somente leitura, `cap_drop: ALL`, `no-new-privileges`, limite de memória, usuário sem privilégios):

| Cenário | Memória em repouso | Teto do compose |
|---|---|---|
| Amostra de 44 filmes, embedder de hash | 217 MiB | 768 MiB |
| 5000 filmes do CMU montados em `/srv/catalog`, embedder de hash | 321 MiB (e 321 MiB depois de 3 buscas) | 768 MiB |

A imagem tem 354 MB. Sem OOM e sem reinício. Esse teste usou o embedder de hash e o provedor `echo`, **sem LLM nem embeddings reais** dentro do container.

## Deploy na VPS

Mesmo fluxo dos outros apps: imagem no GHCR, SSH, `docker compose up --wait` e o trecho do Caddy em `filmes.SEUDOMINIO`. Os detalhes estão em [CI/CD e deploy](@root/portfolio/plataforma-docker-cicd/ci-cd.html). **O deploy nunca foi executado.**

## O risco do índice do catálogo grande na VPS

No primeiro start, o app embute todos os filmes: **5000 chamadas ao embedder**. No Ollama local isso levou **5 minutos**. Mas:

- **A VPS não tem GPU**, então o Ollama não é uma opção realista nela.
- **Com a API do Google no plano gratuito**, 5000 embeddings podem **estourar a cota** (não testei).
- **O índice só vale para o embedder que o criou**: a consulta precisa do mesmo modelo, então não dá para gerar o índice no Ollama e consultá-lo com o Google.

Saídas possíveis: usar a amostra de 44 filmes na VPS; usar um catálogo menor (`--max`); pagar por embeddings do Google com cota maior; ou rodar o Ollama numa máquina com GPU e apontar `LOCAL_LLM_BASE_URL` para ela. Nenhuma foi testada.

## Custos

Cada pedido gasta tokens do LLM (o prompt tem as regras e a lista de gêneros; cada ferramenta devolve até 6 sinopses de 400 caracteres) e, na busca por descrição, uma chamada de embedding da consulta. A busca por filme de exemplo **não chama o embedder**. O teto diário (300 pedidos) e um limite de gasto no provedor são as proteções.

## Testes

```bash
cd 01-recomendador-filmes && ../.venv/Scripts/python -m pytest      # 66 testes, nenhum chama LLM nem embedder real
```
