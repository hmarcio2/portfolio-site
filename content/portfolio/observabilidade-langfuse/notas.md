---
title: Notas automáticas (guardrails)
order: 2
summary: As 13 notas dos três apps, o raciocínio de usar heurísticas baratas, o que elas medem e o que medem mal.
---

## Por que notas, e por que heurísticas

Um trace diz **o que aconteceu**; uma **nota** (*score*) diz **se foi bom ou ruim**. Com notas, o painel do Langfuse responde perguntas como "quantas conversas tentaram injeção de prompt?" ou "em quais perguntas o assistente não sabia?", em vez de eu ler trace por trace.

As notas aqui são **heurísticas determinísticas** (regex e comparações), sem outro LLM:

| | Heurística | Juiz LLM |
|---|---|---|
| Custo | Zero | Uma chamada extra por turno |
| Latência | Desprezível | Pode atrasar ou exigir fila |
| Reprodutível | Sim | Não |
| Auditável | O `comment` diz o que disparou | Depende do juiz |
| Falsos positivos e negativos | **Muitos**, e conhecidos | Menos, mas imprevisíveis |

Escolhi heurísticas porque o objetivo é **observar tendências** e achar casos para ler, não decidir se uma resposta pode sair. Elas **nunca bloqueiam** nada: quem protege é o prompt e a API. Um juiz LLM (por exemplo, fidelidade da resposta ao contexto) é um próximo passo, comparado contra estas.

## As notas, por app

### Chat (8 notas)

| Nota | Tipo | O que mede |
|---|---|---|
| `injection_suspect` | booleana | A pergunta casa com padrões de injeção ou extração de prompt, em português e inglês |
| `pii_in_input` | booleana | A pergunta tinha e-mail, telefone, CPF/CNPJ ou cartão (já é mascarado antes do envio) |
| `no_context` | booleana | Nenhum trecho da base casou com a pergunta |
| `unsupported_links` | numérica | Links da resposta que **não** estavam no contexto (link inventado) |
| `prompt_leak_suspect` | booleana | A resposta contém trechos do prompt do sistema |
| `pii_in_output` | booleana | A resposta contém e-mail, telefone ou documento |
| `knowledge_gap` | booleana | O assistente disse que não tinha a informação (ou nada foi recuperado): **lista do que falta na base** |
| `user_feedback` | booleana | O visitante clicou "Útil" (1) ou "Não ajudou" (0) |

Detalhes e limites em [Observabilidade do chat](@root/portfolio/chat-do-portfolio/observabilidade.html).

### Recomendador de filmes (3 notas)

| Nota | Tipo | O que mede |
|---|---|---|
| `no_search` | booleana | O agente respondeu sem chamar uma ferramenta de busca |
| `empty_search` | booleana | Alguma busca não devolveu nenhum filme |
| `unretrieved_titles` | numérica | Filmes **do catálogo** citados na resposta que a busca não devolveu (sinal de filme "de memória") |

Detalhes em [Observabilidade do recomendador](@root/portfolio/recomendador-de-filmes/observabilidade.html).

### Analista de planilhas (3 notas)

| Nota | Tipo | O que mede |
|---|---|---|
| `unverified_numbers` | numérica | Números grandes da resposta que nenhuma consulta produziu |
| `tool_errors` | numérica | Chamadas de ferramenta que falharam |
| `no_query` | booleana | Resposta sem nenhuma consulta SQL bem-sucedida |

Detalhes em [Observabilidade do analista](@root/portfolio/agente-de-planilhas/observabilidade.html) e [Ancoragem dos números](@root/portfolio/agente-de-planilhas/ancoragem.html).

## O que cada tipo de nota ensina

| Pergunta de negócio | Nota | O que fazer com o resultado |
|---|---|---|
| "Estão tentando atacar o chat?" | `injection_suspect`, `prompt_leak_suspect` | Ler os casos; endurecer o prompt; ver se o vazamento aconteceu |
| "O que falta na minha base de conhecimento?" | `knowledge_gap`, `no_context` | Listar as perguntas e **escrever o conteúdo que falta** |
| "O modelo está inventando?" | `unsupported_links`, `unretrieved_titles`, `unverified_numbers` | Comparar modelos e prompts pela taxa; ler os casos |
| "A busca está falhando?" | `no_context`, `empty_search`, `no_search` | Ajustar a busca, o catálogo ou o prompt de uso das ferramentas |
| "O modelo erra o SQL?" | `tool_errors` | Medir por modelo antes de trocar o padrão |
| "As pessoas gostaram?" | `user_feedback` | Cruzar com as notas acima nos casos de 👎 |

## O que medem mal (limites honestos)

- **Padrões de injeção são uma lista curta, de propósito.** Pegam as tentativas comuns (em português e inglês) e **perdem as criativas**; e podem disparar em perguntas legítimas que citam essas frases.
- **`knowledge_gap` olha a resposta**: só o primeiro parágrafo (até 300 caracteres), porque o prompt manda começar pela resposta. Já teve um falso positivo (um aviso no segundo parágrafo), corrigido.
- **`unretrieved_titles` só vê filmes que existem no catálogo**, escritos como no catálogo; um título inventado passa. Um filme citado corretamente "de memória" também é contado.
- **`unverified_numbers` não prova que o número está certo**, só que veio de uma consulta; ignora números pequenos e anos.
- **O feedback é só 👍/👎** e só aparece com o tracing ligado.
- Nenhuma foi **validada contra um juiz humano** em escala: a validação foi ler casos reais (8 conversas do chat: 3 alertas, todos verdadeiros).

## O que 8 conversas reais mostraram

Capturei 8 conversas do chat pelo pipeline real (Gemini Flash-Lite): **60 notas e 3 alertas, todos verdadeiros** (`knowledge_gap` em "Ele já trabalhou na Google?", `injection_suspect` no pedido de ignorar instruções e `pii_in_input` num e-mail digitado). Depois reenviei as mesmas conversas a um Langfuse real, e os mesmos números voltaram (8 traces, 60 notas). É uma amostra minúscula: serve para mostrar que o mecanismo funciona, não para estimar taxas.
