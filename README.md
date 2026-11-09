# Portfólio · Heriberto Márcio

Esta pasta é um **workspace**: a raiz é o repositório do site (`portfolio-site`) e cada subpasta é **um repositório próprio**,
com Docker e CI/CD independentes. Planejamento completo dos projetos em [PROJETOS.md](PROJETOS.md).

| Pasta | Repositório no GitHub | O que é | Estado |
|---|---|---|---|
| `.` (raiz: `build.py`, `content/`, `templates/`, `assets/`) | `portfolio-site` | Site estático gerado de Markdown: home, blog de estudos e portfólio documentado, com widget de chat (nginx) | funcional, 19 testes |
| `_core/` | `portfolio-core` | Biblioteca compartilhada: provedor de LLM (Gemini Flash-Lite por padrão), agente, BM25, limites | funcional, testada |
| `_infra/` | `portfolio-edge` | Caddy (HTTPS) + rede Docker `edge` + passo a passo da VPS | escrito; **não aplicado em VPS** |
| `_langfuse/` | `portfolio-langfuse` | Langfuse self-hosted em Docker (um para todos os projetos), atrás do Caddy | compose validado; **nunca iniciado** (Docker local com falha) |
| `00-site-chat/` | `portfolio-chat` | API do chat com RAG (BM25 medido contra embeddings), em PT/EN | funcional, 75 testes; avaliado com Gemini Flash-Lite (16/16 casos) |
| `01-recomendador-filmes/` | `portfolio-filmes` | Recomendador de filmes (busca híbrida + agente) | funcional, 66 testes (com tracing no Langfuse); catálogos em português (amostra) e inglês (CMU, 5000 filmes); busca por descrição e por filme de exemplo; busca avaliada com 3 embedders; agente testado com Gemini Flash-Lite |
| `02-agente-planilhas/` | `portfolio-planilhas` | Agente analista de planilhas | funcional, 97 testes (com tracing no Langfuse); avaliado com Gemini Flash-Lite (23/24 numéricas; checagem de números inventados) |

O usuário do GitHub nos arquivos é `hmarcio2`; se for outro, troque em `requirements-core.txt`, nos `compose.yml` e nos READMEs.

## O site: home, estudos e portfólio

`build.py` lê o conteúdo em Markdown e gera HTML puro em `dist/` (Jinja2 + Markdown + PyYAML, `requirements-build.txt`). O site usa só caminhos relativos, então abre também direto do disco.

| Página | O que mostra |
|---|---|
| **Home** (`index.html`) | Quem sou (`content/home.md`), resumo do currículo (`content/curriculo.yml`) e os 3 últimos projetos e estudos, preenchidos sozinhos |
| **Estudos** (`estudos/`) | Blog: conceitos, papers, livros e análises dos projetos. Barra lateral por categoria, cards paginados do mais recente ao mais antigo, uma página por categoria e por estudo |
| **Portfólio** (`portfolio/`) | Igual aos estudos, mas cada página é a documentação detalhada de um projeto; `portfolio/roadmap.html` lista os planejados |

A barra de navegação (Home, Estudos, Portfólio) e os links do **LinkedIn** e do **GitHub** ficam no topo de todas as páginas; o chat também. Textos do site que não são conteúdo (nome, links, categorias, tamanho da página, rótulos) ficam em `content/site.yml`.

### Adicionar um estudo ou um projeto

1. Crie `content/estudos/<slug>.md` ou `content/portfolio/<slug>.md` (o nome do arquivo vira o endereço: minúsculas, números e hífens). Arquivos que começam com `_` são ignorados; `draft: true` esconde o texto.
2. Comece com o cabeçalho YAML e escreva o corpo em Markdown (títulos `##`, tabelas, blocos de código):

```markdown
---
title: "Título do texto"
date: 2026-11-15
seq: 1                  # opcional: desempata textos do mesmo dia (maior = mais recente)
category: papers        # estudos: conceitos, papers, livros, analises · portfólio: agentes-rag, observabilidade, plataforma
summary: Uma ou duas frases que aparecem no card.
tags: [RAG, avaliação]
# só no portfólio:
status: local           # planejado, em-construcao, local, no-ar
repo: https://github.com/hmarcio2/portfolio-chat     # só quando o repositório estiver publicado
demo: https://chat.seudominio.com.br                 # idem
---
Texto em Markdown. Para ligar a outra página: [Chat](@root/portfolio/chat-do-portfolio.html)
```
3. `python build.py` (ou `.\dev.ps1`) e confira. Erro de conteúdo (campo faltando, categoria inexistente, data inválida) para a geração e diz qual arquivo corrigir. A home, as listagens, a paginação, as categorias e a barra lateral se atualizam sozinhas; categoria sem textos não aparece.
### Documentar um projeto em várias páginas

Um projeto do portfólio pode ser uma **pasta**, com a documentação dividida em páginas e uma barra lateral própria:

```
content/portfolio/meu-projeto/
├─ index.md          # a visão geral: leva o cabeçalho completo (title, date, category, status, repo, summary, tags)
├─ arquitetura.md    # cada outro .md é uma página da documentação
└─ avaliacao.md
```

