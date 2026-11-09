---
title: Imagens Docker
order: 3
summary: Como as imagens são construídas e endurecidas, os arquivos de compose, o que foi medido ao construí-las e o que o teste local não cobre.
---

## Por repositório

Cada app tem o mesmo conjunto de arquivos:

| Arquivo | Para quê |
|---|---|
| `Dockerfile` | Imagem em **dois estágios**, usuário sem privilégios, `HEALTHCHECK` em `/health` |
| `.dockerignore` | Deixa de fora `.git`, `.venv`, caches, `.env`, `evaluation/results`, `data/index`, `deploy` (e os catálogos grandes, no recomendador) |
| `compose.yml` | **Produção:** puxa a imagem do GHCR, entra na rede `edge`, com as restrições de segurança |
| `compose.local.yml` | **Desenvolvimento:** constrói a imagem com o `portfolio-core` local e publica a porta, sem a rede `edge` |
| `deploy/*.caddy` | O trecho do Caddy que o deploy instala |
| `.env.example` | As variáveis do app |

## O Dockerfile dos apps

```dockerfile
# syntax=docker/dockerfile:1.7
FROM scratch AS core                      # contexto nomeado "core": vazio, a menos que o build o preencha

FROM python:3.12-slim AS builder          # estágio 1: instala as dependências num venv
  ... pip install -r requirements.txt
  ... se houver /core (contexto local) instala dali; senão, pip install -r requirements-core.txt (a tag do GitHub)

FROM python:3.12-slim                     # estágio 2: só o venv, o código e os dados
  useradd --system --uid 10001 app        # usuário sem privilégios
  COPY --from=builder /opt/venv /opt/venv
  COPY --chown=app app ./app ...
  USER app
  HEALTHCHECK ... /health
  CMD uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

- **Dois estágios:** o `git` e as ferramentas de build ficam no primeiro; a imagem final tem só o ambiente virtual pronto e o código.
- **Contexto nomeado `core`:** o repositório é **autossuficiente** (o contexto de build é só ele); o `portfolio-core` vem pela tag. Para testar o core local sem publicar, `--build-context core=../_core` (o `compose.local.yml` faz isso).
- **Usuário `app` (uid 10001)** e nenhum `root` no processo.
- **O `HEALTHCHECK`** chama `/health` com a biblioteca padrão do Python (sem `curl` na imagem). O período de carência varia: 30 s no chat e 90 s no recomendador, que monta o índice no start.
- O **site** usa um Dockerfile diferente: o primeiro estágio roda o `build.py` (Python), e o segundo é o **nginx sem privilégios** (`nginx-unprivileged`), que só copia o HTML gerado.

## O compose de produção

Os containers dos apps rodam assim (as mesmas linhas em chat, filmes e planilhas):

```yaml
read_only: true                  # sistema de arquivos da raiz somente leitura
tmpfs: [/tmp]                    # só /tmp é gravável (e na memória)
cap_drop: [ALL]                  # sem nenhuma capability do Linux
security_opt: [no-new-privileges:true]
mem_limit: 512m                  # o teto de cada app (768m filmes, 1g planilhas, 128m site)
networks: [edge]                 # sem portas publicadas; só o Caddy fala com a internet
```

Diferenças por app:
- **Filmes:** monta o volume `filmes_index` em `/srv/data/index` (o índice não é recalculado a cada deploy) e `./catalog` em `/srv/catalog`, somente leitura, para o catálogo grande opcional.
- **Planilhas:** `/tmp` é um `tmpfs` de **512 MB**, porque os uploads vivem lá e nada pode persistir em disco.
- **Site:** nginx na porta 8080, `read_only`, `mem_limit: 128m`.

## O que foi construído e medido (2026-11-08)

Construí as quatro imagens localmente e as rodei **com exatamente essas restrições** (somente leitura, `cap_drop ALL`, `no-new-privileges`, limite de memória, tmpfs):

| Imagem | Tamanho | Memória em repouso | Teto | Resultado |
|---|---|---|---|---|
| `portfolio-site` | 48,5 MB | n/d | 128 MB | `healthy`; páginas e `chat.js` servidos |
| `portfolio-chat` | 271 MB | 108 MiB | 512 MiB | `healthy`; `/health` e `/chat` (modo offline) |
| `portfolio-filmes` | 354 MB | 217 MiB (**321 MiB** com os 5000 filmes do CMU montados) | 768 MiB | `healthy`; `/info`, a interface e `/chat`; 321 MiB também depois de 3 buscas |
| `portfolio-planilhas` | 476 MB | 170 MiB | 1 GiB | `healthy`; o upload de um CSV passou por pandas, Parquet e DuckDB |

Todos rodaram como `app`, sem erros nos logs, sem OOM e sem reinício.

**Um percalço do ambiente, não do Docker:** no Windows com Git Bash, o caminho `/tmp` e os pontos de montagem eram convertidos para caminhos do Windows (`C:/Program Files/Git/tmp`) e o `docker run` falhava; resolve com `MSYS_NO_PATHCONV=1`. Não afeta o CI nem a VPS (Linux).

**O que esse teste NÃO cobre:**
- **Sem LLM nem embeddings reais** dentro do container (provedor `echo` e embedder de hash): o consumo de memória com um modelo real e com planilhas grandes não foi medido.
- **Sem carga:** são medidas em repouso e depois de poucas requisições.
- **O build via CI do GitHub e o pull do GHCR** nunca ocorreram.
- **Arquitetura:** construí na minha máquina (amd64); a VPS também deve ser amd64, mas não conferi.

## Um defeito encontrado ao construir

O `.dockerignore` do recomendador não excluía os catálogos grandes (`cmu_movies.csv`, `tmdb_movies.csv`), então um build local copiaria um CSV de 7 MB para dentro da imagem (e, no CI, eles nem existem, porque o git os ignora). Corrigi: o catálogo grande **não vai na imagem**, é montado de `./catalog`.

## Decisões

- **Imagens enxutas e sem ferramentas** (sem `curl`, sem `git` na final) reduzem a superfície de ataque e o tamanho.
- **Sistema de arquivos somente leitura com tmpfs** transforma uma invasão que escreva em disco em algo que some ao reiniciar.
- **Um compose por app, sem um único `docker-compose` gigante:** cada deploy só mexe no que é seu.
- **Tags `sha-<commit>` e `latest`:** o `latest` é conveniência; o rollback usa o `sha`.
