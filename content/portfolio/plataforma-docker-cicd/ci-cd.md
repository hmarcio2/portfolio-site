---
title: CI/CD e deploy
order: 4
summary: Os workflows de CI e de deploy, os segredos, o rollback e, com franqueza, o que ainda nunca foi executado.
---

> **Estado:** os workflows foram escritos e revisados, mas **nunca rodaram com sucesso**. O CI do GitHub Actions falhou em todos os repositórios porque a conta está com um **bloqueio de cobrança** ("your account is locked due to a billing issue"): os jobs nem iniciam. Tudo abaixo é **projeto não exercitado**, e o primeiro deploy pode revelar defeitos. Os testes e as imagens foram validados **localmente**.

## CI (em todo push e pull request)

| Repositório | Jobs |
|---|---|
| **Apps** (chat, filmes, planilhas) | `test`: instala o core pela tag e as dependências, roda `pytest` (Python 3.12, com cache do pip). `docker`: constrói a imagem **sem publicar** (com cache do GitHub Actions), sobe o container e espera o `/health` responder |
| **`portfolio-core`** | `test` com uma matriz de **Python 3.11 e 3.12** e a verificação de que o pacote **constrói** (`python -m build`) |
| **`portfolio-site`** | `build-site`: instala o gerador, roda os testes (29) e gera o site. `docker`: constrói a imagem e confere que a página inicial responde com o meu nome |
| **`portfolio-langfuse`** | Testes (o gerador de `.env`, o compose e o orçamento de memória) e `docker compose config` |
| **`portfolio-edge`** | Só o deploy (não tem CI) |

O CI de um app **depende de o core estar publicado na tag** do `requirements-core.txt`: sem a tag `v0.3.0`, ele falharia. É um motivo para publicar o core primeiro.

## Deploy (manual por enquanto)

Cada repositório tem um workflow `Deploy` com gatilho `workflow_dispatch` (rodar à mão em Actions > Deploy > Run workflow). Quando a VPS estiver pronta, basta trocar o gatilho por *push* na `main` (há as linhas comentadas). Os passos, num app:

1. **Construir e publicar a imagem** no GHCR com as tags `latest` e `sha-<commit>` (com cache).
2. **Configurar o SSH** com a chave privada do ambiente `production` e o `known_hosts` fixado.
3. **Enviar os arquivos** por SCP: o `compose.yml` para `/opt/apps/<app>/` e o trecho do Caddy para `/opt/edge/routes` (chat) ou `/opt/edge/sites` (filmes, planilhas e Langfuse).
4. **Login temporário no GHCR** na VPS, com o `GITHUB_TOKEN` do job (expira com ele; nada fica salvo).
5. Conferir que existe o **`.env` na VPS** (senão, falha de propósito pedindo para criá-lo).
6. `docker compose pull` e `docker compose up -d --wait --wait-timeout 240 --remove-orphans`, com a `IMAGE_TAG` do commit.
7. **Recarregar o Caddy** (`caddy reload`) para pegar o trecho novo.
8. `docker logout` e `docker image prune`.

O deploy do Langfuse não constrói imagem (usa as oficiais), confere o orçamento de memória e espera até 10 minutos pelo primeiro start. O da borda valida o compose e o Caddyfile (`caddy validate`) antes de recarregar.

### Segredos e variáveis (por repositório, no ambiente `production`)

| Nome | Valor |
|---|---|
| `VPS_HOST` | IP ou hostname da VPS |
| `VPS_USER` | `deploy` (usuário sem senha e sem sudo) |
| `VPS_SSH_KEY` | Chave privada **exclusiva** do CI |
| `VPS_KNOWN_HOSTS` | Saída de `ssh-keyscan` (conferir a impressão digital no painel da Hostinger) |
| variável `VPS_PORT` | Opcional, se o SSH não estiver na 22 |

As chaves de API dos LLMs **não** ficam no GitHub: só no `.env` de cada app **na VPS** (`/opt/apps/<app>/.env`).

### Rollback

Na VPS: `cd /opt/apps/chat && IMAGE_TAG=sha-<commit-antigo> docker compose up -d --wait`. Funciona porque cada deploy publica uma tag `sha-<commit>`.

## Escolhas de segurança do pipeline

- **Permissões mínimas** (`contents: read`; `packages: write` só no deploy).
- **`concurrency`** por app, **sem cancelar** um deploy em andamento: dois deploys do mesmo app não correm juntos.
- **`StrictHostKeyChecking=yes`** com `known_hosts` fixado: evita um ataque de intermediário no SSH.
- **O `GITHUB_TOKEN` do job** para o GHCR em vez de um token pessoal de longa duração.
- **Usuário de deploy sem senha e sem sudo**, só com acesso ao Docker.
- **Ambiente `production`** do GitHub, que permite exigir aprovação manual e guarda os segredos por ambiente.

**Um risco para ter em mente:** quem pode rodar um comando como o usuário `deploy` com acesso ao Docker tem, na prática, poder de `root` na VPS. É um trade-off comum em deploy por SSH.

## O que ainda precisa ser validado

- **O primeiro run verde do CI** em todos os repositórios (depende de resolver o bloqueio de cobrança).
- O **build pelo `docker/build-push-action`** com o cache do GitHub e o **push ao GHCR** (incluindo a visibilidade pública dos pacotes, para a VPS conseguir o `pull`).
- O **deploy completo** por SSH, os trechos do Caddy e a **ordem de primeiro deploy** descrita em [Edge e Caddy](@root/portfolio/plataforma-docker-cicd/edge-caddy.html).
- O **rollback** por tag.
