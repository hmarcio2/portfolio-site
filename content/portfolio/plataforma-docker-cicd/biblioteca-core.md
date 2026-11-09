---
title: A biblioteca portfolio-core
order: 2
summary: "Os módulos da biblioteca compartilhada: provedores de LLM, loop de agente, BM25, limites, sessões, SSE e tracing, com a API, as decisões e o que está testado."
---

O `portfolio-core` (versão 0.3.0, Python 3.11 ou mais novo) é o que os três apps têm em comum. Dependências obrigatórias: `anthropic` e `python-dotenv`; o resto é opcional (`langchain`, `langfuse`, `dev`). 51 testes, nenhum chama uma API de verdade.

| Módulo | Para quê |
|---|---|
| `config.py` | `Settings` lidas de variáveis de ambiente |
| `llm.py`, `llm_langchain.py` | Provedores de LLM com uma interface única de streaming |
| `agent_loop.py` | Loop de agente com *tool use*, independente de provedor |
| `bm25.py` | Busca lexical em Python puro |
| `guard.py`, `sessions.py`, `sse.py` | Limites de uso, histórico por sessão e eventos SSE |
| `tracing.py` | Log JSON por chamada e o tracer opcional do Langfuse |

## Configuração (`Settings`)

A mesma regra do meu outro projeto de chat: **`LLM_PROVIDER` + `LLM_MODEL` + a chave do provedor** escolhem o modelo, sem mexer em código. Com `LLM_PROVIDER=auto` (o padrão), o provedor é o primeiro disponível: `google_genai` se houver `GOOGLE_API_KEY`; senão `anthropic` se houver `ANTHROPIC_API_KEY`; senão `ollama` se `LOCAL_LLM_ENABLED`; senão `echo` (offline). O modelo padrão é o **mínimo** de cada provedor (`gemini-flash-lite-latest` no Google) para economizar custo. A lista completa de variáveis está em [Operação do chat](@root/portfolio/chat-do-portfolio/operacao.html). `Settings.resolved()` resolve o `auto` e o modelo padrão e é idempotente.

## Provedores de LLM

Todos implementam um único método assíncrono, `stream(system, messages, tools)`, que devolve pedaços (`LLMChunk`): o texto aos poucos e, no último pedaço, `done=True`, o `stop_reason` (`end_turn`, `tool_use`, `max_tokens`, `refusal`), o uso de tokens e, com ferramentas, as chamadas pedidas (`tool_uses`) e o turno completo do assistente num formato opaco do provedor, que o loop devolve sem alterar. Falhas viram `LLMError`.

| Provedor | Como | Estado |
|---|---|---|
| **Google Gemini** (padrão) | LangChain (`init_chat_model`), com limpeza do esquema das ferramentas para o formato do Gemini e mapeamento dos motivos de parada (`SAFETY` e afins viram `refusal`, `MAX_TOKENS` vira `max_tokens`) | **Usado nas medições**; testado com modelos falsos |
| **Ollama** (local) | LangChain | Reserva quando a API falha; testado com modelos falsos |
| **Anthropic** | Cliente nativo, com streaming, *tool use* e o recurso de *fallback* do servidor | Implementado, **sem testes automáticos e nunca rodado com uma chave real** |
| **OpenAI** | LangChain | Existe no código, mas o pacote `langchain-openai` **não está nas dependências** e nunca foi testado |
| **Echo** | Devolve a última mensagem, "[modo offline]" | Para desenvolvimento e testes |
| **Fallback** | `FallbackProvider(primário, reserva)`: se o primário falha **antes de emitir qualquer pedaço**, usa o reserva (por exemplo, o Ollama) | Testado |

Detalhes que importam:
- **Falha no meio da resposta não é reaproveitada** pelo `FallbackProvider`: o usuário já viu texto parcial, e recomeçar com outro modelo daria uma resposta diferente.
- **Conversão de turnos entre provedores:** os blocos de um turno do assistente no formato da Anthropic são convertidos para o formato do LangChain quando a reserva local assume no meio de uma conversa com ferramentas.
- **Tokens:** o uso (entrada, saída e *cache read*) é somado a cada passo do agente.

## Loop de agente (`run_tool_loop`)

A função que roda o ciclo **modelo → ferramenta → modelo**: recebe o provedor, o prompt, o histórico em texto, as definições das ferramentas e uma função `execute(nome, argumentos)`, e devolve eventos (`delta`, `tool`, eventos próprios das ferramentas como `chart` e `movies`, `done` ou `error`; o último é sempre `done` ou `error`).

