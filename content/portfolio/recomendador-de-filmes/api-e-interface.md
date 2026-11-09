---
title: API e interface
order: 6
summary: As rotas, os eventos SSE (incluindo os cartões) e como a página usa tudo isso.
---

## Rotas

| Método e rota | Para quê |
|---|---|
| `POST /chat` | Envia o pedido e recebe a conversa em streaming (SSE), com os cartões de filmes |
| `GET /info` | Resumo do catálogo: nº de filmes, fonte, atribuição, embedder e gêneros |
| `GET /health` | `{"status": "ok", "movies": 44, "provider": "..."}`; usado pelo `HEALTHCHECK` do Docker |
| `GET /` | A interface estática (`web/`) |

## `POST /chat`

**Requisição** (JSON): `{"message": "...", "session_id": "opcional"}`. Mesmas validações dos outros apps: 1 a 1000 caracteres (422 se fora), taxa por minuto e teto diário (429, com `Retry-After` na taxa).

**Resposta** (`text/event-stream`), eventos nesta ordem típica:

| Evento | Dados | Quando |
|---|---|---|
| `meta` | `{"session_id": "...", "trace_id": "..."}` | Sempre primeiro (o `trace_id` só com o Langfuse ligado) |
| `tool` | `{"name": "search_movies" \| "similar_movies", "input": {...}}` | Cada vez que o modelo chama uma ferramenta |
| `movies` | `{"movies": [ {id, title, year, genres, overview, rating, votes, poster_url} ], "reference": {"title", "year"}}` | Depois de cada busca com resultado; `reference` só nos "parecidos com" |
| `delta` | `{"text": "..."}` | Pedaços do texto do modelo; pode haver texto antes e depois das ferramentas |
| `done` | `{"searches": 1}` | Fim normal, com o número de buscas feitas |
| `error` | `{"error": "..."}` | Falha do provedor, recusa, ou estouro do teto de passos |

Exemplo (abreviado), para "algo parecido com Matrix":

```
event: meta
data: {"session_id": "..."}

event: tool
data: {"name": "similar_movies", "input": {"title": "The Matrix", "year_min": 2000}}

event: movies
data: {"movies": [{"title": "The Matrix Reloaded", "year": 2003, ...}], "reference": {"title": "The Matrix", "year": 1999}}

event: delta
data: {"text": "Aqui estão algumas opções..."}

event: done
data: {"searches": 1}
```

## `GET /info`

Alimenta o rodapé da página: `{"movies": 5000, "source": "cmu", "attribution": "Sinopses e metadados: CMU Movie Summary Corpus (...)", "embedder": "ollama-nomic-embed-text", "genres": [...]}`. A página mostra a atribuição exigida pela licença do catálogo.

## A interface (`web/`)

HTML, CSS e JavaScript puros (com os estilos de base copiados do site), sem framework nem etapa de build.

- **Campo de pedido** e **quatro exemplos** clicáveis (por exemplo, "Um suspense psicológico tipo Ilha do Medo, mas mais leve" e "Algo parecido com Matrix, mas mais recente").
- **Streaming de verdade:** usa `fetch` com `POST` e lê o corpo aos pedaços; o texto do modelo aparece enquanto é gerado.
- **Chips de passos:** "buscando filmes" ou "buscando filmes parecidos", cada um com a consulta (ou o título de exemplo) como dica ao passar o mouse.
- **Cartões** com título, ano, gêneros, a nota (quando o catálogo tem) e a sinopse cortada em 300 caracteres; o **pôster** só aparece se o catálogo tiver `poster_url` (TMDB). Nos "parecidos com", uma linha "Parecidos com *The Matrix* (1999)" abre o grupo de cartões.
- **Conversa contínua:** a página guarda o `session_id` e manda a pergunta atual; o histórico fica no servidor.
- **Segurança do texto:** o texto do modelo é inserido como texto (`textContent`), nunca como HTML.
- **Rodapé** com o catálogo usado ("Catálogo: 5000 filmes (cmu)") e a atribuição, vindos de `/info`.

O texto do assistente aparece como texto simples: um `**negrito**` do modelo é mostrado com os asteriscos, porque esta página (ao contrário do chat do portfólio) não tem renderizador de Markdown. É um defeito conhecido e simples de corrigir.
