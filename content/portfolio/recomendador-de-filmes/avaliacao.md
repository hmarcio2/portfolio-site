---
title: Avaliação
order: 5
summary: "Três medições: a busca por descrição (44 filmes), a busca por filme de exemplo (5000 filmes) e a leitura do agente real, com o que cada uma prova."
---

Cada medição responde a uma pergunta diferente e tem limites próprios. Nenhuma avalia o **texto** que o agente escreve.

## 1. Busca por descrição, catálogo pequeno (sem LLM)

`evaluation/run_eval.py` mede a busca sozinha, sem o agente: 30 consultas contra os 44 filmes da amostra, com os filmes relevantes julgados a partir das sinopses (ganho 2 para o filme procurado, 1 para uma resposta aceitável). Compara vetorial, BM25 e híbrida em **nDCG@10**, recall@10 e MRR.

As consultas têm três tipos:
- **16 diretas**: descrevem o filme com palavras próximas às da sinopse.
- **6 por paráfrase**: quase não repetem palavras da sinopse, onde embeddings deveriam superar o BM25.
- **8 por nome ou palavra exata** ("Totoro", "Keyser Söze"): onde o BM25 deveria ajudar.

```powershell
cd 01-recomendador-filmes
..\.venv\Scripts\python -m evaluation.run_eval --embedder hash          # offline: linha de base
..\.venv\Scripts\python -m evaluation.run_eval --embedder ollama        # com nomic-embed-text
..\.venv\Scripts\python -m evaluation.run_eval --embedder google_genai  # com GOOGLE_API_KEY (~74 chamadas de embedding)
```

**nDCG@10 por embedder** (2026-11-01; "híbrida w" = RRF com peso `w` para o BM25, o do vetor é 1):

| Embedder | Estratégia | todas | diretas | paráfrase | por nome |
|---|---|---|---|---|---|
| **Google `gemini-embedding-001`** | **só vetorial** | **0,996** | 1,000 | **0,981** | 1,000 |
| | híbrida w=0,2 | 0,965 | 1,000 | 0,824 | 1,000 |
| | híbrida w=1 | 0,954 | 1,000 | 0,769 | 1,000 |
| | só BM25 | 0,919 | 0,991 | 0,620 | 1,000 |
| **Ollama `nomic-embed-text`** | só vetorial | 0,883 | 0,914 | 0,645 | 1,000 |
| | **híbrida w=1** | **0,943** | 0,991 | **0,739** | 1,000 |
| | híbrida w=0,2 | 0,906 | 0,925 | 0,728 | 1,000 |
| | só BM25 | 0,919 | 0,991 | 0,620 | 1,000 |
| Hash (sem semântica) | híbrida w=1 | 0,906 | 0,982 | 0,577 | 1,000 |

**O que mostra**
- **A melhor estratégia depende do embedder.** Com o multilíngue do Google, o BM25 (ruim nas paráfrases) arrasta a fusão para baixo; com o `nomic-embed-text`, a híbrida é a melhor. Por isso o peso é configurável e o padrão é por embedder.
- **Uma correção minha:** uma versão anterior do README dizia que a híbrida superava cada busca isolada. A medição com o Google desmentiu isso, e corrigi a frase. Também corrigi um bug em que o modo de texto puro herdava o peso do vetor.
- **As buscas por nome empatam em 1,000 em todas as estratégias**, inclusive só vetorial: com 44 filmes, o BM25 não traz ganho mensurável nem onde deveria ajudar.

**O que não prova:** o catálogo é pequeno; as consultas foram escritas por mim **conhecendo as sinopses** (viés a favor da busca lexical); são só 6 paráfrases e 8 buscas por nome, então diferenças de poucos centésimos não são conclusivas (a de 0,98 para 0,77 nas paráfrases é grande). Com um catálogo grande, o resultado pode mudar, e **não medi a busca por descrição no catálogo de 5000 filmes**.

## 2. Busca "parecidos com este filme", catálogo de 5000 filmes (sem LLM)

