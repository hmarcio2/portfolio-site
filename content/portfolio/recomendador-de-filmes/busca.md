---
title: Busca e ranking
order: 3
summary: Embeddings, Qdrant, BM25, a fusão por RRF com peso, os filtros e a busca por filme de exemplo.
---

## Os dois lados da busca

**Vetorial.** Cada filme vira um vetor (título, gêneros e sinopse) e as consultas também. O Qdrant devolve os filmes de vetor mais próximo (distância do cosseno). Acha o que tem o **mesmo sentido**, ainda que sem palavras em comum: é o que resolve paráfrases ("um idoso viaja numa casa com balões" para *Up*).

**Lexical (BM25).** Pontua os filmes pelas palavras da consulta que aparecem na sinopse, dando mais peso às raras. Acha **nomes e termos exatos** (um personagem, uma sigla), onde o vetor às vezes se perde. É o BM25 do `portfolio-core`, o mesmo do chat.

## Os embedders

Escolhidos pela mesma regra do meu outro projeto de chat, na ordem:

1. **Ollama local** (`LOCAL_EMBEDDING_ENABLED=true`): `nomic-embed-text`, 768 dimensões. Grátis, mas precisa de máquina com o Ollama; é focado em inglês.
2. **Google** (com `GOOGLE_API_KEY`): `gemini-embedding-001`, multilíngue.
3. **`HashingEmbedder`**: bag-of-words e trigramas de caracteres projetados por hash em 512 dimensões. Determinístico e offline, mas **sem semântica real**: só serve de linha de base e para os testes.

`EMBEDDING_PROVIDER` (`ollama`, `google_genai`, `hash`) força um. O índice só vale para o embedder que o criou, porque a consulta precisa estar no mesmo espaço vetorial.

## Reciprocal Rank Fusion (RRF) com peso

Cosseno e BM25 têm escalas incomparáveis, então somar as notas não faz sentido. O RRF usa só a **posição** de cada filme em cada lista:

```
nota(filme) = 1 / (60 + posição_no_vetor)  +  peso_bm25 / (60 + posição_no_bm25)
```

(`k = 60`, o valor do [paper original](@root/estudos/paper-reciprocal-rank-fusion.html).) Cada lista contribui com os 30 primeiros candidatos (ou 4 vezes o número pedido, se maior), a nota é somada e os `k` melhores voltam. O **peso do BM25** é a extensão minha: o paper não trata de pesos.

### O peso ideal depende do embedder

Medido em `evaluation/` (veja [Avaliação](@root/portfolio/recomendador-de-filmes/avaliacao.html)): com o embedder multilíngue do Google, a busca **só vetorial foi a melhor** e misturar BM25 piorou; com o `nomic-embed-text` (focado em inglês) e com o hash, a híbrida com peso 1 foi a melhor. Por isso o padrão é por embedder: **0** para o Google e **1** para os demais; `PORTFOLIO_FILMES_TEXT_WEIGHT` sobrescreve. Detalhes no estudo [Busca híbrida: o peso do BM25 depende do embedder](@root/estudos/busca-hibrida-peso-do-bm25.html).

Os três modos existem na API interna: `hybrid` (padrão), `vector` e `text`. Peso 0 equivale a `vector`, e o modo `text` ignora o peso (é BM25 puro).

## Filtros

Gênero (qualquer um dos pedidos, casando por igualdade ou prefixo e sem acento), ano mínimo e máximo, nota mínima (só se o catálogo tem notas) e exclusões por id. Valem **nos dois lados**: o Qdrant aplica o filtro na busca vetorial (`must` e `must_not`), e o BM25 só pontua os filmes que passam. Os filmes já mostrados na sessão entram como exclusão, a menos que o modelo peça `include_shown`.

## Buscar parecidos com um filme (`similar`)

Quando o usuário cita um filme de exemplo, a consulta é **o próprio filme**:

- **Vetor:** o índice já guarda o embedding do filme; ele é recuperado do Qdrant e usado como consulta, **sem chamar o embedder** (mais rápido e sem custo de API).
- **Texto:** se o modo for híbrido ou lexical, a sinopse do filme é a consulta do BM25.
- **O próprio filme é excluído** do resultado.
- **Padrão: só vetorial.** Na medição com 5000 filmes, misturar o BM25 da sinopse não ajudou (recall@10 de 0,999 só com o vetor, contra 0,989 com a híbrida de peso 1), e o BM25 com a sinopse inteira como consulta é mais caro. Os números estão em [Avaliação](@root/portfolio/recomendador-de-filmes/avaliacao.html).

## Desempenho medido

Em 5000 filmes, na minha máquina:

| Operação | Tempo |
|---|---|
| Subir o app (carregar o catálogo, montar o BM25 e abrir o Qdrant) | ~11 s |
| Montar o índice vetorial na primeira vez (Ollama, `nomic-embed-text`) | ~5 min (308 s) |
| `similar` só vetorial | ~0,09 s |
| `similar` híbrido ou BM25 | ~0,3 s |

O BM25 da primeira versão levava cerca de **3,5 s** com uma sinopse inteira como consulta, porque reanalisava a consulta para cada documento. Passou a usar um índice invertido (visita só os filmes com algum termo da consulta), com o **mesmo resultado** e ~12 vezes mais rápido; há um teste que compara o resultado com a pontuação documento a documento.