```markdown
---
title: Arquitetura
order: 1                 # ordem na barra lateral (depois, o nome do arquivo)
summary: Uma frase; aparece na lista "Documentação completa" da visão geral.
---
## Primeiro título
Corpo em Markdown. Com 3 ou mais títulos `##`, a página ganha o sumário "Nesta página".
Link para outra página do projeto: [avaliação](@root/portfolio/meu-projeto/avaliacao.html)
```

O card do projeto passa a mostrar "N páginas de documentação". Um projeto continua podendo ser um arquivo só (`content/portfolio/meu-projeto.md`).

4. Nova categoria: acrescente em `categories` no `content/site.yml`. Quando um projeto planejado sair do `content/roadmap.md`, crie a página dele.

`python -m pytest` (na raiz do workspace) testa o gerador e confere que todos os links internos do site real resolvem.

## Como as peças se encaixam

```
GitHub (um repositório por projeto)                     VPS Hostinger
  push → CI (testes + build + /health)
  deploy (manual hoje) → build → ghcr.io/hmarcio2/<repo>:sha-…
                       → SSH: compose.yml + trecho do Caddy → docker compose pull/up --wait
                                                            ┌───────────── rede Docker "edge" ─────────────┐
 internet ─► Caddy (portfolio-edge, 80/443) ──────────────► │ site  chat  filmes  planilhas  (um compose cada) │
              seudominio.com      → site:8080  e /api/chat → chat:8000                                      │
              filmes.seudominio   → filmes:8000                                                            │
              planilhas.seudominio→ planilhas:8000                                                         │
                                                            └──────────────────────────────────────────────┘
```

- **Cada projeto é autossuficiente**: o contexto de build é só o repositório. O que antes era irmão virou dependência
  versionada: o `portfolio-core` é instalado por **tag** do GitHub (`requirements-core.txt`), e o CSS base e a base de
  conhecimento do chat foram copiados para dentro dos projetos.
- **Sem editar nada central por projeto**: cada deploy instala o seu próprio trecho de Caddy (`deploy/*.caddy`) na VPS e recarrega o Caddy.
- **Imagens** no GHCR, com tag `sha-<commit>` (para voltar a uma versão) e `latest`.
- **Segredos** das chaves de API ficam só no `.env` de cada app **na VPS**; o GitHub guarda apenas o acesso SSH do deploy.

## Publicar cada projeto (ordem importa)

> **Já publicado em 2026-11-08** (todos públicos, licença MIT, em `github.com/hmarcio2/portfolio-*`; tag `v0.3.0` no core). A seção abaixo fica como roteiro para repetir o processo.

Não rodei `git init` nem enviei nada. Em cada pasta:

```bash
git init -b main && git add . && git commit -m "Primeira versão"
gh repo create hmarcio2/<nome-do-repositório> --public --source . --push     # ou crie no site e use git remote add/push
```

1. **`portfolio-core`** (`_core/`) primeiro, e então a tag: `git tag v0.3.0 && git push --tags`. Os outros repositórios instalam desta tag.
2. `portfolio-chat`, `portfolio-filmes`, `portfolio-planilhas` (o CI deles instala o core pela tag; sem ela, falha).
3. `portfolio-site` (esta raiz), `portfolio-edge` (`_infra/`) e, se for hospedar o Langfuse na VPS, `portfolio-langfuse` (`_langfuse/`; veja o README dele sobre o tamanho da VPS).

Mantenha **todos públicos**. Repositório privado exige token no `pip install` do core (CI e Docker) e no GHCR.
Antes de tornar público, confira que nenhum `.env` ou chave foi commitado (`.gitignore` já ignora `.env`).

## Rodar localmente

**Chat + site com um comando** (PowerShell, na raiz do workspace):

```powershell
.\dev.ps1 -KeyFrom C:\Users\Marcio\Documents\python\Chatbot\.env   # lê só a GOOGLE_API_KEY dali, na memória; nada é copiado
.\dev.ps1                                                          # se já houver um .env com a chave (ou para o modo offline)
.\dev.ps1 -Stop                                                    # encerra a API e o site
```
Gera o site (`dist/`), sobe a API do chat em `http://localhost:8000` e o site em `http://localhost:8080` (abre o navegador). Depois de editar um texto, rode `python build.py` e recarregue. O widget também funciona se você abrir `dist/index.html` direto do disco (`file://`): o script libera o CORS para esse caso, o que **não** deve ser usado em produção. Se aparecer "Não consegui falar com a API do chat", a API não está rodando.

Desenvolvimento sem Docker (venv único no workspace, `.venv/` ignorado pelo git):

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e "_core[langchain,dev]" -r 00-site-chat/requirements.txt -r 01-recomendador-filmes/requirements.txt -r 02-agente-planilhas/requirements.txt pytest pytest-asyncio httpx
```
Cada projeto: `cd <pasta> && ../.venv/Scripts/python -m pytest` e `../.venv/Scripts/python -m uvicorn app.main:create_app --factory --port <porta>`
(detalhes no README de cada um). Chaves em um `.env` na pasta do projeto ou na raiz do workspace (ignorado pelo git).

Com Docker, em cada projeto (o `compose.local.yml` constrói com o `_core` local, sem precisar publicá-lo):

```bash
cp .env.example .env            # preencha GOOGLE_API_KEY
docker compose -f compose.yml -f compose.local.yml up --build
```

## LLM: mesma regra do Chatbot
`LLM_PROVIDER` + `LLM_MODEL` + a chave do provedor escolhem o modelo, sem mudar código. O padrão é o **Gemini Flash-Lite**
(`gemini-flash-lite-latest`); `anthropic`, `openai` e `ollama` também funcionam, e `LOCAL_LLM_ENABLED=true` liga o Ollama como reserva
quando a API falha ou estoura a cota. Sem nenhuma chave, o provedor offline `echo` deixa as interfaces abrirem (sem conversar).
