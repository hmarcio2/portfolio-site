---
title: Edge e Caddy (a VPS)
order: 5
summary: O proxy único com HTTPS automático, como cada projeto registra a sua rota, como preparar a VPS e a ordem do primeiro deploy.
---

> **Estado:** o `portfolio-edge` foi escrito e o `compose` e o Caddyfile são validados pelo deploy, mas **nada disto foi aplicado numa VPS**. É um roteiro, não um relato.

## A ideia

Numa VPS só, **um único Caddy** escuta nas portas 80 e 443, emite os certificados HTTPS sozinho (Let's Encrypt) e roteia para os containers pela **rede Docker `edge`**, à qual todos os projetos se conectam. Os apps **não publicam portas**: só o Caddy fala com a internet.

O ponto de projeto mais importante: **nenhum projeto edita um arquivo central**. Cada deploy instala o **seu próprio trecho** de Caddy numa pasta e recarrega o Caddy.

| Pasta na VPS | Quem escreve | Exemplo |
|---|---|---|
| `/opt/edge/routes/*.caddy` | Deploy do `portfolio-chat` | `/api/chat/*` no domínio principal |
| `/opt/edge/sites/*.caddy` | Deploy de filmes, planilhas e Langfuse | `filmes.SEUDOMINIO`, `planilhas.SEUDOMINIO`, `langfuse.SEUDOMINIO` |

O domínio principal serve o `portfolio-site` (container `site`, porta 8080).

## O Caddyfile

```
{$DOMAIN} {
    encode zstd gzip
    header { X-Content-Type-Options nosniff; Referrer-Policy strict-origin-when-cross-origin; X-Frame-Options DENY }

    import /etc/caddy/routes/*.caddy      # rotas dos projetos (ex.: /api/chat)

    handle { reverse_proxy site:8080 }    # todo o resto: o site estático
}

import /etc/caddy/sites/*.caddy           # subdomínios dos projetos
```

O `compose.yml` do Caddy (`caddy:2`) publica 80, 443 e 443/udp (HTTP/3), roda com **`cap_drop: ALL` mais `NET_BIND_SERVICE`** (só a capacidade de abrir portas baixas) e `no-new-privileges`. Os volumes `caddy_data` e `caddy_config` guardam os **certificados**: perdê-los obriga a emitir tudo de novo (e há limite de emissões do Let's Encrypt).

## Preparar a VPS (uma vez)

Pressupõe uma VPS Ubuntu da Hostinger com Docker e Compose v2.20 ou mais novo (há um template com Docker no painel).

1. **Usuário de deploy**, sem senha e só com chave SSH, no grupo `docker`, com `/opt/edge` e `/opt/apps` como dono.
2. **Firewall** (`ufw`): só SSH, 80/tcp, 443/tcp e 443/udp.
3. **A chave de deploy** é gerada **no seu computador** (`ssh-keygen -t ed25519`): a pública vai para a VPS, a privada para os segredos do GitHub.
4. **DNS:** registros `A` para o domínio principal e para cada subdomínio (`filmes.`, `planilhas.`, `langfuse.`), apontando para o IP da VPS.
5. **`/opt/edge/.env`** com `DOMAIN=seudominio.com.br`.

## Ordem do primeiro deploy

1. **Edge:** rode `Actions > Deploy edge`. Na primeira vez, o deploy **falha de propósito** se o `/opt/edge/.env` não existir; crie-o e rode de novo.
2. **Site, chat, filmes e planilhas:** em cada um, crie `/opt/apps/<nome>/.env` a partir do `.env.example` e rode `Actions > Deploy`.
3. **Langfuse** (opcional): veja a [operação do Langfuse](@root/portfolio/observabilidade-langfuse/operacao.html).

## Como o tráfego chega a cada app

```
https://seudominio.com.br/              → site:8080
https://seudominio.com.br/api/chat/chat → chat:8000   (o widget chama /api/chat/chat)
https://filmes.seudominio.com.br/       → filmes:8000
https://planilhas.seudominio.com.br/    → planilhas:8000
https://langfuse.seudominio.com.br/     → langfuse-web:3000  (a interface; os apps enviam por http://langfuse-web:3000, interno)
```

Os apps veem o IP do visitante em `X-Forwarded-For` (que o Caddy envia), e por isso rodam com `PORTFOLIO_TRUST_PROXY=1`: sem isso, o limite por cliente enxergaria todos como o IP do proxy.

## Segurança

- **Só o Caddy publica portas**; os apps ficam na rede `edge`.
- Containers dos apps: `read_only`, sem capabilities, `no-new-privileges`, limite de memória.
- O deploy usa um usuário sem senha e sem sudo, uma chave exclusiva para o CI e `StrictHostKeyChecking=yes`.
- O login no GHCR durante o deploy usa o `GITHUB_TOKEN` do job (expira com ele) e é desfeito no fim.
- Cabeçalhos de segurança básicos no domínio principal e no do Langfuse.

## Limites e riscos

- **Um único ponto de falha:** uma VPS, um Caddy. Se o Caddy cair, tudo cai.
- **Sem monitoramento nem alertas** configurados (uptime, disco, memória).
- **Sem backup** do que é estado: os certificados do Caddy, o volume do índice dos filmes e os dados do Langfuse.
- **Recarregar o Caddy** a cada deploy é seguro (`caddy reload` valida antes), mas um trecho inválido de um app pode impedir o recarregamento para todos; o deploy da borda valida, os dos apps não validam antes de enviar.
- **A rede `edge` é compartilhada:** um container comprometido nela alcança os outros que estiverem na mesma rede. A separação é por não publicar portas e por restrições de cada container, não por isolamento de rede entre apps.
