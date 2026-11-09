---
title: Observabilidade e privacidade
order: 8
summary: O trace de cada pergunta, as três notas, o que os traces guardam da planilha do usuário e por que a captura de conteúdo vem desligada.
---

Sem as chaves do Langfuse, nada é enviado. Com elas (as do projeto Langfuse **deste app**), cada pergunta vira um trace `sheet-turn`, agrupado pela sessão. O servidor está descrito na [documentação de observabilidade](@root/portfolio/observabilidade-langfuse/index.html).

## Estrutura do trace

| Observação | Tipo | O que registra |
|---|---|---|
| `sheet-turn` | span (raiz) | A pergunta, a resposta, o modelo, o **número de tabelas e de linhas**, o número do turno, as consultas e as chamadas de ferramenta, o `stop_reason` e a latência |
| `generation` (uma por passo) | generation | O prompt completo do passo, a resposta, os tokens, o tempo até o primeiro token e as ferramentas pedidas |
| `run_sql`, `describe_table`, `make_chart` | tool | Os argumentos (a consulta SQL), o **início do resultado (até 1500 caracteres)** e, se falhou, o erro (nível `ERROR`) |

A hierarquia (`sheet-turn` → `generation` e `tool`) foi conferida num Langfuse real.

## As 3 notas

Calculadas em `app/guardrails.py`, sem outro LLM; **sinais, não bloqueios**.

| Nota | Tipo | O que mede |
|---|---|---|
| `unverified_numbers` | numérica | Quantos números grandes da resposta não aparecem em nenhum resultado de consulta: a mesma [checagem de ancoragem](@root/portfolio/agente-de-planilhas/ancoragem.html) que avisa o usuário, agora como métrica (o comentário lista os números) |
| `tool_errors` | numérica | Quantas chamadas de ferramenta falharam, **mesmo que o modelo tenha se corrigido** (mede o quanto ele erra no SQL) |
| `no_query` | booleana | A resposta saiu sem **nenhuma consulta SQL bem-sucedida**: pode ser uma recusa correta ou um palpite; leia o trace |

Se o provedor falhou, nenhuma nota é gravada.

## Privacidade: leia antes de ligar

Aqui o conteúdo dos traces é **sensível por natureza**: a planilha é do visitante. O trace inclui a pergunta, a resposta e **o começo dos resultados das consultas**, ou seja, **trechos da planilha**.

| Cuidado | O que é feito |
|---|---|
| **Nome do arquivo** | Não vai: o trace leva só o número de tabelas e de linhas (o nome pode ter dado pessoal, como `folha-joao-silva.xlsx`) |
| **Dados pessoais no texto** | E-mails, CPF/CNPJ, cartões e telefones são mascarados antes do envio; o **resto dos dados não** |
| **Resultados** | Cortados em 1500 caracteres por ferramenta |
| **Visitante** | Não é identificado: sem IP e sem `user_id`; só o id aleatório da sessão |
| **Padrão do exemplo de configuração** | **`LANGFUSE_CAPTURE_CONTENT=false`**: só tokens, latência e notas, **sem textos** |

Com `true`, os trechos da planilha ficam no Langfuse: defina a **retenção** do projeto e avise os usuários. O motivo de o padrão ser `false`: a utilidade dos traces (ver o prompt completo de um erro) não compensa guardar dados de terceiros por padrão. Para depurar um caso, dá para ligar temporariamente com amostragem baixa (`LANGFUSE_SAMPLE_RATE`).

## Estado da validação

Testado com um tracer falso e com o SDK real em memória, e o envio foi **confirmado contra um Langfuse 4.72.0 local** (`evaluation/langfuse_smoke.py`: uma planilha de exemplo, uma consulta SQL de verdade no DuckDB; chegaram `sheet-turn`, as duas `generation`, `run_sql` e as 3 notas). **Sem tráfego real** e sem painéis. Painéis úteis: a taxa de `unverified_numbers` e de `tool_errors` por modelo, para comparar modelos.
