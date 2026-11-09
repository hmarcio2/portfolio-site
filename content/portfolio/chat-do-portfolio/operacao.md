---
title: Operação
order: 7
summary: Como rodar localmente e em Docker, todas as variáveis de ambiente, o deploy na VPS e como manter a base de conhecimento atualizada.
---

## Rodar localmente

Na raiz do workspace, com o ambiente virtual criado:

```bash
.venv/Scripts/python -m pip install -e "_core[langchain,dev]" -r 00-site-chat/requirements.txt pytest httpx
cd 00-site-chat
../.venv/Scripts/python -m uvicorn app.main:create_app --factory --port 8000
```

Atalho: na raiz do workspace, `.\dev.ps1 -KeyFrom <caminho de um .env>` gera o site, sobe a API na porta 8000 e o site na 8080, e abre o navegador. O `-KeyFrom` lê **só** a `GOOGLE_API_KEY` do arquivo indicado, na memória, sem copiá-la para o disco. `.\dev.ps1 -Stop` encerra os dois. Sem nenhuma chave, o provedor `echo` responde "[modo offline]": serve para ver a interface, não conversa.

## Variáveis de ambiente

As do `portfolio-core` (comuns aos três apps) e as do Langfuse. Valores padrão entre parênteses.

| Variável | Para quê |
|---|---|
| `LLM_PROVIDER` (`auto`) | `google_genai` (o usado nas medições), `anthropic` (implementado em código próprio, mas **sem testes automáticos** e nunca rodado com uma chave real), `ollama`, `echo` (offline) ou `auto` (escolhe pela chave disponível). `openai` existe no código, mas o pacote `langchain-openai` não está nas dependências e o caminho **nunca foi testado** |
| `LLM_MODEL` (vazio) | Vazio usa o mínimo do provedor: `gemini-flash-lite-latest` no Google |
| `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` | Só a do provedor escolhido. **Defina também um limite de gasto no console do provedor** |
| `LLM_TEMPERATURE` (0,3), `PORTFOLIO_MAX_TOKENS` (2000) | Parâmetros da geração |
| `LOCAL_LLM_ENABLED` (`false`), `LOCAL_LLM_MODEL`, `LOCAL_LLM_BASE_URL` | Ollama como reserva quando a API falha ou estoura a cota. Deixe desligado na VPS (sem GPU) |
| `PORTFOLIO_RATE_LIMIT_PER_MINUTE` (10), `PORTFOLIO_DAILY_MESSAGE_CAP` (300) | Limites de uso ([Prompt e proteções](@root/portfolio/chat-do-portfolio/protecoes.html)) |
| `PORTFOLIO_MAX_MESSAGE_CHARS`, `PORTFOLIO_MAX_HISTORY_MESSAGES`, `PORTFOLIO_SESSION_TTL_SECONDS` | Tamanho da pergunta, do histórico e vida da sessão |
| `PORTFOLIO_ALLOWED_ORIGINS` (`http://localhost:8080,...`) | Origens aceitas no CORS |
| `PORTFOLIO_TRUST_PROXY` (`0`) | `1` atrás do Caddy, para ler o IP em `X-Forwarded-For` |
| `PORTFOLIO_KNOWLEDGE_PATHS` | Pastas ou arquivos da base, separados por vírgula (padrão: `knowledge/`) |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` | Ligam o tracing. Na VPS: `http://langfuse-web:3000` |
| `LANGFUSE_TRACING_ENVIRONMENT`, `LANGFUSE_SAMPLE_RATE`, `LANGFUSE_CAPTURE_CONTENT`, `LANGFUSE_ENABLED` | Ambiente, fração enviada, gravar ou não o texto, e interruptor geral |

## Docker

O `Dockerfile` tem dois estágios: o primeiro instala as dependências e o `portfolio-core` num ambiente virtual; o segundo copia só esse ambiente, o código e a base, e roda com um usuário sem privilégios (uid 10001). O `portfolio-core` vem do GitHub, na tag fixada em `requirements-core.txt` (`v0.3.0`); para testar com uma cópia local, o build aceita `--build-context core=../_core`, que é o que o `compose.local.yml` faz.

```bash
cp .env.example .env                      # preencha GOOGLE_API_KEY
docker compose -f compose.yml -f compose.local.yml up --build     # http://localhost:8000
```

**Medido (2026-11-08):** imagem de 271 MB; sobe `healthy` em segundos; **108 MiB de memória em repouso** (teto de 512 MiB no compose); responde `/health` e `/chat` rodando com as restrições de produção do `compose.yml`: sistema de arquivos somente leitura, `cap_drop: ALL`, `no-new-privileges` e `tmpfs` em `/tmp`. Esse teste usou o provedor `echo`, sem LLM real dentro do container.

## Deploy na VPS

O fluxo (manual por enquanto, `workflow_dispatch` no GitHub Actions): construir a imagem, publicar no GHCR com a tag `sha-<commit>` e `latest`, copiar o `compose.yml` e o trecho do Caddy por SSH, rodar `docker compose up --wait` e recarregar o Caddy. O trecho `deploy/chat.caddy` roteia `/api/chat/*` do domínio principal para o container, sem tirar o prefixo da API. Segredos (as chaves de LLM) ficam só no `.env` da VPS (`/opt/apps/chat/.env`); o GitHub guarda apenas o acesso SSH do deploy. Os detalhes estão na [documentação da plataforma](@root/portfolio/plataforma-docker-cicd/ci-cd.html).

**Voltar a uma versão:** na VPS, `cd /opt/apps/chat && IMAGE_TAG=sha-<commit-antigo> docker compose up -d --wait`.

**Estado:** o deploy **nunca foi executado**, nem o build no CI do GitHub (a conta está com um bloqueio de cobrança). Só o build local e a execução em Docker foram validados.

## Manter a base de conhecimento

O chat só sabe o que está em `knowledge/`, e **informação desatualizada vira resposta errada**. Quando algo muda:

1. Atualize o texto em `knowledge/` (`perfil.md`, `profile.en.md`, `portfolio.md`).
2. Se o catálogo de projetos mudou, copie o `PROJETOS.md` do repositório do site para `knowledge/projetos.md`.
3. Atualize a seção "Estado dos projetos" em `portfolio.md` e o comentário no topo (o chat não pode afirmar que algo está no ar se não está).
4. Rode `evaluation.run_retrieval` e os testes: eles checam que não há e-mail ou telefone e que o catálogo não diz "nada foi implementado".
5. Reinicie o container (a base é carregada no start).

Um exemplo real: depois de publicar os repositórios no GitHub, a base ainda dizia que "nenhum projeto está publicado". Tive de corrigi-la para dizer que o **código** está no GitHub mas **nenhum projeto está no ar**. O telefone e o e-mail do currículo **não** estão na base de propósito: o contato é o LinkedIn.

Para descobrir o que falta na base, a lista de notas `knowledge_gap` no Langfuse mostra as perguntas que o assistente não soube responder.

## Testes

```bash
cd 00-site-chat && ../.venv/Scripts/python -m pytest      # 75 testes, nenhum chama um LLM real
```
