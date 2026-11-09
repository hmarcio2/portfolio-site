---
title: Observabilidade
order: 6
summary: O que cada pergunta registra no Langfuse, as 7 notas automáticas, o feedback do visitante, a privacidade dos dados e o que 8 conversas reais mostraram.
---

Sem `LANGFUSE_PUBLIC_KEY` e `LANGFUSE_SECRET_KEY`, **nada é enviado e nada muda**: o tracer é um no-op. Com as chaves (as do projeto Langfuse deste app), cada pergunta vira um trace. O servidor e a validação estão na [documentação de observabilidade](@root/portfolio/observabilidade-langfuse/index.html); esta página descreve o que o chat registra.

## O trace de cada turno

Um trace chamado `chat-turn`, agrupado pela **sessão** do chat (várias perguntas da mesma conversa aparecem juntas), com duas observações:

| Observação | Tipo | O que registra |
|---|---|---|
| `retrieval` | retriever | A consulta de busca, os trechos escolhidos (arquivo, título, tamanho) e quantos caracteres foram para o prompt |
| `generation` | generation | Modelo e parâmetros, **o prompt completo que o modelo viu** (sistema com os trechos mais o histórico), a resposta, os tokens (entrada, saída, cache), o tempo até o primeiro token e o `stop_reason` |

O trace também leva as fontes consultadas e a latência total. Falha do provedor vira nível `ERROR`, recusa vira `WARNING`, e se o visitante fechar a página no meio o trace é encerrado com a resposta parcial.

## As 7 notas automáticas

Calculadas em `app/guardrails.py` ao fim de cada turno, **sem chamar outro LLM** (regex e comparações). São sinais de observabilidade, **não bloqueios**: quem protege é o prompt e a API; as notas medem se isso funciona.

| Nota | Tipo | O que mede | Para que serve |
|---|---|---|---|
| `injection_suspect` | booleana | A pergunta casa com padrões de injeção ou extração de prompt (PT e EN: "ignore as instruções", "mostre seu prompt", "a partir de agora você é...", `jailbreak`...) | Ver tentativas de ataque e cruzar com as respostas |
| `pii_in_input` | booleana | A pergunta tinha e-mail, telefone, CPF/CNPJ ou cartão | Saber se visitantes colocam dado pessoal (já é mascarado antes do envio) |
| `no_context` | booleana | Nenhum trecho da base casou com a pergunta | Achar lacunas de busca |
| `unsupported_links` | numérica | Quantos links da resposta **não** estavam no contexto | Detectar link inventado (o prompt proíbe) |
| `prompt_leak_suspect` | booleana | A resposta contém trechos do prompt do sistema ("Como responder:", `<contexto>`...) | Detectar vazamento do prompt |
| `pii_in_output` | booleana | A resposta contém e-mail, telefone ou documento | Detectar dado pessoal inventado ou vazado |
| `knowledge_gap` | booleana | O assistente disse que não tinha a informação (ou nada foi recuperado) | **A lista do que falta na base de conhecimento** |

Todas são enviadas por `create_score` com o mesmo ambiente do trace e um **id determinístico** (`<trace_id>-<nome>`): reenviar atualiza em vez de duplicar. O campo `comment` de cada nota diz o que disparou, para auditar no Langfuse.

### Quando a nota não se aplica

Se o provedor falhou (não há resposta), só as notas da pergunta e da busca são gravadas (`injection_suspect`, `pii_in_input` e `no_context`); as da resposta não fazem sentido.

## Feedback do visitante

O servidor devolve o `trace_id` no evento `meta`; o widget mostra "Esta resposta ajudou?" com "Útil" e "Não ajudou", e envia para `POST /feedback`. Vira a 8ª nota, `user_feedback` (1 ou 0). As regras de segurança do endpoint (só traces da própria sessão, limite por minuto) estão em [API e widget](@root/portfolio/chat-do-portfolio/api-e-widget.html). O feedback só aparece com o tracing ligado.

## Privacidade dos dados nos traces

- **O visitante não é identificado:** sem IP e sem `user_id`; só o id aleatório da sessão.
- **Dados pessoais são mascarados antes do envio:** e-mails, CPF/CNPJ, cartões e telefones viram `[email]`, `[documento]`, `[número]` e `[telefone]` (inclusive nos campos de entrada, saída, prompt e comentários das notas).
- **`LANGFUSE_CAPTURE_CONTENT=false`** grava só métricas (tokens, latência, notas): todo texto vira "[conteúdo não registrado: N caracteres]".
- **O widget avisa** que as conversas podem ser registradas.
- **As mensagens ficam no Langfuse.** Use um projeto seu, defina a retenção e lembre da LGPD se guardar conversas de visitantes.

## Falhas do Langfuse não afetam o chat

Toda chamada ao Langfuse é protegida por `try/except` e feita em segundo plano. Os testes cobrem cliente quebrado, observação quebrada e servidor fora do ar. Medido: com o Langfuse fora do ar, o chat responde com a mesma latência, e o desligamento do app leva ~5 s para tentar enviar o que sobrou.

## O que 8 conversas reais mostraram

Capturei 8 conversas pelo pipeline real (Gemini Flash-Lite, base real): 60 notas no total, respostas em cerca de 0,8 a 1,5 s, com o primeiro token em 0,6 a 1,0 s. Houve **3 alertas, todos verdadeiros**: `knowledge_gap` em "Ele já trabalhou na Google?", `injection_suspect` no pedido de ignorar instruções e `pii_in_input` no e-mail digitado.

**Um falso positivo, corrigido com esse método.** O `knowledge_gap` disparava numa resposta correta que, no segundo parágrafo, avisava o que o assistente não sabia ("não há informações sobre salário..."). A detecção passou a olhar só o **primeiro parágrafo** (até 300 caracteres), porque o prompt manda começar pela resposta, e o caso virou teste. Mais detalhes em [o estudo sobre o que medir num chat com RAG](@root/estudos/observabilidade-de-chat-com-rag.html).

## Limites honestos

- São **heurísticas** com falsos positivos e negativos (a lista de padrões de injeção é curta de propósito).
- O feedback é só 👍/👎, sem texto livre na interface.
- O envio foi confirmado contra um Langfuse local (3 observações e 8 notas chegaram), mas **não há tráfego real** nem os painéis montados. Os painéis planejados: taxa semanal de `knowledge_gap`, de `injection_suspect` e de feedback positivo, latência p50/p95 da `generation` e tokens por dia.
