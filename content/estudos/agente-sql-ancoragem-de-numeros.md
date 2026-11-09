---
title: "O agente de SQL inventou um número: checagem de ancoragem"
date: 2026-11-01
seq: 3
category: analises
summary: Numa pergunta sem resposta possível, o modelo ofereceu uma receita sem rodar SQL. O prompt não bastou; a solução foi conferir os números contra os resultados.
tags: [agentes, alucinação, DuckDB, avaliação]
---

**Contexto:** o [agente de planilhas](@root/portfolio/agente-de-planilhas.html) recebe um CSV ou XLSX, converte para Parquet, carrega no DuckDB e deixa o modelo escrever SQL de leitura para responder. Avaliei com o Gemini Flash-Lite: 10 perguntas, cada uma com gabarito calculado em pandas.

## O que aconteceu

A pergunta "qual foi o lucro total?" não tem resposta, porque a planilha não tem coluna de custo.

- **Primeira rodada:** em 0 de 3 execuções o modelo negou corretamente. Ele trocou receita por lucro e respondeu com o valor da receita (R$ 128.158,70).
- **Depois de uma regra no prompt** (responder exatamente ao que foi perguntado e negar já na primeira frase): 3 de 3 negaram, em duas rodadas.
- **Na revisão manual** dessas respostas, uma das execuções negou e, na mesma resposta, **ofereceu uma "receita total de R$ 96.069,57" sem ter rodado SQL**. O valor real era R$ 128.158,70. A checagem automática por palavra-chave tinha aprovado.

## Por que o prompt não resolve

Pedir "não invente números" muda a probabilidade, não dá garantia. Um modelo que negou corretamente a pergunta ainda pode completar a resposta com um número plausível.

## A solução: ancoragem

Ao fim de cada resposta, `app/grounding.py` extrai os **números grandes** (≥ 1000, exceto anos e números já citados na conversa) e confere se cada um aparece em algum resultado de consulta, em qualquer notação (`1.234,56`, `1,234.56`, "128 mil"). Os que não aparecem geram um aviso na interface e no relatório exportado: "Atenção: … não aparece(m) nos resultados das consultas".

## Limites

- Prova que o número **veio de uma consulta**, não que está certo.
- Números pequenos e percentuais derivados pelo modelo não são checados, para evitar falsos alarmes.
- Um valor inventado que coincida com outro dado da planilha passa.

## Lições

1. **Leia as respostas, não só o placar.** O número inventado só apareceu na revisão manual; a checagem por palavra-chave estava errada.
2. **Transforme a falha em teste e em verificação em tempo de execução.** O caso agora reprova na avaliação e avisa o usuário.
3. Amostras pequenas: a rodada completa não foi repetida inteira depois das correções (para poupar a cota da API), e as perguntas são de resposta única em SQL. Perguntas abertas não foram avaliadas.
