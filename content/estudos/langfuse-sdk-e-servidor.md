---
title: "Langfuse: o servidor precisa ser tão novo quanto o SDK"
date: 2026-11-01
seq: 7
category: analises
summary: Ao subir o Langfuse de verdade, os traces chegaram mas as notas não, e o healthcheck nunca ficava saudável. As duas causas, como achei e o que mudei.
tags: [Langfuse, Docker, observabilidade, depuração]
---

**Contexto:** até aqui, a instrumentação do [chat](@root/portfolio/chat-do-portfolio.html), do [recomendador](@root/portfolio/recomendador-de-filmes.html) e do [analista de planilhas](@root/portfolio/agente-de-planilhas.html) só tinha sido testada com um exportador em memória. Ao subir o [Langfuse](@root/portfolio/observabilidade-langfuse.html) de verdade, dois defeitos apareceram, e nenhum deles aparecia nos testes automáticos.

## 1. Os traces chegavam, as notas não

O teste de fumaça mostrou as 3 observações no servidor, mas nenhuma das 8 notas. O SDK avisava só "Bad request". No log do servidor: um `ZodError` ("expected object, received array").

**Causa:** o SDK 5.1.0 envia as notas em lote (um array em `POST /api/public/scores`). A imagem `langfuse:4` que o Docker tinha em cache era a **4.30.0**, de oito semanas antes, e só aceitava uma nota por vez. A tag `:4` não é uma versão: o Docker reaproveita o que já está na máquina.

**Correção:** `docker compose pull` (veio a 4.72.0) e as notas passaram a chegar. Fica a regra de que **o servidor precisa ser tão novo quanto o SDK**: rodar o `pull` antes de subir, e ficar de olho no `"version"` do `/api/public/health`.

## 2. O healthcheck ficava `unhealthy` para sempre

Com a imagem nova, o serviço respondia na porta publicada, mas o Docker o marcava como `unhealthy`. O healthcheck chama `127.0.0.1:3000` por dentro do container, e a chamada falhava.

**Causa:** o Next.js escuta no endereço do `HOSTNAME` do container, que o Docker define como o id do container (`5fbcc7d00bc7`), então ele só atendia no IP da rede, não no loopback. A imagem antiga não tinha esse comportamento.

**Correção:** `HOSTNAME: 0.0.0.0` no serviço `langfuse-web`, mais um teste que trava a configuração.

## O que isso diz sobre os meus testes

- O exportador em memória validava **o que o SDK produz**, não **o que o servidor aceita**. Só um servidor de verdade pega incompatibilidade de versão.
- Um aviso genérico ("Bad request") não diz nada; o log do **servidor** foi o que explicou.
- Em Langfuse 4.x no modo "events only", os endpoints antigos de leitura (`/api/public/traces`, `/scores`) respondem "not available". A leitura vai pelo SDK ou pelo `v2/observations`.

## O que continua sem prova

Os testes de fumaça usam provedores roteirizados (sem LLM) e um trace por app. Não há tráfego real, painéis nem a medição de memória sob carga, e o modo VPS (Caddy, HTTPS) não foi testado.
