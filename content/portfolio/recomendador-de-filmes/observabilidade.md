---
title: Observabilidade
order: 7
summary: O trace de cada pedido no Langfuse e as três notas que medem buscas vazias, ausência de busca e filmes citados que a busca não devolveu.
---

Sem as chaves do Langfuse, o tracer é um no-op e nada é enviado. Com elas (use as do **projeto Langfuse deste app**: uma por app isola os dados), cada pedido vira um trace `movie-turn`, agrupado pela sessão. O servidor está descrito na [documentação de observabilidade](@root/portfolio/observabilidade-langfuse/index.html).

## Estrutura do trace

| Observação | Tipo | O que registra |
|---|---|---|
| `movie-turn` | span (raiz) | O pedido, a resposta, o embedder, o catálogo, o número do turno, o número de buscas e as consultas feitas |
| `generation` (uma por passo do agente) | generation | O prompt completo daquele passo, a resposta, os tokens, o tempo até o primeiro token, o `stop_reason` e as ferramentas pedidas |
| `search_movies` ou `similar_movies` | tool | Os argumentos que o modelo escolheu, o resultado (cortado em 1500 caracteres) e os títulos devolvidos |

A hierarquia é `movie-turn` → `generation` e `tool`. A estrutura foi conferida **num Langfuse real** (os filhos aparecem sob a raiz, com tokens e ambiente corretos). O `trace_id` vai no evento `meta` do stream, para uma futura tela de feedback.

## As 3 notas

Calculadas em `app/guardrails.py`, sem outro LLM, e gravadas por `create_score`. São sinais, **não bloqueios**; o `comment` diz o que disparou.

| Nota | Tipo | O que mede |
|---|---|---|
| `no_search` | booleana | O agente respondeu sem chamar nenhuma ferramenta de busca |
| `empty_search` | booleana | Alguma busca não devolveu filme nenhum (o comentário traz a consulta) |
| `unretrieved_titles` | numérica | Quantos filmes **do catálogo** a resposta cita que a busca não devolveu, e que também não estavam já na sessão nem na pergunta |

### `unretrieved_titles`: o sinal mais próximo de um filme inventado

É a nota mais útil e a mais delicada. A ideia: se a resposta diz "veja Interstellar" e a busca desta conversa nunca devolveu esse filme, o modelo recomendou de memória, fora do contexto. Como funciona:

1. Procura na resposta os **títulos do catálogo**, como palavras inteiras, ignorando acento e pontuação, **mas respeitando as maiúsculas** (muitos títulos são palavras comuns: `Alien`, `Speed`, `Crash`; só contam quando escritos como no catálogo).
2. Ignora títulos de menos de 5 caracteres (`Up`, `Ela`), que dariam falsos positivos em qualquer frase.
3. Desconta os filmes que já foram mostrados na sessão e os que o usuário citou.

**Limites:** só detecta filmes que **existem no catálogo**; um título inventado, ou um filme real que não está nos 5000, passa. Títulos citados por apelido ou muito curtos também passam. É uma medida de que o modelo saiu do contexto, não uma prova de erro: um filme do catálogo pode ser citado corretamente por conhecimento do modelo.

Se o provedor falhou, nenhuma nota é gravada.

## Privacidade

As mensagens de visitantes podem conter dados pessoais; e-mails, CPF e telefones são mascarados antes do envio ao Langfuse, e `LANGFUSE_CAPTURE_CONTENT=false` grava só métricas. O visitante não é identificado. Como o conteúdo das conversas de filmes é pouco sensível, o exemplo de configuração deixa a captura ligada; avalie conforme o seu caso.

## Estado da validação

Testado com um tracer falso e com o SDK real em memória, e o envio foi **confirmado contra um Langfuse 4.72.0 local** (teste de fumaça `evaluation/langfuse_smoke.py`: chegaram a observação raiz, as duas `generation`, a ferramenta e as 3 notas). Ainda **sem tráfego real** e sem painéis montados. Sugestão de painéis: taxa de `empty_search` (o catálogo não cobre o que se pede) e de `unretrieved_titles` (o modelo fala de filmes fora do contexto).
