---
title: "ReAct (Yao et al.): raciocínio e ação intercalados"
date: 2026-11-01
seq: 5
category: papers
summary: Resumo do paper que originou o padrão de agente em que o modelo alterna pensar e usar ferramentas, base dos agentes dos meus projetos.
tags: [agentes, ReAct, tool use, paper]
---

**Referência:** Shunyu Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models* (ICLR 2023, arXiv:2210.03629).

## A ideia

Antes do ReAct, havia duas linhas separadas: pedir ao modelo que *raciocine* passo a passo (chain-of-thought) e pedir que *aja* (chamar buscas, ferramentas, ambientes). O paper propõe **intercalar as duas coisas** no mesmo texto gerado:

```
Pensamento: preciso saber o total por região.
Ação: run_sql("SELECT regiao, SUM(valor) ...")
Observação: [resultado da consulta]
Pensamento: a região Sul lidera; posso responder.
Resposta: ...
```

O raciocínio ajuda a planejar e a tratar exceções ("a consulta falhou, vou corrigir"); a ação traz informação externa que o modelo não tem, o que reduz respostas inventadas.

## O que os autores mostram

Em tarefas de perguntas e respostas com busca, verificação de fatos e ambientes interativos de texto, o ReAct se compara favoravelmente a só raciocinar ou só agir, e as trajetórias ficam mais fáceis de ler e auditar. (Não reproduzo números do paper aqui; consulte o original.)

## Como aparece nos meus projetos

- No [agente de planilhas](@root/portfolio/agente-de-planilhas.html) e no [recomendador de filmes](@root/portfolio/recomendador-de-filmes.html), o loop é o ReAct em sua forma moderna: o modelo recebe a descrição das ferramentas por **tool use** da API (em vez de texto livre "Ação:"), executa, recebe a observação e decide o próximo passo, com teto de passos.
- O erro de uma ferramenta volta ao modelo como observação (`is_error`), para ele se corrigir. É o "tratar exceções" do paper.

## Limites a lembrar

O raciocínio visível **não garante** que a resposta final esteja fundamentada: foi o que vi no [agente de SQL que inventou um número](@root/estudos/agente-sql-ancoragem-de-numeros.html). Por isso conferir a saída contra as observações é uma etapa à parte.
