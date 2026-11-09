---
title: O servidor (Docker)
order: 4
summary: Os seis serviços, as decisões de segurança, o orçamento de 8 GB de memória e como organizar vários projetos numa instância.
---

## Os seis serviços

O Langfuse 4 não é um programa único: ele pede um conjunto de bancos e filas. O `compose.yml` do `portfolio-langfuse` sobe:

| Serviço | Imagem | Papel | Teto de memória |
|---|---|---|---|
| `langfuse-web` | `langfuse/langfuse:4` | Interface e API que recebe os traces | 1,5 GiB |
| `langfuse-worker` | `langfuse/langfuse-worker:4` | Processa as filas e grava os dados | 1 GiB |
| `clickhouse` | `clickhouse-server:25.12` | Armazena traces, observações e notas (analítico) | 3,5 GiB |
| `postgres` | `postgres:17` | Usuários, projetos, chaves e configuração | 1 GiB |
| `redis` | `redis:7` | Filas e cache (com senha, sem despejo de dados) | 0,5 GiB |
| `minio` | `chainguard/minio` | Armazenamento S3 dos eventos brutos e da mídia | 0,5 GiB |

```
 apps (rede "edge")                          langfuse-web ──► postgres   (usuários, projetos, chaves)
 portfolio-chat ──► http://langfuse-web:3000      │      ├──► clickhouse (traces e observações)
 portfolio-filmes                                 │      ├──► redis      (fila)
 portfolio-planilhas                       langfuse-worker├──► minio      (eventos brutos em S3)
 navegador ──► Caddy ──► langfuse.SEUDOMINIO ─────┘
```

## Decisões de segurança

| Decisão | Por quê |
|---|---|
| **Só o `langfuse-web` entra na rede `edge`**; bancos e filas ficam na rede interna do compose | Postgres, ClickHouse, Redis e MinIO nunca ficam acessíveis para os outros containers nem para a internet |
| **Nenhuma porta publicada** no host (o compose de exemplo do Langfuse publica várias) | Só o Caddy (`portfolio-edge`) escuta no mundo; ele faz o HTTPS |
| **Sem segredos padrão:** toda senha é obrigatória (`${VAR:?...}`) e vem do `.env` | O compose oficial traz `mysalt`, `miniosecret` etc. para facilitar o teste; numa instância pública isso é uma vulnerabilidade |
| **`.env` gerado por `scripts/gen_env.py`** | Segredos aleatórios fortes (hex), permissão 600; **nunca sobrescreve** um `.env` existente sem `--force` (trocar o `ENCRYPTION_KEY` ou as senhas depois do primeiro start quebra o que já foi salvo) |
| **Cadastro aberto desligado** (`AUTH_DISABLE_SIGNUP=true`) | Numa instância pública, qualquer pessoa criaria uma conta; entra só o administrador criado no bootstrap e quem for convidado |
| **Telemetria do Langfuse desligada** | Nada de dados de uso saindo |
| **Mídia não exposta ao navegador** | O MinIO só é usado internamente |
| **Healthchecks e `restart: unless-stopped`** em todos os serviços | O compose só dá `healthy` quando tudo está de pé |

### O que o `.env` contém

O `gen_env.py` gera: `DOMAIN`, `SALT`, `ENCRYPTION_KEY` (64 hex), `NEXTAUTH_SECRET`, as senhas do Postgres, ClickHouse, MinIO e Redis, e o **bootstrap** do primeiro start (organização, projeto, **par de chaves do projeto**, e-mail, nome e senha do administrador). A senha e as chaves aparecem uma vez no terminal. **Guarde o `.env`**: sem o `ENCRYPTION_KEY`, os segredos salvos não abrem.

## O orçamento de memória

A VPS planejada tem 16 GB, e o Langfuse **não pode tomar a memória dos apps**. Por isso cada serviço tem um teto (`mem_limit`) e a **soma é exatamente 8 GiB**:

| Serviço | Teto | Variável para mudar |
|---|---|---|
| ClickHouse | 3,5 GiB | `CLICKHOUSE_MEM` |
| langfuse-web | 1,5 GiB | `WEB_MEM` |
| langfuse-worker | 1 GiB | `WORKER_MEM` |
| Postgres | 1 GiB | `POSTGRES_MEM` |
| Redis | 0,5 GiB | `REDIS_MEM` |
| MinIO | 0,5 GiB | `MINIO_MEM` |
| **Total** | **8 GiB** | |

Os outros 8 GB ficam para os apps (cerca de 2,5 GB de tetos configurados) e o sistema operacional.

`scripts/check_memory_budget.py` lê o `compose.yml` e o `.env`, soma os tetos e **falha (saída 1) se passar do orçamento**: roda no CI e no deploy, então subir um teto no `.env` sem notar derruba o deploy em vez de comer a memória dos apps. O orçamento é configurável (`--budget`).

**Isto é um teto configurado, não consumo medido.** Fontes de terceiros indicam 4 GB e 2 vCPU como mínimo e 8 a 16 GB como recomendado para o Langfuse 3 e 4, e um guia fala em 8 GiB só para o ClickHouse; 8 GiB para tudo é, portanto, **apertado** e pode exigir ajuste depois de medir com `docker stats` sob carga. Se a VPS apertar, o Langfuse Cloud (plano gratuito) em produção, com este Docker só para desenvolvimento, é a saída.

## Um Langfuse para todos os projetos

```
Organização "Portfolio"
 ├─ Projeto portfolio-chat         ← chaves próprias, dados próprios
 ├─ Projeto portfolio-filmes
 ├─ Projeto portfolio-planilhas
 └─ Projeto chatbot                ← o meu outro projeto também cabe aqui
        dentro de cada projeto:  environment · tags · nome do trace · sessão · release · metadata
```

**Não existem subprojetos.** Projeto é o menor nível de isolamento; abaixo dele se agrupa por campos do trace:

| Quero separar... | Use | Exemplo |
|---|---|---|
| Apps diferentes | **Um projeto por app** (recomendado) | `portfolio-chat`, `portfolio-filmes` |
| Produção, desenvolvimento, testes | **environment** (`LANGFUSE_TRACING_ENVIRONMENT`) | `production`, `development`, `portfolio-smoke` |
| Partes de um app | **tags** e **nome do trace** | `chat-turn`, `movie-turn` |
| Conversas | **session_id** | O id da sessão |
| Versões do código | **release** (`PORTFOLIO_RELEASE`) | `v0.3.0` |

**Por que um projeto por app, e não tudo num projeto com uma tag `app`:**
- **Isolamento de chaves.** As chaves do Langfuse também *leem* os dados do projeto. O chat é público e guarda uma chave no servidor; se vazar, só expõe o projeto do chat.
- **Dados com sensibilidade diferente.** As planilhas podem ter trechos de visitantes; o chat tem perguntas sobre currículo. Separados, dá para ter retenção e acesso diferentes.
- **Painéis e custos por app** sem filtros.

**O que se perde:** não há um painel único que some todos os projetos. O bootstrap do `.env` cria só o **primeiro** projeto; os outros são criados na interface (Organização > Projects > New project > Settings > API Keys).

## Local ou VPS

| | Local (`compose.local.yml`) | VPS (`compose.yml`) |
|---|---|---|
| Interface | `http://localhost:3300` (só no seu computador; a porta 3300 evita colidir com outro Langfuse na 3000) | `https://langfuse.SEUDOMINIO` (Caddy) |
| Rede `edge` | Não usada | O `langfuse-web` entra nela |
| Apps enviam traces para | `http://localhost:3300` | `http://langfuse-web:3000` (interno) |
