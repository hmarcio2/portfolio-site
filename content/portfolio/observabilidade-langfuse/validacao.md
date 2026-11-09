---
title: Validação e problemas encontrados
order: 6
summary: Como o servidor e a instrumentação foram testados de verdade, os dois defeitos que só apareceram ao subir, e as evidências.
---

## As camadas de validação

| Camada | O que prova | O que **não** prova |
|---|---|---|
| Testes automáticos com um tracer falso | A estrutura que o app monta (nomes, ordem, notas, falhas) | Que o SDK a entenda |
| Testes com o SDK real e exportador **em memória** | O que o SDK produz (tipos, sessão, tokens, mascaramento) | Que o **servidor** aceite |
| **Teste de fumaça contra um servidor real** | Que as observações e as notas chegam e ficam corretas | Tráfego real, carga, VPS |
| Evidências estáticas (visualizador de traces) | Como o trace se parece, sem precisar de servidor | Nada sobre o servidor |

A terceira camada é a que pegou os dois defeitos abaixo: **nenhuma das duas primeiras os via**.

## O teste de fumaça

Cada app tem `evaluation/langfuse_smoke.py`: manda **um** trace de teste pelo **pipeline real** do app, com um provedor roteirizado (sem LLM e sem custo), no ambiente `portfolio-smoke`, e depois **lê de volta do servidor** para conferir.

| App | O que o teste exercita | O que confere |
|---|---|---|
| Chat | A pergunta, a busca e as 7 notas, mais um feedback pelo `/feedback` | 3 observações (`chat-turn`, `retrieval`, `generation`) e as **8 notas** |
| Recomendador | Uma busca de verdade no índice (embedder de hash) | `movie-turn`, 2 `generation`, `search_movies` e as **3 notas** |
| Analista de planilhas | Upload de uma planilha e **uma consulta SQL de verdade** no DuckDB | `sheet-turn`, 2 `generation`, `run_sql` e as **3 notas** |

Resultado (2026-11-01, Langfuse 4.72.0 local, SDK 5.1.0): **os três passaram**. Conferi também, pela API do servidor, a **hierarquia** (as `generation` e as `tool` são filhas da observação raiz), os tokens e o ambiente.

## Defeito 1: os traces chegavam, as notas não

O teste mostrou as 3 observações no servidor, mas nenhuma das 8 notas. O SDK avisava só "Bad request". No log do **servidor**: um `ZodError` ("expected object, received array").

- **Causa:** o SDK 5.1 envia as notas em **lote** (um array em `POST /api/public/scores`). A imagem `langfuse:4` que o Docker tinha em cache era a **4.30.0**, de oito semanas antes, e só aceitava uma nota por vez. A tag `:4` não é uma versão: o Docker reaproveita o que já está na máquina.
- **Correção:** `docker compose pull` (veio a **4.72.0**) e as notas passaram a chegar.
- **Regra:** o servidor precisa ser tão novo quanto o SDK. O deploy da VPS já faz o `pull`; localmente, rode você.

## Defeito 2: o healthcheck ficava `unhealthy` para sempre

Com a imagem nova, o serviço respondia na porta publicada, mas o Docker o marcava como `unhealthy`. O healthcheck chama `127.0.0.1:3000` **por dentro** do container, e a chamada falhava.

- **Causa:** o Next.js escuta no endereço do `HOSTNAME` do container, que o Docker define como o id do container; então ele só atendia no IP da rede, não no loopback. A imagem antiga não tinha esse comportamento.
- **Correção:** `HOSTNAME: 0.0.0.0` no `langfuse-web`, mais um teste que trava a configuração.

O relato completo, com o raciocínio, está no estudo [Langfuse: o servidor precisa ser tão novo quanto o SDK](@root/estudos/langfuse-sdk-e-servidor.html).

## Uma observação sobre a API de leitura

Nesta versão (modo "v4 *events only*"), os endpoints antigos de leitura `GET /api/public/traces` e `/scores` respondem "not available". A leitura vai pelo SDK (`client.api.scores.get_many`, `client.api.observations.get_many`) ou por `GET /api/public/v2/observations`, que é o que os testes de fumaça usam.

## As conversas de exemplo

`evaluation/seed_langfuse.py` (no chat) envia as 7 conversas de exemplo pelo chat real (Gemini Flash-Lite) para o ambiente `portfolio-demo` do servidor. Conferido pela API: **8 traces e 60 notas** (3 `user_feedback`, 2 `knowledge_gap`, 1 `injection_suspect`, 1 `pii_in_input`), os mesmos números do visualizador estático.

O passo a passo para tirar **prints da interface** está no repositório do chat (`docs/observabilidade/README.md`). Eu não faço login na interface por você, e os prints **ainda não foram tirados**.

## O visualizador estático

`docs/observabilidade/trace-viewer.html`, no repositório do chat, abre direto no navegador, sem servidor: lista de traces, linha do tempo (busca e geração, com o primeiro token), tokens, entrada e saída, e as notas. É gerado por `python -m evaluation.capture_traces`, que roda 8 conversas pelo chat real com o SDK do Langfuse ligado a um exportador em memória. **Não é uma captura da interface do Langfuse**: mostra o que o servidor receberia.

## O que ainda não foi validado

- **Tráfego real:** só traces de teste e conversas de exemplo.
- **Painéis do Langfuse:** não montados.
- **Memória sob carga:** os tetos são configuração, não medição (`docker stats` sob carga).
- **O modo VPS:** Caddy, HTTPS e a rede `edge`.
- **Backup e restauração.**
