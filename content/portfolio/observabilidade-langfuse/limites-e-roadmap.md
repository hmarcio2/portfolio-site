---
title: Limites e próximos passos
order: 7
summary: O que a observabilidade atual não cobre e o que vem a seguir.
---

## Limites conhecidos

**Da instrumentação**
- **As notas são heurísticas**, com falsos positivos e negativos (veja [Notas](@root/portfolio/observabilidade-langfuse/notas.html)); não há juiz LLM nem validação contra avaliação humana em escala.
- **Mascaramento por padrões:** nomes, endereços e dados descritos em texto livre passam ([Privacidade](@root/portfolio/observabilidade-langfuse/privacidade.html)).
- **O feedback do visitante** só existe no chat (os dois outros apps devolvem o `trace_id` mas a interface não o usa), e é só 👍/👎.
- **Sem custo em dinheiro:** o trace tem tokens, mas o custo por conversa não é calculado.

**Do servidor**
- **8 GiB é apertado** para o Langfuse 4 (as fontes de terceiros recomendam mais); os tetos de memória nunca foram medidos sob carga.
- **Uma única instância**, sem alta disponibilidade, e **sem backup configurado**.
- **O servidor precisa acompanhar o SDK** (o defeito 1); uma atualização do SDK pode exigir uma do servidor.

**De validação**
- **O modo VPS nunca rodou.**
- **Sem tráfego real**, sem painéis e sem prints da interface.

## Próximos passos

- [ ] Tirar prints reais da interface do Langfuse e guardá-los no repositório (o roteiro está pronto).
- [ ] Montar os painéis: taxa semanal de `knowledge_gap`, de `injection_suspect` e de feedback positivo; latência p50 e p95 da `generation`; tokens por dia; taxa de `unretrieved_titles`, `unverified_numbers` e `tool_errors` **por modelo**.
- [ ] Subir na VPS e medir a memória sob carga com `docker stats`; ajustar os tetos ou migrar para o Langfuse Cloud, se apertar.
- [ ] Configurar e **testar** o backup e a restauração do Postgres e do ClickHouse.
- [ ] Um **juiz LLM** (fidelidade ao contexto) e a comparação dele com as heurísticas, nos casos que as heurísticas marcam.
- [ ] Custo por conversa, a partir dos tokens e do preço do modelo.
- [ ] Ligar o feedback do visitante nos outros apps.
- [ ] Um projeto dedicado a **avaliação e observabilidade de LLMs** (o item 11 do roadmap), reaproveitando traces, notas e avaliações já feitos.

## Decisões que valem ser revistas

| Decisão | Motivo atual | Quando mudar |
|---|---|---|
| Langfuse self-hosted | Demonstra operação e dá controle dos dados | Se a VPS apertar: Langfuse Cloud em produção e o Docker só para desenvolvimento |
| Um projeto por app | Isolamento de chaves e de dados | Se um painel único entre apps for mais importante que o isolamento |
| Heurísticas em vez de juiz LLM | Zero custo, reprodutível, auditável | Quando o volume permitir pagar por um juiz e comparar |
| Captura de conteúdo ligada no chat e desligada nas planilhas | Sensibilidade dos dados | Se for preciso depurar o analista de planilhas com conteúdo (com retenção e aviso) |
| Notas enviadas pelo `create_score` do SDK | É a API suportada, com id determinístico | Se o SDK mudar o formato (o servidor tem de acompanhar) |