Com milhares de filmes não dá para julgar relevância à mão, então `evaluation/run_similar_eval.py` usa como gabarito **a mesma franquia**: tendo um filme de Toy Story, Matrix, Star Wars etc. como referência, os outros filmes da franquia devem aparecer entre os parecidos. São **28 franquias escolhidas por mim, 128 consultas** (cada filme como referência uma vez); as franquias são agrupadas pelo início do título.

Com `nomic-embed-text`, 2026-11-01:

| Estratégia | precisão@5 | recall@10 |
|---|---|---|
| **só vetorial** | **0,716** | **0,999** |
| híbrida (BM25 da sinopse, peso 0,2) | 0,712 | 0,997 |
| híbrida (peso 1) | 0,687 | 0,989 |
| só BM25 (sinopse inteira como consulta) | 0,636 | 0,921 |

(A precisão@5 máxima possível é menor que 1 em franquias com menos de 6 filmes: compare as linhas entre si, não com 1.)

- **O vetor ganhou sozinho**, então `similar_movies` usa só o vetor por padrão, o que também é mais barato (~0,09 s por consulta, contra ~0,3 s com o BM25).
- **Ressalvas:** "mesma franquia" é um **piso**, não a medida do que importa: não diz se os filmes de *outras* franquias são bons parecidos. Ela favorece a busca lexical (as sequências repetem nomes de personagens), e **mesmo assim o vetor ganhou**. Só medi um embedder; o do Google não foi rodado neste catálogo (custaria 5000 chamadas de embedding).
- **Descoberta de desempenho:** a primeira rodada levou mais de 15 minutos porque o BM25 levava ~3,5 s por consulta com sinopses inteiras. Isso me levou ao índice invertido no `portfolio-core`.

## 3. Leitura do agente real

`evaluation/try_agent.py` roda conversas pelo agente de verdade (Gemini Flash-Lite, catálogo CMU, embeddings do Ollama) e mostra, para cada pedido, a ferramenta chamada, os filmes devolvidos e a resposta. É para **ler**, não para pontuar. Seis pedidos em português, lidos à mão:

| Pedido | O que o agente fez |
|---|---|
| "Quero algo parecido com Matrix, mas mais recente" | `similar_movies` com `The Matrix` e o filtro de ano sozinho; recomendou Transformers, Terminator Salvation e The Core |
| "Um suspense psicológico com um final surpreendente" | `search_movies` com `a psychological thriller with a surprising twist ending`; recomendou Deceived, Premonition e The Vanishing |
| "filmes de animação sobre brinquedos que ganham vida" | Consulta em inglês; trouxe os três Toy Story |
| "me mostre outros, mais antigos que 2000" | Excluiu os já mostrados e filtrou o ano; os resultados foram **fracos** (Blues Brothers 2000, Gumby), e o agente avisou que o catálogo é limitado |
| "Algo como A Origem" | `similar_movies` com `Inception` (o título original, como o prompt manda); Dreamscape, The Matrix e Paycheck |
| "Algo como Dune" | `similar_movies` com `Dune`; Stargate, Serenity e Prometheus |

A tradução funcionou. **Fraquezas vistas:** no refinamento "mais antigos que 2000" os resultados foram fracos, porque o catálogo de 5000 filmes foi escolhido por bilheteria e não por tema; as respostas citam 3 filmes e a tela mostra 6 cartões; e foi **uma execução por pedido**, sem medir variação.

## O que falta medir

- A busca por descrição no catálogo grande, que exige consultas julgadas por outra pessoa.
- A avaliação "parecidos" com o embedder do Google.
- O texto do agente (fidelidade às sinopses, escolha dos 3 filmes), por exemplo com um juiz LLM, que não existe ainda.
- A variação entre execuções do agente.

## Testes automáticos

66 testes, **nenhum chama um LLM ou embedder real**: o catálogo (fontes, idioma, busca de título, gêneros mais comuns), o índice (filtros nos dois caminhos, exclusão, reaproveitamento e recriação do índice persistente), as duas ferramentas (não repetir filmes, gênero inexistente, nota sem catálogo com notas, título ambíguo ou inexistente, o filme de exemplo nunca volta, o vetor é reaproveitado), a preparação do CMU (limpeza da marcação, filtros, limite por bilheteria), o loop do agente com um provedor roteirizado, a API (SSE, taxa, validação), as métricas de avaliação e o tracing.
