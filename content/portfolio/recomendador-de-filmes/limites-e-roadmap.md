---
title: Limites e próximos passos
order: 9
summary: O que o recomendador não faz, o que não foi medido e o que vem a seguir.
---

## Limites conhecidos

**Do catálogo**
- **5000 filmes escolhidos por bilheteria**, não por tema nem qualidade: bom para filmes conhecidos, fraco em nichos (vimos isso no pedido "animações antigas sobre brinquedos").
- **Sem notas nem pôsteres** no CMU; filtro por nota só funciona com o TMDB, que **nunca foi testado**.
- **Sinopses da Wikipedia de 2012**: filmes recentes não existem, e há gêneros demais e irregulares (279).
- **Títulos em inglês**: um filme citado por um nome em português só é achado se o modelo o traduzir para o título original (e ele nem sempre sabe).

**Do agente**
- **Os cartões são os 6 primeiros resultados**, não a escolha do modelo; o texto recomenda 3. Pode haver cartão que o texto não menciona.
- **O histórico guarda só o texto**; os filmes já mostrados ficam num conjunto por sessão, com TTL.
- **Cada pedido é uma execução**: um modelo menor pode não chamar a ferramenta, escrever uma consulta pobre ou citar um filme fora do contexto (o que a nota `unretrieved_titles` mede).
- **Qdrant local:** só um processo pode abrir a pasta do índice; para escalar, aponte o cliente para um servidor Qdrant.

**De validação**
- **A busca por descrição no catálogo grande não foi medida.**
- A busca "parecidos" foi medida só com o `nomic-embed-text`, e com o gabarito "mesma franquia", que é um piso.
- **Não há avaliação automática do texto do agente.**
- A leitura do agente real foi de seis pedidos, uma execução cada.
- **Nunca rodou na VPS** nem no CI do GitHub; só o build e a execução locais em Docker.
- O índice do catálogo grande na VPS é um risco aberto (veja [Operação](@root/portfolio/recomendador-de-filmes/operacao.html)).

## Próximos passos

- [ ] Medir a busca por descrição no catálogo grande, com consultas julgadas por outra pessoa, e **re-medir o peso do BM25** nesse catálogo.
- [ ] Rodar a avaliação de "parecidos" também com o embedder do Google.
- [ ] Avaliação automática do texto do agente (fidelidade às sinopses) e o modelo **escolher quais cartões mostrar**.
- [ ] Reranking por LLM dos 20 primeiros resultados e a comparação do ganho contra o custo.
- [ ] Um catálogo com notas e pôsteres (testar o script do TMDB com uma chave) e, se fizer sentido, recortes por tema em vez de só por bilheteria.
- [ ] Resolver o índice do catálogo grande na VPS (cota de embeddings ou um catálogo menor).
- [ ] Renderizar o Markdown do modelo na interface (hoje o `**negrito**` aparece com os asteriscos).
- [ ] Validar os traces com tráfego real e montar o painel de `empty_search` e `unretrieved_titles`.

## Decisões que valem ser revistas

| Decisão | Motivo atual | Quando mudar |
|---|---|---|
| Qdrant local | Zero infraestrutura extra na VPS | Mais de um processo, ou centenas de milhares de filmes |
| `similar` só vetorial | Venceu a híbrida na medição por franquia | Se uma medição melhor (julgada por pessoas) mostrar ganho do BM25 |
| 5000 filmes por bilheteria | Cabe no Ollama em 5 minutos e no orçamento de memória | Quando houver embeddings baratos o bastante para o catálogo inteiro |
| Tradução pelo próprio agente | Sem chamada extra, funcionou nos pedidos lidos | Se erros de tradução de títulos aparecerem com frequência; aí vale um dicionário ou um passo de resolução de título |
