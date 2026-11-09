---
title: Chat do portfólio (RAG com BM25)
date: 2026-11-01
seq: 1
category: agentes-rag
status: local
repo: https://github.com/hmarcio2/portfolio-chat
summary: Assistente que responde, em português ou inglês, sobre meu currículo e meus projetos, com streaming, guardrails e avaliação com o Gemini Flash-Lite real.
tags: [FastAPI, SSE, RAG, BM25, Gemini, Langfuse]
---

## Objetivo

Um assistente flutuante, presente em todas as páginas deste site, que responde a recrutadores e colegas **só com base** em uma base de conhecimento Markdown (perfil, portfólio, catálogo de projetos). O que não sabe (salário, disponibilidade), ele diz que não sabe e indica o LinkedIn.

## Arquitetura

```
pergunta ─► consulta de busca (última pergunta; + a anterior se for curta: "e a stack?")
         ─► BM25 sobre os trechos Markdown ─► até 5 trechos (≤ 5000 caracteres) ─► prompt de sistema
         ─► LLM (Gemini Flash-Lite por padrão) ─► SSE: meta · sources · delta… · done | error
```

- **API:** `POST /chat` (FastAPI) responde em Server-Sent Events: `meta`, `sources`, `delta`, `done` ou `error`. O widget lê o fluxo e mostra o texto aos poucos, com Markdown seguro (só cria nós DOM, nunca usa `innerHTML`).
- **Base de conhecimento:** arquivos Markdown divididos por título e em trechos de até 1000 caracteres.
- **Histórico no servidor** (12 mensagens, 30 min): o navegador não consegue forjar turnos do assistente.
- **Proteções:** limite por IP, teto diário global, tamanho máximo de mensagem; o prompt trata contexto e mensagens como dados, não revela o prompt e recusa o que foge do tema.
- **LLM configurável** por `LLM_PROVIDER`/`LLM_MODEL` (padrão: Google `gemini-flash-lite-latest`; Ollama local como reserva; provedor `echo` offline sem chave).

## Decisão: BM25 em vez de embeddings

Medi antes de decidir (49 trechos, perguntas em 5 grupos; "acerto@5" = algum trecho esperado entre os 5 enviados ao modelo):

| Estratégia | acerto@5 | MRR |
|---|---|---|
| BM25 (antes de ajustar o conteúdo) | 0,97 | 0,79 |
| Embeddings (`nomic-embed-text`) | 0,97 | 0,72 |
| Híbrida (RRF) | 1,00 | 0,86 |

Como o app envia 5 trechos ao modelo, o que importa é o acerto@5: BM25 e embeddings empatam, e a híbrida só melhora a *ordem*. Para esse tamanho de base, BM25 não custa nada e roda offline. Depois, um caso de **morfologia** ("Onde ele trabalha?" não achava "trabalha atualmente") levou a um *stemming* por prefixo: acerto@5 nesse grupo foi de 0,17 para 1,00.

**Ressalvas:** escrevi as perguntas conhecendo os documentos, e os casos de morfologia foram escritos depois de ver a falha. Os números são otimistas; um teste de regressão trava a qualidade atual. Veja o estudo [RAG na prática](@root/estudos/rag-bm25-embeddings-rrf.html).

## Avaliação ponta a ponta

16 casos com o pipeline completo e o Gemini Flash-Lite real: fatos, "não inventar" (salário, telefone, "trabalhou na Google?"), estado dos projetos, injeção de prompt e fora do tema. **Resultado: 16/16**, com uma execução por caso e checagens por palavra-chave (respostas conferidas à mão). Latência típica de ~1 s. Não testei ataques mais elaborados (injeção multi-turno, em outros idiomas ou escondida nos documentos).

## Observabilidade

Cada turno vira um trace no Langfuse (busca e geração, tokens, latência) com **7 notas automáticas** de guardrails e o feedback "útil / não ajudou" do visitante. Detalhes em [Langfuse self-hosted e evidências](@root/portfolio/observabilidade-langfuse.html) e no estudo [O que medir na observabilidade de um chat com RAG](@root/estudos/observabilidade-de-chat-com-rag.html).

## Limites conhecidos

- O chat só sabe o que está na base; informação desatualizada vira resposta errada. Há testes que checam que não há e-mail ou telefone na base.
- O código está no GitHub, mas não há demo online ainda: roda localmente. O envio de traces e notas foi confirmado contra um Langfuse local (teste de fumaça), mas não há tráfego real nem painéis montados.
- Uma execução por caso na avaliação: a variação entre execuções não foi medida.

## Como rodar

```bash
cd 00-site-chat
../.venv/Scripts/python -m uvicorn app.main:create_app --factory --port 8000
```

Defina `GOOGLE_API_KEY` para usar o Gemini Flash-Lite. Na raiz do workspace, `.\dev.ps1` sobe a API e este site juntos.

## Próximos passos

- Publicar na VPS e medir a variação com mais repetições.
- Prints reais do Langfuse quando o servidor subir.
- Banco vetorial só se a base crescer a ponto de a medição pedir.
