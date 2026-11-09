---
title: Arquitetura
order: 1
summary: Os componentes, o caminho de um pedido e como o código está organizado.
---

## Componentes

| Componente | Arquivo | Papel |
|---|---|---|
| Catálogo | `app/catalog.py` | Lê o CSV (amostra, CMU ou TMDB), normaliza gêneros, acha um filme pelo título e define o idioma e a atribuição de cada fonte |
| Embeddings | `app/embeddings.py` | Escolhe o embedder: Ollama local, API do Google ou um embedder de hash offline |
| Índice | `app/index.py` | Qdrant (vetorial, com filtros) mais BM25, fundidos por RRF; `search` por texto e `similar` por filme |
| Agente | `app/agent.py` | Prompt, as duas ferramentas (`search_movies`, `similar_movies`) e a adaptação ao loop de agente do `portfolio-core` |
| Guardrails | `app/guardrails.py` | Notas automáticas do trace (veja [Observabilidade](@root/portfolio/recomendador-de-filmes/observabilidade.html)) |
| API | `app/main.py` | FastAPI: `/chat` (SSE), `/info`, `/health` e a interface estática |
| Interface | `web/` | Página com o campo de pedido, exemplos, os cartões e o resumo do catálogo |
| Scripts | `scripts/` | `prepare_cmu.py` e `fetch_tmdb.py` geram o catálogo |
| Avaliação | `evaluation/` | Consultas de teste, métricas e scripts que rodam a busca e o agente |

## O caminho de um pedido

1. **Validação e limites.** Mesmos controles dos outros apps: tamanho da mensagem, taxa por cliente (10 por minuto), teto diário (300) e histórico de 12 mensagens por 30 minutos no servidor.
2. **Estado da sessão.** O app guarda os **filmes já mostrados** naquela sessão (com TTL), para "me mostre outros" não repetir.
3. **Trace.** Abre-se o trace `movie-turn`, com o embedder e o catálogo nos metadados.
4. **Loop do agente.** O prompt de sistema lista o tamanho do catálogo, as regras e os gêneros mais comuns. O modelo chama `search_movies` ou `similar_movies`; a ferramenta consulta o índice e devolve as sinopses; o modelo escreve a resposta. Há um teto de 8 passos.
5. **Eventos para a tela.** A cada passo o app envia eventos SSE: `tool` (o que o modelo chamou), `movies` (os cartões, vindos da **ferramenta**, não do texto do modelo), `delta` (o texto) e `done`.
6. **Fim.** A resposta entra no histórico; o trace recebe a resposta e as 3 notas de guardrail.

## Decisões de arquitetura

- **Cartões vêm da ferramenta, não do modelo.** Os filmes exibidos são sempre os que a busca devolveu, com os dados do catálogo. Isso torna impossível mostrar um filme inventado na tela (o texto do modelo ainda pode citar um, o que a nota `unretrieved_titles` mede).
- **Qdrant em modo local**, e não um servidor: zero infraestrutura extra na VPS e a mesma API. Serve para volumes pequenos (milhares de filmes) e só **um processo** pode abrir a pasta do índice; para escalar, basta apontar o cliente para um Qdrant em container.
- **Uma coleção por (embedder, catálogo).** O nome da coleção inclui um *fingerprint* do catálogo; trocar de embedder ou de catálogo recria o índice sozinho, e as coleções antigas são removidas. Isso evita consultar um índice com um modelo diferente do que o criou.
- **Dois motores de busca com interfaces iguais.** `search(texto)` e `similar(filme)` passam pelo mesmo funil de filtros e fusão, só mudando a consulta (texto novo ou o vetor já guardado do filme).
- **Loop genérico no `portfolio-core`.** O agente de filmes e o de planilhas usam o mesmo `run_tool_loop`; cada app só define o prompt, as ferramentas e a função que as executa.

Os detalhes da busca estão em [Busca e ranking](@root/portfolio/recomendador-de-filmes/busca.html) e do agente em [Agente e ferramentas](@root/portfolio/recomendador-de-filmes/agente.html).
