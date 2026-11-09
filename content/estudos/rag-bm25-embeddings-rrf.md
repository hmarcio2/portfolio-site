---
title: "RAG na prática: BM25, embeddings e fusão de rankings"
date: 2026-11-01
seq: 1
category: conceitos
summary: O que cada tipo de busca enxerga, quando um empata com o outro e como combinar os dois sem somar notas incomparáveis.
tags: [RAG, BM25, embeddings, RRF]
---

RAG (geração aumentada por recuperação) é o padrão em que o modelo de linguagem responde com base em trechos que o sistema busca antes de gerar o texto. A qualidade da resposta depende, primeiro, de a **busca trazer os trechos certos**. Este texto resume as três peças que uso nos projetos do portfólio.

## Busca lexical: BM25

O BM25 pontua um trecho pelas palavras da pergunta que ele contém. Palavras raras pesam mais (frequência inversa nos documentos), a repetição de uma palavra ajuda cada vez menos e trechos muito longos são penalizados. Não precisa de modelo nem de API, roda offline e é fácil de explicar.

O ponto fraco é o **vocabulário**: se a pergunta diz "onde ele trabalha" e o texto diz "trabalha atualmente", a flexão atrapalha; se diz "publicado" e o texto diz "no ar", não há palavra em comum. Dois remédios baratos: cortar as palavras num prefixo comum (*stemming* simples) e escrever o conteúdo com os termos que as pessoas usam.

## Busca semântica: embeddings

Um modelo de embeddings transforma o texto em um vetor; trechos de sentido parecido ficam próximos, mesmo sem palavras em comum. A busca vira "achar os vetores mais próximos" (similaridade do cosseno), geralmente num banco vetorial.

O ponto fraco é o inverso: nomes próprios, siglas e termos exatos podem se perder, e a qualidade depende do modelo, **inclusive do idioma** para o qual ele foi treinado.

## Combinar: Reciprocal Rank Fusion

Cosseno e BM25 têm escalas diferentes, então somar as notas não faz sentido. O RRF usa só a **posição** de cada trecho em cada lista:

```
nota(trecho) = soma, sobre cada lista, de  peso / (k + posição)
```

com `k` em torno de 60 (veja o [resumo do paper](@root/estudos/paper-reciprocal-rank-fusion.html)). Quem aparece bem posicionado em várias listas sobe. Dá para dar um peso a cada lista.

## O que medi

- No [chat do portfólio](@root/portfolio/chat-do-portfolio/index.html), com 49 trechos, BM25 e embeddings empataram no que importa (o trecho certo entre os 5 enviados ao modelo). Fiquei com o BM25, porque ele não custa nada.
- No [recomendador de filmes](@root/portfolio/recomendador-de-filmes/index.html), a melhor estratégia **dependeu do embedder**: veja [Busca híbrida: o peso do BM25 depende do embedder](@root/estudos/busca-hibrida-peso-do-bm25.html).

A regra que tiro disso: não escolha a arquitetura de busca por moda. Escreva perguntas de teste, meça o acerto e só então adicione peças.
