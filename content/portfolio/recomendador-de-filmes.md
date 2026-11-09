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

## Objetivo

O usuário descreve o que quer assistir ("um suspense psicológico tipo Ilha do Medo, mas mais leve") **ou cita um filme de exemplo** ("algo como Matrix, mas mais recente") e recebe filmes de sinopse parecida, com a explicação de por que combinam. A conversa permite refinar ("mais antigo", "me mostre outros") sem repetir filmes.

## Arquitetura

```
pergunta ─► agente (LLM + tool use) ─┬─► search_movies(descrição, filtros)   "um suspense tipo..."
                                       └─► similar_movies(título, filtros)     "algo como Matrix"
                                              │
                    ┌─────────────────────────┴───────────────────────┐
                    ▼                                                 ▼
          embedding da descrição ─► Qdrant (vetorial, com filtros)   BM25 (lexical, mesmos filtros)
                    └──────────────────► Reciprocal Rank Fusion ◄─────┘
                                              │
              cartões de filmes (dados do catálogo) ─► interface    +    texto do LLM explicando
```

- **Catálogo:** CSV com título, ano, gêneros e sinopse. Duas fontes: uma **amostra de 44 filmes em português** (sinopses escritas por mim) para rodar offline e **5000 filmes em inglês do CMU Movie Summary Corpus** (sinopses da Wikipedia, licença CC BY-SA, com a atribuição exibida no app). Um script prepara o CMU: limpa a marcação da Wikipedia que sobrou, descarta sinopses curtas e, como o índice precisa de um embedding por filme, mantém os 5000 com bilheteria registrada. O IMDb não serviu: seus datasets oficiais não têm sinopse.
- **Embeddings:** Ollama local (`nomic-embed-text`) → Google (`gemini-embedding-001`) → embedder de hash offline, sem semântica real, só como linha de base e para testes.
- **Índice:** Qdrant em modo local (mesma API do servidor) com filtros por gênero, época e nota.
- **Agente com duas ferramentas.** `search_movies` busca por uma descrição que o modelo escreve; `similar_movies` recebe o título de um filme de exemplo e usa a sinopse dele como consulta (a parte vetorial reaproveita o embedding já guardado no índice; o filme nunca volta no resultado). Se o título não existe, a ferramenta sugere títulos parecidos; se há refilmagens, pede o ano. Filtros só se o usuário pedir; filmes já mostrados não se repetem.
- **Tradução da consulta:** como o catálogo é em inglês, o prompt manda o modelo escrever a consulta em inglês, traduzindo o pedido do usuário, e usar o título original ("Inception", não "A Origem"). A resposta continua no idioma do usuário. Quem traduz é o próprio modelo, sem uma chamada a mais.
- **RAG:** as sinopses recuperadas entram no contexto do modelo como resultado da ferramenta, e ele escolhe e explica as recomendações a partir delas.
- **Anti-alucinação:** os cartões vêm da ferramenta, não do texto do modelo; o prompt manda recomendar só filmes devolvidos.

## Avaliação da busca (sem LLM)

30 consultas (16 diretas, 6 por paráfrase, 8 por nome ou palavra exata), nDCG@10, medido em 2026-11-01:

| Embedder | Estratégia | todas | paráfrase |
|---|---|---|---|
| Google `gemini-embedding-001` | **só vetorial** | **0,996** | **0,981** |
| | híbrida (BM25 peso 1) | 0,954 | 0,769 |
| Ollama `nomic-embed-text` | só vetorial | 0,883 | 0,645 |
| | **híbrida (peso 1)** | **0,943** | **0,739** |

A melhor estratégia **depende do embedder**, então o peso do BM25 é configurável e o padrão é por embedder. Análise completa no estudo [Busca híbrida: o peso do BM25 depende do embedder](@root/estudos/busca-hibrida-peso-do-bm25.html), incluindo a correção de uma afirmação minha que a medição desmentiu.

