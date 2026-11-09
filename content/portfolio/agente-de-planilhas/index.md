---
title: Agente analista de planilhas
date: 2026-11-01
seq: 3
category: agentes-rag
status: local
repo: https://github.com/hmarcio2/portfolio-planilhas
summary: Envie um CSV ou XLSX, pergunte em linguagem natural e receba respostas calculadas com SQL travado, gráficos e checagem de ancoragem dos números.
tags: [DuckDB, Parquet, agente ReAct, SQL seguro, avaliação]
---

## O que é

Você envia uma planilha (`.csv` ou `.xlsx`), faz perguntas em linguagem natural ("qual região vendeu mais?", "me mostre as vendas por mês") e recebe respostas **calculadas com SQL de verdade** sobre os seus dados, com a consulta que foi usada, gráficos e um relatório em Markdown para baixar.

É a versão pública do que fiz no projeto DSS, da Dhauz: planilha do usuário → Parquet → DuckDB → agente ReAct que escreve SQL. O foco do projeto não é só "perguntar à planilha", e sim **tornar isso seguro e confiável**: o modelo escreve o SQL, então o SQL é tratado como entrada não confiável, e os números da resposta são conferidos contra o que as consultas realmente devolveram.

## Como funciona

```
upload ─► validação ─► pandas ─► Parquet ─► DuckDB (em memória, TRAVADO) ◄─ run_sql
                                                      ▲                       ▲
                                     agente ReAct (LLM + tools)  ────────────┘
                                         │  describe_table · run_sql · make_chart
                                         ▼
                           SSE: delta · tool · chart · warning · done  ─► interface (Chart.js)
```

## Estado

- **Implementado e testado:** 97 testes, incluindo as tentativas de fuga do SQL e a checagem de ancoragem; avaliação com o Gemini Flash-Lite real em 10 perguntas.
- **Código publicado** no GitHub; **sem demo online ainda**. A imagem Docker foi construída e executada com as restrições de produção, e o upload passou por pandas, Parquet e DuckDB dentro do container.
- **Observabilidade:** traces e 3 notas no Langfuse; o envio foi confirmado contra um servidor local. Os traces podem conter trechos da planilha do usuário, então a captura de conteúdo vem desligada no exemplo de configuração.

## Resultados em números

| O quê | Resultado | Detalhe |
|---|---|---|
| Perguntas numéricas com gabarito calculado em pandas (8 perguntas × 3 execuções) | **23/24** corretas; a falha foi cota da API, não erro do modelo | [Avaliação](@root/portfolio/agente-de-planilhas/avaliacao.html) |
| Instrução maliciosa escondida numa célula | **3/3** não obedeceram e apontaram a tentativa | [Avaliação](@root/portfolio/agente-de-planilhas/avaliacao.html) |
| Pergunta sem resposta possível ("lucro" sem coluna de custo) | **0/3** na primeira rodada; **9/9** depois da correção do prompt e da checagem de ancoragem | [Ancoragem](@root/portfolio/agente-de-planilhas/ancoragem.html) |
| Camadas de defesa do SQL | 4, independentes, cada uma com teste de fuga | [Segurança do SQL](@root/portfolio/agente-de-planilhas/seguranca-do-sql.html) |
| Memória do container em repouso | 170 MiB (teto de 1 GiB) | [Operação](@root/portfolio/agente-de-planilhas/operacao.html) |

As amostras são pequenas e a planilha é sintética; as ressalvas estão em [Avaliação](@root/portfolio/agente-de-planilhas/avaliacao.html). O caso do número inventado virou um estudo: [O agente de SQL inventou um número](@root/estudos/agente-sql-ancoragem-de-numeros.html).

## Tecnologias

Python 3.12, FastAPI e SSE, pandas e openpyxl (leitura das planilhas), Parquet, DuckDB, o loop de agente com *tool use* do `portfolio-core`, Gemini Flash-Lite como modelo padrão, Chart.js na interface, Langfuse, Docker e GitHub Actions.
