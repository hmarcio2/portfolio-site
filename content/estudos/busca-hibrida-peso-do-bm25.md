---
title: "Busca híbrida: o peso do BM25 depende do embedder"
date: 2026-11-01
seq: 2
category: analises
summary: Medi vetorial, BM25 e híbrida com três embedders. Com o embedder multilíngue do Google, misturar BM25 piorou; com o nomic-embed-text, melhorou.
tags: [busca híbrida, avaliação, Qdrant, RRF]
---

**Contexto:** o [recomendador de filmes](@root/portfolio/recomendador-de-filmes/index.html) busca por descrição ("suspense psicológico, mas mais leve") num catálogo de 44 filmes, com Qdrant (vetorial) e BM25, combinados por RRF. Minha primeira versão do README dizia que a híbrida superava cada busca isolada. Medi antes de manter a frase.

## Como medi

30 consultas: 16 diretas, 6 por paráfrase (pouca sobreposição de palavras) e 8 por nome ou palavra exata. Os filmes relevantes foram julgados a partir das sinopses. Métrica: nDCG@10. Sem LLM no caminho, só a busca.

## Resultado (nDCG@10, 2026-11-01)

| Embedder | Estratégia | todas | paráfrase |
|---|---|---|---|
| Google `gemini-embedding-001` | **só vetorial** | **0,996** | **0,981** |
| | híbrida (BM25 com peso 1) | 0,954 | 0,769 |
| | só BM25 | 0,919 | 0,620 |
| Ollama `nomic-embed-text` | só vetorial | 0,883 | 0,645 |
| | **híbrida (peso 1)** | **0,943** | **0,739** |
| | só BM25 | 0,919 | 0,620 |

## O que aprendi

1. **Não existe "a" melhor estratégia.** Com o embedder multilíngue do Google, o BM25 (ruim nas paráfrases) arrasta a fusão para baixo. Com o `nomic-embed-text`, centrado em inglês, o BM25 cobre o que o vetor perde.
2. **O peso virou configuração.** O padrão é por embedder: 0 (só vetor) para o Google e 1 para os demais. Tive de corrigir também um bug em que o modo de texto puro herdava o peso do vetor.
3. **Corrigi a frase do README.** A afirmação original valia só para um dos embedders.
4. **Onde o BM25 deveria ajudar, não ajudou:** nas buscas por nome ("Totoro") todas as estratégias empatam em 1,000, porque 44 filmes são poucos para o vetor errar.

## Limites desta medição

Catálogo pequeno; as consultas foram escritas por mim conhecendo as sinopses (viés a favor da busca lexical); só 6 paráfrases e 8 buscas por nome. Diferenças de poucos centésimos não são conclusivas; a diferença entre 0,98 e 0,77 nas paráfrases é grande. Com um catálogo de ~1000 filmes (TMDB), o resultado pode mudar, e ainda não medi.

Conceitos usados: [RAG na prática](@root/estudos/rag-bm25-embeddings-rrf.html).
