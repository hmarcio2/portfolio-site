---
title: RAG e busca
order: 2
summary: Como a base de conhecimento vira trechos, como a busca BM25 acha o que importa e por que não usei embeddings.
---

## A base de conhecimento

Quatro arquivos Markdown em `knowledge/` (cerca de 30 KB no total, 54 trechos):

| Arquivo | Conteúdo |
|---|---|
| `perfil.md` | Perfil, formação, experiência atual, projeto DSS, habilidades, docência e hobbies (em português) |
| `profile.en.md` | O mesmo perfil em inglês, para perguntas em inglês |
| `portfolio.md` | Como este portfólio e o chat foram feitos, e o **estado real** de cada projeto |
| `projetos.md` | Uma cópia do catálogo de projetos (`PROJETOS.md` do repositório do site) |

Algumas regras de manutenção, todas com teste:
- **Sem e-mail nem telefone.** O contato indicado é só o LinkedIn; um teste falha se aparecer endereço ou número na base.
- **O catálogo não pode negar o que existe**: um teste falha se o `projetos.md` disser que "nada foi implementado".
- **Comentários HTML (`<!-- -->`) não são indexados**: servem de nota para quem mantém a base.

## Da base aos trechos

O Markdown é dividido por títulos (`#`, `##` e `###`): cada seção vira um trecho, rotulado com o arquivo e o título. Seções com mais de **1000 caracteres** são divididas de novo, primeiro por parágrafos, depois por linhas e, se ainda for grande (um parágrafo corrido), por frase e, em último caso, por palavra. O limite curto deixa o prompt enxuto e a busca mais precisa. (A divisão por frase nasceu de um teste que falhou com um parágrafo longo de uma linha só.)

## A busca: BM25 com radical

O motor é um BM25 em Python puro (no `portfolio-core`), sem banco vetorial:

- **Tokenização:** minúsculas, sem acentos, só letras e números, sem *stopwords* de português e inglês e sem tokens de um caractere.
- **Título em dobro:** cada trecho é indexado como `título + título + texto`, porque as perguntas costumam citar o assunto da seção.
- **Radical por truncamento (6 letras):** "trabalha", "trabalhou" e "trabalho" viram `trabal`. É a forma mais barata de lidar com a morfologia do português. Erra por colisão (palavras diferentes com o mesmo começo) e não resolve sinônimos.
- **Índice invertido:** a busca só visita os documentos que contêm algum termo da consulta, com o mesmo resultado de pontuar todos.

### Consulta de busca

A busca usa a **última pergunta do visitante**. Se ela tiver menos de 4 termos ("e quais tecnologias ele usou?"), junta-se a pergunta anterior: `"Fale do projeto DSS e quais tecnologias ele usou?"`. É o que faz uma pergunta de acompanhamento funcionar sem reescrever a consulta com outro LLM.

### O que vai para o prompt

Até **5 trechos**, parando antes de passar de **5000 caracteres** no total. Cada trecho entra como `[arquivo · título]` seguido do texto, dentro de `<contexto>`. Se nada casou, o prompt diz "(nenhum trecho relevante encontrado)", e o modelo é instruído a admitir que não tem a informação.

## Por que BM25 e não embeddings

Medi antes de decidir (`evaluation/run_retrieval.py`). A métrica é o **acerto@5**: algum trecho esperado está entre os 5 enviados ao modelo. É a que importa, porque o app envia 5 trechos.

| Estratégia | acerto@1 | acerto@3 | acerto@5 | MRR |
|---|---|---|---|---|
| BM25 (antes de ajustar o conteúdo) | 0,66 | 0,91 | 0,97 | 0,79 |
| Embeddings (`nomic-embed-text`) | 0,60 | 0,86 | 0,97 | 0,72 |
| Híbrida (RRF) | 0,77 | 0,91 | 1,00 | 0,86 |
| **BM25 (depois de ajustar o conteúdo)** | 0,69 | 0,94 | **1,00** | 0,82 |

(Medido em 2026-11-01 com 49 trechos e 35 perguntas em 5 grupos; hoje são 54 trechos e 41 perguntas, com o grupo de morfologia.)

- BM25 e embeddings **empatam** no que importa (0,97). A híbrida só melhora a *ordem* dos trechos (o MRR), e a ordem dentro dos 5 enviados, em geral, não muda a resposta do modelo (não medi isso).
- A única falha do BM25 foi de vocabulário: a pergunta dizia "está no ar" e o texto dizia "publicado". Foi corrigida no **conteúdo** (escrevendo os dois termos), não com mais infraestrutura.
- Para 54 trechos, o BM25 não custa nada, não depende de API nem de banco e roda offline.

### O caso da morfologia

Um caso real: a pergunta "Onde ele trabalha?" não recuperava nenhum trecho útil. O BM25 de palavras inteiras não ligava "trabalha" às outras formas do verbo, e a base não usava essa palavra. Resolvi com o radical de 6 letras e acrescentando ao conteúdo frases do tipo "trabalha atualmente na Dhauz": o acerto@5 do grupo de morfologia foi de **0,17 para 1,00**.

**Ressalva importante:** os casos de morfologia foram escritos *depois* de eu ver a falha, então esse 1,00 é otimista. O mesmo vale para o ajuste do conteúdo. Há um teste de regressão (`test_bm25_retrieval_quality_does_not_regress`) que trava a qualidade atual, mas não prova que perguntas novas, parafraseadas ou em outros idiomas vão achar o trecho certo.

## Quando a escolha deixa de valer

- Com centenas de trechos, a busca lexical tende a perder para a semântica em perguntas parafraseadas; aí a opção é a [busca híbrida](@root/portfolio/recomendador-de-filmes/busca.html) que uso no recomendador de filmes.
- Perguntas em outros idiomas além de português e inglês caem na busca lexical e podem não achar nada (o que a nota `no_context` registra).
