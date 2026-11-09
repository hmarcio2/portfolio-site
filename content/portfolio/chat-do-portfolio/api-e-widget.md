---
title: API e widget
order: 4
summary: Rotas, formato dos eventos SSE, códigos de erro e como o widget do navegador usa tudo isso.
---

## Rotas

| Método e rota | Para quê |
|---|---|
| `POST /chat` | Envia uma pergunta e recebe a resposta em streaming (SSE) |
| `POST /feedback` | Registra "útil" ou "não ajudou" para uma resposta, como nota do trace |
| `GET /health` | Estado: `{"status": "ok", "chunks": 54, "provider": "LangChainProvider"}`; usado pelo `HEALTHCHECK` do Docker |

Em produção, o Caddy expõe o app em `/api/chat/*` do domínio do site (o widget chama `/api/chat/chat`); em desenvolvimento, o widget fala direto com `http://localhost:8000`.

## `POST /chat`

**Requisição** (JSON):

```json
{ "message": "Quais tecnologias o Heriberto usou no projeto DSS?", "session_id": "opcional" }
```

`message` tem de 1 a 1000 caracteres (o modelo de validação aceita até 4000, mas o app corta em 1000 por configuração). Sem `session_id`, o servidor cria um e devolve no primeiro evento.

**Resposta:** `text/event-stream`, com os eventos abaixo, nesta ordem:

| Evento | Dados | Quando |
|---|---|---|
| `meta` | `{"session_id": "...", "trace_id": "..."}` | Sempre primeiro. O `trace_id` só existe com o Langfuse ligado |
| `sources` | `{"sources": ["Experiência atual: Dhauz", ...]}` | Se algum trecho foi recuperado; são os títulos das seções consultadas |
| `delta` | `{"text": "..."}` | Zero ou mais, com os pedaços da resposta |
| `done` | `{}` | Fim normal |
| `error` | `{"error": "..."}` | Falha do provedor ou recusa; no lugar de `done` |

Exemplo (abreviado):

```
event: meta
data: {"session_id": "HzJG_-CMUQUeklVHpQtM1g"}

event: sources
data: {"sources": ["Experiência atual: Dhauz (hoje parte da Quantum Rise)", "Perfil"]}

event: delta
data: {"text": "O Heriberto trabalha na "}

event: done
data: {}
```

**Erros antes do stream** (JSON com `{"error": "..."}`):

| Código | Quando |
|---|---|
| 422 | Mensagem vazia ou maior que o limite |
| 429 | Taxa por minuto excedida (com `Retry-After`) ou teto diário global atingido |

**Falhas durante o stream** viram um evento `error` (HTTP 200 já enviado): "Não consegui responder agora. Tente novamente em instantes." para falha do provedor, e "Não posso ajudar com esse pedido." para recusa do modelo. Nos dois casos a pergunta é removida do histórico, para a conversa não ficar com um turno órfão.

## `POST /feedback`

```json
{ "session_id": "...", "trace_id": "<32 hex>", "helpful": true, "comment": "opcional, até 500 caracteres" }
```

- Só aceita um `trace_id` que **o próprio servidor emitiu para aquela sessão** (guardado por `IssuedTraces`, com o mesmo TTL das sessões). Isso impede gravar notas em conversas de outras pessoas, mesmo que alguém descubra um `trace_id`. Se não bate, responde 404.
- Limite de 20 por minuto por cliente.
- Mudar de ideia atualiza a nota: o id da nota é determinístico (`<trace_id>-user_feedback`).
- Sem Langfuse não há para onde gravar, então o widget nem mostra os botões (o `trace_id` não vem no `meta`).

## O widget (`assets/chat.js`)

JavaScript puro, sem dependências, injetado em todas as páginas do site pelo mesmo template. O que ele faz:

- **Streaming de verdade.** Como `EventSource` só faz GET, o widget usa `fetch` com `POST` e lê o corpo (`ReadableStream`), separando os eventos por linha em branco.
- **Markdown seguro.** Renderiza só `**negrito**`, `` `código` ``, listas com `-` e links `http(s)`, **criando nós DOM** (`createElement`/`textContent`), nunca `innerHTML`. Isso elimina a classe de ataque em que a resposta do modelo (ou um trecho da base) injetaria HTML ou script na página.
- **Conversa persistente na aba.** Guarda o `session_id` e as últimas 30 mensagens em `sessionStorage` (chave `portfolio-chat-v1`): navegar entre as páginas do site não perde a conversa. Fechar a aba perde. Se o servidor tiver reiniciado, o texto aparece, mas o servidor não tem mais o contexto.
- **Sugestões de perguntas** na primeira abertura e **"Nova conversa"** para recomeçar.
- **"Tentar de novo"** nas falhas, que repete a última pergunta.
- **Feedback** ("Útil" / "Não ajudou") sob cada resposta, quando há `trace_id`.
- **Acessibilidade básica:** painel com `role="dialog"` e `aria-label`, `aria-live` no log, foco no campo ao abrir, `Esc` fecha, `aria-busy` durante a resposta.
- **Endereço da API automático:** `http://localhost:8000/chat` em `localhost`/`127.0.0.1` ou ao abrir o HTML direto do disco (`file://`); `/api/chat/chat` nos demais casos. Dá para sobrescrever com `window.PORTFOLIO_CONFIG.chatUrl`.
- **Mensagem de erro útil em desenvolvimento:** se a API local não estiver no ar, o widget diz qual endereço tentou e aponta o `dev.ps1`.

Abrir o site direto do disco (`file://`) manda `Origin: null`; por isso o `dev.ps1` libera `null` no CORS **só em desenvolvimento**. Isso não deve ser usado em produção.
