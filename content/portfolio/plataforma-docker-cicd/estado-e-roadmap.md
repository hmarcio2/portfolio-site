---
title: Estado e próximos passos
order: 9
summary: O que foi validado, o que nunca foi exercitado e o caminho até ter tudo no ar.
---

## O que está validado

| Item | Como |
|---|---|
| Testes de todos os repositórios (342) | Rodam localmente; nenhum chama um LLM real |
| Imagens Docker dos quatro componentes | Construídas e rodadas localmente com as restrições de produção: `healthy`, `/health` e rotas principais, sem erros |
| Langfuse | Levantado de verdade, localmente; os testes de fumaça dos três apps passaram |
| Varredura de segredos | Feita antes de publicar |
| Código publicado | Sete repositórios públicos no GitHub, com licença MIT, e a tag `v0.3.0` do core |

## O que nunca foi exercitado

| Item | Por quê / risco |
|---|---|
| **O CI do GitHub Actions** | A conta está com um bloqueio de cobrança; os jobs não iniciam |
| O push das imagens ao GHCR e o `pull` na VPS | Depende do CI e da VPS |
| **O deploy por SSH** | Nunca executado; os workflows podem ter defeitos |
| **A VPS inteira** | DNS, HTTPS, rede `edge`, firewall, usuário de deploy |
| Memória e desempenho **sob carga** | Só medi em repouso |
| Backup e restauração | Não configurados |
| Monitoramento e alertas | Não configurados |
| O provedor Anthropic e o OpenAI | Sem testes (e o OpenAI sem o pacote instalado) |
| Dependências sem varredura de vulnerabilidades | Não configurado |

## Próximos passos, em ordem

1. **Resolver o bloqueio de cobrança do GitHub** e rodar o CI de todos os repositórios: é o primeiro teste real dos workflows.
2. **Preparar a VPS** ([Edge e Caddy](@root/portfolio/plataforma-docker-cicd/edge-caddy.html)) e fazer o **primeiro deploy** na ordem descrita, corrigindo o que quebrar.
3. **Medir a memória sob carga** e ajustar os tetos ([Memória e capacidade](@root/portfolio/plataforma-docker-cicd/memoria-e-capacidade.html)).
4. **Backup e monitoramento:** os certificados do Caddy, o volume do índice dos filmes e os dados do Langfuse; um alerta de uptime, disco e memória.
5. **Automatizar o deploy** (trocar o gatilho manual por *push* na `main`) quando o fluxo manual estiver estável, com a aprovação do ambiente `production`.
6. **Endurecer a cadeia de suprimentos:** `pip-audit` ou Dependabot, e imagens base fixadas por *digest*.
7. **Provedores:** testar o provedor Anthropic e decidir se o OpenAI fica ou sai.
8. **Medir o custo por conversa** e criar alertas de gasto.

## Decisões que valem ser revistas

| Decisão | Motivo atual | Quando mudar |
|---|---|---|
| Um repositório por projeto | Independência de deploy e vitrine | Se a coordenação entre repositórios virar o gargalo |
| Core instalado por tag | Versionamento explícito sem registro de pacotes | Se houver muitos consumidores: publicar no PyPI |
| Deploy manual | Segurança enquanto a VPS não existe | Quando o fluxo estiver estável |
| Uma VPS e um Caddy | Simplicidade e custo | Se a disponibilidade passar a importar |
| Estado em memória nos apps | Uma réplica basta | Mais de uma réplica: Redis |
| Gerador de site próprio | Controle e poucos recursos necessários | Se faltar busca, feed ou imagens otimizadas |