- **Teto de passos** (8 por padrão): estourar vira um `error` claro em vez de um loop infinito.
- **`execute` roda numa thread** (`asyncio.to_thread`) e **não deve levantar exceções**: erros viram `ToolResult(is_error=True)`, que volta ao modelo para ele se corrigir.
- **Vários `tool_use` no mesmo passo** são todos executados e seus resultados enviados juntos.
- **O turno do assistente volta sem alteração** ao histórico (inclui blocos de raciocínio), exigência de alguns provedores.
- **Recusa e resposta cortada** (`max_tokens` com ferramenta pendente) viram `error` com mensagem para o usuário.
- **`ToolResult`** carrega o texto que o modelo vê, o indicador de erro, **eventos extras** para a interface (gráfico, cartões) e um `meta` de uso do app (por exemplo, o SQL executado).
- **Tracing opcional (`trace=`):** cria uma `generation` por passo e uma observação `tool` por chamada. As mensagens enviadas ao trace usam uma **visão serializável** (o formato opaco do provedor pode não ser JSON), e os resultados de ferramenta são cortados em 1500 caracteres.

Os dois agentes (filmes e planilhas) são só um prompt, as ferramentas e a função `execute`. Há testes com um provedor roteirizado: execução da ferramenta e devolução do resultado, teto de passos, recusa, estrutura do trace, erro de ferramenta e falha do provedor.

## BM25 (`bm25.py`)

Busca lexical em Python puro: `tokenize` (minúsculas, sem acento, sem *stopwords* de português e inglês, com **radical opcional por truncamento**) e `BM25Index` (`k1=1,5`, `b=0,75`).

- **Índice invertido:** a busca só visita os documentos que contêm algum termo da consulta, e pode ser restrita a um subconjunto (`allowed`, usado pelos filtros do recomendador). Mesmo resultado que pontuar todos, mas muito mais rápido com consultas longas: de ~3,5 s para ~0,3 s com a sinopse de um filme como consulta em 5000 documentos, com um teste que compara os dois caminhos.
- **Radical por truncamento:** `prefix=6` junta "trabalha", "trabalhou" e "trabalho". Barato e com colisões; é o que o chat usa.

## Limites, sessões e SSE

- **`RateLimiter`:** janela deslizante por chave (por padrão, 10 eventos por 60 s por cliente); devolve também quantos segundos faltam, para o `Retry-After`. Poda as chaves antigas quando passa de 10 mil.
- **`DailyBudget`:** teto diário global (UTC), que zera sozinho na virada do dia: a **proteção de custo** da API do LLM.
- **`SessionStore`:** histórico **no servidor**, por sessão (TTL de 30 min, 12 mensagens), para o cliente não forjar turnos do assistente; sempre começa por uma fala do usuário; `drop_last` remove o turno órfão quando a resposta falha. Em memória, por enquanto (com mais de um processo seria Redis).
- **`sse_event(nome, dados)`:** formata um evento Server-Sent Events (`event:` e `data:` em JSON, com UTF-8 de verdade).

## Tracing (`tracing.py`)

O tracer opcional do Langfuse, o mascaramento de dados pessoais e o log JSON de cada chamada ao LLM (aplicativo, modelo, latência, tokens e erro) estão descritos em [Instrumentação](@root/portfolio/observabilidade-langfuse/instrumentacao.html) e [Privacidade](@root/portfolio/observabilidade-langfuse/privacidade.html).

## Decisões de projeto

- **Uma interface de streaming para todos os provedores.** Os apps não sabem qual modelo roda; trocar é uma variável de ambiente.
- **Extras opcionais** (`langchain`, `langfuse`), mas o SDK da Anthropic é obrigatório no pacote (`anthropic>=1.0`), mesmo para quem só usa o Gemini: um acoplamento que vale revisar.
- **Falhas como valores, não exceções, nas ferramentas.** O modelo precisa **ver** o erro para se corrigir.
- **Estado em memória.** Simples e suficiente para uma réplica; é um limite conhecido.

## O que está e o que não está testado

| Módulo | Testado |
|---|---|
| Provedor Gemini (LangChain), `FallbackProvider`, resolução do `auto` | Sim, com modelos falsos |
| Provedor Anthropic nativo | **Não** |
| Provedor OpenAI | **Não** (e o pacote não está instalado) |
| `run_tool_loop` | Sim: execução, teto, recusa, tracing, SDK real do Langfuse em memória |
| BM25, limites, sessões, SSE | Sim |
| Tracer do Langfuse e mascaramento | Sim, e o envio foi confirmado contra um servidor local |
