---
title: Operação
order: 9
summary: Como rodar, as variáveis de ambiente, o Docker medido, o deploy e os cuidados de privacidade e de cota.
---

## Rodar localmente

```bash
.venv/Scripts/python -m pip install -e "_core[langchain]" -r 02-agente-planilhas/requirements.txt pytest pytest-asyncio httpx
cd 02-agente-planilhas
../.venv/Scripts/python -m uvicorn app.main:create_app --factory --port 8002
```

Abra `http://localhost:8002`. Sem nenhuma chave, o provedor é o `echo` (não analisa nada, serve só para ver a interface). Para usar o Gemini Flash-Lite, defina `GOOGLE_API_KEY` (no terminal ou num `.env`); com `LOCAL_LLM_ENABLED=true`, o Ollama local assume se a API falhar ou estourar a cota.

## Variáveis de ambiente

As do `portfolio-core` (LLM, limites, CORS, Langfuse) são as do [chat](@root/portfolio/chat-do-portfolio/operacao.html). As deste app:

| Variável | Padrão | Efeito |
|---|---|---|
| `PORTFOLIO_SHEETS_EFFORT` | `medium` | Esforço de raciocínio do modelo (só provedores que suportam; o Gemini ignora) |
| `PORTFOLIO_SHEETS_MAX_TOKENS` | `4000` | Tamanho máximo de cada passo do agente |
| `PORTFOLIO_SHEETS_MAX_MB` | `5` | Tamanho máximo do arquivo |
| `PORTFOLIO_SHEETS_MAX_ROWS`, `_MAX_COLUMNS`, `_MAX_SHEETS` | `200000`, `100`, `5` | Limites por tabela |
| `PORTFOLIO_SHEETS_TTL_SECONDS` | `1800` | Quando a sessão e os arquivos são apagados |
| `PORTFOLIO_SHEETS_MAX_SESSIONS` | `30` | Análises simultâneas |
| `LANGFUSE_CAPTURE_CONTENT` | **`false`** no exemplo | Veja a [privacidade dos traces](@root/portfolio/agente-de-planilhas/observabilidade.html) |

## Docker

Imagem em dois estágios, usuário sem privilégios e `HEALTHCHECK` em `/health`. Como os uploads vivem em `/tmp` do container, o compose de produção monta `/tmp` como **tmpfs de 512 MB**, com o sistema de arquivos **somente leitura**: nada persiste em disco e tudo some ao reiniciar.

```bash
cp .env.example .env                      # preencha GOOGLE_API_KEY
docker compose -f compose.yml -f compose.local.yml up --build     # http://localhost:8002
```

**Medido em Docker (2026-11-08)**, com as restrições de produção (somente leitura, `cap_drop: ALL`, `no-new-privileges`, teto de 1 GiB, usuário sem privilégios): imagem de **476 MB** (a maior, por causa do pandas, DuckDB e openpyxl); `healthy`; **170 MiB em repouso**; o upload de um CSV passou por pandas, Parquet e DuckDB dentro do container (sistema de arquivos somente leitura com `/tmp` gravável). Esse teste não usou LLM real; o consumo de memória com uma planilha grande e consultas pesadas **não foi medido** (os limites do DuckDB, de 512 MB, e do container, de 1 GiB, existem para isso).

## Deploy

Mesmo fluxo dos outros apps: imagem no GHCR, SSH, `docker compose up --wait` e o trecho do Caddy em `planilhas.SEUDOMINIO` ([CI/CD e deploy](@root/portfolio/plataforma-docker-cicd/ci-cd.html)). **O deploy nunca foi executado.**

## Antes de expor a demo

- **Cota e termos da API do Google.** Em geral, o plano **gratuito** pode usar o conteúdo enviado para melhorar produtos, o que **não combina com uploads de planilhas de visitantes**. Confira os termos do plano antes de publicar; a alternativa é um plano pago ou outro provedor.
- **Limite de gasto** no console do provedor, além do teto diário do app (300 análises).
- **Aviso na interface:** já existe (conteúdo enviado ao provedor; arquivos apagados em 30 minutos), mas vale reforçar o texto na página que hospeda a demo.
- **Retenção do Langfuse** se a captura de conteúdo for ligada.

## Testes

```bash
cd 02-agente-planilhas && ../.venv/Scripts/python -m pytest      # 97 testes, nenhum chama um LLM real
```
