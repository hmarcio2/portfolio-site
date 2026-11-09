---
title: Operação
order: 5
summary: Subir localmente, subir na VPS, atualizar, fazer backup, configurar retenção e o que cada teste cobre.
---

## Subir localmente

```powershell
cd _langfuse
python scripts\gen_env.py --email voce@exemplo.com          # cria o .env; mostra login, senha e as chaves do projeto (uma vez)
docker compose -f compose.yml -f compose.local.yml pull     # imagem recente: veja Validação
docker compose -f compose.yml -f compose.local.yml up -d --wait
```

Interface em `http://localhost:3300`, com o e-mail e a senha de administrador do `.env` (`LANGFUSE_INIT_USER_EMAIL`, `LANGFUSE_INIT_USER_PASSWORD`). No primeiro start, as migrações do Postgres e do ClickHouse levam alguns minutos. Para um app enviar traces, ponha no `.env` dele:

```
LANGFUSE_PUBLIC_KEY=pk-lf-...        # as que o gen_env.py mostrou
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=http://localhost:3300
```

e confira com o teste de fumaça do app (`python -m evaluation.langfuse_smoke`, em cada projeto). Parar: `docker compose -f compose.yml -f compose.local.yml down` (os dados ficam nos volumes); apagar tudo: `down -v`.

## Subir na VPS (Hostinger)

Pré-requisitos: o [`portfolio-edge`](@root/portfolio/plataforma-docker-cicd/edge-caddy.html) no ar (rede `edge` e Caddy) e um registro DNS `A` para `langfuse.SEUDOMINIO`.

1. Rode `Actions > Deploy` no repositório `portfolio-langfuse`. Na primeira vez ele copia os arquivos e **para pedindo o `.env`**.
2. Na VPS: `cd /opt/apps/langfuse && python3 scripts/gen_env.py --email voce@exemplo.com --domain seudominio.com.br`. Guarde a senha e as chaves que aparecem.
3. Rode o deploy de novo. Ele confere o orçamento de memória, faz `docker compose pull`, sobe tudo (`up -d --wait`, com até 10 minutos de espera para as migrações), instala o trecho do Caddy e recarrega o Caddy.
4. Nos `.env` dos apps na VPS: `LANGFUSE_BASE_URL=http://langfuse-web:3000` e as chaves do **projeto de cada app**.

**Estado:** o modo VPS **nunca foi executado**.

## Atualizar

As tags das imagens são `:4` (a série), mas **o Docker reaproveita a imagem que já está na máquina**. O deploy já faz `docker compose pull` antes de subir; localmente, faça você. Leia as notas de versão do Langfuse antes de subir de série (`:5`) e **faça backup antes**. O Postgres está fixo na `17` (`POSTGRES_VERSION`): trocar de versão maior exige migrar os dados.

Regra que aprendi na prática: **o servidor precisa ser tão novo quanto o SDK** (`langfuse>=5,<6` no core). Confira a versão em `GET /api/public/health` (`"version"`).

## Backup

O que importa são os volumes:

| Volume | Conteúdo | Importância |
|---|---|---|
| `langfuse_postgres_data` | Projetos, chaves e usuários | **Crítico** (sem ele, perde-se a configuração) |
| `langfuse_clickhouse_data` | Traces e notas | Alto (perde-se o histórico) |
| `langfuse_minio_data` | Eventos brutos e mídia | Médio |

Mínimo viável: `docker compose exec postgres pg_dump -U postgres postgres > backup.sql` (projetos e chaves) mais um snapshot da VPS para o resto. **Guarde o `.env`**. Nenhuma rotina de backup foi configurada nem testada.

## Retenção e custo de armazenamento

Os traces crescem com o uso, e o ClickHouse é o que mais cresce. Defina a retenção do projeto na interface se for guardar conversas de visitantes (veja [Privacidade](@root/portfolio/observabilidade-langfuse/privacidade.html)). Para os apps, `LANGFUSE_SAMPLE_RATE` reduz a fração enviada e `LANGFUSE_CAPTURE_CONTENT=false` reduz o tamanho de cada trace.

## Segurança operacional

- A interface é pública em `langfuse.SEUDOMINIO`: senha forte, só convidados, e considere **restringir por IP no Caddy** se só você acessa.
- Os apps **não passam pelo Caddy** para enviar traces; usam a rede interna.
- O trecho do Caddy adiciona `X-Content-Type-Options`, `Referrer-Policy` e `X-Frame-Options` e comprime as respostas.

## Os testes do repositório

24 testes (e 1 ignorado) que **não precisam do Docker**:

- o gerador de `.env`: segredos fortes e únicos, projeto e administrador definidos, não sobrescreve sem `--force`, `.env` com permissão restrita, domínio e nomes personalizados;
- o **compose e o gerador concordam**: toda variável obrigatória do compose é gerada;
- o compose **não publica portas**, só o `langfuse-web` entra na rede `edge`, todo serviço tem teto de memória;
- cadastro desligado por padrão, telemetria desligada e **nenhum segredo padrão inseguro**;
- o `HOSTNAME` do `langfuse-web` é `0.0.0.0` (a regressão do healthcheck);
- o **orçamento de memória**: a soma bate, e estourar um teto faz o script falhar.

No CI, além dos testes, o `docker compose config` valida o arquivo.