## Avaliação de "parecidos com este filme" (catálogo CMU)

Sem como julgar milhares de filmes à mão, o gabarito é **a mesma franquia**: dado um filme de Toy Story, Matrix, Star Wars etc., os outros filmes da franquia devem aparecer (28 franquias escolhidas por mim, 128 consultas). Com `nomic-embed-text`, 5000 filmes:

| Estratégia | precisão@5 | recall@10 |
|---|---|---|
| **só vetorial** | **0,716** | **0,999** |
| híbrida (BM25 da sinopse, peso 0,2) | 0,712 | 0,997 |
| híbrida (peso 1) | 0,687 | 0,989 |
| só BM25 | 0,636 | 0,921 |

O vetor ganhou sozinho, então `similar_movies` usa só o vetor. Ressalvas: "mesma franquia" é um piso, não mede se os filmes de outras franquias são bons parecidos; só medi um embedder; e **a busca por descrição no catálogo grande não foi medida**, porque não há gabarito. Medir isso também revelou um problema de desempenho: o BM25 levava ~3,5 s por consulta com sinopses inteiras porque reanalisava a consulta para cada documento; com um índice invertido caiu para ~0,3 s com o mesmo resultado.

Com o Gemini Flash-Lite real, sete pedidos lidos à mão: a tradução funcionou ("um suspense psicológico com um final surpreendente" virou "a psychological thriller with a surprising twist ending"), "algo como A Origem" chamou `similar_movies` com "Inception", e o pedido "mais antigos que 2000" deu resultados fracos, porque o catálogo de 5000 filmes foi escolhido por bilheteria e não por tema. Uma execução por pedido, sem nota.

## Testes

66 testes (catálogo e fontes, embedder, índice com filtros, as duas ferramentas, preparação do CMU, loop do agente, API com SSE, métricas, tracing). Nenhum chama um LLM ou embedder real. O agente foi testado à mão com o Gemini Flash-Lite: o pedido sobre "ficção científica sobre linguagem e comunicação com alienígenas" devolveu *A Chegada* em primeiro, e o acompanhamento "mais antigos que 2010" aplicou o filtro sozinho e não repetiu filmes.

## Observabilidade

Cada pergunta gera um trace no Langfuse (quando as chaves existem) com um passo `generation` por volta do agente e uma observação `search_movies` com a descrição, os filtros e os filmes devolvidos. Três notas automáticas, heurísticas e sem bloquear nada: `no_search` (respondeu sem buscar), `empty_search` (a busca não achou nada) e `unretrieved_titles` (a resposta cita filmes do catálogo que a busca não devolveu, o sinal mais próximo de um filme inventado que dá para medir sem outro LLM). Limite: só pega títulos completos que existem no catálogo. Detalhes em [Observabilidade com Langfuse](@root/portfolio/observabilidade-langfuse.html).

## Decisões e limites

- **Qdrant local** em vez de servidor: zero infraestrutura extra na VPS; só um processo pode abrir a pasta do índice.
- **RRF** em vez de somar notas, pelo motivo explicado em [RRF (Cormack et al.)](@root/estudos/paper-reciprocal-rank-fusion.html).
- Os cartões são sempre os 6 primeiros resultados da busca, não a escolha do LLM; pode haver cartão que o texto não recomenda.
- As medições da busca por descrição valem para o catálogo pequeno em português; no catálogo CMU só a busca por filme de exemplo foi medida.
- Não há avaliação automática do texto do agente, só da busca.

## Próximos passos

- Medir a busca por descrição no catálogo grande (precisa de consultas julgadas por outra pessoa), rodar a avaliação de "parecidos" também com o embedder do Google e, se quiser notas e pôsteres, testar o script do TMDB.
- O modelo escolher quais cartões mostrar; reranking por LLM dos 20 primeiros e o custo disso.
- Validar os traces no Langfuse e montar o painel das notas.
