---
title: Repositórios e versionamento
order: 1
summary: Por que um repositório por projeto, como a biblioteca compartilhada é versionada por tag, e a ordem e as regras de publicação.
---

## Um repositório por projeto

Cada projeto tem o seu repositório, com **testes, Dockerfile, CI e deploy independentes**. As razões:

- **Independência de deploy:** atualizar o chat não reconstrói o analista de planilhas; cada um tem a sua imagem e o seu ciclo.
- **Vitrine:** cada repositório é uma unidade legível, com README, testes e histórico próprios, que um recrutador abre sem precisar entender um monorepo.
- **Isolamento de dependências:** o analista de planilhas puxa pandas e DuckDB; o chat não precisa.

O custo é a **duplicação controlada** (o CSS base do site e a base de conhecimento do chat foram copiados para dentro dos projetos) e a necessidade de versionar o que é compartilhado, o que leva à biblioteca.

No meu computador, todos ficam numa pasta de trabalho (*workspace*) com um venv único, e cada subpasta tem o seu `.git`; a raiz é o repositório do site, que ignora as subpastas.

## A biblioteca compartilhada, por tag

O que é comum aos apps (provedor de LLM, loop de agente, BM25, sessões, limites, SSE e tracing) está no `portfolio-core`. Os apps **não copiam esse código**: instalam o pacote **pela tag do Git**, num arquivo `requirements-core.txt`:

```
portfolio-core[langchain,langfuse] @ git+https://github.com/hmarcio2/portfolio-core.git@v0.3.0
```

Regras de versão:
- Mudou algo no core? Faça o commit, **crie uma tag nova** (`git tag v0.4.0 && git push --tags`) e atualize o `requirements-core.txt` nos projetos que precisam da mudança.
- Quem não atualizou **continua na tag antiga e não quebra**.
- O repositório do core precisa ser **público**; se ficar privado, o `pip install` do git no CI e no Docker passa a precisar de um token.
- Extras: `langchain` (Gemini e Ollama), `langfuse` (tracing), `dev` (testes).

Hoje, a única tag é `v0.3.0` (a primeira publicada).

## Testar uma mudança do core sem publicar

- Localmente: no projeto, `pip install -e ../_core[langchain]`.
- No Docker: `docker build --build-context core=../_core .`. O `Dockerfile` tem um estágio vazio `FROM scratch AS core` e, se o contexto nomeado `core` existir, instala dali; senão, instala pela tag. O `compose.local.yml` de cada app faz isso (`additional_contexts`).

Foi assim que construí as imagens antes de publicar o core, e é também o que impede o build local de depender do GitHub.

## Ordem de publicação

1. **`portfolio-core`** primeiro, e **a tag**: os outros instalam dela, e o CI deles falha sem ela.
2. `portfolio-chat`, `portfolio-filmes`, `portfolio-planilhas`.
3. `portfolio-site`, `portfolio-edge` e `portfolio-langfuse`.

Foi a ordem seguida em 2026-11-08. Antes do primeiro push, fiz uma **varredura de segredos** em todas as pastas: o único achado foi o `.env` do Langfuse (gerado localmente), que está no `.gitignore` e não foi publicado.

## O que não vai para o repositório

| Item | Por quê |
|---|---|
| `.env` (todos) | Chaves de API e senhas |
| `data/index/` (filmes) | Índice vetorial gerado, 46 MB |
| `data/cmu_movies.csv`, `data/tmdb_movies.csv` | Catálogos grandes, gerados por script (licença CC BY-SA do CMU) |
| `evaluation/results/` | Respostas de avaliações (podem ter conteúdo) |
| `dist/` (site) | Gerado pelo `build.py` |
| `.venv/`, caches | Ambiente local |

## Licença

MIT em todos os repositórios. O catálogo CMU (CC BY-SA) **não** é redistribuído: cada pessoa o gera do original, e o app mostra a atribuição.

## Limitações do modelo

- **Mudanças atravessando repositórios** (uma alteração no core que exige mudar três apps) têm um custo de coordenação: tag, três atualizações de `requirements-core.txt` e três pushes. Para um portfólio de um autor só, o ganho de independência compensa; numa equipe, valeria avaliar um monorepo.
- Os apps ainda têm **cópias** (o catálogo de projetos no chat) que precisam ser sincronizadas à mão; isso está documentado nos READMEs, mas **não há um teste que compare as cópias**, então o esquecimento é um risco real (o chat já respondeu com base num catálogo desatualizado uma vez).
