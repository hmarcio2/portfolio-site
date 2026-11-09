---
title: API e interface
order: 7
summary: As rotas, os eventos SSE (texto, ferramentas, gráfico, aviso), os códigos de erro e a página.
---

## Rotas

| Método e rota | Para quê |
|---|---|
| `POST /upload` | Envia a planilha (`multipart/form-data`, campo `file`) e cria a sessão |
| `POST /chat` | Faz uma pergunta sobre a planilha e recebe a resposta em streaming (SSE) |
| `GET /sessions/{id}/report.md` | Baixa o relatório da análise em Markdown (`analise.md`) |
| `DELETE /sessions/{id}` | Apaga a sessão e os arquivos ("Nova planilha") |
| `GET /health` | `{"status": "ok", "sessions": 0, "provider": "..."}` |
| `GET /` | A interface estática (`web/`) |

## `POST /upload`

Campo `file` com um `.csv` ou `.xlsx` (até 5 MB por padrão). Resposta:

```json
{
  "session_id": "gm2ItX1fy837jVf3FLgtCw",
  "filename": "t.csv",
  "tables": [{"name": "t", "rows": 2, "columns": [{"name": "regiao", "type": "VARCHAR"}, {"name": "vendas", "type": "BIGINT"}]}],
  "ttl_minutes": 30
}
```

| Código | Quando |
|---|---|
| 422 | Arquivo recusado (formato, tamanho, linhas, colunas, abas, vazio ou ilegível); a mensagem diz o motivo |
| 429 | Mais de 5 uploads por minuto por cliente (com `Retry-After`) |
| 503 | Muitas análises simultâneas (limite de sessões) |

## `POST /chat`

**Requisição:** `{"session_id": "...", "message": "qual região vendeu mais?"}`. O `session_id` é **obrigatório** (vem do upload).

**Erros antes do stream:** 404 (sessão inexistente ou expirada: "Envie a planilha novamente"), 422 (pergunta vazia ou maior que 1000 caracteres), 429 (taxa de 10 por minuto, ou teto diário de 300 análises).

**Resposta:** `text/event-stream`:

| Evento | Dados | Quando |
|---|---|---|
| `meta` | `{"session_id": "...", "trace_id": "..."}` | Primeiro (o `trace_id` só com o Langfuse ligado) |
| `delta` | `{"text": "..."}` | Pedaços do texto do modelo; pode haver texto antes e depois das ferramentas |
| `tool` | `{"name": "run_sql", "input": {"query": "SELECT ..."}}` | Cada chamada de ferramenta; a interface mostra um chip e a consulta ao passar o mouse |
| `chart` | `{"kind": "bar", "title": "...", "x": "regiao", "labels": [...], "datasets": [{"label": "total", "data": [...]}]}` | Quando `make_chart` desenhou algo |
| `warning` | `{"unverified": ["96.069,57"]}` | Números grandes da resposta que nenhuma consulta produziu, **antes** do `done` |
| `done` | `{"queries": 2}` | Fim normal, com o número de consultas SQL feitas |
| `error` | `{"error": "..."}` | Falha do provedor ou do agente (recusa, teto de passos, resposta cortada) |

Em falha, a pergunta é removida do histórico, para a conversa não ficar com um turno órfão.

## O relatório (`report.md`)

Um Markdown com o nome do arquivo, a data, o **esquema das tabelas** e, para cada pergunta: a pergunta, a resposta, o aviso de números não verificados (quando houver), a contagem de gráficos e **o SQL usado** em blocos de código. Termina com o aviso de que são respostas geradas por IA e que os números críticos devem ser conferidos. Por isso o relatório serve também como **trilha de auditoria** da análise.

## A interface (`web/`)

HTML, CSS e JavaScript puros, com o **Chart.js** carregado do cdnjs numa versão fixa (se não carregar, o gráfico mostra um aviso).

- **Upload por arrastar e soltar** ou por seleção, com os erros do servidor mostrados na hora.
- **Esquema das tabelas** (nome, linhas e colunas com tipos) logo depois do upload, e um aviso de privacidade: o conteúdo é enviado ao provedor do LLM e os arquivos são apagados em 30 minutos.
- **Chat com streaming**, usando `fetch` e lendo o corpo aos pedaços.
- **Chips do que o agente executou**, e a consulta SQL ao passar o mouse no chip "SQL".
- **Gráficos** de barras, linhas, dispersão e pizza, com cores adaptadas ao tema claro ou escuro.
- **Aviso de números não verificados** no balão da resposta.
- **Download do relatório** e o botão **"Nova planilha"**, que apaga a sessão no servidor.
- O texto do modelo é inserido como texto (nunca como HTML).
