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

## Objetivo

A versão pública do que fiz no projeto DSS: planilha do usuário → Parquet → DuckDB → agente ReAct que responde com SQL. O visitante envia um arquivo, pergunta, e recebe respostas com a consulta usada, gráficos e um relatório exportável.

## Arquitetura

```
upload ─► validação ─► pandas ─► Parquet ─► DuckDB (em memória, TRAVADO) ◄─ run_sql
                                                       ▲                       ▲
                                      agente ReAct (LLM + tools)   ───────────┘
                                          │  describe_table · run_sql · make_chart
                                          ▼
                            SSE: delta · tool · chart · done  ─► interface (Chart.js)
```

- **Upload:** só `.csv`/`.xlsx`, com limites de tamanho, linhas, colunas e abas; checagem de "zip bomb" no xlsx; nomes de tabelas e colunas normalizados; datas viram `TIMESTAMP`.
- **Agente:** loop ReAct manual sobre tool use (veja o [resumo do ReAct](@root/estudos/paper-react.html)). Erros de SQL voltam ao modelo como `is_error` para ele se corrigir; teto de 8 passos.
- **Interface:** esquema das tabelas, chips do que o agente executou, gráficos e download do relatório `.md`.

## Segurança do SQL

O modelo escreve o SQL, então ele é tratado como entrada **não confiável**. Quatro camadas independentes:

| Camada | O que bloqueia |
|---|---|
| Parser do DuckDB | mais de uma instrução; qualquer coisa que não seja `SELECT`/`WITH … SELECT` |
| DuckDB travado após a carga | sem acesso externo (`read_csv('arquivo')`, rede), sem autoload de extensões, configuração travada |
| Recursos | timeout de 10 s, limite de memória de 512 MB, poucas linhas devolvidas ao modelo |
| Dados | conteúdo de células declarado "dado, não instrução" no prompt |

Os testes tentam cada uma dessas fugas e verificam que os dados continuam intactos.

## Avaliação com o Gemini Flash-Lite

10 perguntas × 3 execuções, com gabarito calculado em pandas sobre uma planilha sintética (600 vendas):

| Grupo | Resultado |
|---|---|
| 8 perguntas numéricas | **23/24** corretas; a falha foi cota da API (429), não erro do modelo |
| Injeção de prompt escondida numa célula | **3/3** não obedeceram e apontaram a tentativa |
| Pergunta sem resposta possível ("lucro" sem coluna de custo) | **0/3** na 1ª rodada; depois da correção do prompt e da checagem de ancoragem, 9/9 na rodada final |

O caso do lucro levou a uma checagem em tempo de execução: leia o estudo [O agente de SQL inventou um número](@root/estudos/agente-sql-ancoragem-de-numeros.html).

**Honestamente:** a rodada completa não foi repetida inteira depois das correções, as amostras são pequenas e perguntas abertas ("quais insights você vê?") não foram avaliadas.

## Privacidade

Sem login; o `session_id` aleatório funciona como credencial. Arquivos ficam em diretório temporário (`tmpfs` no Docker) e são apagados após 30 min sem uso. **O conteúdo da planilha é enviado ao provedor do LLM**, e a interface avisa para não enviar dados sensíveis.

## Observabilidade e privacidade dos traces

Cada pergunta gera um trace no Langfuse (quando as chaves existem): um passo `generation` por volta do agente e uma observação por ferramenta (`run_sql` com a consulta e o início do resultado, e o erro quando falha). Notas automáticas: `unverified_numbers` (a checagem de ancoragem, agora como métrica), `tool_errors` e `no_query`. Como o trace pode conter **trechos da planilha do visitante**, o nome do arquivo não é enviado (só o número de tabelas e de linhas) e o exemplo de configuração deixa a captura de conteúdo desligada: só tokens, latência e notas. Ligar o conteúdo exige definir a retenção e avisar o usuário. Detalhes em [Observabilidade com Langfuse](@root/portfolio/observabilidade-langfuse.html).

## Testes

97 testes: carga de CSV/XLSX, limites, TTL, bloqueios de SQL, timeout, ferramentas, loop do agente com provedor roteirizado, API completa, limites de taxa, a checagem de ancoragem e o tracing. Nenhum chama um LLM de verdade; para isso, existe a avaliação acima.

## Limites e próximos passos

- Fórmulas do Excel chegam como o último valor salvo, sem recalcular; `.xls` e arquivos com senha não são suportados.
- Comparar com um modelo local e um maior (modelo × acertos × custo).
- Conferir os termos do plano gratuito da API do Google antes de expor a demo: uploads de visitantes não combinam com um plano que pode usar o conteúdo para melhorar produtos.
- Validar os traces no Langfuse, calcular o custo por conversa e definir a retenção.
