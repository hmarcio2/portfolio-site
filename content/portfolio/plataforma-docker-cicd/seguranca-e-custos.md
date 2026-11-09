---
title: Segurança e custos
order: 7
summary: O modelo de ameaças de uma demo pública com LLM, as defesas em camadas, o controle de custo e o que ainda está aberto.
---

Uma demo pública com um LLM por trás tem dois riscos que um site comum não tem: **quem usa pode abusar do modelo** (custo, injeção de prompt, extração de dados) e **o conteúdo que o visitante envia é sensível**. Esta página junta o que foi feito, por camada, e o que **não** foi feito.

## Custo: a primeira ameaça

Uma API de LLM cobra por uso, e uma demo pública sem limite pode gerar uma conta alta, por abuso ou por popularidade. As defesas, da mais externa à mais interna:

| Camada | Defesa | Onde |
|---|---|---|
| Provedor | **Limite de gasto no console do provedor** (a rede de segurança; recomendado no `.env.example`) | Fora do código |
| App | **Teto diário global** de mensagens (300 por padrão; zera à meia-noite UTC) | `DailyBudget` |
| App | **Limite por cliente** (10 por minuto; 5 uploads por minuto no analista) | `RateLimiter` |
| App | **Tamanho** da mensagem (1000 caracteres), do histórico (12 mensagens) e do que o modelo vê (30 linhas por consulta nas planilhas) | `Settings`, `tools.py` |
| Modelo | **O mais barato por padrão** (`gemini-flash-lite-latest`) | `DEFAULT_MODELS` |
| Prompt | Recusar o que foge do tema, para não virar um chat genérico às custas do orçamento | Prompt do chat |

**O que falta:** não calculo o **custo por conversa** (há os tokens, não o preço), e o teto diário e os limites vivem **na memória do processo**, então reiniciar o container dá uma cota nova. Há também um risco: **o teto diário é global**: uma pessoa pode esgotá-lo e deixar os outros visitantes sem resposta até a meia-noite.

## Abuso do modelo e do conteúdo

| Ameaça | Defesa | Medição |
|---|---|---|
| Injeção de prompt | O prompt trata contexto e mensagens como dado; recusa mudar de papel | 4 casos de ataque nos 16 da avaliação do chat (passaram) e notas de guardrail |
| Extração do prompt | O prompt manda não revelar; a nota `prompt_leak_suspect` mede vazamento | Idem |
| Link ou número inventado | Prompt, mais as notas `unsupported_links`, `unretrieved_titles` e `unverified_numbers` (esta com **aviso ao usuário**) | Avaliações |
| SQL malicioso (planilhas) | **4 camadas independentes**, com o banco travado | Testes de fuga |
| Falso turno do assistente | Histórico guardado **no servidor** | Testes |
| HTML injetado na tela | Texto inserido como texto (nunca `innerHTML`); Markdown restrito no chat | Revisão e testes |
| Forjar feedback de outra conversa | O servidor só aceita `trace_id` que ele mesmo emitiu para **aquela sessão** | Testes |

Detalhes por projeto: [prompt e proteções do chat](@root/portfolio/chat-do-portfolio/protecoes.html) e [segurança do SQL](@root/portfolio/agente-de-planilhas/seguranca-do-sql.html).

## Dados do visitante

- **Planilhas:** em memória e em `tmpfs`, apagadas em 30 minutos, sem login, o `session_id` como credencial; **o conteúdo que o modelo vê vai ao provedor do LLM** (a interface avisa).
- **Observabilidade:** dados pessoais mascarados, sem IP nem `user_id`, e a captura de conteúdo **desligada** nas planilhas ([Privacidade dos traces](@root/portfolio/observabilidade-langfuse/privacidade.html)).
- **Termos do provedor:** no plano gratuito do Google, em geral, o conteúdo pode ser usado para melhorar produtos. Isso **não combina com aceitar uploads de visitantes**; confira os termos e considere um plano pago antes de expor a demo.

## Infraestrutura

| Item | Estado |
|---|---|
| Containers sem privilégios, somente leitura, sem capabilities, com limite de memória | Feito e testado localmente ([Docker](@root/portfolio/plataforma-docker-cicd/docker.html)) |
| Só o Caddy publica portas; HTTPS automático | Projetado, **não aplicado** |
| Deploy por SSH com usuário sem senha, chave exclusiva e `known_hosts` fixado | Projetado, **não executado** |
| Segredos de LLM só no `.env` da VPS, nunca no GitHub | Projetado |
| Varredura de segredos antes de publicar os repositórios | **Feita** (nenhum segredo publicado) |
| Cadastro desligado no Langfuse, sem segredos padrão | Feito e testado |

## O que não está coberto

- **Sem WAF nem proteção contra DDoS** além do que o Caddy e a VPS oferecem; o limite por IP é por processo, e atrás de NAT muitos visitantes compartilham um IP.
- **Sem autenticação** nas demos (de propósito).
- **Sem monitoramento nem alertas** de uso, de custo ou de erros.
- **Sem revisão de segurança externa** nem teste de intrusão. As defesas foram testadas por mim, com casos que eu imaginei.
- **Dependências:** não há varredura automática de vulnerabilidades (por exemplo, `pip-audit` ou Dependabot) configurada.
- **Imagens:** as bases (`python:3.12-slim`, `nginx-unprivileged`) não são fixadas por *digest*, então um rebuild pode trazer uma versão nova.
