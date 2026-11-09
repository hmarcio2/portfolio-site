---
title: Recomendador de filmes por descrição
date: 2026-11-01
seq: 2
category: agentes-rag
status: local
repo: https://github.com/hmarcio2/portfolio-filmes
summary: Agente que recomenda filmes por descrição livre ou a partir de um filme de exemplo, sobre 5000 filmes em inglês, com busca híbrida (Qdrant + BM25 + RRF) e avaliação da busca.
tags: [RAG, Qdrant, busca híbrida, embeddings, agente, tool use]
---

## O que é

O usuário descreve o que quer assistir ("um suspense psicológico tipo Ilha do Medo, mas mais leve") **ou cita um filme de exemplo** ("algo como Matrix, mas mais recente") e recebe filmes de sinopse parecida, com a explicação de por que combinam. A conversa permite refinar ("mais antigo", "me mostre outros") sem repetir filmes já mostrados.

Por baixo há um agente com duas ferramentas de busca sobre um catálogo de sinopses. A busca combina **similaridade semântica** (banco vetorial Qdrant) e **busca por palavras** (BM25), fundidas por *Reciprocal Rank Fusion*. É um RAG: as sinopses recuperadas entram no contexto do modelo, que escolhe e explica as recomendações a partir delas.

## Como funciona, em um desenho

```
pergunta ─► agente (LLM + tool use) ─┬─► search_movies(descrição, filtros)   "um suspense tipo..."
                                     └─► similar_movies(título, filtros)     "algo como Matrix"
                                            │
                  ┌─────────────────────────┴───────────────────────┐
                  ▼                                                 ▼
        embedding da consulta ─► Qdrant (vetorial, com filtros)   BM25 (lexical, mesmos filtros)
                  └──────────────────► Reciprocal Rank Fusion ◄─────┘
                                            │
            cartões de filmes (dados do catálogo) ─► interface    +    texto do LLM explicando
```

## Estado

- **Implementado e testado:** 66 testes; a busca foi avaliada com três embedders e a busca "parecidos com este filme" com 128 consultas em 5000 filmes.
- **Dois catálogos:** uma amostra de 44 filmes em português (para rodar offline) e **5000 filmes em inglês** do CMU Movie Summary Corpus (a consulta é traduzida pelo agente). O TMDB também é suportado por um script, mas **não foi testado** contra a API real.
- **Código publicado** no GitHub, **sem demo online ainda**. A imagem Docker foi construída e executada com as restrições de produção.

## Resultados em números

| O quê | Resultado | Detalhe |
|---|---|---|
| Busca por descrição, catálogo de 44 filmes, 30 consultas (nDCG@10) | **0,996** com o embedder do Google (só vetor); **0,943** com `nomic-embed-text` (híbrida) | [Avaliação](@root/portfolio/recomendador-de-filmes/avaliacao.html) |
| "Parecidos com este filme", 5000 filmes, 128 consultas (recall@10 pela franquia) | **0,999** só vetorial; 0,921 só BM25 | [Avaliação](@root/portfolio/recomendador-de-filmes/avaliacao.html) |
| Peso ideal do BM25 | **Depende do embedder**: 0 para o Google, 1 para o `nomic-embed-text` | [Busca híbrida](@root/portfolio/recomendador-de-filmes/busca.html) |
| Memória em Docker | 217 MiB (321 MiB com 5000 filmes) para um teto de 768 | [Operação](@root/portfolio/recomendador-de-filmes/operacao.html) |

A busca por descrição **no catálogo grande não foi medida** (não há gabarito para 5000 filmes), e os números do catálogo pequeno vêm de consultas que eu escrevi conhecendo as sinopses. Veja os limites em [Limites e próximos passos](@root/portfolio/recomendador-de-filmes/limites-e-roadmap.html) e o estudo [Busca híbrida: o peso do BM25 depende do embedder](@root/estudos/busca-hibrida-peso-do-bm25.html).

## Tecnologias

Python 3.12, FastAPI e SSE, Qdrant (modo local), BM25 e RRF (em `portfolio-core`), embeddings do Google (`gemini-embedding-001`) ou do Ollama (`nomic-embed-text`), Gemini Flash-Lite como modelo padrão com *tool use*, Langfuse, Docker e GitHub Actions. A interface é HTML, CSS e JavaScript puros.
