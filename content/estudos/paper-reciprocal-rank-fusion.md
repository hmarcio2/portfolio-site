---
title: "Reciprocal Rank Fusion (Cormack et al., 2009)"
date: 2026-11-01
seq: 6
category: papers
summary: O método simples de combinar rankings que usa só posições, por que a constante k existe e onde ele aparece na busca híbrida.
tags: [busca híbrida, RRF, recuperação de informação, paper]
---

**Referência:** Gordon V. Cormack, Charles L. A. Clarke e Stefan Büttcher, *Reciprocal Rank Fusion outperforms Condorcet and individual rank learning methods* (SIGIR 2009).

## O problema

Várias buscas devolvem listas ordenadas com notas em escalas diferentes (cosseno, BM25, um reranker). Somar ou normalizar as notas é frágil. O que todas têm em comum é a **posição**.

## O método

Para cada documento, soma-se, sobre as listas em que ele aparece:

```
RRF(d) = Σ  1 / (k + posição_da_lista(d))
```

A constante `k` suaviza a diferença entre as primeiras posições: sem ela, o 1º lugar valeria muito mais que o 2º. O paper usa `k = 60`, que virou o valor padrão em bibliotecas e bancos de busca. Documentos ausentes de uma lista simplesmente não recebem termo daquela lista.

## O que o paper defende

Que esse método simples, sem treino, supera métodos de fusão mais elaborados e listas individuais em coleções de teste de recuperação de informação. (Não cito os números; veja o original.)

## Uso nos meus projetos

O [recomendador de filmes](@root/portfolio/recomendador-de-filmes/index.html) combina vetor e BM25 por RRF, com um **peso por lista**. O paper não trata de pesos; essa é uma extensão minha, calibrada por medição. O resultado mostrou que o peso certo depende do embedder: veja [a análise](@root/estudos/busca-hibrida-peso-do-bm25.html).

## Limites

Descarta a magnitude das notas: uma lista com um único candidato muito acima dos outros e uma com todos empatados contribuem igual. E, como vimos, uma lista fraca arrasta a fusão se tiver o mesmo peso de uma forte.
